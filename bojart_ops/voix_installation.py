"""Voix de Jarvis prête dès l'installation : poids faster-whisper épinglés et réglage local.

Avant ce module, l'installation complète posait les bibliothèques voix mais laissait la voix
éteinte : aucun poids, aucun réglage. Ici, une seule fois et avec l'accord donné à l'installateur :

1. les poids ``small`` retenus par le banc vocal du 2 novembre 2026 (65/80 commandes cibles,
   0 erreur critique) sont téléchargés à leur révision Hugging Face épinglée, puis l'empreinte de
   ``model.bin`` est contrôlée ; un dossier incomplet ou altéré est mis de côté, jamais effacé ;
2. la voix est activée dans la configuration privée ``jarvis/apps/jarvis/config.json`` (ignorée par
   Git). Une configuration existante ne change que dans sa section voix, et seulement si elle ne
   désigne pas déjà des poids présents.

Le micro n'est jamais ouvert ici : la première écoute reste une action de l'utilisateur dans le
navigateur, et la qualité réelle (micro, bruit de l'atelier) reste à mesurer sur la tour.
"""
from __future__ import annotations

from datetime import datetime
import json
import os
from pathlib import Path

from bojart_ops.banc_voix import MODEL_FILES, MODELES, download_model, model_identity

ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / 'jarvis/apps/jarvis'
CONFIG = APP / 'config.json'
EXAMPLE = APP / 'config.example.json'
DEFAULT_MODEL = 'small'
CONFIG_KEYS = {'version', 'ollama', 'voice'}


def home_dir(env=None):
    env = os.environ if env is None else env
    return Path(env.get('USERPROFILE') or env.get('HOME') or Path.home())


def target_dir(name=DEFAULT_MODEL, home=None):
    """One folder per pinned revision: a later choice never overwrites tested weights."""
    spec = MODELES[name]
    return (Path(home) if home else home_dir()) / 'BOJART' / 'modeles' / 'voix' / f'faster-whisper-{name}-{spec["revision"][:8]}'


def weights_status(path, name=DEFAULT_MODEL):
    path = Path(path)
    if not path.is_dir():
        return 'absent'
    prints = model_identity(path)['empreintes']
    if not all(prints.get(f) for f in MODEL_FILES):
        return 'incomplet'
    expected = MODELES[name].get('model_bin_sha256')
    return 'verifie' if not expected or prints['model.bin'] == expected else 'altere'


def _set_aside(path, reason, now=None):
    stamp = f'{(now or datetime.now()):%Y%m%d-%H%M%S}'
    aside = path.with_name(f'{path.name}.{reason}-{stamp}')
    path.rename(aside)
    return aside


def ensure_weights(name=DEFAULT_MODEL, home=None, download=download_model, now=None):
    """Present and verified weights, downloading them once. Returns what happened."""
    if name not in MODELES:
        raise ValueError('Modèle vocal inconnu : ' + name)
    target = target_dir(name, home)
    status = weights_status(target, name)
    if status == 'verifie':
        return {'statut': 'present', 'modele': name, 'dossier': str(target)}
    moved = []
    if target.exists():
        moved.append(str(_set_aside(target, status, now)))
    partial = target.with_name(target.name + '.telechargement')
    if partial.exists():  # download interrupted by a previous run
        moved.append(str(_set_aside(partial, 'interrompu', now)))
    partial.parent.mkdir(parents=True, exist_ok=True)
    download(name, partial)  # refuses a model.bin whose digest differs from the pinned one
    if weights_status(partial, name) != 'verifie':
        raise RuntimeError('Poids vocaux incomplets après téléchargement : ' + str(partial))
    partial.rename(target)
    return {'statut': 'telecharge', 'modele': name, 'dossier': str(target), 'mis_de_cote': moved}


def _voice_ready(voice):
    path = voice.get('model_dir') if isinstance(voice, dict) else None
    return bool(voice.get('enabled')) and bool(path) and all((Path(path) / f).is_file() for f in MODEL_FILES)


def enable_voice(model_dir, config_path=CONFIG, example=EXAMPLE):
    """Turn the voice on in the private configuration, without touching any other setting."""
    config_path, model_dir = Path(config_path), Path(model_dir).resolve()
    existing = config_path.exists()
    config = json.loads((config_path if existing else Path(example)).read_text(encoding='utf-8'))
    if not isinstance(config, dict) or set(config) != CONFIG_KEYS or not isinstance(config.get('voice'), dict):
        raise ValueError(f'Configuration inattendue dans {config_path} : rien n’a été modifié.')
    if _voice_ready(config['voice']):
        return {'statut': 'inchange', 'configuration': str(config_path), 'model_dir': config['voice']['model_dir']}
    config['voice'] = {'enabled': True, 'model_dir': str(model_dir)}
    tmp = config_path.with_name(config_path.name + '.tmp')
    tmp.write_text(json.dumps(config, ensure_ascii=False, indent=2) + '\n', encoding='utf-8', newline='\n')
    os.replace(tmp, config_path)
    return {'statut': 'active' if existing else 'cree', 'configuration': str(config_path), 'model_dir': str(model_dir)}


def prepare(name=DEFAULT_MODEL, home=None, config_path=CONFIG, download=download_model):
    weights = ensure_weights(name, home, download)
    config = enable_voice(weights['dossier'], config_path)
    return {'schema': 'bojart.voix-installation.v1', 'poids': weights, 'configuration': config,
            'micro_ouvert': False, 'qualite_reelle': 'à mesurer sur la tour (micro, bruit, voix réelle)'}
