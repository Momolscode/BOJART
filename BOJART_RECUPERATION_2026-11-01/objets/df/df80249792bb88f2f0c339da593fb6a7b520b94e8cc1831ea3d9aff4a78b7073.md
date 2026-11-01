# BOJ.ART / Jarvis — Mission 01
## Une demande écrite → un socle réel → des preuves conservées

**Livraison du 28 octobre 2026 · module 0.1.0 · projet indépendant d’UNUM et M-Tek.**

### Voir le résultat sans installer
Ouvrir `APERCU_MISSION_01.html` dans un navigateur. Il contient le vrai maillage d’un socle calculé ici avec CadQuery : on peut le tourner au clavier ou à la souris. **Cette version de consultation ne génère pas de nouveaux modèles.** Les boutons de création, de commande et de sauvegarde y sont désactivés. Les fichiers STEP, STL, GLB et le reçu de l’exemple sont dans `exemples/180mm/`.

### Ce qui est nouveau
Le module de travail relie une commande française volontairement bornée, la recette paramétrique du socle déjà présente dans le pack précédent, les contrôles numériques, un journal SQLite et un affichage du modèle. Il accepte aussi des dimensions en centimètres ou en pouces, avec conversion explicite.

Exemples acceptés :
- « Jarvis, crée un socle de 180 mm et affiche-le à droite ».
- « Prépare un socle de 24 cm ».
- « Génère un socle de 7 pouces ».

Le diamètre vient de la phrase. Les six autres paramètres viennent d’une recette affichée et modifiable avant validation. Les demandes plus complexes sont **refusées**, pas amputées silencieusement. Ce n’est ni un LLM, ni une compréhension vocale générale.

### Préparer la reprise sur le PC — pour Claude / l’intégrateur
Le propriétaire n’a pas à recopier des commandes. Les étapes ci-dessous sont celles de l’agent autorisé lorsque le PC sera accessible.

1. Inventorier le PC et les sources actuelles. Ne pas utiliser le matériel d’UNUM comme référence. Pas d’achat avant inventaire (budget 3 000–5 000 €).
2. Récupérer les dépôts complets des deux sites et leurs sauvegardes. Ce module **ne contient pas leurs sources complètes, leurs bases ou tous les médias**.
3. Créer un environnement Python isolé ; installer les versions de `requirements.txt` après examen du plan d’installation. Aucune modification des protections système.
4. Exécuter `tests/test_mission01.py` puis le test navigateur direct `tests/test_browser.py`. Le second reste à exécuter dans un navigateur autorisant le service local.
5. Ouvrir `Lancer_Jarvis.cmd` sur Windows ou `Lancer_Jarvis.sh` sur Linux. Ces lanceurs utilisent uniquement les dépendances déjà installées et ne téléchargent rien. Windows n’a pas été testé ici.
6. La page s’ouvre sur **127.0.0.1**, avec une session aléatoire. Les dossiers sont conservés par défaut dans `~/BOJART/mission01`. La fenêtre terminal maintient le service ; la fermer l’arrête. Aucun service système n’est installé.
7. Réaliser le parcours 180 mm puis 240 mm, relire les exports, sauvegarder et tester la restauration sur un nouveau dossier.

Commandes de reproduction pour l’intégrateur, pas une tâche demandée au propriétaire :
```sh
python -m venv .venv
# Activer l’environnement selon le système, sans modifier la politique globale.
python -m pip install -r requirements.txt
python tests/test_mission01.py
python app/server.py
```

Le script navigateur utilise Playwright et Chromium, uniquement pour la recette de développement. Ils ne sont pas nécessaires à l’utilisation de l’application dans un navigateur courant. Les dépendances transitives et les roues de la plateforme cible devront être gelées après cette recette ; le fichier de versions actuel ne constitue pas un verrou complet de chaîne logicielle.

### Garanties limitées de ce prototype
- Les paramètres sont numériques, bornés et vérifiés ; aucun code venant du texte utilisateur n’est exécuté.
- Les sorties d’une mission sont conservées dans un nouveau dossier ; les anciennes versions ne sont pas écrasées.
- Une opération répétée avec le même identifiant retrouve son résultat. Le même identifiant avec d’autres paramètres est refusé.
- Un changement de révision ou une mission encore en cours bloque un nouveau départ dans ce dossier.
- Les empreintes des exports et le manifeste sont vérifiés à la relecture.
- Une exception n’est jamais transformée en réussite.
- La sauvegarde réunit base, contexte et fichiers ; elle refuse de capturer un travail déclaré en cours.

**Ce n’est pas une garantie « exactly once » sur des machines physiques : aucun connecteur machine n’existe dans ce module.** Une interruption brutale peut laisser un statut RUNNING ; il bloque la poursuite et nécessite une résolution explicite par l’intégrateur, sans relance automatique.

### Sécurité locale et limites
Session par lancement, cookie HttpOnly/SameSite=Strict, vérification de Host et d’Origin, refus de champs inconnus et de chemins arbitraires. Aucune ouverture LAN, aucun tunnel public, aucun appel externe. Ces protections ne constituent pas un audit de sécurité exhaustif. Le service standard Python est destiné à ce poste local mono-utilisateur, pas à l’hébergement public.

Une sauvegarde avec empreintes détecte des altérations accidentelles ; elle n’est ni chiffrée ni signée par un éditeur. La conserver sur un stockage autorisé. Une modification coordonnée de la base et des fichiers par un administrateur local ne relève pas de ce contrôle.

### Ce que cette livraison ne fait pas
Pas de reconnaissance vocale, pas d’appel Jev/Ollama, pas de création générale de figurines, pas de slicing, de départ machine, de publication, de devis contractuel ou de consommation de crédits. Pas de mise à jour des sites publiés. Pas d’installation sur la tour. Ce module est une base d’intégration, **pas encore l’installateur plug-and-play complet**.

### Preuves
- `preuves/TESTS_MISSION01.txt` : 62 tests de contrats, géométrie, versions, restauration, contexte et HTTP local.
- `preuves/TESTS_INTERFACE.json` : 15 contrôles sous Chromium ; transport API simulé, maillages réellement générés.
- `tests/test_browser.py` : recette directe navigateur/serveur fournie, mais bloquée ici par la politique du navigateur (`ERR_BLOCKED_BY_ADMINISTRATOR`). Aucune politique n’a été contournée.
- `preuves/mission_180mm.json` : dimensions, contrôles et empreintes de la pièce fournie.
- `preuves/TESTS_ANTERIEURS_REEXECUTES.txt` : 22 tests du simulateur antérieur, séparés de ce module.
- `MANIFESTE_SHA256.json` : inventaire d’intégrité du pack.

`CONTEXTE_LISIBLE.md` et `context/CONTEXTE_REFERENCE.json` séparent contraintes utilisateur, preuves locales, historique non réaudité, propositions et inconnues. La présence d’une fonction dans une note n’est pas une preuve qu’elle est installée.
