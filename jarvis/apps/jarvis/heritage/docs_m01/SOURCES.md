# Sources primaires vérifiées le 28 octobre 2026

S1 — CadQuery, Importing and Exporting Files
https://cadquery.readthedocs.io/en/latest/importexport.html
Supports STEP/STL/3MF/glTF ; précision importante : la recette Python porte le paramétrage CadQuery. Le fichier STEP n’est pas le script de construction. Ne pas déduire de cette liste la compatibilité d’une imprimante.

S2 — Ollama, Structured Outputs
https://docs.ollama.com/capabilities/structured-outputs
Schéma JSON dans `format`, validation applicative toujours nécessaire. La page indique que les sorties structurées ne sont actuellement pas prises en charge par son cloud. Notre choix reste local ; aucune exécution de modèle réalisée ici.

S3 — Ollama, Tool Calling
https://docs.ollama.com/capabilities/tool-calling
Contrats d’outils via `/api/chat`. Un appel demandé par un modèle ne supprime pas les contrôles de permission, de cible, d’unité ou de révision.

S4 — TypeSafe, Models
https://docs.typesafe.ai/models
Modèles Jev 1.13/1.14, entrées décrites comme texte. Alias stable/preview distincts ; fixer la version lors d’une évaluation. Aucun benchmark de notre atelier n’est inféré.

S5 — TypeSafe, System One API
https://docs.typesafe.ai/api/system-one
Décisions typées et actifs image expérimentaux (`TypeSafe-Danger-Zone-Images`), conditionnés à un modèle de vision compatible. La capacité de l’API n’est pas une preuve que tous les modèles Jev peuvent lire les images.

S6 — Ollama, FAQ
https://docs.ollama.com/faq
Mode local seul (`OLLAMA_NO_CLOUD=1`), temps de maintien des modèles en mémoire, paramètres de concurrence et consommation supplémentaire liée au contexte. Réglages à mesurer sur le matériel cible ; aucun prix matériel établi dans ce livrable.

S7 — Moonraker, Job Queue Management
https://moonraker.readthedocs.io/en/latest/external_api/job_queue/
La file est FIFO et peut contenir des références dupliquées. Elle ne fournit pas à elle seule notre garantie d’absence de réémission.

S8 — Moonraker, Printer Administration / Printer Objects
https://moonraker.readthedocs.io/en/latest/external_api/printer/
https://moonraker.readthedocs.io/en/latest/printer_objects/
Commandes et états disponibles uniquement pour les installations compatibles. Un état `complete` ne mesure pas un retrait physique de pièce.

## Références de projet
Archives accessibles : `BOJART_Pack_Lancement_20-10-2026.zip`, `BOJART_V6_STORYBOARD_CHARACTER_LOCK.zip`, `BOJ_ART_Integration_IA_Locale_Jev_REA_2026-10-20.zip`. Empreintes et liste exacte : `preuves/inventaire_antecedents.json`.
Les contraintes budget, local, trois écrans, parc, identité et simplicité viennent de l’utilisateur dans cette conversation. Les affirmations anciennes sur le code publié sont conservées comme historiques, pas reverifiées par la seule lecture des rapports.
