#!/usr/bin/env python3
"""Banc de la chaîne vocale Jarvis : « Affiche le dashboard atelier » de l'audio au reçu.

Sous-commandes :
  corpus   génère un corpus de prises (synthèse Piper, bruit d'atelier, code navigateur réel via Node) ;
  mesurer  rejoue le corpus sur le vrai serveur avec le vrai moteur faster-whisper et mesure chaque étape ;
  bruit    rejoue des flux sans parole et vérifie que la reconnaissance n'invente aucune commande ;
  comparer compare deux rapports (par exemple ce conteneur et la tour) étape par étape ;
  modele   télécharge explicitement un modèle faster-whisper épinglé et vérifie son empreinte.

Aucun ordre physique, aucun service distant hors téléchargement explicite du modèle.
Un rapport existant n'est jamais écrasé.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from bojart_ops import banc_voix, voix_corpus  # noqa: E402


def _output(path, label, fallback, prefix):
    """Fichier donné, ou dossier : nom horodaté. Jamais d'écrasement."""
    output = Path(path)
    if output.is_dir() or path.endswith(('/', '\\')):
        stamp = datetime.now().strftime('%Y%m%d-%H%M%S')
        name = re.sub(r'[^a-z0-9]+', '-', (label or fallback).lower()).strip('-')
        output = output / f'{prefix}-{name}-{stamp}.json'
    if output.exists() or output.with_suffix('.md').exists():
        raise SystemExit('Rapport existant : choisir un nouveau nom.')
    return output, output.with_suffix('.md')


def _progress(position, total, result):
    if position == total or position % 10 == 0:
        print(f'  {position}/{total} prises — dernière : {result.get("clip")} → {result.get("classement")}',
              flush=True)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    commands = parser.add_subparsers(dest='commande', required=True)

    corpus = commands.add_parser('corpus', help='générer un corpus de prises vocales')
    corpus.add_argument('--sortie', required=True, help='dossier neuf du corpus (hors du dépôt)')
    corpus.add_argument('--piper', required=True, help='exécutable piper (piper-tts)')
    corpus.add_argument('--voix', required=True, help='dossier des voix Piper .onnx/.onnx.json')
    corpus.add_argument('--locuteurs', nargs='*', choices=sorted(voix_corpus.VOICES), help='sous-ensemble de voix')
    corpus.add_argument('--node', default='node')

    measure = commands.add_parser('mesurer', help='mesurer la chaîne vocale sur un corpus')
    measure.add_argument('--corpus', required=True)
    measure.add_argument('--modele', required=True, help='dossier faster-whisper (model.bin, config.json, tokenizer.json)')
    measure.add_argument('--sortie', required=True,
                         help='rapport JSON neuf, ou dossier (nom horodaté) ; un .md est écrit à côté')
    measure.add_argument('--libelle', help='nom lisible de la mesure (ex. « tour small »)')
    measure.add_argument('--sans-langgraph', action='store_true', help='forcer le repli sur les règles locales')
    measure.add_argument('--variante', choices=sorted(banc_voix.VARIANTES), default='runtime',
                         help='paramètres de décodage ajoutés à voice.py, pour comparaison uniquement')
    measure.add_argument('--limite', type=int, help='ne rejouer que les N premières prises')
    measure.add_argument('--froids', type=int, default=3, help='démarrages à froid mesurés')
    measure.add_argument('--sans-scenarios', action='store_true')

    probe = commands.add_parser('bruit', help='bruit seul : vérifier qu’aucune commande n’est inventée')
    probe.add_argument('--modele', required=True)
    probe.add_argument('--sortie', required=True, help='rapport JSON neuf, ou dossier (nom horodaté) ; un .md à côté')
    probe.add_argument('--graines', type=int, default=8, help='flux par condition et par niveau')
    probe.add_argument('--libelle')
    probe.add_argument('--node', default='node')

    comparison = commands.add_parser('comparer', help='comparer deux rapports')
    comparison.add_argument('reference')
    comparison.add_argument('autre')
    comparison.add_argument('--sortie', help='fichier Markdown neuf')

    model = commands.add_parser('modele', help='télécharger un modèle épinglé (accord explicite)')
    model.add_argument('--nom', required=True, choices=sorted(banc_voix.MODELES))
    model.add_argument('--dossier', required=True)
    model.add_argument('--je-confirme-le-telechargement', action='store_true', required=True)

    args = parser.parse_args(argv)
    if args.commande == 'corpus':
        manifest = voix_corpus.generate(args.sortie, args.piper, args.voix, args.locuteurs, node=args.node)
        print(f"Corpus : {len(manifest['clips'])} prises dans {args.sortie}")
        return 0
    if args.commande == 'mesurer':
        output, markdown_path = _output(args.sortie, args.libelle, Path(args.modele).name, 'banc-voix')
        report = banc_voix.run(args.corpus, args.modele, output, langgraph=not args.sans_langgraph,
                               variante=args.variante, limit=args.limite, repetitions_froid=args.froids,
                               with_scenarios=not args.sans_scenarios, label=args.libelle, progress=_progress)
        with open(markdown_path, 'x', encoding='utf-8') as handle:
            handle.write(banc_voix.markdown(report))
        summary = report['synthese']
        failed = [s['nom'] for s in report['scenarios'] if not s['reussi']]
        print(f"Rapport : {output} et {markdown_path}")
        print(f"Erreurs critiques : {summary['erreurs_critiques']} ; cas d'erreur non conformes : {failed or 'aucun'}")
        return 1 if summary['erreurs_critiques'] or failed else 0
    if args.commande == 'bruit':
        output, markdown_path = _output(args.sortie, args.libelle, Path(args.modele).name, 'bruit-seul')
        report = banc_voix.noise_probe(args.modele, output, seeds=args.graines, node=args.node, label=args.libelle,
                                       progress=_progress)
        with open(markdown_path, 'x', encoding='utf-8') as handle:
            handle.write(banc_voix.noise_markdown(report))
        invented = {name: data['commandes_declenchees'] for name, data in report['synthese'].items()}
        print(f"Rapport : {output} et {markdown_path}")
        print(f"Commandes déclenchées par du bruit seul : {invented}")
        return 1 if any(invented.values()) else 0
    if args.commande == 'comparer':
        reference = json.loads(Path(args.reference).read_text(encoding='utf-8'))
        other = json.loads(Path(args.autre).read_text(encoding='utf-8'))
        text = banc_voix.compare_markdown(banc_voix.compare(reference, other))
        if args.sortie:
            with open(args.sortie, 'x', encoding='utf-8') as handle:
                handle.write(text)
        print(text)
        return 0
    if args.commande == 'modele':
        identity = banc_voix.download_model(args.nom, args.dossier)
        print(json.dumps(identity, ensure_ascii=False, indent=1))
        return 0
    return 2


if __name__ == '__main__':
    raise SystemExit(main())
