> Synthèse créative préservée du dépôt au commit `cd71c6ba640f304248702d8a3e64c60f900f9d0b`. Le point d’entrée courant est [le README](../README.md). Liens adaptés à ce dossier.

# BOJART — Marwin Studio

Projet de direction artistique et de production audiovisuelle hybride pour les sculptures et créations de BOJ.ART.

> **État : recherche & développement.** Les essais de génération ne sont pas des films terminés ni des validations de qualité.

## Production en cours — 1 novembre 2026

[**Le dernier geste — R03**](../productions/le-dernier-geste/README.md) dispose d’une coupe de travail de **9,25 s**, 222 images, 24 i/s, 720 × 1280. Le dossier contient le script de montage reproductible, le découpage, les paramètres G1, la provenance sonore et les contrôles techniques.

G1 est terminé ; le personnage animé reste l’ancien TEST19. Le plan d’éveil G2 définitif reste à produire. Les médias et archives demeurent dans le stockage privé, conformément à la politique ci-dessous. La R03 n’est pas un master final approuvé.

## Deux directions artistiques

### Painted Reality — prioritaire
Un pinceau entre en contact avec une sculpture brute ; la peinture se propage en respectant la matière et révèle l'œuvre. Signature recherchée : macro réaliste, transformation tactile, raccords motivés, fidélité au modèle physique.

### The Awakening
Une sculpture devient subtilement vivante : respiration, regard, tension musculaire, interaction avec son socle. Signature recherchée : suspense, précision anatomique, caméra cinématographique.

## Pipeline cible

1. **Préproduction** : sélection de l'œuvre, photographies authentiques, concept, storyboard et référence de mouvement.
2. **Analyse** : PySceneDetect / TransNetV2, SAM 2, CoTracker, contrôle de provenance et droits.
3. **Génération contrôlée** : image/vidéo avec modèles locaux ou hébergés ; prompt, paramètres, coût et limites conservés.
4. **VFX physiques** : Blender (3D, fractures, débris), Fusion (tracking, occlusion, compositing).
5. **Montage et son** : DaVinci Resolve, Fairlight, étalonnage et lecture mobile.
6. **Contrôle qualité** : cohérence des personnages, mouvements, matière, colorimétrie, audio, licences et validation humaine.

## Pistes de recherche

- One-to-All Animation / Wan Animate : transfert de mouvement de personnages.
- ComfyUI / Wan / LTX / HunyuanVideo : génération et workflows reproductibles.
- OpenTimelineIO : échanges structurés de timelines.
- Blender / Fusion / OpenColorIO : simulation et compositing.

Ces technologies sont des **candidates à tester**, non des composants installés ou validés.

## Tests Higgsfield — 30 octobre 2026

Les essais **The Awakening** et **Painted Reality** (Seedance 2.5, 5 s, 9:16, 720p) ont été générés à titre exploratoire.

Leur statut de génération ne vaut pas validation artistique. Les références authentiques et les droits des médias devront être vérifiés avant toute publication.

## Politique du dépôt

Ce dépôt est **public** tant que sa visibilité n'a pas été modifiée. Les médias sources, archives complètes, notes privées, informations de clients et exports non validés ne doivent pas y être ajoutés.

Voir [PRODUCTION.md](../PRODUCTION.md) et [SECURITY.md](../SECURITY.md).

## Archives et continuité — mise à jour du 1er novembre 2026

La mémoire historique disponible est progressivement versée dans `docs/historical/` : storyboard V25, registre R&D, manifeste V23, ancien bilan de consolidation et référence textuelle de la tour de contrôle. Les requêtes et résultats **Painted Reality** / **The Awakening** sont conservés dans `runs/higgsfield/`.

**Portée de la sauvegarde :** les documents et métadonnées ont été publiés ; le ZIP de travail préparé localement, les 28 médias récupérés, les PDF originaux et les MP4 Higgsfield ne sont **pas tous stockés sur GitHub**. Une archive annoncée comme préparée ne signifie pas qu'elle a été poussée. Un inventaire indique explicitement les éléments non publiés et les vérifications nécessaires.

Certaines images de la récupération historique montrent des personnes ou des captures de conversations non directement liées aux sculptures. Leur diffusion publique est suspendue tant que la provenance et les autorisations pertinentes ne sont pas vérifiées.

## Audit des données et suivi des générations

[Mode d’emploi opérationnel](OPERATIONS.md) · [Audit du 1 novembre](AUDIT_CONTINU_2026-11-01.md) · [Outils et essais](OUTILS_ET_ESSAIS.md).

Un contrôle technique couvre chaque push et chaque PR avec un inventaire SHA-256. Le journal local `bojart_ops` conserve requêtes, budgets, statuts et reçus sans appeler de fournisseur. L’analyse contextuelle des PR est programmée séparément ; les limites et les preuves figurent dans le mode d’emploi.
