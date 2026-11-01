# Installer BOJ.ART sur la tour

Pour le démarrage mémoire sans dépendances externes, suivre d’abord [INSTALLER_DEMAIN.md](../INSTALLER_DEMAIN.md). Les étapes ci-dessous décrivent la recette complète M07.

Procédure logicielle ; pas encore exécutée sur le PC réel. GPU, pilotes, microphone, moniteurs et imprimantes sont à inventorier.

## Préparer

Installer Git, Python 3.12 et FFmpeg/FFprobe via le gestionnaire adapté au système.

```bash
git clone https://github.com/Momolscode/BOJART.git
cd BOJART
python3 -m venv .venv
.venv/bin/python -m pip install -r jarvis/requirements-tests.txt
.venv/bin/python tools/doctor.py
bash Lancer_BOJART.sh
```

Windows : `py -3.12 -m venv .venv`, puis `.venv\Scripts\python -m pip install -r jarvis\requirements-tests.txt`, `.venv\Scripts\python tools\doctor.py` et `Lancer_BOJART.cmd`.

Les dépendances directes M07 sont fixées dans les requirements. Ce n’est pas un verrou exhaustif des dépendances transitives ou une qualification des roues Windows. Conserver les versions installées après recette. La mémoire seule utilise Python standard/FTS5 ; CAO, LangGraph et voix ont leurs dépendances propres.

## Données

Le lanceur indexe le contexte dans `~/BOJART/memory` ; `BOJART_MEMORY_STATE` change cet emplacement privé. L’état opérationnel M07 garde son dossier existant ; utiliser `--state` pour une recette dans un nouveau dossier. Sauvegarder avant toute mise à jour.

Le dépôt public démarre avec un catalogue média vide. Pour restaurer les trois médias d’essai autorisés depuis l’archive M07 d’origine :

```bash
python3 tools/hydrate_m07_media.py /chemin/BOJART_JARVIS_M07_2026-11-01.zip
```

L’outil vérifie l’archive et les membres attendus, refuse d’écraser un fichier différent et laisse ces médias ignorés par Git. Le catalogue des autres archives ne les télécharge pas automatiquement.

## Voix facultative

Installer `jarvis/requirements-voice.txt` dans le même environnement. Préparer séparément les poids multilingues faster-whisper. Copier `jarvis/apps/jarvis/config.example.json` hors du dépôt et renseigner `voice.enabled=true`, `voice.model_dir`. Aucun téléchargement des poids à la première commande.

Lancer avec `--config /chemin/config-locale.json`. Premier geste navigateur et permission micro nécessaires. Jev : `BOJ_JEV_ENABLED=1` et `TYPESAFE_API_KEY` dans l’environnement privé, jamais dans Git. Les textes envoyés à Jev vont au service TypeSafe ; les ordres connus fonctionnent localement.

## Recette

1. Rechercher Jev/G2/restauration dans **Mémoire du projet**, retrouver les sources.
2. Ouvrir les trois vues au clavier et obtenir trois reçus.
3. Qualifier français, bruit, annulation, fenêtre fermée et redémarrage. Mesurer ASR, décision et affichage séparément.
4. Créer un socle confirmé ; sauvegarder/restaurer les deux ensembles de données.
5. Compléter `jarvis/config/M04_INVENTAIRE_A_REMPLIR.json`. Qualifier une FDM et une résine avec opérateur avant extension.

Mot d’éveil, conversation continue et connecteurs machines ne sont pas actifs. Ne pas reprendre le PC UNUM comme configuration BOJ.ART.

Les sites gardent leur hébergement et données distincts ; les copies ici ne reproduisent pas D1, l’authentification ni tous les médias. Reprendre le flux Sites d’origine pour déployer. R03 se reprend depuis l’archive de production ; G2 reste à produire.
