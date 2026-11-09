---
name: bojart-context-reconstruction
description: Reconstruire le contexte BOJART lors d’une reprise de session, d’une contradiction ou d’un audit de mémoire. Préserver les sources et challenger les hypothèses sans supprimer l’historique.
---

# Reconstruire un contexte utile et contestable

« Détruire le contexte » signifie ici retirer les hypothèses obsolètes du contexte actif, pas effacer les originaux. Repartir des décisions directes de l’utilisateur, des sources authentiques et du code courant. Une préférence ancienne peut être remplacée ; conserver la preuve de son remplacement et la date.

Lire le registre `data/knowledge/claims.jsonl`, les sources correspondantes et les décisions dans `docs/preinstallation/DECISIONS_UTILISATEUR.txt`. Séparer observation, décision directe, information rapportée, proposition et inconnu. Vérifier le projet : BOJ.ART, création ou sites ; UNUM/M-Tek/Marwin ne fournit pas automatiquement le matériel ni les décisions de Jarvis.

La mémoire SQLite existante conserve objets, versions, propositions et épisodes. Employer ses outils de recherche et de restauration ; ne pas créer un second magasin actif pour contourner un problème de classement. Une nouvelle mémoire préparée à partir du dépôt ne contient pas les conversations privées de l’utilisateur.

Pour une question, vérifier que les sources retrouvées soutiennent la réponse et qu’un conflit hors sujet ne chasse pas les faits pertinents. Tester ajout de documents, source retirée, contradiction, information absente et instruction injectée. Une citation reconnue syntaxiquement ne suffit pas. Un contrôle du hash original ne prouve pas à lui seul que le texte de l’index lui correspond.

Lors d’un audit conversationnel, examiner la fraîcheur des sources, le budget de contexte, la conservation des échanges complets, l’isolation de session/projet et la réservation des identifiants avant inférence. Rejouer les courses avec un faux fournisseur ; ne pas mesurer un défaut d’idempotence en facturant des appels réels.

Produire une reprise courte : objectif, décisions directes, révision/code testé, faits établis, hypothèses invalidées, défauts ouverts, prochaines vérifications et liens vers les preuves. Conserver à part le texte intégral et la table de couverture. Réévaluer les conclusions dans une session neuve à partir des sources : ne pas demander au prochain modèle de simplement confirmer ce résumé.
