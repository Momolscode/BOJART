"""Evidence-based launch gate for BOJ.ART Jarvis. Read-only; never scans network or controls equipment."""
from __future__ import annotations
import importlib.util, json, platform, shutil
from datetime import datetime, timezone
from pathlib import Path
from diagnostics import collect

REQUIRED_GATES = {
 'cad_runtime': ('CAO paramétrique', 'Créer et relire un modèle sur le PC cible.'),
 'speech_offline': ('Voix locale', 'Microphone, bruit atelier, transcription et interruption testés.'),
 'llm_qualified': ('LLM local', 'Modèle installé, identité et benchmarks français vérifiés.'),
 'jev_contract': ('Jev', 'Contrat Jev testé avec panne, réponse invalide et repli déterministe.'),
 'screen_physical': ('Trois moniteurs', 'Appairage réel, rendu visible, latence et déconnexion vérifiés.'),
 'printer_fdm': ('FDM', 'Une machine réelle qualifiée avec supervision humaine.'),
 'printer_resin': ('Résine', 'Une machine et son post-traitement qualifiés, ventilation et EPI vérifiés.'),
 'production_safety': ('Sécurité', 'Arrêt d’urgence matériel, autorisations, contrôles et risques validés.'),
 'restore_drill': ('Sauvegarde', 'Restauration complète testée sur le PC cible.'),
 'studio_identity': ('Studio vidéo', 'Fidélité des œuvres et droits médias vérifiés sur de vrais rushes.'),
 'social_publish': ('Publication', 'Compte propriétaire, droits, API et accusé public vérifiés.'),
 'site_quotes': ('Site et devis', 'Tunnel de demande et devis réels vérifiés, consentements contrôlés.'),
}


def assessment(store, tower, config, qualified=None):
    """Only the local software checks are marked verified. Never infer hardware qualification."""
    qualified = qualified or {}
    hardware = collect(store.root)
    status = tower.status()
    gates = []
    for key, (label, criterion) in REQUIRED_GATES.items():
        if key == 'cad_runtime':
            installed = importlib.util.find_spec('cadquery') is not None and importlib.util.find_spec('trimesh') is not None
            state = 'available_unqualified' if installed else 'blocked'
            evidence = 'Paquets présents sur cet hôte, modèle réel et imprimante non qualifiés.' if installed else 'Dépendances CAO absentes.'
        elif key == 'screen_physical':
            state = 'unverified'
            evidence = f"{status['browser_views_connected']} vue(s) navigateur locale(s), aucun moniteur physique identifié."
        elif key == 'speech_offline':
            state = 'unverified' if config['voice']['enabled'] else 'blocked'
            evidence = 'Configuration demandée, micro et précision non testés.' if config['voice']['enabled'] else 'Voix désactivée par défaut.'
        elif key == 'llm_qualified':
            state = 'unverified' if config['ollama']['enabled'] else 'blocked'
            evidence = 'LLM configuré mais benchmarks non prouvés.' if config['ollama']['enabled'] else 'LLM désactivé par défaut.'
        else:
            state = 'unverified'
            evidence = 'Aucune qualification de bout en bout sur le PC BOJ.ART.'
        # This is a template for acceptance, NOT a user-editable override that can fake green status.
        gates.append({'id': key, 'label': label, 'state': state, 'criterion': criterion, 'evidence': evidence})
    return {'schema': 'bojart.launch-readiness.v1', 'observed_at': datetime.now(timezone.utc).isoformat(),
            'host_os': platform.system(), 'host_cpu_logical': hardware['cpu_logical_count'],
            'host_ram_gib': hardware['ram_gib'], 'host_nvidia_gpus': hardware['nvidia_gpus'],
            'ffmpeg_present': shutil.which('ffmpeg') is not None,
            'ffprobe_present': shutil.which('ffprobe') is not None,
            'local_software': {'cadquery': importlib.util.find_spec('cadquery') is not None,
                               'trimesh': importlib.util.find_spec('trimesh') is not None,
                               'studio': True, 'growth_drafts': True, 'browser_tower': True,
                               'physical_printer_commands': False, 'jev_connected': False},
            'gates': gates, 'production_ready': False,
            'launch_mode': 'local_demonstration_only',
            'why_not_ready': 'Matériel, sécurité, voix, trois moniteurs, imprimantes, sauvegarde complète et comptes sociaux non qualifiés.',
            'note': 'Diagnostic sur l’hôte exécutant Jarvis, pas sur une tour distante. Aucun scan réseau.'}
