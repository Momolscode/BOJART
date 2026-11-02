# BOJ.ART / JARVIS — Mission 02
## Dialogue français, proposition vérifiable et préparation du vocal local
**28 octobre 2026 · prototype 0.2.0 · BOJ.ART uniquement, indépendant d’UNUM et M-Tek.**

### À montrer sans rien installer
Ouvrez **APERCU_MISSION_02.html**. Choisissez « Socle 18 cm » ou « Variante 24 cm », puis préparez la proposition et affichez le résultat. Les maillages sont de vrais exports CadQuery calculés pendant cette livraison. L’aperçu ne déclenche ni IA, ni microphone, ni création nouvelle, ni réseau. Les STEP/STL/GLB sont dans `exemples/`.

### Ce qui fonctionne dans le module local
- Demandes françaises bornées : chiffres, mots (« dix-huit centimètres »), pouces et virgules décimales.
- Questions simples sur le dossier et affichage du dernier modèle.
- Proposition persistée en SQLite : diamètre, autres paramètres de recette visibles, révision, contexte intégral, origine et expiration.
- Validation séparée, génération CadQuery réelle, relecture STL, fichiers, reçu et visualisation.
- Reprise idempotente de la même proposition ; une ancienne révision ou un contexte différent bloque une nouvelle exécution.
- Diagnostic matériel en lecture seule, sans inventaire des fichiers privés ni scan réseau.
- Sauvegarde du dossier réunissant base, propositions (dont contexte utilisé), contexte courant et fichiers.

### Ce qui est codé mais encore à qualifier sur le PC réel
**Ollama local.** Adaptateur `/api/chat` à sortie sous schéma, limité à `127.0.0.1`. Il vérifie le modèle présent et son empreinte, refuse les modèles identifiés comme distants et compare le résultat à la dimension réellement écrite. Pas de téléchargement, de choix automatique du « meilleur modèle » ou de repli cloud. Le modèle n’exécute rien. Les essais fournisseur utilisent un serveur de réponse contrôlé, pas un vrai LLM.

**Voix.** Bouton démarrer/arrêter, arrêt automatique à 15 s, retour texte à relire, capture Web Audio et WAV mono 16 kHz. La transcription utilise facultativement faster-whisper CPU/int8 et **un dossier de poids déjà présent** (`local_files_only=True`). Aucun audio n’est écrit en base par ce module. Les tests utilisent un WAV synthétique et un transcripteur doublure : la qualité de reconnaissance, le vrai microphone et le bruit n’ont pas été mesurés. Le cœur ne crée jamais un modèle sur simple transcription.

**Lecture à voix haute.** Le bouton choisit seulement une voix française que le navigateur déclare `localService=true`. Sans voix locale annoncée, il reste désactivé. Cela demande une vérification hors ligne sur le navigateur et le système réels. Aucun moteur TTS ni aucune voix n’est distribué dans ce ZIP.

### Double-clic prévu pour le propriétaire
`Lancer_Jarvis.cmd` (Windows) ou `Lancer_Jarvis.sh` (Linux) utilise d’abord l’environnement `.venv`, puis Python existant. Sans Python, le lanceur Windows ouvre l’aperçu. Aucun logiciel n’est installé, aucune politique de sécurité modifiée.

Le poste peut ouvrir son diagnostic même sans CadQuery. La création 3D nécessite les dépendances. Le service écoute uniquement sur 127.0.0.1, ouvre une session aléatoire, n’expose pas le PC au réseau et s’arrête avec son processus. Les données vont par défaut dans `~/BOJART/mission02`, **sans écraser les données Mission 01**.

**Ce n’est pas encore l’installateur universel plug-and-play signé.** La préparation des dépendances est à réaliser une fois par l’intégrateur ; le propriétaire n’a pas à recopier des commandes.

### Pour Claude / l’intégrateur
1. Lire `AGENTS.md`, `CONTEXTE_LISIBLE.md` et `docs/REPRISE_PC_CIBLE.md`.
2. Inventorier la tour, les logiciels et les sources disponibles. Ne rien acheter avant de comparer le matériel récupérable au budget 3 000–5 000 €.
3. Créer un environnement Python isolé et examiner `requirements.txt`. Les versions y sont celles utilisées ici sur Linux/Python 3.13 ; les roues Windows et dépendances transitives sont à vérifier et verrouiller.
4. Exécuter les tests, notamment la recette navigateur **directe** sur le PC cible.
5. Pour l’IA, copier `config.example.json` en `config.json` seulement après inventaire. Renseigner un modèle local déjà installé et son empreinte. `offline_verified=true` signifie qu’un contrôle réel hors ligne a été effectué, pas qu’on souhaite ignorer ce test.
6. Pour la voix, installer et verrouiller une version de faster-whisper examinée, puis préparer un modèle multilingue avec licence et empreintes consignées. Aucun chemin de poids fictif ne doit être activé.
7. Tester le micro et la voix en bruit réel, vérifier les unités transcrites et les refus. Qualifier la qualité séparément du bon fonctionnement de l’interface.

### Périmètre de recette
- 110 tests M02 backend, dialogue, contrats fournisseur contrôlés, audio et HTTP.
- 62 tests hérités M01 réexécutés.
- 21 contrôles Chromium : HTML local en mémoire et **pont de test explicite vers le vrai service HTTP/CadQuery**. Le microphone et le transcripteur sont remplacés pour les parcours voix.
- L’accès direct du navigateur administré à localhost est bloqué. Aucune politique n’a été modifiée. Le test direct est livré, mais reste à passer sur la tour.

Les logs exacts sont dans `preuves/`. Ces nombres ne sont pas une mesure de précision d’un modèle IA, ni une qualification industrielle.

### Ce qui reste volontairement absent
Commande machine, slicing, modélisation organique générale, raisonnement libre, Jev connecté, RAG exhaustif, génération vidéo, paiements, publications et liens aux statistiques sociales. Aucune modification du site hébergé. Aucun matériel, modèle ou compte cible connecté pendant cette livraison.

La mention « à droite » désigne ici la zone de visualisation du poste. Le routage vers trois moniteurs physiques reste à intégrer.
