const MAX_FILE_BYTES=52428800;
const ID=/^[A-Za-z0-9][A-Za-z0-9._:-]{0,199}$/;
const SHA=/^[a-f0-9]{64}$/;
const BASE='/api/workshop/assets';
const error=(message,code)=>{const result=new Error(message);result.code=code;return result;};
export async function assetSHA256(buffer){
  if(!(buffer instanceof ArrayBuffer)&&!ArrayBuffer.isView(buffer))throw error('Le fichier ne contient pas des octets.','invalid_asset');
  if(!globalThis.crypto?.subtle)throw error('Un contexte HTTPS ou localhost est requis pour vérifier les fichiers.','crypto_unavailable');
  return [...new Uint8Array(await crypto.subtle.digest('SHA-256',buffer))].map(n=>n.toString(16).padStart(2,'0')).join('');
}
function assetMetadata(value){
  if(!value||typeof value.id!=='string'||!ID.test(value.id)||typeof value.name!=='string'||!value.name||value.name.length>255||/[\u0000-\u001f\u007f/\\]/.test(value.name)||!/\.stl$/i.test(value.name)||typeof value.sha256!=='string'||!SHA.test(value.sha256)||!Number.isSafeInteger(value.byteLength)||value.byteLength<1||value.byteLength>MAX_FILE_BYTES||!Number.isSafeInteger(value.createdAt)||value.createdAt<0||value.createdAt>8640000000000000||value.format!=='stl')throw error('Le manifeste du coffre est invalide.','invalid_response');
  return value;
}
async function boundedBytes(response,limit){
  if(response.body?.getReader){
    const reader=response.body.getReader(),chunks=[];let length=0;
    try{while(true){const {done,value}=await reader.read();if(done)break;length+=value.byteLength;if(length>limit){await reader.cancel();throw error('Le coffre a renvoyé trop de données.','response_too_large');}chunks.push(value);}}
    finally{reader.releaseLock();}
    const result=new Uint8Array(length);let offset=0;for(const chunk of chunks){result.set(chunk,offset);offset+=chunk.byteLength;}return result.buffer;
  }
  const result=await response.arrayBuffer();if(result.byteLength>limit)throw error('Le coffre a renvoyé trop de données.','response_too_large');return result;
}
async function readJSON(response){
  if(typeof response.arrayBuffer!=='function')return response.json();
  const bytes=await boundedBytes(response,16777216);try{return JSON.parse(new TextDecoder().decode(bytes));}catch{throw error('Le coffre n’a pas renvoyé un manifeste JSON valide.','invalid_response');}
}
/** Same-origin only; status 2.5 s and complete file transfers 120 s maximum. */
export function createWorkshopAssetClient({fetchImpl=(...args)=>globalThis.fetch(...args)}={}){
  async function request(path,options={},consume=readJSON,timeoutMs=120000){
    const controller=new AbortController(),timer=setTimeout(()=>controller.abort(),timeoutMs);
    try{
      const response=await fetchImpl(BASE+path,{...options,credentials:'same-origin',cache:'no-store',redirect:'error',signal:controller.signal});
      if(!response.ok){let body;try{body=await readJSON(response);}catch{}throw error(body?.message||'Le coffre local n’est pas disponible sur cette origine.',body?.code||(response.status===404?'service_absent':'service_unavailable'));}
      return await consume(response);
    }catch(failure){if(failure.name==='AbortError'||controller.signal.aborted)throw error('Le coffre n’a pas répondu dans le délai prévu. Le fichier peut être vérifié puis renvoyé avec le même identifiant.','transfer_timeout');throw failure;}
    finally{clearTimeout(timer);}
  }
  return {
    backupURL:BASE+'/backup',
    async status(){
      try{const value=await request('/status',{},readJSON,2500);if(value?.ok!==true||value.version!==1||value.capabilities?.stlStorage!==true||value.capabilities?.printerCommands!==false)throw error('Le coffre local ne confirme pas ses capacités.','invalid_response');return {...value,available:true};}
      catch(failure){return {available:false,ok:false,code:failure.code||'service_unavailable',message:failure.message};}
    },
    async putAsset(record){
      if(!record||typeof record.id!=='string'||!ID.test(record.id)||typeof record.name!=='string')throw error('Le fichier à conserver est invalide.','invalid_asset');
      const bytes=record.buffer?.byteLength;if(!Number.isSafeInteger(bytes)||!bytes||bytes>MAX_FILE_BYTES)throw error('Un STL doit être non vide et inférieur ou égal à 50 Mio.','asset_too_large');
      if(!(record.buffer instanceof ArrayBuffer)&&!ArrayBuffer.isView(record.buffer))throw error('Le fichier ne contient pas des octets.','invalid_asset');
      const id=record.id,name=record.name,createdAt=record.createdAt??null,expectedSha256=record.sha256;
      const source=record.buffer instanceof ArrayBuffer?new Uint8Array(record.buffer):new Uint8Array(record.buffer.buffer,record.buffer.byteOffset,record.buffer.byteLength);
      const buffer=new Uint8Array(source).buffer;
      const sha256=await assetSHA256(buffer);
      assetMetadata({id,name,sha256,byteLength:bytes,createdAt:createdAt??0,format:'stl'});
      if(expectedSha256&&expectedSha256!==sha256)throw error('Le fichier local ne correspond plus à son empreinte.','checksum_mismatch');
      // The repository owns an omitted creation date. Reusing an ID after a
      // lost receipt therefore retrieves the same date instead of inventing one.
      const value=await request('/'+encodeURIComponent(id),{method:'POST',headers:{'Content-Type':'application/octet-stream','X-BOJ-File-Name':encodeURIComponent(name),'X-BOJ-SHA256':sha256,...(createdAt===null?{}:{'X-BOJ-Created-At':String(createdAt)})},body:buffer});
      const asset=assetMetadata(value.asset);
      if(value.ok!==true||asset.id!==id||asset.sha256!==sha256||asset.byteLength!==bytes||asset.name!==name||createdAt!==null&&asset.createdAt!==createdAt)throw error('Le coffre n’a pas confirmé le fichier attendu.','invalid_receipt');return asset;
    },
    async readAsset(id,{expectedSha256=null}={}){
      if(typeof id!=='string'||!ID.test(id)||expectedSha256!==null&&(typeof expectedSha256!=='string'||!SHA.test(expectedSha256)))throw error('Identifiant ou empreinte du fichier invalide.','invalid_asset_id');
      try{return await request('/'+encodeURIComponent(id),{},async response=>{
        const rawLength=response.headers.get('content-length'),rawTime=response.headers.get('x-boj-created-at');
        if(!/^\d+$/.test(rawLength||'')||!/^\d+$/.test(rawTime||''))throw error('La taille ou la date du fichier est absente.','invalid_response');
        let name;try{name=decodeURIComponent(response.headers.get('x-boj-file-name')||'');}catch{throw error('Le nom du fichier renvoyé est invalide.','invalid_response');}
        const metadata=assetMetadata({id:response.headers.get('x-boj-asset-id'),name,sha256:response.headers.get('x-boj-sha256'),byteLength:Number(rawLength),createdAt:Number(rawTime),format:'stl'});
        if(metadata.id!==id||expectedSha256&&metadata.sha256!==expectedSha256)throw error('Le coffre renvoie une autre référence de fichier.','checksum_mismatch');
        const buffer=await boundedBytes(response,metadata.byteLength);
        if(buffer.byteLength!==metadata.byteLength||await assetSHA256(buffer)!==metadata.sha256)throw error('Les octets reçus ne correspondent pas à l’empreinte du fichier.','checksum_mismatch');
        return {...metadata,buffer};
      });}catch(failure){if(failure.code==='asset_missing')return null;throw failure;}
    },
    async listAssets(after=0){
      if(!Number.isSafeInteger(after)||after<0)throw error('Curseur du coffre invalide.','invalid_cursor');
      const value=await request('?after='+after,{},readJSON,10000);
      if(value?.ok!==true||value.version!==1||!Array.isArray(value.assets)||value.assets.length>100||!Number.isSafeInteger(value.nextCursor)||value.nextCursor<after||typeof value.hasMore!=='boolean'||value.hasMore&&value.nextCursor===after)throw error('La liste des fichiers est invalide.','invalid_response');value.assets.forEach(assetMetadata);return value;
    },
    async restoreBackup(file){
      if(!file||!Number.isFinite(file.size)||file.size<12||file.size>1073741824)throw error('La sauvegarde du coffre est invalide ou dépasse 1 Gio.','invalid_archive');
      const value=await request('/restore',{method:'POST',headers:{'Content-Type':'application/octet-stream'},body:file});
      if(value?.ok!==true||value.version!==1||!Array.isArray(value.added)||!Array.isArray(value.duplicates)||!Number.isSafeInteger(value.verifiedFiles)||value.verifiedFiles!==value.added.length+value.duplicates.length)throw error('Le coffre n’a pas confirmé la restauration.','invalid_receipt');return value;
    }
  };
}
