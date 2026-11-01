"""Audit documentaire et décision locale, sans génération ni jugement automatique."""
from pathlib import Path
from typing import TypedDict
import sys, hashlib, json
sys.path.insert(0, str(Path(__file__).parent/'control'/'MARWIN_Atelier_Controle'))
from controle import scene_gate
from langgraph.graph import StateGraph, START, END

ROOT=Path(__file__).parent
PIPELINE_VERSION='0.1.0'

class State(TypedDict, total=False):
    snapshot: dict
    stage: str
    report: dict
    decision: dict

def audit(state):
    s=state['snapshot']
    return {'report':{'source':s['source'], 'episodes':s['episodes'],
        'latest_feedback':s['latest_feedback'], 'scope':'Audit documentaire, sans nouveau visionnage ni écoute.',
        'lessons':s['lessons'], 'scene':s['scene'], 'audience_metrics':None}}

def decide(state):
    reasons=scene_gate(state['report']['scene'],state['stage'])
    return {'decision':{'stage':state['stage'],'eligible':not reasons,'reasons':reasons,
        'pipeline_version':PIPELINE_VERSION,
        'effects_executed':False,'scope':'Cohérence déclarative ; pas autorisation de génération ou publication.'}}

def make_graph():
    g=StateGraph(State);g.add_node('audit',audit);g.add_node('decision',decide)
    g.add_edge(START,'audit');g.add_edge('audit','decision');g.add_edge('decision',END)
    return g.compile()

GRAPH=make_graph()

def load_snapshot():
    return json.loads((ROOT/'data'/'studio_snapshot.json').read_text())

def run_local(stage='develop'):
    if stage not in ('develop','render','publish'):raise ValueError('stage inconnu')
    result=GRAPH.invoke({'snapshot':load_snapshot(),'stage':stage})
    return {'report':result['report'],'decision':result['decision']}

def digest(value):
    return hashlib.sha256(json.dumps(value,sort_keys=True,ensure_ascii=False).encode()).hexdigest()
