#!/usr/bin/env python3
"""Restore a verified Jarvis workspace into a new directory, without replacing files."""
import argparse, json, sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'apps/jarvis/app'))
from workspace_state import restore_snapshot, verify_snapshot

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('archive',nargs='?');parser.add_argument('destination',nargs='?')
    parser.add_argument('--verify',action='store_true');parser.add_argument('--choose',action='store_true')
    args=parser.parse_args()
    if args.choose:
        try:
            import tkinter as tk
            from tkinter import filedialog, simpledialog, messagebox
            window=tk.Tk();window.withdraw()
            archive=filedialog.askopenfilename(title='Sauvegarde globale Jarvis',filetypes=[('Sauvegarde ZIP','*.zip')])
            if not archive:return
            parent=filedialog.askdirectory(title='Emplacement du nouveau dossier')
            if not parent:return
            name=simpledialog.askstring('Nouveau dossier','Nom du dossier à créer :',initialvalue='Jarvis-restaure')
            if not name:return
            if name in {'.','..'} or Path(name).name!=name or any(c in name for c in '/\\:'):raise ValueError('Choisir un nom de dossier simple.')
            result=restore_snapshot(archive,Path(parent)/name)
            messagebox.showinfo('Restauration vérifiée',str(result['verified_files'])+' fichiers vérifiés.\nDossier : '+result['destination']+'\nLes anciens fichiers sont conservés.')
        except Exception as e:
            if 'messagebox' in locals():messagebox.showerror('Restauration interrompue',str(e))
            else:print('Interface de choix indisponible. Utiliser : python tools/restore_workspace.py ARCHIVE NOUVEAU_DOSSIER',file=sys.stderr)
            raise SystemExit(1)
        return
    if not args.archive or (not args.verify and not args.destination):parser.error('Indiquer une archive et un nouveau dossier, ou utiliser --choose.')
    try:result=verify_snapshot(args.archive) if args.verify else restore_snapshot(args.archive,args.destination)
    except Exception as e:print('Restauration refusée : '+str(e),file=sys.stderr);raise SystemExit(1)
    print(json.dumps(result,ensure_ascii=False,indent=2))
if __name__=='__main__':main()
