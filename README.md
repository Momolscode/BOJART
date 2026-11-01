# BOJ.ART — Bilan de vérification de la sauvegarde

**Rapport daté du 1 novembre 2026.** Cette branche conserve le bilan demandé et ses annexes originales, séparément du logiciel courant. Elle ne doit pas être fusionnée dans `main`.

## Lecture

- [Bilan lisible](BILAN_VERIFICATION.md) : conclusion, méthode, références des trois branches d'archive et limites.
- [Archive originale du bilan](BOJART_VERIFICATION_SAUVEGARDE_2026-11-01.zip) : les quatre fichiers remis à l'utilisateur, sans modification.
- [Comparaison détaillée](comparison.json).
- [Éléments de preuve sélectionnés](remote_selected_evidence.json).
- [Script d'audit historique](audit.py) : conservé comme source, non exécuté par la publication.
- [Contrôle d'intégrité de cette publication](INTEGRITY.json).

Le ZIP original pèse **19 824 octets**. SHA-256 : `322626473beb2de1c69ae28bea1958d368ccb7bf34fb213c3829397fabf8efec`.

## Portée

Le contrôle rapproche le paquet créatif de **87 fichiers** avec la collecte de **3 340 contenus uniques** documentée dans les trois branches de récupération. Il distingue les vérifications locales du rapport antérieur de restauration globale. **La publication de ce bilan ne constitue pas une nouvelle restauration des 1,09 Go**, ni une validation de l'installation, des appareils ou de la qualité artistique.

Les chemins absents de `main` ne doivent pas être assimilés à des pertes sans vérifier les branches d'archive. Cette sauvegarde ne garantit pas un export intégral des conversations ou des fichiers restés uniquement sur le PC de l'atelier.

Le dossier de projet courant et le rapport de restauration de référence restent dans [main/docs/ETAT_ARCHIVES_2026-11-01.md](https://github.com/Momolscode/BOJART/blob/main/docs/ETAT_ARCHIVES_2026-11-01.md).

## Publication

Une action ponctuelle reconstruit le ZIP à partir des octets transmis, contrôle taille, SHA-256 et CRC, extrait uniquement les quatre membres attendus et publie leurs empreintes. Elle ne télécharge aucune autre donnée, ne lance aucune génération et n'exécute pas le script historique. La branche `main` et les trois branches de récupération ne sont pas modifiées.
