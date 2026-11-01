"""Read-only, bounded hardware inventory. No file crawl, serials, network scan or installation."""
from __future__ import annotations
import importlib.metadata, importlib.util, json, os, platform, shutil, subprocess
from datetime import datetime, timezone
from pathlib import Path

def run_fixed(args):
    """Only callers below provide predefined commands; never call with a user prompt."""
    if not shutil.which(args[0]):return {'status':'not_found','value':None}
    try:
        result=subprocess.run(args,capture_output=True,text=True,encoding='utf-8',errors='replace',
                              timeout=7,check=False,shell=False)
        if result.returncode:return {'status':'unavailable','value':None}
        return {'status':'measured','value':result.stdout.strip()[:10000]}
    except (OSError,subprocess.TimeoutExpired):return {'status':'unavailable','value':None}

def memory_gib():
    try:
        if platform.system()=='Windows':
            import ctypes
            class Status(ctypes.Structure):
                _fields_=[('dwLength',ctypes.c_ulong),('dwMemoryLoad',ctypes.c_ulong)]+[(n,ctypes.c_ulonglong) for n in ['ullTotalPhys','ullAvailPhys','ullTotalPageFile','ullAvailPageFile','ullTotalVirtual','ullAvailVirtual','ullAvailExtendedVirtual']]
            st=Status();st.dwLength=ctypes.sizeof(st)
            if not ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(st)):return None
            return round(st.ullTotalPhys/(1024**3),1)
        return round(os.sysconf('SC_PHYS_PAGES')*os.sysconf('SC_PAGE_SIZE')/(1024**3),1)
    except (ValueError,OSError,AttributeError):return None

def version(name):
    try:return importlib.metadata.version(name)
    except importlib.metadata.PackageNotFoundError:return None

def collect(state_root):
    # No CPU/GPU claims derived from the quoted price of the target tower.
    gpu=run_fixed(['nvidia-smi','--query-gpu=name,memory.total,driver_version','--format=csv,noheader,nounits'])
    gpus=[]
    if gpu['status']=='measured':
        for line in gpu['value'].splitlines():
            parts=[p.strip() for p in line.split(',')]
            if len(parts)==3:
                try:gpus.append({'name':parts[0],'vram_mib':int(float(parts[1])),'driver':parts[2]})
                except ValueError:pass
    disk=shutil.disk_usage(state_root)
    ram=memory_gib()
    report={'schema':'bojart.diagnostic.v1','observed_at':datetime.now(timezone.utc).isoformat(),
            'scope':'Hôte qui exécute ce diagnostic ; à distinguer du futur PC BOJ.ART.',
            'os':{'family':platform.system(),'release':platform.release(),'architecture':platform.machine()},
            'cpu_logical_count':os.cpu_count(),'ram_gib':ram,
            'storage_free_gib':round(disk.free/(1024**3),1),
            'nvidia_gpus':gpus,'gpu_detection_status':gpu['status'],
            'packages':{x:version(x) for x in ['cadquery','trimesh','faster-whisper']},
            'python':platform.python_version(),
            'capabilities':{'physical_commands':False,'media_scan':False,'network_scan':False,'downloads':False},
            'unmeasured':['audio réel','bruit atelier','nombre d’écrans et résolution','puissance sous charge','imprimantes','autres GPU non NVIDIA']}
    report['recommendation']={
        'action':'Benchmarks avant sélection définitive, aucun achat proposé automatiquement.',
        'cad':'Tester une génération 180 mm avec relecture des fichiers.',
        'speech':'Tester la transcription CPU pour ne pas réserver le GPU au démarrage.',
        'llm':'Choisir parmi les modèles déjà installés et compatibles, puis mesurer leur qualité en français.',
        'memory_policy':'Un travail lourd à la fois au pilote ; VRAM totale non assimilée à la mémoire libre.'}
    return report
