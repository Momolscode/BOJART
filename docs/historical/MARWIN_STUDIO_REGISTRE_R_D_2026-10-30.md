# MARWIN STUDIO / BOJ.ART — Registre R&D et direction artistique
Date : 2026-10-30
Statut : document de continuité, pas preuve d'installation ou de qualité finale.

## Idée stratégique conservée
Créer une tour BOJ.ART équipée à terme d'un GPU NVIDIA RTX, orchestrée avec ComfyUI, pour réaliser des édits premium hybrides : animation IA locale, VFX 3D simulés, compositing, montage, étalonnage et sound design. Cible exploratoire : 24–32 Go de VRAM, à ajuster selon modèle, budget et benchmarks. La tour BOJ.ART est distincte des autres projets et configurations informatiques.

## Critères artistiques non négociables
- Ne pas livrer un diaporama animé comme un édit premium.
- Fidélité à la sculpture authentique, à son visage, sa tenue, sa peinture et son socle.
- Animation crédible et raccords cohérents, sans mutations de personnage.
- Destruction et impacts physiquement plausibles, 3D et compositing soigné.
- Son professionnel, mixage et silence intentionnel ; pas de bruitages synthétiques bas de gamme.
- Mesurer les résultats, conserver prompts, graines, modèles, paramètres, médias, licences, coûts et échecs.

## Domaines à approfondir (backlog priorisé)
1. Références et acquisition : TikTok public, API autorisées, droits, provenance, inventaire des rushs, sauvegardes.
2. Reverse engineering créatif : découpage PySceneDetect/TransNetV2, tracking CoTracker, segmentation SAM2, analyse caméra, optical flow, rythme et audio.
3. Écriture et DA : concept, tension, rétention, storyboard, animatique, continuity bible, composition et optiques.
4. Animation : One-to-All 1.3B/14B, Wan 2.2 Animate, Wan Animate 2, performance capture, poses, identité, LoRA.
5. Génération : LTX-2.5, Wan, HunyuanVideo, ComfyUI, paramètres reproductibles, VRAM et latence.
6. VFX : Blender rigid bodies, fracture, débris, fumée, collisions, suivi caméra, rendu EXR.
7. Compositing et couleur : Fusion, occlusion, motion blur, grain, ACES/OpenColorIO, matching.
8. Montage : OpenTimelineIO, FFmpeg, Resolve, transitions motivées, tests mobile 9:16.
9. Audio : Foley, couches sonores, ambiances, impacts, mixage, loudness, droits musicaux.
10. Infrastructure : RTX, stockage, GPU distant de secours, versions, licences commerciales, CI et sauvegardes 3-2-1.
11. Contrôle qualité : identité, anatomie, physique, temporalité, artefacts, cohérence sonore, score et validation humaine.
12. Production/économie : devis, crédits, coûts GPU, temps de rendu, révisions, livrables et portfolio.

## Nouveautés documentées (sources vérifiées le 30/10/2026)
- Wan Animate 2, ComfyUI, vidéo de performance directement conditionnée, contrôle du point de vue, variante Lite : https://blog.comfy.org/p/wan-animate-2-is-now-available-in
- Wan 2.2 Animate : workflows Mix et Move, dépendances et contraintes dimensions : https://github.com/Comfy-Org/docs/blob/main/tutorials/video/wan/wan2-2-animate.mdx
- One-to-All Animation : poids 1.3B v1/v2 et 14B, code d'entraînement/évaluation : https://github.com/elvisxu/one-to-all-animation
- LTX-2.5 : modèles locaux, audio-vidéo, image-to-video, pipelines Python : https://docs.ltx.io/open-source-model/getting-started/quick-start
- Blender VFX : tracking caméra/objet, compositing multilayer OpenEXR : https://www.blender.org/features/vfx/
- OpenTimelineIO : interchange éditorial ; vérifier la compatibilité de chaque éditeur : https://summerofcode.withgoogle.com/programs/2026/projects/IVkxBrR2

## Benchmark à exécuter quand RTX disponible
Même sculpture authentique + même performance de 4 à 6 secondes ; comparer One-to-All 1.3B, Wan 2.2 Animate, Wan Animate 2 et LTX en image-to-video (tâches non identiques, comparer selon objectifs). Garder les rendus bruts et noter fidélité visuelle, motion, anatomie, contact, artefacts, VRAM, temps, coût, licence. Finaliser les effets dans Blender/Fusion, jamais en les confondant avec la sortie brute du modèle.

## État des preuves
Idée et recherches : documentées. Intégration et rendu premium final : non démontrés. Dépôts, GPU futur, installations et médias exhaustifs : à vérifier.