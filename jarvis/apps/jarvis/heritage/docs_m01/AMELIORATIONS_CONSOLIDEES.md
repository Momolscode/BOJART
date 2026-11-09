# BOJ.ART / Jarvis — amélioration de la cohérence d’ensemble
**28 octobre 2026.** Périmètre : archives locales accessibles et documentation primaire. Pas d’accès au PC cible ; pas de réaudit du code complet des applications publiées. Aucun crédit créatif ou budget publicitaire engagé.

## 1. Le changement de méthode
La multiplication de rapports, maquettes et générations a fait progresser le concept, mais crée un risque : une intention, un prototype et une fonction réellement branchée finissent par porter le même nom. Ce module introduit un parcours très limité, dont le résultat peut être vérifié sans machine ni abonnement : demande de socle → paramètres → CAO → exports relus → reçu → affichage.

L’objectif suivant sera de remplacer la grammaire limitée par une interprétation locale évaluée, **sans changer le contrat de géométrie**. Le modèle proposera les paramètres ; le même validateur gardera l’autorité sur ce qui est exécuté.

## 2. Contexte vivant plutôt que conversation géante
### Implémenté dans ce module
Un contexte de référence JSON avec 21 faits classés : contrainte utilisateur, vérifié ici, historique, proposition ou inconnu. Chaque fait porte une source et une portée. Une preuve vérifiée a une référence de fichier ; un inconnu reste `null`, pas zéro. Un doublon de clé est refusé. Une observation opérationnelle n’est utilisable que si elle est datée et encore dans sa durée de validité.

Le contexte humain est produit à partir du JSON : un agent comme Claude peut reprendre les décisions sans confondre BOJ.ART, UNUM et M-Tek. Chaque mission conserve l’empreinte du contexte et la version de recette utilisés.

### À intégrer ensuite
Index documentaire pour les dossiers autorisés, sources médias horodatées, recherche par œuvre, statut « source débranchée » et séparation des données clients. Ne pas aspirer automatiquement tout le PC, les courriels ou les comptes du propriétaire. Un mandat d’accès doit décrire les dossiers et comptes concernés.

L’état des machines et du stock vient des connecteurs métier, pas d’une recherche dans d’anciens PDF. Le brief doit pouvoir préciser « information inconnue / périmée », et demander uniquement le renseignement réellement manquant.

## 3. Conception 3D : conserver ce qui permet de modifier
Le fichier STEP est utile à l’échange, mais la recette paramétrique et ses paramètres doivent rester le modèle source de cette famille. La documentation CadQuery indique que ses formats d’échange ne conservent pas son paramétrage ; le format Python est sa source paramétrique [S1].

Le module conserve donc STEP, STL en convention mm, GLB en mètres, paramètres, recette et contrôles. La fermeture du maillage, les normales et les dimensions sont examinées. La résistance, la charge, l’assemblage et le tranchage ne sont pas attestés par ces contrôles.

Le choix futur des moteurs reste : CadQuery pour familles techniques délimitées ; Blender pour la création artistique ; FreeCAD/Fusion selon l’usage et les licences. Aucun nouvel abonnement imposé. La génération d’une sculpture organique ne doit pas être promise comme équivalente à la génération d’un socle paramétrique.

## 4. IA locale et Jev : réduire le nombre de dépendances obligatoires
Le socle d’intégration retenu est une interface de décision commune, avec règles déterministes en premier. La documentation Ollama vérifie les appels d’outils et les sorties sous schéma sur `/api/chat` [S2, S3]. Ces capacités ne valident pas la précision d’un modèle sur les commandes françaises ni ses scores de confiance.

L’endpoint local `/v1/systemone` figure dans les anciens documents comme candidat. Il n’est pas devenu un prérequis de ce module : sa disponibilité et son comportement doivent être testés sur le binaire réellement choisi. Cela évite d’immobiliser le produit à cause d’une compatibilité seulement supposée.

Jev reste optionnel et distant. La page modèles décrit Jev 1.13/1.14 à entrée texte et recommande de fixer une version si les seuils ont été évalués [S4]. L’API décrit désormais aussi des actifs image sous un en-tête expérimental, conditionnés à un modèle vision-langage [S5]. **L’existence de ce champ ne suffit pas à conclure que le modèle Jev choisi accepte nos images.** La vision est donc maintenue comme moteur distinct tant que la combinaison exacte n’est pas testée.

La page publique des modèles/API n’établit ni notre latence, ni notre français, ni le droit d’utiliser tous les poids communautaires. Pas de modèle définitivement retenu avant inventaire et mini-benchmark du PC.

## 5. Voix, rendu et GPU : un ordre de priorité
Proposition à intégrer, pas service livré :
1. Le suivi machine et le journal fonctionnent sans LLM et gardent une voie d’arrêt indépendante.
2. La commande vocale, les erreurs et les réponses courtes ont priorité sur un rendu différable.
3. Un seul travail lourd de génération/rendu utilise le GPU au début ; le parallélisme sera mesuré, pas déduit du prix de la tour.
4. Les modèles sont déchargés quand nécessaire ; les options de durée de chargement et de concurrence existent dans Ollama [S6]. La mémoire de contexte et les requêtes parallèles consomment aussi de la RAM/VRAM.

Pour le mode local strict, le plan prévoit `OLLAMA_NO_CLOUD=1`, puis un contrôle des journaux et des sorties réseau lors de la recette [S6]. Le module actuel n’installe ni ne configure Ollama.

## 6. Fabrication : finir une pièce, pas seulement vider une file
Moonraker expose des commandes sur les machines compatibles, mais sa file est FIFO et peut contenir plusieurs fois le même travail [S7, S8]. Nous conservons donc notre registre de commandes, un identifiant d’opération, un contrôle de révision et une résolution des accusés inconnus. L’absence de réponse n’autorise pas à relancer aveuglément.

Proposition de cycle : préparé → slicing identifié → transféré → départ observé → en cours → impression terminée → contrôle → retrait attesté → machine re-préparée. Lavage, polymérisation, assemblage, peinture et emballage sont des ressources à planifier. Une machine `complete` n’atteste pas que son plateau est libre.

Le parc de 7–8 imprimantes est un objectif. La préférence grandes figurines résine / socles FDM reste explicite, mais ne remplace pas l’étude par pièce. Sans leurs modèles exacts, aucun adaptateur n’est déclaré compatible.

## 7. Studio : la qualité devient une condition de passage
Les TESTS vidéos ont montré que « terminé » ne signifie pas « conforme ». Le modèle peut livrer un fichier lisible tout en changeant le visage, les vêtements, le socle ou le personnage.

La fiche V6 reste la référence consultable dans ce pack. Elle ne constitue pas une autorisation de générer ou de publier. Pour les futures versions de Studio, chaque plan doit relier :
- œuvre et références authentiques ;
- version de prompt, fournisseur, réglages et coût autorisé ;
- fichier produit, format/cadence/durée mesurés ;
- verdict technique, verdict de fidélité et accord artistique ;
- timecodes sélectionnés et exclusions observées.

Ne jamais faire d’une image générée la nouvelle « vérité » de la figurine. Une génération rejetée reste dans l’historique comme contre-exemple, pas comme référence automatiquement réutilisable.

Proposition : un registre d’essais décrit ce qui a été réellement modifié entre A et B (référence, moteur, durée, action). Cela empêche de diagnostiquer une panne fournisseur en affirmant sans preuve que « le prompt était trop complexe ».

## 8. Commerce et acquisition : promettre selon la capacité
Les deux comptes TikTok restent séparés. Leur audience ne s’additionne pas en audience unique ; les anciennes captures ne sont pas des métriques actuelles. La répartition vitrine / coulisses est à tester.

Avant amplification publicitaire, le plan doit vérifier : offre réalisable, accès aux bons médias, droits pertinents documentés, formulation exacte des dimensions, formulaire testé, responsable de la demande et capacité de finition. Ce n’est pas un lancement de campagne dans cette livraison.

Le devis futur doit préciser version de la pièce, quantité, finition, hypothèses, prix et échéance ; un changement crée une nouvelle version. Une génération « prête » ne doit pas annoncer automatiquement un produit « en stock ».

Le Growth Dashboard devrait présenter les demandes qualifiées, les devis acceptés et la charge à livrer avant de recommander plus de publicité. L’attribution conserve une catégorie « inconnue » ; une seule bio commune ne permet pas une attribution parfaite par vidéo.

## 9. Installation réellement réversible
Les lanceurs de ce module ne sont pas l’installateur final. Ils contrôlent la présence de Python/CadQuery/trimesh, ne téléchargent rien et ouvrent une session locale. Le futur installateur devra être signé ou distribué via un canal approuvé, annoncer les modifications, vérifier l’espace, conserver les versions et proposer un retour arrière testé.

Le budget de référence est 3 000–5 000 € avec réemploi ; aucune commande matérielle. Les données sensibles et profils restent sur stockage sauvegardé. Une archive avec SHA-256 n’est pas une signature et ne remplace pas une restauration testée.

## 10. Les prochains jalons, avec leur preuve
| Jalon | Preuve attendue | État dans ce module |
|---|---|---|
| M01 : demande écrite bornée → socle réel | Exports, mesures, empreintes, versions et reprise | Code et tests fournis |
| M02 : interprétation générale locale | Jeu français annoté ; mauvaises unités et intentions ambiguës détectées | Non raccordé |
| M03 : voix française | Tests bruit / silence / conversation / interruption ; pas d’ordre involontaire | Non raccordé |
| M04 : une FDM et une résine | Bonne pièce, bon fichier, bonne machine ; réception perdue sans doublon | Matériel inconnu |
| M05 : création + vidéo + devis | Dossier commun, identité préservée, coût réel, proposition versionnée | Intégration à poursuivre |
| M06 : parc et acquisition | Charge machine + humaine mesurée ; campagne autorisée et traçable | Après pilote |

## 11. Limites de recette de cette livraison
62 tests backend/contrats passent et 15 contrôles de l’interface passent sous Chromium avec transport simulé. Les maillages dans ces tests sont réellement calculés ; le serveur HTTP fait l’objet de tests séparés. Le navigateur administré bloque l’accès direct à localhost : l’essai navigateur → service est donc fourni mais non conclu ici. Pas de test Windows, GPU cible, microphone, fournisseur IA, imprimante, paiement ou compte social. Aucun site publié modifié.

Le réaudit porte sur les trois ZIP accessibles et leur code de démonstration, pas sur une copie récupérée des bases de production. Il faut les restaurer dans un environnement distinct avant intégration.

## Sources primaires
Les références S1–S8 et leur portée sont détaillées dans `SOURCES.md`, consultées le 28 octobre 2026. Les recommandations de réalisation ci-dessus sont nos choix de conception, non une certification des fabricants.
