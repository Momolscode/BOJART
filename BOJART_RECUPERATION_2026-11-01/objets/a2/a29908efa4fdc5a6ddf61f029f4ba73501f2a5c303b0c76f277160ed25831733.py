#!/usr/bin/env python3
"""Explicit download of the version used for this calibration; run once."""
import argparse, json
from pathlib import Path
from huggingface_hub import snapshot_download
ap=argparse.ArgumentParser();ap.add_argument('--out',required=True,type=Path);a=ap.parse_args()
p=snapshot_download('Systran/faster-whisper-tiny',revision='d90ca5fe260221311c53c58e660288d3deb8d356',local_dir=str(a.out.resolve()),allow_patterns=['config.json','model.bin','tokenizer.json','vocabulary.*','preprocessor_config.json'],max_workers=2)
print(json.dumps({'model_directory':p,'network_used':'model download only; no user media uploaded'}))
