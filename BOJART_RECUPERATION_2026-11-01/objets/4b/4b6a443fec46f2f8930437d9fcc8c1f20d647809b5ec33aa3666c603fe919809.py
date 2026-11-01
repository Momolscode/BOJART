"""Point d'entrée local reproductible ; aucun appel à un modèle."""
import argparse,json
from dbos import DBOS
from durable import start_dbos,run_durable

if __name__=='__main__':
    p=argparse.ArgumentParser()
    p.add_argument('--stage',choices=['develop','render','publish'],default='develop')
    args=p.parse_args()
    start_dbos()
    try:print(json.dumps(run_durable(args.stage),ensure_ascii=False,indent=2))
    finally:DBOS.destroy()
