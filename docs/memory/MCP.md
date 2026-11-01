# Donner le même contexte aux assistants de code

Le serveur local stdio `tools/memory_mcp.py` implémente la capacité outils MCP, protocole `2025-06-18`. Il indexe les documents sélectionnés au démarrage et accède à la **même** base que Jarvis. Les sources renvoyées sont des données non fiables, pas des instructions.

Exemple de déclaration pour les clients acceptant `mcpServers` ; adapter les chemins absolus et le format si le client utilise une autre configuration :

```json
{
  "mcpServers": {
    "bojart-memory": {
      "command": "C:/BOJART/.venv/Scripts/python.exe",
      "args": ["C:/BOJART/tools/memory_mcp.py"],
      "env": {"BOJART_MEMORY_STATE": "C:/Users/UTILISATEUR/BOJART/memory"}
    }
  }
}
```

Linux : `command` vaut `/chemin/BOJART/.venv/bin/python`, et `args` contient `/chemin/BOJART/tools/memory_mcp.py`. Aucun serveur réseau MCP n’est ouvert. Le démarrage et les outils sont testés par échange JSON-RPC local ; l’interface de chaque client reste à configurer sur le poste.

| Outil | Entrée | Effet |
|---|---|---|
| `memory_search` | `query`, `project` facultatif | Passages cités, recherche lexicale et éventuellement sémantique |
| `memory_context` | `query`, `project` facultatif | Contexte borné, faits datés, contradictions, références |
| `memory_status` | Aucun champ | Compteurs et contrôle SQLite |
| `memory_note` | `key`, `value`, `source`, `project` facultatif | Ajout idempotent d’une proposition locale |

`project` : `bojart.jarvis` par défaut, `bojart.creative` ou `bojart.sites`. Aucun outil d’exécution, de suppression, d’impression ou de publication n’est exposé.

Le fichier `AGENTS.md` et le registre `data/knowledge/claims.jsonl` restent les points d’entrée lisibles sans MCP. La mémoire ne dispense jamais l’assistant de lire les fichiers qu’il modifie. Les notes issues de MCP ne sont pas automatiquement promues en décisions du projet.

Références : [transport stdio](https://modelcontextprotocol.io/specification/2025-06-18/basic/transports), [cycle de vie](https://modelcontextprotocol.io/specification/2025-06-18/basic/lifecycle), [outils](https://modelcontextprotocol.io/specification/2025-06-18/server/tools).
