#!/usr/bin/env python3
"""Read-only launch report: no microphone, no downloads, no provider request."""
import argparse, importlib.metadata, json, os, sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'apps/jarvis/app'))
from workbench import load_config
from voice import LocalVoice
from jev_decider import JevDecider


def report(config=None):
    versions={}
    for name in ('cadquery','trimesh','langgraph','langgraph-checkpoint-sqlite','faster-whisper'):
        try:versions[name]=importlib.metadata.version(name)
        except importlib.metadata.PackageNotFoundError:versions[name]=None
    return {'schema':'bojart.preflight.m06.v1','packages':versions,
            'voice':LocalVoice(load_config(config)['voice']).status(), 'jev':JevDecider().status(),
            'required_configuration':['voice.enabled and voice.model_dir in local config','BOJ_JEV_ENABLED=1 and server-only TYPESAFE_API_KEY for optional Jev'],
            'target_pc_tested':False,'microphone_tested':False,'external_calls':0,'production_ready':False}


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--config');args=parser.parse_args()
    print(json.dumps(report(args.config),ensure_ascii=False,indent=2))
