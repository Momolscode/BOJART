#!/usr/bin/env python3
from pathlib import Path
import shutil,subprocess,sys
R=Path(__file__).resolve().parents[1]
node=shutil.which('node')
if not node:raise SystemExit('Node.js requis pour les tests de signal M07 ; le lancement de Jarvis utilise Python.')
checks=[([node,'--test','tests/voice_endpoint.test.cjs'],R),
 ([sys.executable,'-m','unittest','discover','-s','tests','-v'],R),
 ([sys.executable,'-m','pytest','tests/test_mission01.py','tests/test_m02.py','tests_m03/test_media_library.py','tests_m03/test_studio_http.py','-q'],R/'apps/jarvis'),
 ([sys.executable,'-m','unittest','discover','-s','tests','-v'],R/'knowledge/metier'),
 ([sys.executable,'-m','unittest','test_planner','-v'],R/'labs/planning/prototype')]
for args,cwd in checks:
 p=subprocess.run(args,cwd=cwd)
 if p.returncode:raise SystemExit(p.returncode)
print('All selected suites passed. No live model, microphone, printer or GitHub remote was tested.')
