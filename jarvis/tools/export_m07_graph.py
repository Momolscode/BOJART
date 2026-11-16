#!/usr/bin/env python3
"""Export the installed local graph as JSON and simple Mermaid, without a request."""
import json, sys, tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'apps/jarvis/app'))
from core import Store
from consolidated_workbench import ConsolidatedWorkbench


def export():
    out=ROOT/'docs/m07';out.mkdir(parents=True,exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='boj-graph-') as tmp:
        app=ConsolidatedWorkbench(('127.0.0.1',0),Store(tmp))
        try:
            if app.jarvis.graph is None:raise SystemExit('Installer requirements-orchestration.txt pour exporter le graphe réel.')
            graph=app.jarvis.graph.get_graph();data=graph.to_json()
            (out/'GRAPHE_EXECUTE.json').write_text(json.dumps(data,ensure_ascii=False,indent=2))
            labels={'__start__':'Début','__end__':'Fin','route':'route · intention','guard':'guard · vérification',
                    'dispatch':'dispatch · distribution','receipt':'receipt · journal et résultat'}
            lines=['flowchart TD']
            for key,label in labels.items():lines.append('  '+key+'["'+label+'"]')
            for edge in graph.edges:
                label='|valide|' if edge.source=='guard' and edge.target=='dispatch' else '|refus ou confirmation|' if edge.source=='guard' else ''
                lines.append('  '+edge.source+' -->'+label+' '+edge.target)
            (out/'GRAPHE_EXECUTE.mmd').write_text('\n'.join(lines)+'\n')
            return {'nodes':len(graph.nodes),'edges':len(graph.edges),'requests_executed':0}
        finally:app.server_close()


if __name__=='__main__':print(json.dumps(export()))
