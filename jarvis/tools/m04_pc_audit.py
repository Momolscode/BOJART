#!/usr/bin/env python3
"""Read-only BOJ.ART PC inventory. No directory crawl, network scan or printer call."""
import argparse, json, sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'apps/jarvis/app'))
from diagnostics import collect

def main():
 p=argparse.ArgumentParser(description=__doc__)
 p.add_argument('--output',type=Path,help='Optional destination for the report JSON (no automatic upload).')
 a=p.parse_args()
 report=collect(ROOT)
 report['launch_scope']='Inventory of this host only; no acceptance of printers or physical monitors.'
 text=json.dumps(report,ensure_ascii=False,indent=2)+'\n'
 if a.output:
  if a.output.exists():raise SystemExit('Refus d’écraser un rapport existant.')
  a.output.parent.mkdir(parents=True,exist_ok=True)
  a.output.write_text(text,encoding='utf-8')
  print('Rapport local enregistré :',a.output)
 else:print(text)
if __name__=='__main__':main()
