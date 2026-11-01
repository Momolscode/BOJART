import { readFile } from 'node:fs/promises';
import { resolve } from 'node:path';
import { spawnSync } from 'node:child_process';
const browser=JSON.parse(await readFile('../evidence/browser.json','utf8'));
const result=spawnSync(resolve('node_modules/.bin/hyperframes'),process.argv.slice(2),{stdio:'inherit',env:{...process.env,HYPERFRAMES_BROWSER_PATH:browser.path}});
if(result.error)throw result.error;
process.exitCode=result.status??1;
