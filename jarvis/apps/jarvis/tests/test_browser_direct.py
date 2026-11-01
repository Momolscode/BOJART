"""Run on the authorized target PC. No policy override; fail visibly if localhost is blocked.
Requires Playwright + installed Chromium for development verification, not for the user UI.
"""
import os,sys,tempfile,threading
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'app'))
from core import Store
from workbench import Workbench
from playwright.sync_api import sync_playwright
def main():
 with tempfile.TemporaryDirectory() as td:
  s=Workbench(('127.0.0.1',0),Store(td),token='local-e2e-test')
  threading.Thread(target=s.serve_forever,daemon=True).start()
  try:
   with sync_playwright() as p:
    kwargs={'headless':True}
    if os.environ.get('BOJART_CHROMIUM_PATH'):kwargs['executable_path']=os.environ['BOJART_CHROMIUM_PATH']
    b=p.chromium.launch(**kwargs);page=b.new_page()
    page.goto(s.origin+'/?session=local-e2e-test')
    page.locator('#prepare').click();page.wait_for_function("!document.getElementById('confirm').disabled")
    page.locator('#confirm').click();page.wait_for_function("document.getElementById('modelRev').textContent==='R1'",timeout=120000)
    assert s.store.project_revision()==1
    b.close();print('DIRECT_BROWSER_HTTP_CAD_PASS')
  finally:s.shutdown();s.server_close()

if __name__=="__main__":main()
