import argparse
import json
from pathlib import Path
import sqlite3
from .ledger import Ledger


def main():
    p=argparse.ArgumentParser(description='BOJART local generation receipts; no generation is launched.')
    p.add_argument('--db',type=Path,default=Path.home()/'BOJART/operations/generations.sqlite3')
    sub=p.add_subparsers(dest='command',required=True)
    b=sub.add_parser('budget'); b.add_argument('id'); b.add_argument('ceiling')
    r=sub.add_parser('plan');r.add_argument('id');r.add_argument('request',type=Path);r.add_argument('--budget',required=True);r.add_argument('--max-credits',required=True)
    for name in ('begin','unknown','show'):
        sub.add_parser(name).add_argument('id')
    r=sub.add_parser('receipt');r.add_argument('id');r.add_argument('job_id');r.add_argument('status')
    a=sub.add_parser('attach');a.add_argument('id');a.add_argument('file',type=Path);a.add_argument('--sha256',required=True)
    sub.add_parser('export')
    sub.add_parser('backup').add_argument('destination',type=Path)
    args=p.parse_args()
    with Ledger(args.db) as ledger:
        if args.command=='budget': result=ledger.set_budget(args.id,args.ceiling)
        elif args.command=='plan':
            from .audit import strict_json
            result=ledger.plan(args.id,strict_json(args.request.read_text(encoding='utf-8')),args.budget,args.max_credits)
        elif args.command=='receipt':result=ledger.receipt(args.id,args.job_id,args.status)
        elif args.command=='attach':result=ledger.attach(args.id,args.file,args.sha256)
        elif args.command=='show':result=ledger.get(args.id)
        elif args.command=='backup':result=ledger.backup(args.destination)
        else:result=getattr(ledger,args.command)(args.id) if args.command!='export' else ledger.export()
    print(json.dumps(result,ensure_ascii=False,indent=2))


if __name__=='__main__':
    try:main()
    except (OSError,ValueError,sqlite3.Error) as exc:raise SystemExit(str(exc))
