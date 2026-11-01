from pathlib import Path,PurePosixPath
import zipfile,hashlib,json,collections
ROOT=Path('/mnt/data/bojart_verification')
ZIP=Path('/mnt/data/BOJART_MARWIN_PRET_GITHUB_2026-11-01.zip')
COMMIT='3c288214539adf97381f6053b43225485a873b6a'

def blob(b):return hashlib.sha1(b'blob '+str(len(b)).encode()+b'\0'+b).hexdigest()
# Transcription of GitHub API tree entries returned by the connected GitHub read tools.
# Each mapping below is checked at the pinned commit, not against a moving main branch.
remote={
'.gitattributes':('5cda778c545dddb0de854fb0fe55abae953a5f93',72),
'.gitignore':('fd63e61ce7e08e8277a92546541405ddbb20c30f',596),
'README.md':('6ff86cd6ba375eff2a8f19f98b27718448918367',4231),
'docs/historical/BOJART_BREAK_THE_FRAME_V6_STORYBOARD_AUDIT.pdf':('0c6b2ddf774e746bd6e4b0d0774bad42787eef13',784472),
'docs/historical/BOJART_MANIFEST_V23.json':('43f2637ee57aa13e9e048b18b47420978fea2ee5',1476),
'docs/historical/BOJART_V25_STORYBOARD.md':('da1226e8d6c05145db2cc47368e215a9897eb1d6',2819),
'docs/historical/BOJ_ART_Atelier_3D_Plan_de_mise_en_oeuvre.pdf':('7bc136970627d04dd7f858ecd74b63b79c121734',1014463),
'docs/historical/MARWIN_STUDIO_REGISTRE_R_D_2026-10-30.md':('840521027a23f0455b31d0d4801d317b715e32e3',4156),
'runs/higgsfield/painted-reality-01/prompt.txt':('a891c07fe86bcea4fa57bbef9f5ab525d7d28e8a',1112),
'runs/higgsfield/painted-reality-01/request.json':('e62c42a84564137a3e7adece9e4efedc99d01d06',1250),
'runs/higgsfield/painted-reality-01/status.json':('5e8d0cb9931f7ce4759eacee3ad5fc599941afad',703),
'runs/higgsfield/the-awakening-01/prompt.txt':('776eb15ffb076275976467b0ee4f272344dd3e0c',1043),
'runs/higgsfield/the-awakening-01/request.json':('5d69f01f5aef01ef6533da25b6bc3f1b022d572d',1181),
'runs/higgsfield/the-awakening-01/status.json':('3c3a19aa10cb567de7f764d47faabf676d68f6f0',703),
' tools/download_remote_media.py'.strip():('9302dbd2e490af7627b8eba20d22f402f40119f7',2886),
'tools/verify_manifest.py':('4e377aa78869ee164c12d82c2b7d244da97509c1',1849),
}
chunk_shas={
'BOJART_BREAK_THE_FRAME_PREVISUAL_V1.mp4':[
'd2515030ff8624959871a1882894632c777b7473','ab38a9cf06640308ca6da25e3aedd46d9f78e329','1bbe3d0def48b25e5751ad3e65cd5800baa1e1a2','0f2306e0b333add84eb113a71e182e7069205df9','9d0ed3904fb4462bf6da1672b3a73e3dbeafa19a'],
'BOJ_ART_Reaudit_Concept_2026-10-19.pdf':[
'e9d52a6d7c9e7fc68f48be111ab091bc386cf371','8640b2828062bdf025a6d70bb99d8e3ff371d687','eb865fd942f2a628bb126545b648f3f446eadf81'],
'MARWIN_Audit_Global_2026-10-25.pdf':[
'51fc3015961e86885692efa637ab54b3ab926bbc','70eeeb20832a835322dca673347c99905cb43f79','02c4180220be8fab31f423f358885e287c79ddd7','ad21e32f7522e36d051c8372a438d0a4b27eb5c9','31d127c56f0e53cf211b81cbdc4887cacd740bc5','34ec0eb98935558cf61ca0af0bc4d4014e29eeda','c9e0cdb136d97c694cffc90554b049b47b837d35','cec7ea50d79432e4a454b198787ea12cda3edb18','769bc207b5561fa6e1650ca6a893ec5745fcccc9','91dfbd9e57517a438411b0f94c22299401d11887','efd81d47308c88b6abf259b66ef4ce56fd185155','a3c50ae4ccd863dc662e592b1c9157dd89b3b6d8']}
source_prefix='BOJART_MARWIN_GITHUB_2026-11-01/'
with zipfile.ZipFile(ZIP) as z:
 files={n[len(source_prefix):]:z.read(n) for n in z.namelist() if n.startswith(source_prefix) and not n.endswith('/')}
 entries=z.infolist()
 manifest=json.loads(files['MANIFEST_SHA256.json'])
 records={x['path']:x for x in manifest['files']}
 errors=[]
 for p,rec in records.items():
  if p not in files: errors.append({'path':p,'error':'missing'})
  elif rec['bytes']!=len(files[p]) or rec['sha256']!=hashlib.sha256(files[p]).hexdigest():errors.append({'path':p,'error':'checksum_or_size'})
 extras=sorted(set(files)-set(records)-{'MANIFEST_SHA256.json'})
 rows=[]; checks=[]
 for p,b in files.items():
  sha=blob(b)
  row={'path':p,'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest(),'git_blob_sha':sha,'manifest_covered':p in records}
  if p in remote:
   rs,rn=remote[p]
   row.update({'remote_blob_sha':rs,'remote_bytes':rn,'status':'identical' if sha==rs and len(b)==rn else 'different_version'})
  elif PurePosixPath(p).name in chunk_shas:
   name=PurePosixPath(p).name
   pieces=[b[i:i+900000] for i in range(0,len(b),900000)]
   expected=chunk_shas[name]
   match=(len(pieces)==len(expected))
   parts=[]
   for i,part in enumerate(pieces):
    actual=blob(part);target=expected[i] if i<len(expected) else None
    matched=actual==target;match=match and matched
    parts.append({'path':f'archive/2026-11-01/chunks/{name}.part{i:03d}','bytes':len(part),'local_blob_sha':actual,'remote_blob_sha':target,'match':matched,'sha256':hashlib.sha256(part).hexdigest()})
   row.update({'status':'identical_via_chunks' if match else 'chunks_mismatch','remote_location':'archive/2026-11-01/chunks/','parts':parts})
   checks.extend(parts)
  else:
   row['status']='absent_at_expected_path'
  rows.append(row)
 summary={
  'scope':'Comparison of the local BOJART_MARWIN_PRET_GITHUB archive against its expected repository paths plus the documented archive/2026-11-01 chunk layout. Does not audit every unrelated Jarvis file or search arbitrary renamed copies inside other archives.',
  'repository':'Momolscode/BOJART','snapshot_commit':COMMIT,'zip_filename':ZIP.name,'zip_bytes':ZIP.stat().st_size,'zip_sha256':hashlib.sha256(ZIP.read_bytes()).hexdigest(),
  'zip_entries':len(entries),'zip_regular_files':len(files),'zip_directory_entries':sum(e.is_dir() for e in entries),'zip_crc_failure':z.testzip(),
  'manifest_records':len(records),'manifest_errors':errors,'unmanifested_files_excluding_manifest':extras,
  'comparison_counts':dict(collections.Counter(x['status'] for x in rows)),
  'chunk_verification':{'chunks_checked':len(checks),'mismatches':sum(not c['match'] for c in checks),'method':'Compare SHA1(blob header + original local bytes) to GitHub tree object SHA, and compute local per-part SHA256. No network re-download performed.'},
  'source_tree_evidence':{'root':'3c288214539adf97381f6053b43225485a873b6a','docs':'9b87b28e125e8d010392f83425387efc63ecb65d','historical':'61eb42ac622ab41d79d919a00498ee80b169e4da','runs':'bb72d557caaaacd4d458dc0361b7cb19df2ad60c','tools':'dd26e81cba98d58dcafa05d040d363062df419a4','chunks':'5c323458908ee9c953aa600e2a565fe2c05efef9'},
  'notes':['The repository root has no assets/ or renders/ tree at the pinned snapshot. The three split files are explicitly credited as covered via their archive chunks.','Absence at an expected path is not proof of irretrievable loss or absence from other accounts or differently named storage.','A different version may be a legitimate update, redaction, or whitespace-only change. It is not automatically corrupt and must not be overwritten blindly.','This verifies transfer coverage and byte identity, not artistic quality, commercial rights, or successful installation.']
 }
 (ROOT/'comparison.json').write_text(json.dumps({'summary':summary,'files':rows},ensure_ascii=False,indent=2)+'\n')
 (ROOT/'remote_selected_evidence.json').write_text(json.dumps({'snapshot_commit':COMMIT,'canonical_paths':remote,'chunk_shas':chunk_shas},indent=2)+'\n')
 print(json.dumps(summary,ensure_ascii=False,indent=2))
 print('\nPRESENT:')
 for r in rows:
  if r['status']!='absent_at_expected_path':print(r['status'],r['path'],r['bytes'],r.get('remote_bytes'))
 print('\nMISSING RELEVANT DOCS:')
 for r in rows:
  if r['status']=='absent_at_expected_path' and not r['path'].startswith('assets/'):print(r['path'])
