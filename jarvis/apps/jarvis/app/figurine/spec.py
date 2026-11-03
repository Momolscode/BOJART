"""Demande texte (ou transcription) -> spécification structurée de figurine.

Analyse bornée, sans LLM : chaque champ indique s'il vient de la demande ou d'une
hypothèse de simulation. Aucune action physique n'est déduite d'une phrase.
"""
from __future__ import annotations

import re
import unicodedata

SPEC_VERSION = 'bojart.figurine.spec.v1'

# Hypothèses de simulation de la mission du 2 novembre 2026 (pas des réglages de production).
DEFAULTS = {
    'height_mm': 200.0,
    'base_included': True,
    'process': 'FDM',
    'nozzle_mm': 0.4,
    'material': 'PLA',
}

# Personnages tiers : la chaîne accepte la demande mais ne sculpte pas leur ressemblance.
# Un maillage dont la provenance est documentée doit être importé (--mesh).
THIRD_PARTY = {
    'vegeta': {'label': 'Végéta', 'franchise': 'Dragon Ball (Akira Toriyama / Bird Studio, Shueisha, Toei Animation)'},
    'goku': {'label': 'Son Goku', 'franchise': 'Dragon Ball (Akira Toriyama / Bird Studio, Shueisha, Toei Animation)'},
}
ORIGINAL = {
    'sentinelle': {'label': "La Sentinelle de l'atelier", 'franchise': None},
    'ardoise': {'label': 'Ardoise, le duelliste des strates', 'franchise': None},
    'veille': {'label': 'Veille, la gardienne du trait', 'franchise': None},
}
# Noms de personnages qui sont aussi des mots courants (« mets-toi en veille », « la veille de Noël ») :
# ils ne comptent que dans une demande qui parle d'une figurine, et jamais dans ces tournures.
AMBIGUOUS_NAMES = {'veille': re.compile(r"\b(?:en|mode) veille\b|\bla veille (?:de|du|des|d')(?! ?[0-9])")}
# Mots proches d'un nom de personnage : signe probable d'une transcription erronée.
ASR_CONFUSIONS = {
    'vegetal': 'vegeta', 'vegetale': 'vegeta', 'vegetaux': 'vegeta', 'vegetarien': 'vegeta',
    'gecko': 'goku', 'gokou': 'goku',
}
POSES = {
    'iconique': 'iconic', 'stylee': 'iconic', 'style': 'iconic', 'remarquable': 'iconic', 'heroique': 'iconic',
    'combat': 'combat', 'garde': 'combat', 'attaque': 'combat',
    'repos': 'rest', 'debout': 'rest', 'calme': 'rest',
}
UNITS = {'mm': 1.0, 'millimetres': 1.0, 'millimetre': 1.0, 'cm': 10.0, 'centimetres': 10.0,
         'centimetre': 10.0, 'm': 1000.0, 'metre': 1000.0, 'metres': 1000.0}
PHYSICAL = re.compile(r"\b(imprime[sz]?|imprimez|lance[sz]?|lancez|demarre\w*|chauffe\w*|envoie\w*|publie\w*|achete\w*|commande[sz]?)\b(?!\s*-?\s*moi\s+un)")
FIGURINE_WORDS = {'figurine', 'statuette', 'personnage', 'buste', '3d', 'sculpture'}
CREATE_WORDS = {'cree', 'creer', 'genere', 'generer', 'prepare', 'preparer', 'fais', 'faire', 'sculpte', 'modelise', 'veux', 'voudrais', 'aimerais'}


class SpecRejected(ValueError):
    """Demande refusée ou à clarifier, avec un message lisible."""

    def __init__(self, message, status='CLARIFY'):
        super().__init__(message)
        self.status = status


def normalize(text: str) -> str:
    s = unicodedata.normalize('NFD', text.lower())
    s = ''.join(c for c in s if unicodedata.category(c) != 'Mn')
    return re.sub(r'\s+', ' ', s.replace('’', "'")).strip()


def _names(s: str, words: set) -> set:
    """Noms de personnages présents, sans les mots courants ambigus hors d'une demande de figurine."""
    found = words & (set(THIRD_PARTY) | set(ORIGINAL))
    for name, phrase in AMBIGUOUS_NAMES.items():
        if name in found and (not words & FIGURINE_WORDS or phrase.search(s)):
            found.discard(name)
    return found


def is_figurine_request(text: str) -> bool:
    if not isinstance(text, str):
        return False
    s = normalize(text)
    words = set(re.findall(r'[a-z0-9]+', s))
    return bool(words & FIGURINE_WORDS) or bool(_names(s, words))


def _height(s: str):
    hits = re.findall(r'(\d+(?:[.,]\d+)?)\s*(mm|millimetres?|cm|centimetres?|metres?|m)\b', s)
    if not hits:
        if re.search(r"\bun metre\b|\b1 metre\b", s):
            return 1000.0, 'un mètre'
        return None, None
    if len(hits) > 1:
        raise SpecRejected('Plusieurs dimensions dans la demande : précisez la hauteur totale seule.')
    value, unit = hits[0]
    return float(value.replace(',', '.')) * UNITS[unit], f'{value} {unit}'


def parse_request(text: str, *, source: str = 'typed') -> dict:
    """Retourne la spécification ou lève SpecRejected (CLARIFY / REFUSED)."""
    if source not in ('typed', 'voice_transcript', 'fixture'):
        raise SpecRejected('Source de demande inconnue.', 'REFUSED')
    if not isinstance(text, str) or not text.strip() or len(text) > 500:
        raise SpecRejected('Demande vide ou trop longue.', 'REFUSED')
    s = normalize(text)
    if PHYSICAL.search(s):
        raise SpecRejected("Démarrage machine, publication ou achat non disponibles dans cette chaîne. "
                           "Aucune action physique envoyée.", 'REFUSED')
    words = re.findall(r'[a-z0-9]+', s)
    wset = set(words)
    if not wset & CREATE_WORDS:
        raise SpecRejected('Précisez ce que Jarvis doit créer.')

    names = _names(s, wset)
    found = [{'id': k, **THIRD_PARTY[k], 'rights': 'third_party_licensed'} for k in THIRD_PARTY if k in names]
    found += [{'id': k, **ORIGINAL[k], 'rights': 'bojart_original'} for k in ORIGINAL if k in names]
    if len(found) > 1:
        raise SpecRejected('Plusieurs personnages dans la demande (' + ', '.join(c['label'] for c in found)
                           + ') : lequel ? Rien n’est lancé.')
    character = found[0] if found else None
    if character is None:
        suspects = sorted(ASR_CONFUSIONS[w] for w in wset if w in ASR_CONFUSIONS)
        if suspects:
            raise SpecRejected(f"Personnage incertain : vouliez-vous dire « {THIRD_PARTY[suspects[0]]['label']} » ? "
                               "Rien n'est lancé avant confirmation.")
        raise SpecRejected('Quel personnage ? Aucun sujet reconnu dans la demande ; rien n’est lancé.')

    pose_words = [POSES[w] for w in words if w in POSES]
    pose = pose_words[0] if pose_words else 'iconic'
    height, quote = _height(s)
    fields = {}
    if height is None:
        height = DEFAULTS['height_mm']
        fields['height_mm'] = 'hypothèse de simulation'
    else:
        fields['height_mm'] = f'demande : « {quote} »'
    if not 40 <= height <= 1200:
        raise SpecRejected('Hauteur hors du périmètre étudié (40 mm à 1,2 m).', 'REFUSED')
    for key in ('base_included', 'process', 'nozzle_mm', 'material'):
        fields[key] = 'hypothèse de simulation'
    material = DEFAULTS['material']
    if 'resine' in wset:
        material, fields['material'] = 'résine', 'demande'
    elif 'petg' in wset:
        material, fields['material'] = 'PETG', 'demande'

    return {
        'version': SPEC_VERSION,
        'source': source,
        'request_normalized': s,
        'character': character,
        'variant': None if character['rights'] == 'third_party_licensed' else 'v1 — référence BOJ.ART interne',
        'pose_intent': pose,
        'expression': 'déterminée' if pose != 'rest' else 'calme',
        'height_mm': round(height, 3),
        'base_included': DEFAULTS['base_included'],
        'detail_level': 'figurine de vitrine (lisible à 30 cm)',
        'process': 'résine' if material == 'résine' else DEFAULTS['process'],
        'nozzle_mm': None if material == 'résine' else DEFAULTS['nozzle_mm'],
        'material': material,
        'assembly': 'socle séparé, tenons détrompés' if height <= 300 else 'découpe multi-pièces à étudier',
        'field_origin': fields,
        'geometry_source': 'import_required' if character['rights'] == 'third_party_licensed' else 'procedural_sdf',
        'llm_used': False,
        'asr_tested': False,
    }
