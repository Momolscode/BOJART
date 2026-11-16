# Ce qui a réellement avancé

## Livré
1. Un dialogue français borné accepte désormais des variantes de formulation et des nombres écrits en lettres. Le diamètre est extrait et converti par du code déterministe, jamais inventé par le modèle.
2. Une proposition durable conserve la révision, le contexte utilisé, l’origine (texte/transcription relue), les paramètres et la décision. Elle expire au bout de 10 minutes. La même confirmation retrouve son résultat après une réponse perdue.
3. Le moteur géométrique M01 reste indépendant du modèle de langage. Une nouvelle interface expose clairement texte, proposition, fichier et contrôles.
4. L’adaptateur Ollama est codé, limité au serveur local et aux formats attendus. Il ne télécharge aucun poids. Un résultat de modèle incompatible avec les preuves est rejeté.
5. Capture vocale explicite, encodeur WAV, transcripteur local facultatif et lecture vocale locale facultative sont câblés. Par défaut, le micro est indisponible tant que le moteur n’est pas configuré. La transcription reste un brouillon.
6. Diagnostic en lecture seule : RAM, architecture, versions, stockage libre et sonde NVIDIA éventuelle. Aucune décision d’achat ou de modèle définitive n’en découle automatiquement.
7. Lanceurs Windows et Linux utilisent l’environnement isolé en priorité ; aucune dépendance n’est installée sans contrôle.

## Réaudit : ce qui reste à ne pas confondre
- Conversation bornée ≠ agent universel. Figurines, calculs mécaniques, modifications arbitraires et fabrication restent hors de cette recette.
- Fichiers de poids présents ≠ reconnaissance vocale qualifiée. Le chargement et la précision restent à vérifier.
- JSON valide ≠ choix juste. L’adaptateur vérifie aussi la dimension explicitement demandée.
- Fournisseur sur localhost ≠ absence prouvée de trafic extérieur. Le contrôle hors ligne doit être réalisé sur le poste.
- Champ « affiche à droite » ≠ moniteur physique appairé. Dans ce module, il s’agit du panneau 3D à droite.
- Archives avec empreintes ≠ signature de l’éditeur ou chiffrement. Conserver sur un support autorisé, tester la restauration.
- Nouveau module livré ≠ site de production mis à jour. Les sources et données du produit hébergé restent à réunir avant intégration.

## Ce que les tests disent
Les tests de géométrie exécutent réellement CadQuery. Les réponses d’Ollama et du transcripteur sont des doublures contrôlées. Chromium teste l’interface via un pont de développement explicitement nommé vers le vrai serveur local ; sa connexion réseau directe est bloquée dans cet environnement. Le test direct est fourni pour la tour. Aucun contournement de politique, aucun accès au PC de l’utilisateur.

## Priorités suivantes
A. Passer la recette directe sur la tour et relever les ressources disponibles.
B. Qualifier un modèle local et le microphone en français, y compris silence, bruit, hésitations et unités.
C. Ajouter la consultation indexée de sources BOJ.ART autorisées ; séparer contenu documentaire et état courant.
D. Raccorder un slicer, puis une FDM et une résine sur fichiers versionnés et préconditions explicites.
E. Appliquer la même traçabilité aux générations vidéo : référence authentique, budget, fichier, validation de fidélité et accord artistique.

Aucun nouveau budget, compte social, rendu payant ou achat engagé par ce module.
