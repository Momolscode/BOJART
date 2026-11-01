"""Serveur MCP local borné à la consultation du même audit."""
from mcp.server import MCPServer
from studio_core import load_snapshot
from durable import start_dbos, run_durable
from dbos import DBOS
from reverse_api_adapter import Scope, inspect_and_record
from durable import runtime_dir

server=MCPServer('Marwin Studio Local')

@server.tool()
def studio_status()->dict:
    """Lit le snapshot documentaire, jamais une conversation en direct."""
    s=load_snapshot();return {'source':s['source'],'scene':s['scene'],'scope':'snapshot local'}

@server.tool()
def studio_audit(stage:str='develop')->dict:
    """Contrôle développer/rendre/publier ; aucun effet externe."""
    return run_durable(stage)

@server.tool()
def connector_inspect_har(har:dict,origin:str,authority_ref:str,allow_loopback:bool=False)->dict:
    """Inspecte un HAR fourni hors ligne et journalise le contrat candidat, sans appel externe."""
    return inspect_and_record(har,Scope('marwin-studio',origin,authority_ref,allow_loopback),runtime_dir())

if __name__=='__main__':
    start_dbos()
    try:server.run()
    finally:DBOS.destroy()
