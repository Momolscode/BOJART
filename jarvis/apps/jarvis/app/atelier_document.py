"""Devis imprimable (A4, enregistrement PDF par le navigateur).

La page lit uniquement le document figé du devis. Le client voit des désignations, des
quantités et des montants HT : le coût de revient, la marge et les taux internes restent
sur la page atelier. Les montants client répartissent le total HT au prorata des coûts,
au centime, et leur somme est exactement le total HT du devis.
"""
from __future__ import annotations

from datetime import date
from decimal import Decimal, ROUND_FLOOR
from html import escape

MOIS = ('janvier', 'février', 'mars', 'avril', 'mai', 'juin', 'juillet', 'août', 'septembre', 'octobre', 'novembre', 'décembre')
PROCEDES = {'FDM': 'impression FDM', 'RESINE': 'impression résine'}
CENT = Decimal('0.01')


def long_date(iso):
    d = date.fromisoformat(iso)
    return f'{d.day} {MOIS[d.month - 1]} {d.year}'


def euros(value):
    whole, cents = f'{Decimal(value):.2f}'.split('.')
    groups = []
    while len(whole) > 3:
        whole, groups = whole[:-3], [whole[-3:]] + groups
    return ' '.join([whole] + groups) + ',' + cents + ' €'


def client_lines(doc):
    """Lignes client : une par pièce, opération et frais, au prorata des coûts, somme exacte."""
    totals = doc.get('totaux')
    if not totals:
        return []
    costs = {}
    for line in doc['lignes']:
        group = 'frais' if line['type'] == 'frais' else 'operation' if line['type'] == 'main_oeuvre' else 'piece'
        costs[(group, line['ref'])] = costs.get((group, line['ref']), Decimal(0)) + Decimal(line['montant_ht'])
    copies = doc['exemplaires']
    rows = []
    for piece in doc['pieces']:
        if ('piece', piece['id']) in costs:
            label = f"{piece['libelle']} — {PROCEDES.get(piece['procede'], piece['procede'])}, {piece['matiere']}"
            rows.append({'ref': piece['id'], 'designation': label, 'quantite': copies * piece['par_exemplaire'], 'unite': 'pièce',
                         'cout': costs[('piece', piece['id'])]})
    for op in doc['operations']:
        if ('operation', op['id']) in costs:
            per_copy = op['par'] == 'exemplaire'
            rows.append({'ref': op['id'], 'designation': op['libelle'], 'quantite': copies if per_copy else 1,
                         'unite': 'exemplaire' if per_copy else 'forfait', 'cout': costs[('operation', op['id'])]})
    for fee in doc['frais']:
        if ('frais', fee['id']) in costs:
            rows.append({'ref': fee['id'], 'designation': fee['libelle'], 'quantite': 1, 'unite': 'forfait', 'cout': costs[('frais', fee['id'])]})
    total = Decimal(totals['total_ht'])
    cost = sum((r['cout'] for r in rows), Decimal(0))
    shares = [(r['cout'] * total / cost) if cost else Decimal(0) for r in rows]
    floors = [s.quantize(CENT, rounding=ROUND_FLOOR) for s in shares]
    left = int((total - sum(floors, Decimal(0))) / CENT)
    # Méthode du plus fort reste : les centimes restants vont aux plus grands restes, à égalité dans l'ordre du devis.
    for index in sorted(range(len(rows)), key=lambda i: (-(shares[i] - floors[i]), i))[:left]:
        floors[index] += CENT
    return [{'ref': r['ref'], 'designation': r['designation'], 'quantite': r['quantite'], 'unite': r['unite'], 'montant_ht': str(amount)}
            for r, amount in zip(rows, floors)]


def watermarks(quote):
    doc, state = quote['document'], quote['etat']
    marks = {'brouillon': 'DOCUMENT DE TRAVAIL — NON ÉMIS', 'remplace': 'VERSION REMPLACÉE — NE PAS UTILISER',
             'expire': 'DEVIS EXPIRÉ', 'refuse': 'DEVIS REFUSÉ'}
    out = [marks[state]] if state in marks else []
    if doc.get('grille', {}).get('origine') == 'exemple':
        out.append('EXEMPLE — NE PAS ENVOYER')
    return out


def render_quote(quote):
    doc = quote['document']
    e = lambda v: escape(str(v), quote=True)
    issued = doc.get('emis_le')
    emitter = doc.get('emetteur')
    parts = ['<!doctype html><html lang="fr"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">',
             f'<title>Devis {e(quote["numero"])} v{e(quote["version"])}</title><link rel="stylesheet" href="/atelier-devis.css"></head><body>',
             '<p class="noprint toolbar"><button type="button" id="print">Imprimer ou enregistrer en PDF</button> <a href="/atelier">Retour à l’atelier</a></p>',
             '<main class="sheet">']
    for mark in watermarks(quote):
        parts.append(f'<p class="watermark">{e(mark)}</p>')
    if emitter:
        lines = [f'<strong>{e(emitter["raison_sociale"])}</strong>', e(emitter['adresse']), 'SIRET ' + e(emitter['siret'])]
        if emitter.get('contact'):
            lines.append(e(emitter['contact']))
        who = '<br>'.join(lines)
    else:
        who = '<strong>Émetteur non déclaré</strong><br>Raison sociale, adresse et SIRET à renseigner dans la grille.'
    parts.append(f'<header class="top"><address class="emitter">{who}</address><div class="meta"><h1>Devis</h1>'
                 f'<p>N° {e(quote["numero"])} · version {e(quote["version"])}</p>'
                 f'<p>{"Établi le " + e(long_date(issued)) if issued else "Calculé le " + e(long_date(doc["date_calcul"]))}</p>'
                 f'<p><strong>Valable jusqu’au {e(long_date(doc["valide_jusqu_au"]))}</strong></p>'
                 + (f'<p>Accepté</p>' if quote['etat'] == 'accepte' else '') + '</div></header>')
    client = e(doc['destinataire']) if doc.get('destinataire') else 'Destinataire renseigné à l’émission.'
    parts.append(f'<section class="client"><h2>Client</h2><p>{client}</p></section>')
    delay = f'{e(doc["delai_jours"])} jours après accord' if doc.get('delai_jours') else 'à préciser'
    reference = f' · Votre demande : {e(doc["reference_demande"])}' if doc.get('reference_demande') else ''
    parts.append(f'<section><h2>Objet</h2><p class="object">{e(doc["titre"])}</p>'
                 f'<p>Exemplaires : {e(doc["exemplaires"])} · Délai de réalisation : {delay}{reference}</p></section>')
    totals = doc.get('totaux')
    if not totals:
        parts.append('<p class="incomplete">Montants incomplets : une estimation ou un tarif manque. Ce document ne peut pas être envoyé.</p>')
    else:
        parts.append('<table class="lines"><thead><tr><th>Désignation</th><th class="num">Quantité</th><th class="num">Montant HT</th></tr></thead><tbody>')
        for line in client_lines(doc):
            unit = line['unite'] + ('s' if line['quantite'] > 1 and line['unite'] != 'forfait' else '')
            parts.append(f'<tr><td>{e(line["designation"])}</td><td class="num">{e(line["quantite"])} {e(unit)}</td>'
                         f'<td class="num">{e(euros(line["montant_ht"]))}</td></tr>')
        parts.append(f'</tbody><tfoot><tr><th colspan="2">Total HT</th><td class="num">{e(euros(totals["total_ht"]))}</td></tr>')
        regime = totals['regime_tva']
        if regime == 'assujetti':
            rate = f'{Decimal(totals["taux_tva"]) * 100:.2f}'.rstrip('0').rstrip('.').replace('.', ',')
            parts.append(f'<tr><th colspan="2">TVA {e(rate)} %</th><td class="num">{e(euros(totals["tva"]))}</td></tr>'
                         f'<tr class="grand"><th colspan="2">Total TTC</th><td class="num">{e(euros(totals["total_ttc"]))}</td></tr>')
        elif regime == 'franchise_293B':
            parts.append(f'<tr class="grand"><th colspan="2">Total à payer</th><td class="num">{e(euros(totals["total_ttc"]))}</td></tr>')
        else:
            parts.append('<tr><th colspan="2">TVA</th><td class="num">Régime à déclarer, TTC non calculé.</td></tr>')
        parts.append('</tfoot></table>')
        if totals.get('mention_tva'):
            parts.append(f'<p class="mention">{e(totals["mention_tva"])}</p>')
    if doc.get('bloquants_emission') and quote['etat'] == 'brouillon':
        items = ''.join(f'<li>{e(b)}</li>' for b in doc['bloquants_emission'])
        parts.append(f'<section class="blocked"><h2>Émission bloquée</h2><ul>{items}</ul></section>')
    parts.append('<section class="accord"><h2>Bon pour accord</h2><p>Date, signature et mention manuscrite « Bon pour accord » :</p>'
                 '<div class="sign"></div></section>')
    parts.append(f'<footer>Document {e(quote["numero"])} v{e(quote["version"])} · empreinte SHA-256 {e(quote["document_sha256"])}</footer>')
    parts.append('</main><script src="/atelier-devis.js"></script></body></html>')
    return ''.join(parts)
