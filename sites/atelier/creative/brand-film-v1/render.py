#!/usr/bin/env python3
"""Render BOJ.ART's reviewed 22.7 s silent Baki edit from the retained originals.

Usage:
  python3 creative/brand-film-v1/render.py --archive-root ARCHIVE --output-dir OUTPUT --assets-dir SITE_ASSETS

FFmpeg performs all media transformations. No images are generated or painted.
The original files are read only and their hashes are recorded in the recipe.
"""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess


def run(args):
    subprocess.run(args, check=True)


def digest(path):
    h = hashlib.sha256()
    with path.open('rb') as source:
        for block in iter(lambda: source.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def probe(path):
    return json.loads(subprocess.check_output(['ffprobe', '-v', 'error', '-show_entries',
        'format=duration,size:stream=index,codec_type,codec_name,width,height,r_frame_rate,nb_frames',
        '-of', 'json', str(path)], text=True))


def main():
    parser = argparse.ArgumentParser(description='Render the reviewed BOJ.ART Baki edit from existing local originals; no network access.')
    parser.add_argument('--archive-root', type=Path, required=True, help='Existing extracted archive containing posts/<id>/video.mp4')
    parser.add_argument('--output-dir', type=Path, required=True, help='Destination for the master, resolved FFmpeg filter and render recipe')
    parser.add_argument('--assets-dir', type=Path, required=True, help='Directory containing display.ttf/body.ttf; receives preview, poster and four review frames')
    args = parser.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    args.assets_dir.mkdir(parents=True, exist_ok=True)
    font = args.assets_dir / 'display.ttf'
    body = args.assets_dir / 'body.ttf'
    for candidate in (font, body):
        if not candidate.is_file():
            raise FileNotFoundError(candidate)
    sources = {
        'reveal': {'id': '7467517355535404310', 'label': 'Baki fini, lumière UV puis lumière d’atelier', 'reviewed_sha256':'27f922de227cd93c79ba5ca11f3adf9c08d883436ed27590d0abae2936ac44e8'},
        'paint': {'id': '7464268707989114134', 'label': 'Partie 2 du projet Baki Hanma de 60 cm : mise en peinture', 'reviewed_sha256':'9ca3bd55f02e5841a1f8fba53adef40b4bd5c13954c6f8ff615dfe6ab3d56bf4'}
    }
    for key,source in sources.items():
        source['key'] = key
        source['archive_file'] = f"posts/{source['id']}/video.mp4"
        path = args.archive_root / source['archive_file']
        source['source_url'] = f"https://www.tiktok.com/@boj.art/video/{source['id']}"
        source['sha256'] = digest(path)
        if source['sha256'] != source['reviewed_sha256']:
            raise ValueError('Source différente du plan inspecté : '+source['id'])
        source['media'] = probe(path)
    shots = [
        {'id':'detail-uv','source':'reveal','start':8.9,'source_duration':3.0,'duration':3.0,'output':[0.0,3.0],'label':'Regard et surface sous lumière UV'},
        {'id':'detail-colour','source':'reveal','start':24.0,'source_duration':2.2,'duration':2.2,'output':[3.0,5.2],'label':'Détail peint, lumière d’atelier'},
        {'id':'gesture-01','source':'paint','start':3.8,'source_duration':1.6,'duration':1.6,'output':[5.2,6.8],'label':'Première touche de peinture'},
        {'id':'gesture-02','source':'paint','start':11.6,'source_duration':1.6,'duration':1.6,'output':[6.8,8.4],'label':'Mouvement du pinceau sur la pièce'},
        {'id':'gesture-03','source':'paint','start':20.5,'source_duration':2.4,'duration':2.4,'output':[8.4,10.8],'label':'Précision de la main et du pinceau'},
        {'id':'reveal-full','source':'reveal','start':16.5,'source_duration':3.8,'duration':3.8,'output':[10.6,14.4],'label':'Figurine et socle dans l’atelier'},
        {'id':'reveal-moving','source':'reveal','start':29.2,'source_duration':5.0,'duration':5.0,'output':[14.4,19.4],'label':'Présentation mobile de l’œuvre finie'},
        {'id':'signature','source':'reveal','start':35.2,'source_duration':1.5,'duration':3.6,'output':[19.1,22.7],'label':'Emblème original BOJ.ART','hold_last_frame_seconds':2.1}
    ]
    filters = ['[0:v]split=5[r0][r1][r5][r6][r7]', '[1:v]split=3[p2][p3][p4]']
    for index, shot in enumerate(shots):
        shot['source_id'] = sources[shot['source']]['id']
        label = ('p' if shot['source']=='paint' else 'r') + str(index)
        f = f"[{label}]trim=start={shot['start']}:end={shot['start']+shot['source_duration']},setpts=PTS-STARTPTS,fps=30"
        if shot['source']=='paint':
            shot['crop'] = {'x':0,'y':662,'width':576,'height':324}
            shot['scaled_size'] = [640,360]
            shot['pad_offset'] = [40,460]
            f += ',crop=576:324:0:662,scale=640:360:flags=lanczos,pad=720:1280:40:460:color=0x09090d'
        else:
            shot['crop'] = None
            shot['scaled_size'] = [630,1120]
            shot['pad_offset'] = [45,80]
            f += ',scale=630:1120:flags=lanczos,pad=720:1280:45:80:color=0x09090d'
        f += f",setsar=1,format=yuv420p,tpad=stop_mode=clone:stop_duration={shot.get('hold_last_frame_seconds',0)+0.1},trim=end_frame={round(shot['duration']*30)},setpts=N/(30*TB),settb=1/30[s{index}]"
        filters.append(f)
    filters += [
        '[s0][s1][s2][s3][s4]concat=n=5:v=1:a=0,settb=1/30[before]',
        '[s5][s6]concat=n=2:v=1:a=0,settb=1/30[reveal]',
        '[before][reveal]xfade=transition=fade:duration=0.2:offset=10.6[first]',
        '[first][s7]xfade=transition=fade:duration=0.3:offset=19.1[edit]'
    ]
    # Text is rendered into the clean canvas margins. The source painting title,
    # large duplicated logo and old subscription line stay in the retained original.
    title = str(font)
    textfont = str(body)
    final = '[edit]'
    final += f"drawtext=fontfile={textfont}:text=BOJ.ART:x=28:y=27:fontsize=19:fontcolor=0xf4f0ed:enable='lt(t,19.1)'"
    final += f",drawtext=fontfile={textfont}:text='BAKI HANMA / 60 CM':x=w-tw-28:y=29:fontsize=14:fontcolor=0xc4a5ad:enable='lt(t,19.1)'"
    final += ',drawbox=x=28:y=64:w=664:h=1:color=0x613340:t=fill'
    final += ',drawbox=x=28:y=1215:w=664:h=1:color=0x613340:t=fill'
    phases = [
        {'label':'LE DÉTAIL.','number':'01','start':0.0,'end':5.2},
        {'label':'LE GESTE.','number':'02','start':5.2,'end':10.6},
        {'label':'L’ŒUVRE.','number':'03','start':10.6,'end':19.1},
        {'label':'LA SIGNATURE.','number':'04','start':19.1,'end':22.7}
    ]
    for phase in phases:
        start,end = phase['start'],phase['end']
        alpha = f"if(lt(t,{start+0.25}),(t-{start})/0.25,if(gt(t,{end-0.18}),({end}-t)/0.18,1))"
        final += f",drawtext=fontfile={title}:text='{phase['label']}':x='28+20*exp(-9*(t-{start}))':y=1230:fontsize=34:fontcolor=0xf4f0ed:alpha='{alpha}':enable='between(t,{start},{end})'"
        final += f",drawtext=fontfile={title}:text={phase['number']}:x=w-tw-28:y=1230:fontsize=34:fontcolor=0xf13a54:alpha='{alpha}':enable='between(t,{start},{end})'"
    gesture_alpha = "if(lt(t,5.5),(t-5.2)/0.3,if(gt(t,10.3),(10.6-t)/0.3,1))"
    final += f",drawtext=fontfile={title}:text='LE GESTE.':x='40+25*exp(-8*(t-5.2))':y=284:fontsize=94:fontcolor=0xf4f0ed:alpha='{gesture_alpha}':enable='between(t,5.2,10.6)'"
    final += r',drawbox=x=40:y=409:w=112:h=3:color=0xf13a54:t=fill:enable=between(t\,5.2\,10.6)'
    final += f",drawtext=fontfile={textfont}:text='LA COULEUR PREND FORME.':x=40:y=855:fontsize=19:fontcolor=0xe5b9c3:alpha='{gesture_alpha}':enable='between(t,5.2,10.6)'"
    final += f",drawtext=fontfile={textfont}:text='La précision de la main.':x=40:y=891:fontsize=16:fontcolor=0xb398a1:alpha='{gesture_alpha}':enable='between(t,5.2,10.6)'"
    final += ',fade=t=in:st=0:d=0.2,fade=t=out:st=22.3:d=0.4,trim=end_frame=681,setpts=N/(30*TB)[master]'
    filters.append(final)
    filter_script = '\n'.join(part+';' for part in filters[:-1])+'\n'+filters[-1]+'\n'
    filter_path = args.output_dir / 'BOJ_ART_Edit_Signature_v1.ffmpeg.txt'
    filter_path.write_text(filter_script, encoding='utf-8')
    output = args.output_dir / 'BOJ_ART_Edit_Signature_v1.mp4'
    command = ['ffmpeg','-hide_banner','-loglevel','error','-y','-i',str(args.archive_root / sources['reveal']['archive_file']),'-i',str(args.archive_root / sources['paint']['archive_file']),
        '-filter_complex_threads','1','-filter_complex_script',str(filter_path),'-map','[master]','-an','-c:v','libx264','-preset','slow','-crf','17','-pix_fmt','yuv420p','-r','30','-movflags','+faststart',str(output)]
    run(command)
    preview = args.assets_dir / 'brand-film-preview.mp4'
    run(['ffmpeg','-hide_banner','-loglevel','error','-y','-i',str(output),'-vf','scale=360:640:flags=lanczos','-an','-c:v','libx264','-preset','slow','-crf','22','-movflags','+faststart',str(preview)])
    poster = args.assets_dir / 'brand-film-poster.webp'
    run(['ffmpeg','-hide_banner','-loglevel','error','-y','-ss','12.3','-i',str(output),'-frames:v','1','-quality','90',str(poster)])
    stills=[]
    for index, (name,sec) in enumerate([('detail',1.3),('geste',9.1),('oeuvre',12.3),('signature',20.6)],1):
        target=args.assets_dir / f'brand-film-frame-{index:02d}-{name}.webp'
        run(['ffmpeg','-hide_banner','-loglevel','error','-y','-ss',str(sec),'-i',str(output),'-frames:v','1','-quality','90',str(target)])
        stills.append({'file':target.name,'output_time_seconds':sec,'label':name})
    decode=subprocess.run(['ffmpeg','-hide_banner','-loglevel','error','-i',str(output),'-f','null','-'],capture_output=True,text=True,check=True)
    recipe={
        'format':'bojart.brand-film.v1','brand':'BOJ.ART','title':'Baki — Du détail à l’œuvre',
        'version':1,'purpose':'Nouvel édit de démonstration silencieux, issu de deux publications de la même figurine Baki de 60 cm.',
        'master_file':output.name,'preview_file':preview.name,'poster_file':poster.name,
        'duration_seconds':22.7,'fps':30,'frames':681,'audio_tracks':0,
        'master_dimensions':[720,1280],'preview_dimensions':[360,640],
        'music':'Aucune piste audio ajoutée. Les pistes des originaux restent conservées dans l’archive.',
        'sources':list(sources.values()),'shots':shots,'chapters':phases,
        'transitions':[{'type':'crossfade','output_seconds':[10.6,10.8]},{'type':'crossfade','output_seconds':[19.1,19.4]}],
        'edit_decisions':{
            'painting_derivation':'Extraction du seul bandeau vidéo 576×324, à x=0,y=662. Le geste et le cadre horizontal sont conservés ; la grande carte logo et l’ancienne incitation à s’abonner restent dans l’original archivé.',
            'painting_display':'640×360 dans le master : agrandissement de 11,1 %, sans transformation générative.',
            'portrait_display':'630×1120 : cadre entier et proportions des originaux 576×1024 conservés.',
            'source_colours':'Couleurs d’origine conservées ; pas d’étalonnage sélectif.',
            'speed':'Vitesse source inchangée. Cadence normalisée à 30 i/s ; maintien final du logo 2,1 s.',
            'graphics':'Typographie BOJ.ART, quatre chapitres, entrées courtes, marges charbon et accent carmin.',
            'reality':'Images de la figurine publiée comme 60 cm ; aucune relation à un modèle généré de 1 m ni à une impression actuelle.'
        },
        'review_frames':stills,
        'ffmpeg_version':subprocess.check_output(['ffmpeg','-version'],text=True).splitlines()[0],
        'ffmpeg_command':command,'filter_file':filter_path.name,
        'outputs':{'master':{'sha256':digest(output),'bytes':output.stat().st_size,'probe':probe(output)},'preview':{'sha256':digest(preview),'bytes':preview.stat().st_size,'probe':probe(preview)},'poster':{'sha256':digest(poster),'bytes':poster.stat().st_size}},
        'validation':{'source_contact_sheets_reviewed':True,'painting_band_reviewed':True,'full_decode_exit_code':decode.returncode,'full_decode_errors':decode.stderr,'browser_rendering_verified':False,'output_stills_reviewed':False,'review_note':'Les quatre images et les raccords sont à inspecter après chaque nouveau rendu.'}
    }
    (args.output_dir / 'BOJ_ART_Edit_Signature_v1.recipe.json').write_text(json.dumps(recipe,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    # Expose the successfully decoded master under the Studio's stable asset name.
    site_master = args.assets_dir / 'brand-film-master.mp4'
    staged_master = args.assets_dir / 'brand-film-master.mp4.tmp'
    shutil.copyfile(output, staged_master)
    staged_master.replace(site_master)
    public_recipe = {key:value for key,value in recipe.items() if key not in {'ffmpeg_command','filter_file'}}
    public_recipe.update(master_file=site_master.name, download_name=output.name)
    (args.assets_dir / 'brand-film-sources.json').write_text(json.dumps(public_recipe,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'master':str(output),'site_master':str(site_master),'duration':22.7,'preview':str(preview),'poster':str(poster),'stills':stills,'bytes':output.stat().st_size},ensure_ascii=False,indent=2))


if __name__=='__main__':
    main()
