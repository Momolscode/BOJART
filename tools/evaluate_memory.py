#!/usr/bin/env python3
"""Small lexical retrieval regression set; not an LLM or hardware benchmark."""
import json
import sys
import tempfile
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from bojart_memory import Memory

def evaluate():
    records=json.loads((ROOT/'data/knowledge/index.json').read_text())
    cases=json.loads((ROOT/'data/knowledge/retrieval_cases.json').read_text())
    with tempfile.TemporaryDirectory() as state, Memory(state) as memory:
        for r in records:memory.ingest_file(ROOT/r['path'],root=ROOT,project=r['project'],collection='canonical',provenance=r['provenance'],kind='project_document')
        results=[]
        for case in cases:
            found=memory.search(case['question'],project=case['project'],limit=5)['results']
            paths=[r['source_path'] for r in found]
            results.append({**case,'hit_at_5':case['expected_source'] in paths,'returned_sources':paths,'all_citations_verified':all(r['source_bytes_verified'] for r in found)})
    return {'scope':'10 hand-authored lexical retrieval cases over selected documents; no generative-answer evaluation','cases':len(results),'hits_at_5':sum(r['hit_at_5'] for r in results),'results':results}

if __name__=='__main__':
    r=evaluate();print(json.dumps(r,ensure_ascii=False,indent=2));raise SystemExit(0 if r['hits_at_5']==r['cases'] else 1)
