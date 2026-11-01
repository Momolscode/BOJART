# Mission Claude Code — BOJ.ART Jarvis

Tu travailles sur un atelier 3D BOJ.ART, indépendant d'UNUM et de M-Tek.
Objectif : 7–8 imprimantes FDM/résine, trois écrans, assistant vocal local, conception et visualisation 3D, fabrication, contenus et acquisition/devis.

## Phase 0 — sécuriser
- Ne pas effacer, déplacer, formater, réinstaller ni lancer d'impression.
- Ne pas utiliser de commandes destructives ni installer des dépendances avant inventaire et autorisation.
- Sauvegarder les sources et les données avant toute modification.
- Ne jamais copier des rushes privés ou des données client vers un fournisseur externe sans autorisation.

## Phase 1 — inventorier
- Identifier OS, CPU, GPU/VRAM, RAM, stockage, sorties vidéo, audio, réseau et pilotes.
- Inventorier les slicers, Blender/CAO, logiciels vidéo, moteurs IA et leurs versions.
- Chercher les fichiers BOJ.ART dans les répertoires expressément autorisés : rushes, masters, projets, images, logos, STL/STEP/3MF, G-code, sauvegardes.
- Produire un catalogue : chemin, taille, empreinte, date, type, provenance, œuvre associée si vérifiée.
- Inventorier imprimantes, firmware, volumes, profils, capacités API, stations de lavage/cure et finition.

## Phase 2 — concevoir selon les mesures
- Benchmark des candidats IA locaux en français, avec charge simultanée.
- Moteur de décision interchangeable : règles locales -> décideur local -> Jev distant facultatif.
- Les modèles ne créent jamais directement une commande machine : validation des préconditions et journal transactionnel.
- Visualisation depuis fichiers réels via moteur 3D ; Jev choisit seulement parmi des composants et outils autorisés.
- Mémoire RAG séparée des états machines et commandes ; chaque réponse renvoie à une source.
- Prévoir import sécurisé des sources existantes du projet BOJ.ART, sans écraser la version en production.

## Phase 3 — tests d'acceptation
- Test restauration fichiers + base + médias.
- Simulation d'une commande vocale ambiguë, d'un changement de dossier et d'une coupure réseau.
- Tester sur une FDM et une résine avec opérateur présent, puis élargir le parc.
- Rendu d'un extrait vidéo avec signature BOJ.ART et comparaison aux originaux.
- Vérifier droits d'accès, consentement, devis versionnés, confidentialité des prospects.

## Livrables attendus
1. Rapport matériel et recommandations IA par configuration mesurée.
2. Inventaire des contenus avec preuves et doublons.
3. Architecture cible et écarts avec le code existant.
4. Plan d'installation réversible et testable.
5. Liste des opérations nécessitant l'approbation du propriétaire.
Ne jamais déclarer « installé » sans logs de vérification.
