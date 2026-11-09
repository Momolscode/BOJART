#!/usr/bin/env python3
"""Audit non destructif, sans dépendance tierce ni exploration de fichiers privés."""
import json, os, platform, shutil, subprocess, datetime
from pathlib import Path
def command(args):
    try:
        p=subprocess.run(args,capture_output=True,text=True,timeout=8,check=False)
        return (p.stdout or p.stderr).strip()[:3500]
    except Exception as exc:
        return f"indisponible: {type(exc).__name__}"
def safe_disk():
    try:
        d=shutil.disk_usage(Path.home())
        return {"total_GB":round(d.total/1e9,1),"free_GB":round(d.free/1e9,1)}
    except Exception: return {}
report={
 "timestamp_utc":datetime.datetime.now(datetime.timezone.utc).isoformat(),
 "os":platform.platform(),"architecture":platform.machine(),
 "cpu":platform.processor(),"logical_cpus":os.cpu_count(),
 "home_disk":safe_disk(),
 "gpu_nvidia":command(["nvidia-smi","--query-gpu=name,memory.total,driver_version","--format=csv,noheader"]),
 "gpu_linux":command(["lspci"]) if platform.system()=="Linux" else "non applicable",
 "memory_linux":command(["free","-h"]) if platform.system()=="Linux" else "non applicable",
 "screens_linux":command(["xrandr","--listmonitors"]) if platform.system()=="Linux" else "non applicable",
 "python":platform.python_version(),
 "notes":"Lecture seule. Aucune exploration des médias, comptes, fichiers personnels ni secrets."
}
out=Path.cwd()/("BOJART_AUDIT_PC_"+datetime.datetime.now().strftime("%Y%m%d_%H%M%S")+".json")
out.write_text(json.dumps(report,indent=2,ensure_ascii=False),encoding="utf-8")
print("Rapport créé :",out)
