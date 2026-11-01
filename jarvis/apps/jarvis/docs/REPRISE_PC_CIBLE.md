# Reprise du poste BOJ.ART — Mission 02

## Parcours du propriétaire
Double-cliquer sur le lanceur une fois l’environnement préparé. Le navigateur ouvre une session locale. Lire le diagnostic ; préparer un socle de 18 cm ; relire la conversion et les valeurs héritées de recette ; valider ; tourner le vrai modèle ; créer une sauvegarde. Aucun mot de passe ou secret ne doit être envoyé dans le chat.

## Préparation par l’intégrateur
Le PC cible n’a pas été accessible dans cette livraison. OS, GPU, VRAM, RAM, disques, interfaces audio, trois écrans, machines et profils restent à relever. Le diagnostic du module ne parcourt pas les vidéos : l’inventaire des médias est une phase séparée, bornée à des dossiers autorisés.

### 1 — Environnement réversible
Sauvegarder l’existant. Déployer dans un nouveau dossier. Réutiliser un Python compatible dans `.venv` ; vérifier les roues de CadQuery. Lancer sans Ollama et sans voix ; exécuter le parcours 180 mm puis 240 mm. Ne pas importer une base de production avant examen de sa version.

### 2 — Vérifier le contexte
Le contexte documente des objectifs, des faits vérifiés, des propositions et des inconnues. Ne pas utiliser une ancienne observation comme état courant d’imprimante. Les propositions de cette version enregistrent une copie du contexte, en plus de son empreinte.

### 3 — Interprétation locale
Sélectionner un modèle déjà installé, compatible avec les sorties structurées. Mesurer le français sur le corpus des tests et un ensemble indépendant de phrases atelier. Garder la compréhension bornée tant que les négations, unités, contraintes et demandes multiples ne sont pas qualifiées. Pas de code généré exécuté.

L’adaptateur ne contacte que 127.0.0.1 et ne suit pas de redirection. Un modèle fourni par un serveur local pourrait malgré tout déléguer son traitement : tester l’absence de sortie réseau, activer le mode sans cloud du fournisseur, puis renseigner `offline_verified`. Le drapeau n’est pas un pare-feu.

### 4 — Audio
Préparer faster-whisper et des poids multilingues locaux dans une version revue. Déclarer `model_dir`, sans URL, puis vérifier : permission, annulation, arrêt à 15 secondes, sortie de la page, bruit, saturation et silence. Les scores de transcription ne sont pas des probabilités de commande sûre.

L’audio est gardé en mémoire pendant le traitement puis libéré ; aucun enregistrement persistant n’est prévu par le module. Cela ne constitue pas une garantie d’effacement de la mémoire ou du swap du système. Vérifier les journaux et le poste.

Exemples de réception : « dix-huit centimètres », « sept pouces », « sans trous », « ne lance pas », « arrête », conversation sans commande, double clic, permission refusée. La voix ne remplace pas un arrêt physique. La commande d’arrêt d’une machine n’est pas implémentée.

### 5 — Lecture vocale
Sélection locale explicitement demandée par bouton, pas de lecture automatique pendant une prise. Vérifier `localService` puis faire un essai hors ligne. Si aucune voix française locale n’est disponible, rester en texte ; ne pas substituer silencieusement une voix distante.

### 6 — Réception technique
Exécuter `tests/test_browser_direct.py` sur un navigateur autorisant le service local, sans désactiver une protection globale. Vérifier les STEP, STL, unités GLB, sauvegarde et restauration vers un dossier neuf. La base SQLite est mono-poste et ne doit pas être placée sur un partage réseau non qualifié.

## Critères de passage
Une création exacte et restaurable ; aucun déclenchement depuis la seule transcription ; ancien contexte bloqué ; échec non présenté comme réussite ; métriques de latence et d’erreurs mesurées sur la tour. Ensuite seulement : slicer identifié, une FDM + une résine, plateau préparé et contrôle opérateur.
