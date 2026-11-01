/**
 * BOJ.ART — decorative motion studies. No telemetry, printer state or AI activity.
 * The host owns its positioning and height; this module owns only its canvas.
 */
const mounts = new WeakMap();
const TAU = Math.PI * 2;
const RED = '255,55,91';
const PINK = '216,54,131';
const INK = '240,217,229';
const rgba = (color, alpha) => `rgba(${color},${alpha})`;

function path(ctx, points, color, width = 1, fill = null, closed = false) {
  if (!points.length) return;
  ctx.beginPath();
  ctx.moveTo(points[0][0], points[0][1]);
  for (let i = 1; i < points.length; i++) ctx.lineTo(points[i][0], points[i][1]);
  if (closed) ctx.closePath();
  if (fill) { ctx.fillStyle = fill; ctx.fill(); }
  if (color) { ctx.strokeStyle = color; ctx.lineWidth = width; ctx.stroke(); }
}

function glow(ctx, x, y, radius, color, alpha) {
  const gradient = ctx.createRadialGradient(x, y, 0, x, y, radius);
  gradient.addColorStop(0, rgba(color, alpha));
  gradient.addColorStop(.3, rgba(color, alpha * .36));
  gradient.addColorStop(1, rgba(color, 0));
  ctx.fillStyle = gradient;
  ctx.fillRect(x - radius, y - radius, radius * 2, radius * 2);
}

function dot(ctx, x, y, radius, color) {
  ctx.beginPath();
  ctx.arc(x, y, radius, 0, TAU);
  ctx.fillStyle = color;
  ctx.fill();
}

function background(ctx, width, height, kind) {
  const wash = ctx.createLinearGradient(0, 0, width, height);
  wash.addColorStop(0, '#101015');
  wash.addColorStop(.55, '#111016');
  wash.addColorStop(1, '#08090d');
  ctx.fillStyle = wash;
  ctx.fillRect(0, 0, width, height);
  glow(ctx, width * .55, height * .52, Math.max(width, height) * .53, PINK, .075);
  const spacing = Math.max(19, Math.min(28, width / 22));
  for (let x = spacing / 2; x < width; x += spacing) {
    for (let y = spacing / 2; y < height; y += spacing) {
      const falloff = Math.max(0, 1 - Math.hypot((x-width*.5)/width, (y-height*.5)/height));
      dot(ctx, x, y, .55, rgba(INK, falloff * .10));
    }
  }
  // Quiet registration marks, not gauges or measurement claims.
  const m = Math.max(12, Math.min(width, height) * .055), length = 13;
  [[m,m,1,1],[width-m,m,-1,1],[m,height-m,1,-1],[width-m,height-m,-1,-1]].forEach(([x,y,dx,dy]) => {
    path(ctx, [[x+length*dx,y],[x,y],[x,y+length*dy]], rgba(INK,.17), .7);
  });
  if (kind === 'jarvis') {
    path(ctx, [[width*.5, 10],[width*.5,height-10]], rgba(PINK,.06), .6);
    path(ctx, [[10,height*.5],[width-10,height*.5]], rgba(PINK,.06), .6);
  }
}

function production(ctx, width, height, time) {
  const scale = Math.min(width / 740, height / 460);
  const cx = width * .50, cy = height * .56;
  const project = (x, y, z = 0) => [cx + (x-y)*.87*scale, cy + ((x+y)*.43-z)*scale];
  const line = (points, color, weight = 1) => path(ctx, points.map(p => project(...p)), color, Math.max(.5, weight*scale));
  const face = (points, fill, stroke = rgba(INK,.10)) => path(ctx, points.map(p => project(...p)), stroke, Math.max(.45,.8*scale), fill, true);
  const box = (x,y,w,d,bottom,top,topColor,sideColor,frontColor,edge = rgba(INK,.14)) => {
    const a=[x-w/2,y-d/2], b=[x+w/2,y-d/2], c=[x+w/2,y+d/2], d0=[x-w/2,y+d/2];
    face([[...d0,bottom],[...c,bottom],[...c,top],[...d0,top]],frontColor,edge);
    face([[...b,bottom],[...c,bottom],[...c,top],[...b,top]],sideColor,edge);
    face([[...a,top],[...b,top],[...c,top],[...d0,top]],topColor,edge);
  };

  // The stage and its eight sculptural printer silhouettes remain static in place.
  ctx.save();
  ctx.translate(cx,cy+72*scale);
  ctx.scale(1,.40);
  glow(ctx,0,0,320*scale,RED,.19);
  ctx.restore();
  box(0,0,470,286,-25,-9,'#15151d','#101017','#19131d',rgba(INK,.12));
  face([[-230,-138,-8],[230,-138,-8],[230,138,-8],[-230,138,-8]],'#14151d',rgba(PINK,.27));
  for (let x=-220; x<=220; x+=22) line([[x,-133,-7],[x,133,-7]],rgba(INK,.045),.7);
  for (let y=-132; y<=132; y+=22) line([[-224,y,-7],[224,y,-7]],rgba(INK,.045),.7);
  line([[-235,143,-16],[235,143,-16],[235,-143,-16]],rgba(RED,.34),1.6);
  line([[-232,138,-9],[232,138,-9]],rgba(INK,.16),.8);

  const units = Array.from({length:8},(_,index) => ({index,x:(index%4-1.5)*100,y:index<4?-70:70}));
  // Branches are decorative light paths; no live routing or job progress is implied.
  for (const unit of units) {
    const route=[[-255,0,-5],[-208,0,-5],[unit.x,0,-5],[unit.x,unit.y,-5]];
    line(route,rgba(PINK,.25),1);
    const points=route.map(p=>project(...p));
    const lengths=points.slice(1).map((point,i)=>Math.hypot(point[0]-points[i][0],point[1]-points[i][1]));
    const total=lengths.reduce((sum,n)=>sum+n,0);
    let distance=((time*.042+unit.index*.117)%1)*total;
    for (let segment=0;segment<lengths.length;segment++) {
      if (distance<=lengths[segment]) {
        const ratio=lengths[segment] ? distance/lengths[segment] : 0;
        const from=points[segment],to=points[segment+1];
        const x=from[0]+(to[0]-from[0])*ratio,y=from[1]+(to[1]-from[1])*ratio;
        glow(ctx,x,y,10*scale,RED,.38);
        dot(ctx,x,y,Math.max(.7,1.5*scale),rgba(INK,.80));
        break;
      }
      distance-=lengths[segment];
    }
  }

  units.sort((a,b)=>a.x+a.y-b.x-b.y).forEach(({index,x,y}) => {
    const lit=.72+.14*Math.sin(time*.55+index*.8);
    // A soft foot shadow anchors every unit independently of motion.
    face([[x-37,y-34,-4],[x+38,y-34,-4],[x+43,y+35,-4],[x-32,y+35,-4]],'#07090bd9',null);
    box(x,y,68,62,-3,10,'#343039','#111118','#211b24',rgba(INK,.24));
    box(x,y,58,52,10,21,'#171820','#0d0e14','#18161f',rgba(INK,.11));
    if (index<5) {
      // Five enclosed UV-resin-inspired forms; no manufacturer is represented.
      box(x,y,54,48,23,100,rgba(PINK,.10),rgba(PINK,.085),rgba(RED,.08),rgba(PINK,.42));
      line([[x-24,y-21,25],[x-24,y-21,96],[x+24,y-21,96]],rgba(INK,.21),1);
      box(x,y,42,37,22,28,'#231b29','#211323','#311823',rgba(PINK,.43));
      line([[x,y-13,32],[x,y-13,88]],rgba(INK,.28),2.2);
      box(x,y,33,27,69,73,'#4b3748','#352134','#594053',rgba(INK,.29));
      // Layered abstract object, deliberately not a claimed STL or printed part.
      for (let layer=0;layer<8;layer++) {
        const z=34+layer*3.1,r=11+Math.sin(layer*.65)*4;
        const polygon=Array.from({length:7},(_,n)=>[x+Math.cos(n/6*TAU)*r,y+Math.sin(n/6*TAU)*r,z]);
        line(polygon,rgba(index%2?PINK:RED,(.26+layer*.023)*lit),1);
      }
      line([[x-25,y+24,97],[x+25,y+24,97],[x+25,y+24,25]],rgba(RED,.63*lit),1.35);
      box(x,y,56,50,101,105,'#30242f','#231924','#402936',rgba(INK,.22));
    } else {
      // Three open-frame FDM-inspired forms.
      const corners=[[-27,-23],[27,-23],[-27,23],[27,23]];
      corners.forEach(([dx,dy],i)=>line([[x+dx,y+dy,19],[x+dx,y+dy,105]],rgba(i<2?INK:PINK,i<2?.26:.47),3.2));
      box(x,y,60,52,104,109,'#3c303a','#251c27','#4a2d3a',rgba(INK,.29));
      box(x,y,45,40,31,34,'#3a2a36','#211620','#4c2b3b',rgba(PINK,.42));
      line([[x-24,y,79],[x+24,y,79]],rgba(INK,.39),2);
      const headX=x+Math.sin(time*.38+index)*10;
      box(headX,y,10,12,69,84,'#6c4557','#382633','#7d324e',rgba(RED,.72));
      line([[headX,y,68],[headX,y,61]],rgba(INK,.57),1.7);
      for(let layer=0;layer<7;layer++) {
        const r=12-layer*.8,z=35+layer*2.5;
        line([[x-r,y-r,z],[x+r,y-r,z],[x+r,y+r,z],[x-r,y+r,z],[x-r,y-r,z]],rgba(RED,(.35+layer*.025)*lit),1.1);
      }
    }
    line([[x-23,y+31,5],[x-7,y+31,5]],rgba(RED,.74*lit),1.7);
    // Small enclosure seams, with no status lamps, percentages or readouts.
    for(let n=0;n<4;n++) line([[x+9+n*3,y+31,2],[x+9+n*3,y+31,7]],rgba(INK,.14),.7);
  });
}

function jarvis(ctx, width, height, time) {
  const cx=width*.5,cy=height*.50,r=Math.min(width*.275,height*.305);
  glow(ctx,cx,cy,r*1.85,PINK,.16);
  glow(ctx,cx-r*.22,cy+r*.12,r,RED,.16);
  // Orbital planes have depth; rear arcs are quieter than the near rim.
  const orbit=(radius,tilt,rotation,phase,front,alpha)=>{
    const points=[];
    for(let i=0;i<=100;i++) {
      const a=i/100*TAU+phase;
      const ox=Math.cos(a)*radius,oy=Math.sin(a)*radius*Math.cos(tilt),oz=Math.sin(a)*Math.sin(tilt);
      const p=[cx+ox*Math.cos(rotation)-oy*Math.sin(rotation),cy+ox*Math.sin(rotation)+oy*Math.cos(rotation)];
      if((oz>=0)===front) points.push(p);
      else if(points.length) {path(ctx,points,rgba(PINK,alpha),.7);points.length=0;}
    }
    path(ctx,points,rgba(PINK,alpha),.7);
  };
  const rings=[{radius:r*1.46,tilt:1.07,rotation:-.37},{radius:r*1.30,tilt:.99,rotation:.90},{radius:r*1.58,tilt:1.28,rotation:-1.03}];
  rings.forEach((o,i)=>orbit(o.radius,o.tilt,o.rotation+Math.sin(time*.055+i)*.07,time*.04,false,.16));

  const spherePoint=(longitude,latitude)=>{
    const x=Math.cos(latitude)*Math.cos(longitude+time*.115);
    const y=Math.sin(latitude),z=Math.cos(latitude)*Math.sin(longitude+time*.115);
    const tilt=.30,ny=y*Math.cos(tilt)-z*Math.sin(tilt),nz=y*Math.sin(tilt)+z*Math.cos(tilt);
    const lens=1+nz*.09;
    const breathing=1+.013*Math.sin(time*.8);
    return [cx+x*r*lens*breathing,cy+ny*r*lens*breathing,nz];
  };
  const filament=(points,front)=>{
    let segment=[];
    for(const p of points) {
      if((p[2]>=0)===front)segment.push(p);
      else if(segment.length){path(ctx,segment,rgba(front?RED:PINK,front?.36:.09),front?.75:.55);segment=[];}
    }
    path(ctx,segment,rgba(front?RED:PINK,front?.36:.09),front?.75:.55);
  };
  const weave=[];
  for(let lat=-6;lat<=6;lat++) weave.push(Array.from({length:73},(_,n)=>spherePoint(n/72*TAU,lat/7*Math.PI*.5)));
  for(let meridian=0;meridian<16;meridian++) weave.push(Array.from({length:57},(_,n)=>spherePoint(meridian/16*TAU,n/56*Math.PI-Math.PI*.5)));
  weave.forEach(points=>filament(points,false));
  const core=ctx.createRadialGradient(cx-r*.25,cy-r*.24,r*.05,cx,cy,r);
  core.addColorStop(0,'#36202e');core.addColorStop(.50,'#1c1420');core.addColorStop(1,'#110f18');
  ctx.beginPath();ctx.arc(cx,cy,r*.97,0,TAU);ctx.fillStyle=core;ctx.fill();
  weave.forEach(points=>filament(points,true));

  // Finely spaced wave contours form an abstract nucleus, not an audio waveform.
  ctx.save();ctx.globalCompositeOperation='screen';
  for(let ring=0;ring<9;ring++) {
    const radius=r*(.22+ring*.039),points=[];
    for(let i=0;i<=96;i++) {
      const a=i/96*TAU;
      const ripple=1+.064*Math.sin(a*5+time*.70+ring*.38)+.038*Math.cos(a*3-time*.32);
      points.push([cx+Math.cos(a)*radius*ripple,cy+Math.sin(a)*radius*ripple*.92]);
    }
    path(ctx,points,rgba(ring<4?INK:RED,.47-ring*.035),.7);
  }
  glow(ctx,cx,cy,r*.31,RED,.22);
  dot(ctx,cx,cy,Math.max(1,r*.016),rgba(INK,.82));
  ctx.restore();
  rings.forEach((o,i)=>{
    const rotation=o.rotation+Math.sin(time*.055+i)*.07;
    orbit(o.radius,o.tilt,rotation,time*.04,true,.46);
    const a=time*(.18+i*.036)+i*2.14;
    const ox=Math.cos(a)*o.radius,oy=Math.sin(a)*o.radius*Math.cos(o.tilt);
    const x=cx+ox*Math.cos(rotation)-oy*Math.sin(rotation),y=cy+ox*Math.sin(rotation)+oy*Math.cos(rotation);
    glow(ctx,x,y,Math.max(5,r*.10),RED,.4);
    dot(ctx,x,y,Math.max(1,r*.017),rgba(INK,.9));
  });
  // Incomplete peripheral arcs keep the composition open and light.
  for(let index=0;index<4;index++) {
    const start=index*Math.PI*.5+time*.035;
    ctx.beginPath();ctx.arc(cx,cy,r*1.23,start,start+.20);
    ctx.strokeStyle=rgba(INK,.26);ctx.lineWidth=.8;ctx.stroke();
  }
}

/**
 * Mount into a positioned host with a non-zero height.
 * @returns {{setMotion(value: boolean): void, dispose(): void}}
 */
export function mountMotionStage(container, {kind='production',motion=true}={}) {
  if(!container?.ownerDocument || typeof container.appendChild!=='function') throw new TypeError('Un conteneur DOM est requis.');
  if(kind!=='production' && kind!=='jarvis') throw new TypeError('Scène inconnue.');
  mounts.get(container)?.dispose();
  const doc=container.ownerDocument,win=doc.defaultView||globalThis;
  const canvas=doc.createElement('canvas');
  canvas.className='motion-stage-canvas';
  canvas.setAttribute('aria-hidden','true');
  canvas.setAttribute('role','presentation');
  canvas.dataset.kind=kind;
  Object.assign(canvas.style,{position:'absolute',inset:'0',width:'100%',height:'100%',display:'block',pointerEvents:'none'});
  container.appendChild(canvas);
  const ctx=canvas.getContext('2d',{alpha:false});
  if(!ctx) {canvas.remove();return {setMotion(){},dispose(){}};}

  const backdrop=doc.createElement('canvas'),backdropContext=backdrop.getContext('2d',{alpha:false});
  const media=win.matchMedia?.('(prefers-reduced-motion: reduce)');
  const requestFrame=win.requestAnimationFrame?.bind(win),cancelFrame=win.cancelAnimationFrame?.bind(win);
  let disposed=false,wanted=motion!==false,visible=true,lost=false;
  let width=0,height=0,dpr=1,frame=0,last=0,lastPaint=0,time=8;
  let ratioMedia=null,resizeObserver=null,intersectionObserver=null;
  const listen=(query,fn)=>{if(query?.addEventListener)query.addEventListener('change',fn);else query?.addListener?.(fn);};
  const unlisten=(query,fn)=>{if(query?.removeEventListener)query.removeEventListener('change',fn);else query?.removeListener?.(fn);};
  const canMove=()=>!disposed&&!lost&&wanted&&!media?.matches&&!doc.hidden&&visible&&width>0&&height>0&&!!requestFrame;
  function paint() {
    if(disposed||lost||width<=0||height<=0)return;
    ctx.setTransform(dpr,0,0,dpr,0,0);
    ctx.globalCompositeOperation='source-over';ctx.globalAlpha=1;
    ctx.lineCap='round';ctx.lineJoin='round';
    if(backdropContext)ctx.drawImage(backdrop,0,0,width,height);
    else background(ctx,width,height,kind);
    if(kind==='production')production(ctx,width,height,time);else jarvis(ctx,width,height,time);
  }
  function stop() {
    if(frame)cancelFrame?.(frame);
    frame=0;last=0;lastPaint=0;
  }
  function tick(now) {
    frame=0;
    if(!canMove()){last=0;return;}
    if(last)time+=Math.min(64,Math.max(0,now-last))/1000;
    last=now;
    if(!lastPaint||now-lastPaint>=1000/30){paint();lastPaint=now;}
    frame=requestFrame(tick);
  }
  function reconcile(redraw=false) {
    if(disposed)return;
    if(!canMove())stop();
    if(redraw&&!doc.hidden&&visible)paint();
    if(canMove()&&!frame)frame=requestFrame(tick);
  }
  function resize() {
    if(disposed)return;
    const rect=container.getBoundingClientRect();
    const nextWidth=Math.max(0,rect.width),nextHeight=Math.max(0,rect.height);
    const ratio=Math.max(.5,Math.min(2,win.devicePixelRatio||1,Math.sqrt(2000000/Math.max(1,nextWidth*nextHeight))));
    if(width===nextWidth&&height===nextHeight&&dpr===ratio){reconcile();return;}
    width=nextWidth;height=nextHeight;dpr=ratio;
    canvas.width=Math.max(1,Math.round(width*dpr));canvas.height=Math.max(1,Math.round(height*dpr));
    backdrop.width=canvas.width;backdrop.height=canvas.height;
    if(backdropContext&&width>0&&height>0){backdropContext.setTransform(dpr,0,0,dpr,0,0);background(backdropContext,width,height,kind);}
    reconcile(true);
  }
  function watchRatio() {
    unlisten(ratioMedia,onRatio);
    ratioMedia=win.matchMedia?.(`(resolution: ${win.devicePixelRatio||1}dppx)`);
    listen(ratioMedia,onRatio);
  }
  function onRatio(){resize();watchRatio();}
  function onVisibility(){reconcile(true);}
  function onPreference(){reconcile(true);}
  function onLost(event){event.preventDefault();lost=true;stop();}
  function onRestored(){lost=false;reconcile(true);}
  const api={
    setMotion(value){if(disposed)return;wanted=value!==false;reconcile(true);},
    dispose(){
      if(disposed)return;
      disposed=true;stop();
      resizeObserver?.disconnect();intersectionObserver?.disconnect();
      doc.removeEventListener('visibilitychange',onVisibility);
      win.removeEventListener?.('resize',resize);
      unlisten(media,onPreference);unlisten(ratioMedia,onRatio);
      canvas.removeEventListener('contextlost',onLost);canvas.removeEventListener('contextrestored',onRestored);
      canvas.remove();canvas.width=canvas.height=1;backdrop.width=backdrop.height=1;
      if(mounts.get(container)===api)mounts.delete(container);
    }
  };
  mounts.set(container,api);
  doc.addEventListener('visibilitychange',onVisibility);
  win.addEventListener?.('resize',resize,{passive:true});
  listen(media,onPreference);watchRatio();
  canvas.addEventListener('contextlost',onLost);canvas.addEventListener('contextrestored',onRestored);
  if(typeof win.ResizeObserver==='function'){resizeObserver=new win.ResizeObserver(resize);resizeObserver.observe(container);}
  if(typeof win.IntersectionObserver==='function'){
    intersectionObserver=new win.IntersectionObserver(entries=>{
      if(disposed)return;
      visible=entries.some(entry=>entry.target===container&&entry.isIntersecting);
      reconcile(true);
    },{rootMargin:'24px',threshold:0});
    intersectionObserver.observe(container);
  }
  resize();
  return api;
}
