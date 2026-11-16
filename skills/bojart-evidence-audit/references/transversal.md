# Audit transversal et passation contestable

Construire la matrice de mission depuis la demande utilisateur avant de choisir les défauts à corriger : code et fichiers nouveaux, contexte accessible, fonctions Jarvis, architecture, données, outils, skills, améliorations concrètes et passation. Pour chaque volet, conserver preuve, limite et résultat remis. Ne pas confondre « auditer la fonction » et « avoir implémenté toute la fonction ».

## Contre-audit par scénarios

- Mémoire : requête courte, source pertinente peu répétée, contradiction pertinente, retrait, ambiguïté, absence de source, changement de projet et contexte trop volumineux. Recalculer les scores depuis les mesures brutes ; une latence de SQLite n'est pas celle d'une réponse de LLM.
- Audio : annulation pendant chaque attente asynchrone, nouvelle prise, ancienne réponse tardive, arrêt puis reprise, doublon et changement de dossier. Vérifier l'identité de la prise avant l'envoi du WAV, puis avant tout changement d'état. Un test synthétique valide la course, pas le français dans le bruit.
- Site 3D : fermeture du graphe d'import, provenance exacte du vendeur, décodage STL et rendu navigateur. Séparer le succès WebGL des médias absents et du service métier non lancé.
- Production : même contenu sous nom différent, fichier ressemblant de mauvais hash, archive partielle, corruption tardive, destination déjà créée et absence de rendu demandé. Vérifier les octets et les rôles artistiques sans convertir un ancien essai en plan final.
- Atelier : intention « sculpture d'un mètre répartie sur le parc ». Demander les données de fabrication manquantes dans le dossier, préparer une simulation explicite, conserver échelle assemblée, assemblages, supports et ressources humaines. Une boîte englobante compatible ne suffit pas à autoriser une impression.

## Relecture indépendante

Donner au relecteur la demande, le code figé et les entrées du scénario sans lui fournir le diagnostic attendu. Lui demander de reconstruire le chemin causal et une preuve réfutable. Si les sous-agents ne sont pas disponibles dans le client, faire une passe séparée ; ne pas inventer un outil de délégation. Conserver les désaccords et leur résolution par preuve.

## Reprise dans Codex ou Claude

Lire uniquement le contexte court au démarrage, puis ouvrir les sources de chaque question. Les noms d'outils dépendent du client ; découvrir les outils réellement accessibles. Une skill lue, une validation de son format, un test de protocole MCP et un essai dans le client sont quatre preuves distinctes. Ne pas déclarer un gain de qualité sans comparaison sur les mêmes cas et versions.

La livraison doit contenir source révisée ou patch applicable, manifeste, résultats datés, états ouverts, contexte nettoyé et prompt de reprise. Dire exactement quelles conversations et quels fichiers restent partiellement couverts. Les archives originales restent disponibles ; ne pas les charger toutes dans le prompt ni les effacer pour le raccourcir.
