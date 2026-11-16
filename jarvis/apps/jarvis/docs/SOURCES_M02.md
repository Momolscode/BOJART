# Sources primaires consultées — 28 octobre 2026
Les capacités documentées ne prouvent pas la qualité de notre assemblage sur le PC cible.

1. Ollama — Structured outputs. Schéma JSON fourni au champ `format`, validation de la réponse : https://docs.ollama.com/capabilities/structured-outputs
2. Ollama — Chat API. Réponse non streaming, `keep_alive`, options et état `done` : https://docs.ollama.com/api/chat
3. Ollama — List models. Inventaire des modèles installés, taille et empreinte : https://docs.ollama.com/api/tags
4. Ollama — FAQ. Mode sans cloud, charge mémoire et configuration : https://docs.ollama.com/faq
5. SYSTRAN — faster-whisper, dépôt primaire et code du transcripteur. Exécution CPU/int8, `local_files_only`, segments paresseux et VAD : https://github.com/SYSTRAN/faster-whisper et https://raw.githubusercontent.com/SYSTRAN/faster-whisper/master/faster_whisper/transcribe.py
6. MDN — getUserMedia. Permission, contexte sécurisé, refus et microphone : https://developer.mozilla.org/en-US/docs/Web/API/MediaDevices/getUserMedia
7. MDN — SpeechSynthesisVoice.localService. Distinction déclarée par le navigateur entre synthèse locale et distante : https://developer.mozilla.org/en-US/docs/Web/API/SpeechSynthesisVoice/localService

## Choix de réalisation propres à BOJ.ART
Recette volontairement bornée ; validation manuelle de la proposition ; transcription limitée à 15 secondes ; état matériel inconnu avant observation ; adaptateurs payants et physiques absents. Ce sont des décisions du prototype, pas des recommandations certifiées des fournisseurs.
