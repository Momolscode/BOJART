# BOJART — Marwin Studio

Projet de direction artistique et de production audiovisuelle hybride pour les sculptures et créations de BOJ.ART.

> **État : recherche & développement.** Les essais de génération ne sont pas des films terminés ni des validations de qualité.

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

Voir [PRODUCTION.md](PRODUCTION.md) et [SECURITY.md](SECURITY.md).
