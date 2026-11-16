# BOJ.ART — Archive des sources vérifiées (01/11/2026)

Cette branche conserve les binaires originaux d'une sélection **pertinente pour BOJ.ART / Marwin Studio**. L'intégrité a été contrôlée par SHA-256 et, à la création des blobs Git, par correspondance exacte des empreintes Git.

## Disponibles directement
- `docs/historical/BOJART_BREAK_THE_FRAME_V6_STORYBOARD_AUDIT.pdf`
- `docs/historical/BOJ_ART_Atelier_3D_Plan_de_mise_en_oeuvre.pdf`

## Disponibles sous forme de fragments binaires
- `BOJ_ART_Reaudit_Concept_2026-10-19.pdf`
- `MARWIN_Audit_Global_2026-10-25.pdf`
- `BOJART_BREAK_THE_FRAME_PREVISUAL_V1.mp4` (prévisualisation non validée, **pas** un master premium).

Les fragments sont de véritables octets bruts, et non de la base64. Leur somme restitue exactement les fichiers d'origine.

### Restauration sans installer de logiciel tiers

Depuis le dépôt cloné :

```bash
python tools/restore_archive_2026_11_01.py --destination ./BOJART_RESTAURE
```

Le programme refuse d'écraser une destination existante et vérifie chaque fragment puis chaque fichier reconstruit contre `archive/2026-11-01/MANIFEST.json`.

## Non inclus dans cette archive publique

- Le PDF de lancement des associés, dont une portion binaire a été refusée par les contrôles de sécurité.
- Les portraits privés, captures de conversations et médias non directement attribuables aux sculptures BOJ.ART.
- Les médias non garantis libres de diffusion et les archives de contexte personnel non vérifiées.
- Les deux MP4 finaux de génération Higgsfield *Painted Reality* / *The Awakening*, dont seuls les jobs et paramètres sont enregistrés dans le dépôt ; ils ne sont pas téléchargés ici.
- Les anciens rushs/projets After Effects/DaVinci non récupérés.

Ce dépôt public n'est pas une sauvegarde exhaustive de toutes les conversations et sources historiques. Conserver les ZIP originaux dans une sauvegarde indépendante.
