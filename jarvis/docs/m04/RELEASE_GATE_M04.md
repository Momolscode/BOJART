# BOJ.ART — Jarvis M04 : critères de lancement vérifiables

## Résultat réel de M04

La régie M04 route des **propositions visuelles déterministes** vers des vues navigateur locales (atelier, pilotage, création). Elle conserve les commandes dans SQLite et les accuse après traitement par le navigateur. Pour le modèle 3D, la vue vérifie l'empreinte SHA-256 du GLB avant d'utiliser le maillage. Ce reçu **n'est pas une preuve de visibilité sur un écran physique**.

Aucune commande FDM/résine, aucune publication, aucune dépense, aucun LLM/Jev/LangGraph ou microphone n'a été activé. Le PC cible n'a pas été inventorié.

## Douze portes de recette obligatoires

| Porte | Preuve attendue avant usage réel |
|---|---|
| CAO | Export réel + relecture STEP/STL/GLB sur le PC cible |
| Voix | ASR local testé en français dans le bruit de l'atelier, interruption et corrections |
| LLM | Modèle local identifié, version et VRAM mesurées, jeu de tests français réussi |
| Jev | Intégration facultative testée, réponses invalides et panne traitées |
| Trois écrans | Appairage de chaque moniteur physique, chargement du vrai modèle, déconnexion et latence mesurés |
| FDM | Une imprimante, un slicer et un profil qualifiés sur pièce test, opérateur présent |
| Résine | Une imprimante, lavage, polymérisation, ventilation, EPI et gestion des déchets qualifiés |
| Sécurité | Interverrouillages, arrêt d'urgence physique, limites de température, validation des commandes |
| Sauvegarde | Restauration du dossier global, médias, SQLite, recettes et identifiants vérifiée sur un autre emplacement |
| Studio | Références authentiques, droits médias et identité des œuvres validés sur les vrais rushes |
| Publication | Comptes autorisés, droits son/image, mode de publication, reçu et doublons testés |
| Site et devis | Formulaire, consentements, devis, capacités réelles et notifications testés |

**Politique :** ne pas afficher « prêt production » tant que toutes les preuves de terrain ne sont pas enregistrées et vérifiées. La présence d'une dépendance Python n'est pas une preuve de qualification.

## Commandes réellement disponibles dans M04

- « Montre les sources au centre » → affiche le résumé du catalogue local.
- « Affiche le planning à gauche » → montre explicitement une simulation.
- « Affiche le modèle à droite » → exige un modèle existant, un GLB dont l'empreinte correspond et un maillage relu.
- « Arrête de parler » → ordre d'interface seulement ; aucun moteur vocal actif dans M04.

La commande écrite peut être ultérieurement alimentée par la transcription vocale locale. Jev n'est ni un microphone ni un moteur de rendu.

## Ce qui reste à corriger avant production

1. Projet pilote `BOJ-PILOTE-001` imposé dans les contrats d'affichage : généraliser sans casser l'isolation des dossiers.
2. Pairing navigateur ≠ détection de moniteur physique : ajouter l'appairage OS et les preuves d'affichage.
3. Backup actuel CAO/Studio/Growth non atomique : mettre en place une sauvegarde transactionnelle complète avec restauration répétée.
4. Route audio présente mais non qualifiée sur micro réel ; benchmark CPU/GPU requis.
5. FDM/résine : inventaire, firmware, profil, interfaces, sécurité, post-traitement, consentement d'action.
6. Connecteurs réseaux sociaux et fournisseurs : contrats, droits, coûts et reçus d'exécution.
7. Charge réelle : mesurer voix + 3 vues + slicer + rendu simultanés et établir une file GPU.
8. Panne d'écran : vérifier la récupération après expiration du bail de livraison, sans double exécution physique.

## Sécurité de déploiement

Service lié à `127.0.0.1` uniquement, session par cookie HttpOnly, vérification Origin des écritures, routes en liste blanche, pas de shell depuis le navigateur, pas de découverte de machine réseau. Ne pas ouvrir ce service directement à Internet ou au LAN. Les mots de passe et tokens restent hors Git.

## Critère de « plug and play »

L'installateur final devra détecter le matériel, installer **uniquement après accord** les dépendances versionnées, vérifier leurs empreintes, créer une sauvegarde préalable, faire les tests, puis proposer un retour arrière. M04 n'est pas encore cet installateur ; ses lanceurs utilisent les dépendances déjà présentes.
