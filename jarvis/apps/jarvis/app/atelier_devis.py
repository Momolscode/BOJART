"""Moteur de devis BOJ.ART : calcul déterministe et explicable, jamais d'envoi.

Le prix suit la convention déjà utilisée par l'Atelier V11 (``calculateQuote``) :
prix HT = coût de revient / (1 − marge − commission). La marge est donc un taux de
marque. Les montants sont des ``Decimal`` ; chaque ligne est arrondie au centime et
les totaux sont la somme des lignes arrondies, pour qu'un document émis s'additionne.

Une valeur manquante n'est jamais remplacée par zéro (``missing_values_are_zero`` du
registre métier). Le calcul reste alors un brouillon incomplet, sans total.
"""
from __future__ import annotations

import hashlib
import json
import math
import re
from datetime import date, timedelta
from decimal import Decimal, ROUND_HALF_UP, InvalidOperation

from core import Rejected

MOTEUR = 'bojart.devis.moteur.v1'
SCHEMA_TARIFS = 'bojart.tarifs.v1'
SCHEMA_ENTREE = 'bojart.devis.entree.v1'
SCHEMA_DEVIS = 'bojart.devis.v1'
PROCEDES = ('FDM', 'RESINE')
SOURCES = ('trancheur', 'geometrique_resine', 'mesure')
CENT = Decimal('0.01')
MENTION_293B = 'TVA non applicable, art. 293 B du CGI'
_ID = re.compile(r'^[a-z0-9][a-z0-9_-]{0,47}$')
_DOSSIER = re.compile(r'^BOJ-[A-Z0-9_-]{2,59}$')
_SHA = re.compile(r'^[0-9a-f]{64}$')


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False)


def digest(value):
    return hashlib.sha256(canonical(value).encode('utf-8')).hexdigest()


def dec(value, name, *, zero=True, maximum=None):
    """Nombre décimal exact. Les flottants passent par leur écriture la plus courte."""
    if type(value) is bool or not isinstance(value, (int, float, str)):
        raise Rejected(f'{name} : nombre attendu.')
    if isinstance(value, float) and not math.isfinite(value):
        raise Rejected(f'{name} : nombre fini attendu.')
    if isinstance(value, str) and not re.fullmatch(r'[0-9]{1,9}(?:\.[0-9]{1,6})?', value.strip()):
        raise Rejected(f'{name} : écrire un nombre positif, point décimal, sans unité.')
    try:
        result = Decimal(str(value).strip())
    except InvalidOperation as exc:
        raise Rejected(f'{name} : nombre illisible.') from exc
    if result < 0 or (not zero and result == 0) or (maximum is not None and result > Decimal(str(maximum))):
        raise Rejected(f'{name} hors limites.')
    return result


def money(value):
    return value.quantize(CENT, rounding=ROUND_HALF_UP)


def text(value, name, maximum=200, *, empty=False):
    if not isinstance(value, str) or any(ord(c) < 32 for c in value):
        raise Rejected(f'{name} : texte sans caractère de contrôle attendu.')
    clean = value.strip()
    if (not clean and not empty) or len(clean) > maximum:
        raise Rejected(f'{name} vide ou trop long.')
    return clean


def keys(raw, name, required, optional=()):
    if not isinstance(raw, dict):
        raise Rejected(f'{name} : objet attendu.')
    missing = set(required) - set(raw)
    extra = set(raw) - set(required) - set(optional)
    if missing or extra:
        detail = (' manquant : ' + ', '.join(sorted(missing)) if missing else '') + (' inconnu : ' + ', '.join(sorted(extra)) if extra else '')
        raise Rejected(f'{name} :{detail}.')
    return raw


# --- Grille tarifaire ------------------------------------------------------------------

def _luhn(digits):
    total = 0
    for index, char in enumerate(reversed(digits)):
        value = int(char) * (2 if index % 2 else 1)
        total += value - 9 if value > 9 else value
    return total % 10 == 0


def siret_ok(number):
    """Clé de contrôle du SIRET, même règle que python-stdnum 2.1 (``stdnum/fr/siret.py``) :
    Luhn sur les 14 chiffres et sur le SIREN ; établissements de La Poste (SIREN 356000000,
    hors siège 35600000000048) : somme des chiffres multiple de 5. Une clé juste détecte une
    faute de frappe ; elle ne prouve pas que l'établissement existe (répertoire SIRENE)."""
    if number.startswith('356000000') and number != '35600000000048':
        return sum(map(int, number)) % 5 == 0
    return _luhn(number) and _luhn(number[:9])


def grid_blockers(tariffs):
    """Ce qui, dans la grille seule, empêche d'émettre un devis."""
    out = []
    if tariffs['tva']['regime'] == 'a_definir':
        out.append('Régime de TVA de BOJ.ART à déclarer (assujetti ou franchise) : total TTC non calculé.')
    if tariffs['origine'] == 'exemple':
        out.append('Grille tarifaire d’exemple : aucun prix réel de BOJ.ART.')
    if 'emetteur' not in tariffs:
        out.append('Identité de l’émetteur (raison sociale, adresse, SIRET) absente.')
    return out


def validate_tariffs(raw):
    keys(raw, 'Grille tarifaire', {'schema', 'version', 'origine', 'devise', 'matieres', 'machines', 'main_oeuvre',
                                    'pertes_matiere', 'provision_reprise', 'marge', 'commission', 'tva', 'validite_jours'},
         {'emetteur', 'declare_par', 'declare_le', 'note'})
    if raw['schema'] != SCHEMA_TARIFS:
        raise Rejected('Grille tarifaire : schéma bojart.tarifs.v1 attendu.')
    if raw['origine'] not in ('exemple', 'declare'):
        raise Rejected('Grille tarifaire : origine exemple ou declare.')
    if raw['origine'] == 'declare' and not (raw.get('declare_par') and raw.get('declare_le')):
        raise Rejected('Une grille déclarée indique qui l’a renseignée et quand.')
    if raw['devise'] != 'EUR':
        raise Rejected('Seul l’euro est pris en charge.')
    out = {'schema': SCHEMA_TARIFS, 'version': text(raw['version'], 'Version de grille', 80), 'origine': raw['origine'],
           'devise': 'EUR', 'matieres': {}, 'machines': {}}
    if not isinstance(raw['matieres'], dict) or len(raw['matieres']) > 64:
        raise Rejected('Matières : au plus 64 entrées.')
    for name, item in raw['matieres'].items():
        text(name, 'Nom de matière', 80)
        keys(item, 'Matière ' + name, {'procede', 'unite', 'prix_ht', 'source'})
        if item['procede'] not in PROCEDES or item['unite'] != ('kg' if item['procede'] == 'FDM' else 'litre'):
            raise Rejected(f'Matière {name} : FDM au kg, résine au litre.')
        out['matieres'][name] = {'procede': item['procede'], 'unite': item['unite'],
                                 'prix_ht': str(dec(item['prix_ht'], 'Prix matière ' + name, zero=False, maximum=100000)),
                                 'source': text(item['source'], 'Source du prix matière', 300)}
    if not isinstance(raw['machines'], dict) or not set(raw['machines']) <= set(PROCEDES):
        raise Rejected('Coût machine par procédé : FDM et/ou RESINE.')
    for proc, item in raw['machines'].items():
        keys(item, 'Machine ' + proc, {'cout_horaire_ht', 'detail'})
        out['machines'][proc] = {'cout_horaire_ht': str(dec(item['cout_horaire_ht'], 'Coût horaire ' + proc, maximum=1000)),
                                 'detail': text(item['detail'], 'Détail du coût machine', 300)}
    keys(raw['main_oeuvre'], 'Main-d’œuvre', {'taux_horaire_ht'})
    out['main_oeuvre'] = {'taux_horaire_ht': str(dec(raw['main_oeuvre']['taux_horaire_ht'], 'Taux horaire', maximum=1000))}
    for field in ('pertes_matiere', 'provision_reprise'):
        if not isinstance(raw[field], dict) or not set(raw[field]) <= set(PROCEDES):
            raise Rejected(f'{field} par procédé : FDM et/ou RESINE.')
        out[field] = {p: str(dec(v, f'{field} {p}', maximum=1)) for p, v in raw[field].items()}
    marge = dec(raw['marge'], 'Marge', maximum='0.95')
    commission = dec(raw['commission'], 'Commission', maximum='0.95')
    if marge + commission >= 1:
        raise Rejected('La somme marge + commission doit être inférieure à 100 %.')
    out['marge'], out['commission'] = str(marge), str(commission)
    keys(raw['tva'], 'TVA', {'regime'}, {'taux'})
    regime = raw['tva']['regime']
    if regime not in ('assujetti', 'franchise_293B', 'a_definir'):
        raise Rejected('Régime de TVA : assujetti, franchise_293B ou a_definir.')
    if regime == 'assujetti':
        out['tva'] = {'regime': regime, 'taux': str(dec(raw['tva'].get('taux'), 'Taux de TVA', zero=False, maximum='0.30'))}
    else:
        if 'taux' in raw['tva']:
            raise Rejected('Un taux de TVA n’a de sens que pour un régime assujetti.')
        out['tva'] = {'regime': regime}
    days = raw['validite_jours']
    if type(days) is not int or not 1 <= days <= 365:
        raise Rejected('Durée de validité : 1 à 365 jours.')
    out['validite_jours'] = days
    if 'emetteur' in raw:
        e = keys(raw['emetteur'], 'Émetteur', {'raison_sociale', 'adresse', 'siret'}, {'contact'})
        siret = text(e['siret'], 'SIRET', 14)
        if not re.fullmatch(r'[0-9]{14}', siret):
            raise Rejected('SIRET : 14 chiffres.')
        if not siret_ok(siret):
            raise Rejected('SIRET : clé de contrôle invalide, vérifier la saisie.')
        out['emetteur'] = {'raison_sociale': text(e['raison_sociale'], 'Raison sociale', 160),
                           'adresse': text(e['adresse'], 'Adresse', 300), 'siret': siret}
        if 'contact' in e:
            out['emetteur']['contact'] = text(e['contact'], 'Contact', 160)
    for field in ('declare_par', 'declare_le', 'note'):
        if field in raw:
            out[field] = text(raw[field], field, 500)
    return out


# --- Demande de chiffrage ---------------------------------------------------------------

def validate_input(raw):
    keys(raw, 'Demande de chiffrage', {'schema', 'dossier_id', 'titre', 'exemplaires', 'pieces'},
         {'operations', 'frais', 'delai_jours', 'reference_demande', 'notes'})
    if raw['schema'] != SCHEMA_ENTREE:
        raise Rejected('Demande de chiffrage : schéma bojart.devis.entree.v1 attendu.')
    if not isinstance(raw['dossier_id'], str) or not _DOSSIER.fullmatch(raw['dossier_id']):
        raise Rejected('Dossier BOJ-… requis.')
    copies = raw['exemplaires']
    if type(copies) is not int or not 1 <= copies <= 10000:
        raise Rejected('Exemplaires : entier de 1 à 10 000.')
    out = {'schema': SCHEMA_ENTREE, 'dossier_id': raw['dossier_id'], 'titre': text(raw['titre'], 'Titre', 160),
           'exemplaires': copies, 'pieces': [], 'operations': [], 'frais': []}
    if not isinstance(raw['pieces'], list) or not 1 <= len(raw['pieces']) <= 200:
        raise Rejected('Entre 1 et 200 pièces.')
    seen = set()

    def ident(value, kind):
        if not isinstance(value, str) or not _ID.fullmatch(value) or (kind, value) in seen:
            raise Rejected(f'Identifiant de {kind} invalide ou dupliqué.')
        seen.add((kind, value))
        return value

    for piece in raw['pieces']:
        keys(piece, 'Pièce', {'id', 'libelle', 'procede', 'matiere', 'par_exemplaire'}, {'estimation'})
        if piece['procede'] not in PROCEDES:
            raise Rejected('Procédé de pièce : FDM ou RESINE.')
        per = piece['par_exemplaire']
        if type(per) is not int or not 1 <= per <= 1000:
            raise Rejected('Quantité par exemplaire : entier de 1 à 1000.')
        item = {'id': ident(piece['id'], 'pièce'), 'libelle': text(piece['libelle'], 'Libellé de pièce', 120),
                'procede': piece['procede'], 'matiere': text(piece['matiere'], 'Matière', 80), 'par_exemplaire': per,
                'estimation': None}
        est = piece.get('estimation')
        if est is not None:
            keys(est, 'Estimation', {'source', 'temps_machine_s'}, {'matiere_g', 'matiere_ml', 'fichier_sha256', 'reference', 'marque_simulation'})
            if est['source'] not in SOURCES:
                raise Rejected('Source d’estimation : trancheur, geometrique_resine ou mesure.')
            if piece['procede'] == 'FDM' and est['source'] == 'geometrique_resine':
                raise Rejected('Une pièce FDM demande un tranchage : le temps dépend du parcours d’outil.')
            quantity_key = 'matiere_g' if piece['procede'] == 'FDM' else 'matiere_ml'
            if quantity_key not in est:
                raise Rejected(f'Estimation : {quantity_key} requis pour une pièce {piece["procede"]}.')
            clean = {'source': est['source'],
                     'temps_machine_s': str(dec(est['temps_machine_s'], 'Temps machine', zero=False, maximum=30 * 86400)),
                     quantity_key: str(dec(est[quantity_key], 'Quantité de matière', zero=False, maximum=1_000_000))}
            if 'fichier_sha256' in est:
                if not isinstance(est['fichier_sha256'], str) or not _SHA.fullmatch(est['fichier_sha256']):
                    raise Rejected('Empreinte de fichier : SHA-256 hexadécimal.')
                clean['fichier_sha256'] = est['fichier_sha256']
            if 'reference' in est:
                clean['reference'] = text(est['reference'], 'Référence d’estimation', 200)
            if est.get('marque_simulation') is True:
                clean['marque_simulation'] = True
            item['estimation'] = clean
        out['pieces'].append(item)
    for op in raw.get('operations', []):
        keys(op, 'Opération', {'id', 'libelle', 'heures', 'par'})
        if op['par'] not in ('lot', 'exemplaire'):
            raise Rejected('Opération : par lot ou par exemplaire.')
        out['operations'].append({'id': ident(op['id'], 'opération'), 'libelle': text(op['libelle'], 'Libellé d’opération', 120),
                                  'heures': str(dec(op['heures'], 'Heures', zero=False, maximum=10000)), 'par': op['par']})
    for fee in raw.get('frais', []):
        keys(fee, 'Frais', {'id', 'libelle', 'montant_ht'})
        out['frais'].append({'id': ident(fee['id'], 'frais'), 'libelle': text(fee['libelle'], 'Libellé de frais', 120),
                             'montant_ht': str(dec(fee['montant_ht'], 'Montant de frais', maximum=1_000_000))})
    if len(out['operations']) > 50 or len(out['frais']) > 50:
        raise Rejected('Au plus 50 opérations et 50 frais.')
    if 'delai_jours' in raw:
        if type(raw['delai_jours']) is not int or not 1 <= raw['delai_jours'] <= 365:
            raise Rejected('Délai : 1 à 365 jours.')
        out['delai_jours'] = raw['delai_jours']
    for field, size in (('reference_demande', 80), ('notes', 2000)):
        if field in raw:
            out[field] = text(raw[field], field, size, empty=True)
    return out


# --- Calcul ---------------------------------------------------------------------------

def compute(entry, tariffs, *, today=None):
    """Calcule un brouillon. ``today`` fixe la date pour la reproductibilité."""
    entry = validate_input(entry)
    tariffs = validate_tariffs(tariffs)
    today = today or date.today()
    if not isinstance(today, date):
        raise Rejected('Date de calcul invalide.')
    lines, missing, hypotheses = [], [], []
    copies = Decimal(entry['exemplaires'])
    machine_hours = Decimal(0)

    def add(kind, ref, label, basis, amount):
        lines.append({'type': kind, 'ref': ref, 'libelle': label, 'base': basis, 'montant_ht': str(money(amount))})

    for p in entry['pieces']:
        proc, est = p['procede'], p['estimation']
        qty = copies * p['par_exemplaire']
        if est is None:
            missing.append({'ref': p['id'], 'manque': 'estimation', 'detail': 'Trancher la pièce (FDM) ou estimer sa géométrie (résine).'})
            continue
        if est['source'] != 'mesure':
            hypotheses.append({'ref': p['id'], 'nature': est['source'], 'detail': 'Estimation, pas une mesure d’impression.'})
        if est.get('marque_simulation'):
            hypotheses.append({'ref': p['id'], 'nature': 'profil_simulation', 'detail': 'Tranché avec un profil de simulation non vérifié.'})
        material = tariffs['matieres'].get(p['matiere'])
        machine = tariffs['machines'].get(proc)
        loss = tariffs['pertes_matiere'].get(proc)
        reprint = tariffs['provision_reprise'].get(proc)
        for value, name in ((material, 'prix de la matière ' + p['matiere']), (machine, 'coût horaire ' + proc),
                            (loss, 'pertes matière ' + proc), (reprint, 'provision de reprise ' + proc)):
            if value is None:
                missing.append({'ref': p['id'], 'manque': 'tarif', 'detail': name.capitalize() + ' absent de la grille.'})
        if material is not None and material['procede'] != proc:
            raise Rejected(f'Matière {p["matiere"]} prévue pour {material["procede"]}, pas pour {proc}.')
        hours = Decimal(est['temps_machine_s']) / 3600
        machine_hours += hours * qty
        if None in (material, machine, loss, reprint):
            continue
        if proc == 'FDM':
            kilos = Decimal(est['matiere_g']) / 1000
            used = kilos * qty * (1 + Decimal(loss))
            mat_cost = used * Decimal(material['prix_ht'])
            basis = f'{est["matiere_g"]} g × {qty} × (1 + {loss} pertes) × {material["prix_ht"]} €/kg'
        else:
            litres = Decimal(est['matiere_ml']) / 1000
            used = litres * qty * (1 + Decimal(loss))
            mat_cost = used * Decimal(material['prix_ht'])
            basis = f'{est["matiere_ml"]} ml × {qty} × (1 + {loss} pertes) × {material["prix_ht"]} €/L'
        machine_cost = hours * qty * Decimal(machine['cout_horaire_ht'])
        add('matiere', p['id'], f'{p["libelle"]} — matière {p["matiere"]}', basis, mat_cost)
        add('machine', p['id'], f'{p["libelle"]} — temps machine {proc}',
            f'{money(hours)} h × {qty} × {machine["cout_horaire_ht"]} €/h', machine_cost)
        add('reprise', p['id'], f'{p["libelle"]} — provision de reprise', f'{reprint} × (matière + machine)',
            (mat_cost + machine_cost) * Decimal(reprint))
    labour_hours = Decimal(0)
    rate = Decimal(tariffs['main_oeuvre']['taux_horaire_ht'])
    for op in entry['operations']:
        hours = Decimal(op['heures']) * (copies if op['par'] == 'exemplaire' else 1)
        labour_hours += hours
        add('main_oeuvre', op['id'], op['libelle'], f'{money(hours)} h × {rate} €/h', hours * rate)
    for fee in entry['frais']:
        add('frais', fee['id'], fee['libelle'], 'montant déclaré', Decimal(fee['montant_ht']))
    regime = tariffs['tva']['regime']
    blockers = [m['detail'] for m in missing] + grid_blockers(tariffs)
    if 'delai_jours' not in entry:
        blockers.append('Délai de réalisation à indiquer.')
    if any(h['nature'] == 'profil_simulation' for h in hypotheses):
        blockers.append('Estimation issue d’un profil de simulation : retrancher avec le profil réel de la machine.')
    totals = None
    if not missing:
        cost = sum((Decimal(line['montant_ht']) for line in lines), Decimal(0))
        rate_sum = Decimal(tariffs['marge']) + Decimal(tariffs['commission'])
        price = money(cost / (1 - rate_sum))
        margin = price - cost
        tax = money(price * Decimal(tariffs['tva']['taux'])) if regime == 'assujetti' else Decimal(0)
        known = regime != 'a_definir'
        totals = {'cout_revient_ht': str(cost), 'marge_et_commission_ht': str(margin), 'total_ht': str(price),
                  'tva': str(tax) if known else None, 'total_ttc': str(price + tax) if known else None,
                  'regime_tva': regime, 'prix_unitaire_ht': str(money(price / copies)),
                  'formule': 'total HT = coût / (1 − marge − commission)',
                  'mention_tva': MENTION_293B if regime == 'franchise_293B' else None}
        if regime == 'assujetti':
            totals['taux_tva'] = tariffs['tva']['taux']
    computation = {'moteur': MOTEUR, 'entree_sha256': digest(entry), 'tarifs_sha256': digest(tariffs)}
    document = {
        'schema': SCHEMA_DEVIS, 'statut': 'brouillon', **computation,
        'calcul_sha256': digest({**computation, 'date': today.isoformat()}),
        'date_calcul': today.isoformat(), 'valide_jusqu_au': (today + timedelta(days=tariffs['validite_jours'])).isoformat(),
        'dossier_id': entry['dossier_id'], 'titre': entry['titre'], 'exemplaires': entry['exemplaires'],
        'reference_demande': entry.get('reference_demande'), 'delai_jours': entry.get('delai_jours'),
        'grille': {'version': tariffs['version'], 'origine': tariffs['origine']}, 'emetteur': tariffs.get('emetteur'),
        'pieces': entry['pieces'], 'operations': entry['operations'], 'frais': entry['frais'],
        'lignes': lines, 'totaux': totals, 'heures_machine': str(money(machine_hours)), 'heures_main_oeuvre': str(money(labour_hours)),
        'manques': missing, 'hypotheses': hypotheses, 'bloquants_emission': blockers,
        'emettable': not blockers, 'envoye': False,
        'note': 'Brouillon calculé localement. L’émission fige une version ; l’envoi au client reste une action humaine.',
    }
    return document
