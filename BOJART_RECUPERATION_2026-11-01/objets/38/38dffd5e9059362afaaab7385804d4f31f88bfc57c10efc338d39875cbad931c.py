#!/usr/bin/env python3
"""Archive the public posts of @boj.art without login, tokens or paid services.

Python standard library; ffprobe is required to validate video files.
Public metadata is fetched from the profile, creator embed and creator pagination.
No authentication challenge is solved or bypassed. Only returned public media URLs
are downloaded. Existing verified files are retained and never downloaded again.
"""
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.parse import urlencode, urlparse
from urllib.error import HTTPError
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
import argparse, hashlib, json, re, shutil, subprocess, time

HERE = Path(__file__).resolve().parent
DEFAULT_DEST = HERE if (HERE/'manifest.json').exists() else HERE / 'BOJ_ART_Archive_TikTok'
PROFILE = 'https://www.tiktok.com/@boj.art'
EMBED = 'https://www.tiktok.com/embed/@boj.art'
HEADERS = {'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64)', 'Referer': PROFILE}

def now():
    return datetime.now(timezone.utc).isoformat(timespec='seconds')

def save_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + '.tmp')
    temporary.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')
    temporary.replace(path)

def digest(path):
    h=hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024*1024), b''):
            h.update(block)
    return h.hexdigest()

def request_bytes(url, limit=8_000_000, extra_headers=None):
    parts=urlparse(url)
    if parts.scheme!='https' or not parts.hostname or parts.hostname in ('localhost','127.0.0.1','::1'):
        raise ValueError('Only public HTTPS media URLs are accepted')
    request=Request(url, headers={**HEADERS,**(extra_headers or {})})
    with urlopen(request, timeout=35) as response:
        data=response.read(limit+1)
        content_type=response.headers.get('Content-Type','')
    if len(data)>limit:
        raise ValueError(f'Response exceeds {limit} bytes')
    return data, content_type

def json_state(html, script_id):
    pattern=r'<script[^>]+id=[\"\']'+re.escape(script_id)+r'[\"\'][^>]*>(.*?)</script>'
    match=re.search(pattern, html, re.S)
    if not match:
        raise ValueError(f'Public page does not expose {script_id}; stop, no login bypass')
    return json.loads(match.group(1))

def probe(path):
    result=subprocess.run(['ffprobe','-v','error','-show_entries',
        'format=duration:stream=codec_type,codec_name,width,height,r_frame_rate',
        '-of','json',str(path)],capture_output=True,text=True,timeout=30)
    if result.returncode:
        raise ValueError('ffprobe validation failed: '+result.stderr[:250])
    data=json.loads(result.stdout)
    if not any(s.get('codec_type')=='video' for s in data.get('streams',[])):
        raise ValueError('No video stream')
    return data

def file_info(path, dest):
    return {'file':str(path.relative_to(dest)), 'bytes':path.stat().st_size,'sha256':digest(path)}

def fetch_file(url, path, dest, limit=200_000_000, extra_headers=None):
    if path.is_file() and path.stat().st_size:
        return {**file_info(path,dest),'status':'retained'}
    data,content_type=request_bytes(url,limit,extra_headers)
    if not data:
        raise ValueError('Empty response')
    path.parent.mkdir(parents=True,exist_ok=True)
    temporary=path.with_suffix(path.suffix+'.part')
    temporary.write_bytes(data)
    temporary.replace(path)
    return {**file_info(path,dest),'status':'downloaded','content_type':content_type,'downloaded_at_utc':now(),'source_url':url}

def query_parameters(scope, cursor):
    user=scope['webapp.user-detail']['userInfo']['user']
    app=scope['webapp.app-context']
    return {'aid':'1988','app_language':'en','app_name':'tiktok_web',
        'browser_language':'en-US','browser_name':'Mozilla','browser_online':'true',
        'browser_platform':'Linux x86_64','browser_version':'5.0 (X11; Linux x86_64)',
        'channel':'tiktok_web','cookie_enabled':'false','count':'15','cursor':str(cursor),
        'device_id':app['wid'],'device_platform':'web_pc','focus_state':'true',
        'from_page':'user','history_len':'2','is_fullscreen':'false','is_page_visible':'true',
        'language':'en','os':'linux','priority_region':'','referer':'','region':'US',
        'screen_height':'1080','screen_width':'1920','secUid':user['secUid'],
        'type':'1','tz_name':'UTC','webcast_language':'en'}

def load_record(item, source, records):
    identifier=str(item.get('id',''))
    author=item.get('author',{}).get('uniqueId',item.get('authorUniqueId'))
    if not identifier.isdigit() or author!='boj.art' or item.get('privateItem') or item.get('forFriend'):
        return
    record=records.setdefault(identifier, {'id':identifier,'url':f'{PROFILE}/video/{identifier}','first_seen_at_utc':now(),'sources':[],'status':'pending'})
    if source not in record['sources']:
        record['sources'].append(source)
    record['caption']=item.get('desc','')
    if item.get('createTime'):
        record['posted_at_utc']=datetime.fromtimestamp(int(item['createTime']),timezone.utc).isoformat()
    if item.get('author') or not record.get('metadata'):
        record['metadata']=item
    record['kind']='photo_carousel' if item.get('imagePost') else 'video'

def write_manifest(dest, manifest, records):
    manifest['updated_at_utc']=now()
    manifest['posts']=[records[k] for k in sorted(records,reverse=True)]
    manifest['coverage']={
        'profile_reported_posts':manifest.get('profile_reported_posts'),
        'identified_public_posts':len(records),
        'videos_archived':sum(x.get('status')=='archived' and x.get('kind')=='video' for x in records.values()),
        'photo_posts_archived':sum(x.get('status')=='archived' and x.get('kind')=='photo_carousel' for x in records.values()),
        'pending_or_failed':sum(x.get('status')!='archived' for x in records.values()),
        'pagination_end_observed':manifest.get('pagination_end_observed',False),
    }
    save_json(dest/'manifest.json',manifest)

def discover(dest, manifest, records, seed):
    stamp=now()
    if seed and (HERE/'profile-current.json').exists():
        scope=json.loads((HERE/'profile-current.json').read_text())
        embed=json.loads((HERE/'embed-current.json').read_text())
    else:
        data,_=request_bytes(PROFILE)
        scope=json_state(data.decode(),'__UNIVERSAL_DATA_FOR_REHYDRATION__')['__DEFAULT_SCOPE__']
        data,_=request_bytes(EMBED)
        embed=json_state(data.decode(),'__FRONTITY_CONNECT_STATE__')
    detail=scope['webapp.user-detail']
    user_info=detail.get('userInfo',{})
    if user_info.get('user',{}).get('privateAccount'):
        raise ValueError('Private profile: stop')
    manifest['profile_reported_posts']=int(user_info.get('stats',{}).get('videoCount',0))
    manifest['profile_observed_at_utc']=stamp
    save_json(dest/'evidence/profile.json',{'url':PROFILE,'observed_at_utc':stamp,'detail':detail})
    data=embed['source']['data']['/embed/@boj.art']
    save_json(dest/'evidence/creator-embed.json',{'url':EMBED,'observed_at_utc':stamp,'data':data})
    for item in data.get('videoList',[]):
        load_record(item,EMBED,records)
    cursor=int(time.time()*1000)
    previous_ids=set()
    for page in range(1,51):
        url='https://www.tiktok.com/api/creator/item_list/?'+urlencode(query_parameters(scope,cursor))
        if seed and page==1 and (HERE/'creator-full-query.json').exists():
            payload=json.loads((HERE/'creator-full-query.json').read_text())
            if (HERE/'probe-adapted-log.json').exists():
                provenance=json.loads((HERE/'probe-adapted-log.json').read_text())
                url=next((x['url'] for x in provenance if x.get('file')=='creator-full-query.json'),url)
        else:
            body,_=request_bytes(url)
            payload=json.loads(body)
        save_json(dest/f'evidence/pages/page-{page:03d}.json',{'url':url,'observed_at_utc':now(),'response':payload})
        if payload.get('statusCode',payload.get('status_code',0))!=0:
            raise ValueError('Public API returned non-zero status; no access bypass attempted')
        items=payload.get('itemList',[])
        ids={str(item['id']) for item in items if item.get('id')}
        for item in items:
            load_record(item,url,records)
        manifest['api_pages_observed']=page
        write_manifest(dest,manifest,records)
        print(json.dumps({'event':'page','page':page,'returned':len(items),'identified':len(records),'has_more':payload.get('hasMorePrevious')}),flush=True)
        if not payload.get('hasMorePrevious'):
            manifest['pagination_end_observed']=True
            break
        if ids and ids==previous_ids:
            manifest['discovery_stop_reason']='API repeated the same page; stopped to avoid an infinite loop'
            break
        previous_ids=ids
        times=[int(i.get('createTime',0))*1000 for i in items if i.get('createTime')]
        new_cursor=min(times) if times else cursor-7*86_400_000
        if new_cursor>=cursor:
            new_cursor=cursor-7*86_400_000
        cursor=new_cursor
        time.sleep(.4)
    else:
        manifest['discovery_stop_reason']='50-page limit reached'
    # Embed-only posts need their own public detail page, both for authorship and format.
    for record in list(records.values()):
        if not record.get('metadata',{}).get('author'):
            try:
                body,_=request_bytes(record['url'])
                video_scope=json_state(body.decode(),'__UNIVERSAL_DATA_FOR_REHYDRATION__')['__DEFAULT_SCOPE__']
                detail=video_scope.get('webapp.video-detail',{})
                item=detail.get('itemInfo',{}).get('itemStruct',{})
                if detail.get('statusCode')==0 and str(item.get('id'))==record['id']:
                    load_record(item,record['url'],records)
                else:
                    record['detail_error']='Individual public page did not expose accessible item data'
            except Exception as error:
                record['detail_error']=f'{type(error).__name__}: {error}'
    write_manifest(dest,manifest,records)

def video_candidates(item):
    video=item.get('video',{})
    candidates=[]
    for bitrate in video.get('bitrateInfo',[]):
        addr=bitrate.get('PlayAddr',{})
        for url in addr.get('UrlList',[]):
            candidates.append({'url':url,'width':addr.get('Width',0),'height':addr.get('Height',0),
                'bitrate':bitrate.get('Bitrate',0),'codec':bitrate.get('CodecType'),'source':'video.bitrateInfo'})
    for key in ('playAddr','downloadAddr'):
        value=video.get(key) or item.get(key)
        if isinstance(value,str) and value:
            candidates.append({'url':value,'width':video.get('width',item.get('width',0)),
                'height':video.get('height',item.get('height',0)),'bitrate':video.get('bitrate',0),'codec':video.get('codecType'),'source':'video.'+key})
    return sorted(candidates,key=lambda x:(x['width']*x['height'],x['bitrate']),reverse=True)

def official_player_candidates(identifier, postdir, record):
    """Use the official anonymous iframe's normal request, no account or cookie.

    The page issues its own short-lived, post-scoped embed ticket. It is used only
    for the same public post and is neither forged nor saved in the archive.
    API/CDN URLs and exact returned metadata are saved as provenance instead.
    """
    page_url=f'https://www.tiktok.com/player/v1/{identifier}'
    body,_=request_bytes(page_url)
    router=json_state(body.decode(),'__MODERN_ROUTER_DATA__')
    layout=router.get('loaderData',{}).get('layout',{})
    ticket=layout.get('embedToken')
    if not ticket:
        raise ValueError('Official public player did not issue its normal embed ticket')
    api_url='https://www.tiktok.com/player/api/v1/items?'+urlencode({
        'item_ids':identifier,'language':'fr-FR','aid':'1459','data_source':'web_core'})
    body,_=request_bytes(api_url,extra_headers={'Referer':page_url,'X-TT-Embed-Token':ticket})
    data=json.loads(body)
    save_json(postdir/'official-player-metadata.json',{'url':api_url,'page_url':page_url,'observed_at_utc':now(),'response':data})
    item=next((x for x in data.get('items',[]) if str(x.get('id_str',x.get('id')))==identifier),None)
    if data.get('status_code')!=0 or not item or item.get('author_info',{}).get('unique_id')!='boj.art':
        raise ValueError('Official player did not expose this public B.OJ.art post')
    record['official_player_metadata_file']=str((postdir/'official-player-metadata.json').relative_to(postdir.parent.parent))
    if page_url not in record['sources']:record['sources'].append(page_url)
    info=item.get('video_info',{})
    candidates=[]
    for profile in info.get('profiles',[]):
        addr=profile.get('play_addr',{})
        for url in addr.get('url_list',[]):
            candidates.append({'url':url,'width':addr.get('width',0),'height':addr.get('height',0),
                'bitrate':profile.get('bitrate',0),'codec':profile.get('codec_type'),
                'source':'official_player.video_info.profiles','referer':page_url})
    meta=info.get('meta',{})
    for url in info.get('url_list',[]):
        candidates.append({'url':url,'width':meta.get('width',0),'height':meta.get('height',0),
            'bitrate':meta.get('bitrate',0),'codec':None,'source':'official_player.video_info.url_list','referer':page_url})
    return sorted(candidates,key=lambda x:(x['width']*x['height'],x['bitrate']),reverse=True)

def archive_post(record,dest,legacy,aux_only=False):
    record=dict(record)
    identifier=record['id']
    item=record.get('metadata',{})
    postdir=dest/'posts'/identifier
    postdir.mkdir(parents=True,exist_ok=True)
    save_json(postdir/'metadata.json',item)
    (postdir/'caption.txt').write_text(record.get('caption',''),encoding='utf-8')
    record['metadata_file']=str((postdir/'metadata.json').relative_to(dest))
    record['caption_file']=str((postdir/'caption.txt').relative_to(dest))
    record['retrieval_attempt_at_utc']=now()
    # Retain auxiliary assets even if the video CDN currently refuses playback.
    cover=item.get('video',{}).get('originCover') or item.get('originCoverUrl') or item.get('video',{}).get('cover') or item.get('coverUrl')
    if cover:
        try:
            record['cover']={**record.get('cover',{}),**fetch_file(cover,postdir/'cover.jpg',dest,30_000_000)}
            record.pop('cover_error',None)
        except Exception as error:record['cover_error']=f'{type(error).__name__}: {error}'
    subtitles=[]
    for index,track in enumerate(item.get('video',{}).get('subtitleInfos',[]),1):
        language=re.sub(r'[^A-Za-z0-9_-]','',str(track.get('LanguageCodeName','unknown')))
        output={'language':language,'origin':track.get('Source'),'format':track.get('Format')}
        try:
            output.update(fetch_file(track['Url'],postdir/f'subtitles-{language}-{index:02d}.vtt',dest,5_000_000))
        except Exception as error:output.update(status='failed',error=f'{type(error).__name__}: {error}')
        subtitles.append(output)
    record['subtitles']=subtitles
    if aux_only:
        print(json.dumps({'event':'auxiliary','id':identifier,'cover':bool(record.get('cover')),'subtitles':len(subtitles)}),flush=True)
        return record
    try:
        if record.get('kind')=='photo_carousel':
            images=[]
            for index,img in enumerate(item.get('imagePost',{}).get('images',[]),1):
                urls=img.get('imageURL',{}).get('urlList',[])
                if not urls:raise ValueError(f'Image {index} lacks a public URL')
                last_error=None
                for url in urls:
                    try:
                        images.append(fetch_file(url,postdir/f'image-{index:02d}.jpg',dest,30_000_000));break
                    except Exception as error:last_error=error
                else:raise last_error
            if not images:raise ValueError('Empty carousel')
            record['images']=images
        else:
            path=postdir/'video.mp4'
            legacy_path=legacy/f'{identifier}.mp4' if legacy else None
            if not path.exists() and legacy_path and legacy_path.exists():
                probe(legacy_path)
                shutil.copyfile(legacy_path,path)
                record['video']={**file_info(path,dest),'status':'reused_existing','source':'Previous verified public creator-embed download; retained without re-downloading'}
            if not path.exists():
                errors=[]
                try:
                    candidates=official_player_candidates(identifier,postdir,record)
                except Exception as error:
                    record['official_player_error']=f'{type(error).__name__}: {error}'
                    if isinstance(error,HTTPError) and error.code in (401,403,429):
                        raise ValueError('Official public player refused this request; stopped without bypass') from error
                    candidates=video_candidates(item)
                for choice in candidates:
                    try:
                        info=fetch_file(choice['url'],path,dest,extra_headers={'Referer':choice.get('referer',PROFILE)})
                        validation=probe(path)
                        record['video']={**info,'selected_variant':{k:v for k,v in choice.items() if k!='url'},'probe':validation}
                        break
                    except Exception as error:
                        if path.exists():path.unlink()
                        errors.append(f'{type(error).__name__}: {error}')
                        if isinstance(error,HTTPError) and error.code==429:
                            raise ValueError('Media rate limit received; stopped without retries') from error
                else:raise ValueError('No downloadable public video variant; '+ '; '.join(errors[:3]))
            validation=probe(path)
            record.setdefault('video',file_info(path,dest))
            record['video']['probe']=validation
            record['duration_seconds']=float(validation.get('format',{}).get('duration',0))
        record['status']='archived'
        record.pop('error',None)
    except Exception as error:
        record['status']='failed'
        record['error']=f'{type(error).__name__}: {error}'
    print(json.dumps({'event':'post','id':identifier,'kind':record.get('kind'),'status':record['status'],'error':record.get('error')}),flush=True)
    return record

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--dest',type=Path,default=DEFAULT_DEST)
    parser.add_argument('--legacy',type=Path,default=HERE.parent/'bojart-media')
    parser.add_argument('--seed-existing-evidence',action='store_true')
    parser.add_argument('--discover-only',action='store_true')
    parser.add_argument('--collect-only',action='store_true')
    parser.add_argument('--aux-only',action='store_true',help='Refresh covers and native subtitles without reattempting video downloads')
    parser.add_argument('--retry-missing',action='store_true',help='Download only posts whose media are not yet archived')
    args=parser.parse_args()
    dest=args.dest.resolve();dest.mkdir(parents=True,exist_ok=True)
    if (dest/'manifest.json').exists():
        manifest=json.loads((dest/'manifest.json').read_text())
    else:
        manifest={'schema_version':1,'profile_url':PROFILE,'created_at_utc':now(),
            'scope':'Public @boj.art posts exposed during retrieval; complete account access is not assumed',
            'method':'Public profile and embed HTML plus public creator API pagination, public CDN media; no account, cookies, proxy, signatures generated or paid API'}
    records={x['id']:x for x in manifest.pop('posts',[])}
    if not args.collect_only:
        try:discover(dest,manifest,records,args.seed_existing_evidence)
        except Exception as error:
            manifest['discovery_error']=f'{type(error).__name__}: {error}'
            print(json.dumps({'event':'discovery-error','error':manifest['discovery_error']}),flush=True)
            write_manifest(dest,manifest,records)
    if not args.discover_only:
        with ThreadPoolExecutor(max_workers=3) as executor:
            pending=[record for record in records.values() if not args.retry_missing or record.get('status')!='archived']
            tasks=[executor.submit(archive_post,record,dest,args.legacy,args.aux_only) for record in pending]
            for task in as_completed(tasks):
                record=task.result();records[record['id']]=record
                write_manifest(dest,manifest,records)
    write_manifest(dest,manifest,records)
    print(json.dumps({'event':'complete','coverage':manifest['coverage']},ensure_ascii=False),flush=True)

if __name__=='__main__':main()
