from pathlib import Path
import shutil, json
base=Path(__file__).resolve().parent
image=base.parent.parent/'generated_images/exec-3fa8bdfe-aa11-4bb4-bf26-02ebbdd94c20.png'
tool=base/'toolchain/node_modules/hyperframes/dist'
for variant,reveal in [('a',2),('b',2.5)]:
    project=base/'toolchain'/f'hyperframes-{variant}'
    (project/'assets').mkdir(parents=True,exist_ok=True)
    (project/'compositions').mkdir(exist_ok=True)
    shutil.copy2(image,project/'assets/planche.png')
    shutil.copy2(tool/'vendor/npm/gsap@3.15.0/dist/gsap.min.js',project/'assets/gsap.min.js')
    root='''<!doctype html><html lang="fr"><head><meta charset="utf-8"><title>Marwin — essai de montage</title>
<style>html,body{margin:0;width:540px;height:960px;overflow:hidden}body{background:#17231f}</style>
<script src="assets/gsap.min.js"></script></head><body>
<div id="main" data-composition-id="main" data-start="0" data-duration="6" data-width="540" data-height="960" data-fps="30">
<div id="board" class="clip" data-composition-id="board" data-composition-src="compositions/board.html" data-start="0" data-duration="6" data-track-index="1" data-track-kind="graphics" data-width="540" data-height="960"></div>
</div><script>window.__timelines=window.__timelines||{};window.__timelines.main=gsap.timeline({paused:true});</script>
</body></html>'''
    (project/'index.html').write_text(root)
    windows=[(0,reveal,0,'01 · LE SELFIE'),(reveal,4-reveal,1,'02 · LA PLACE S’INVITE'),(4,2,2,'03 · LE PHOTOGRAPHE')]
    panes=''.join(f'<div id="moment-{i}" class="clip moment" data-start="{start}" data-duration="{duration}" data-track-index="{i+2}"><p class="legend">{title}</p><div class="picture" style="background-position:{-468*i}px 0"></div></div>' for start,duration,i,title in windows)
    scene='''<template><style>
#root{position:absolute;inset:0;background:#17231f;font-family:Inter;color:#f5f0e5}
.brand{position:absolute;left:36px;top:38px;font-size:20px;font-weight:700;letter-spacing:4px;margin:0}
.intro{position:absolute;left:36px;top:74px;font-size:29px;line-height:1.2;font-weight:700;margin:0}
.legend{position:absolute;left:36px;top:126px;margin:0;font-size:18px;line-height:1.2;font-weight:700;letter-spacing:1px}
.picture{position:absolute;left:36px;top:170px;width:468px;height:702px;background-image:url('assets/planche.png');background-repeat:no-repeat;background-size:1404px 702px;border-radius:8px}
.note{position:absolute;left:36px;top:893px;margin:0;font-size:15px;font-weight:400;letter-spacing:1.3px}
.rail{position:absolute;left:36px;top:929px;width:468px;height:3px;background:#3d4b40}
#clock{height:3px;width:468px;background:#d4a866;transform-origin:left center}
</style><div id="root" data-composition-id="board" data-width="540" data-height="960">
<p class="brand">MARWIN</p><h1 class="intro">Maquette de montage</h1>'''+panes+'''
<p class="note">IMAGES FIXES · ESSAI LOCAL</p><div class="rail" data-layout-ignore><div id="clock"></div></div>
</div><script>const tl=gsap.timeline({paused:true});tl.fromTo('#clock',{scaleX:0},{scaleX:1,duration:6,ease:'none'},0);window.__timelines.board=tl;</script></template>'''
    (project/'compositions/board.html').write_text(scene)
    (project/'SPEC.txt').write_text('Essai technique, pas nouveau film. 540x960, 30 fps, 6 s, silencieux. Même planche, sans régénération. Variante '+variant.upper()+', révélation à '+str(reveal)+' s. Le rôle de cet essai est de vérifier coupe, cadrage et réutilisation.\n')
print(json.dumps({'prepared':['hyperframes-a','hyperframes-b'],'change':'reveal 2.0s -> 2.5s','source_unchanged':True}))
