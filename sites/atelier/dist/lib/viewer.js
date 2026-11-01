import * as THREE from 'three';
import {OrbitControls} from '../vendor/OrbitControls.js';
import {STLLoader} from '../vendor/STLLoader.js';

export function inspectSTL(buffer,unit='mm'){
  if(!(buffer instanceof ArrayBuffer)||buffer.byteLength<15||buffer.byteLength>50*1024*1024)throw new Error('STL invalide ou supérieur à 50 Mo.');
  if(!['mm','inch'].includes(unit))throw new Error('Unité non reconnue.');
  if(buffer.byteLength>=84){const count=new DataView(buffer).getUint32(80,true);if(84+count*50===buffer.byteLength&&count>2000000)throw new Error('Le fichier dépasse deux millions de triangles.');}
  let geometry;try{geometry=new STLLoader().parse(buffer);}catch{throw new Error('Le fichier ne peut pas être décodé comme un STL.');}
  const positions=geometry.getAttribute('position');
  if(!positions||positions.count<3||positions.count%3!==0||positions.count>6000000){geometry.dispose();throw new Error('Le maillage est vide ou trop complexe.');}
  for(let i=0;i<positions.array.length;i++){if(!Number.isFinite(positions.array[i])){geometry.dispose();throw new Error('Le maillage contient des coordonnées invalides.');}}
  geometry.computeBoundingBox();const size=new THREE.Vector3();geometry.boundingBox.getSize(size);const factor=unit==='inch'?25.4:1;const dims=size.toArray().map(n=>n*factor);
  if(dims.some(n=>!Number.isFinite(n)||n>1000000)||Math.max(...dims)<=0){geometry.dispose();throw new Error('Dimensions de maillage invalides.');}
  const triangles=positions.count/3;geometry.dispose();return{dims,triangles,unit,demo:false};
}

export async function createViewer(container,{motion=true,onStatus=()=>{}}={}){
  let renderer;try{renderer=new THREE.WebGLRenderer({antialias:true,alpha:true,powerPreference:'high-performance'});}catch{throw new Error('WebGL 2 est nécessaire pour afficher les modèles.');}
  renderer.setPixelRatio(Math.min(window.devicePixelRatio||1,1.7));renderer.localClippingEnabled=true;renderer.shadowMap.enabled=true;renderer.shadowMap.type=THREE.PCFSoftShadowMap;renderer.toneMapping=THREE.ACESFilmicToneMapping;renderer.toneMappingExposure=1.55;renderer.setClearColor(0x000000,0);renderer.domElement.setAttribute('aria-label','Modèle 3D interactif');container.prepend(renderer.domElement);
  const scene=new THREE.Scene();const camera=new THREE.PerspectiveCamera(34,1,.1,10000);camera.position.set(175,125,205);
  const controls=new OrbitControls(camera,renderer.domElement);controls.enableDamping=true;controls.dampingFactor=.065;controls.minDistance=15;controls.maxDistance=2000;controls.maxPolarAngle=Math.PI*.88;controls.target.set(0,18,0);controls.update();
  scene.add(new THREE.AmbientLight(0xbab1d6,1.5));
  const key=new THREE.DirectionalLight(0xfff0dc,4.1);key.position.set(90,170,130);key.castShadow=true;key.shadow.mapSize.set(1024,1024);key.shadow.camera.left=-160;key.shadow.camera.right=160;key.shadow.camera.top=160;key.shadow.camera.bottom=-160;key.shadow.camera.far=600;key.shadow.normalBias=.15;scene.add(key);
  const rim=new THREE.DirectionalLight(0xff2859,3.4);rim.position.set(-100,90,-90);scene.add(rim);
  const fill=new THREE.DirectionalLight(0xaabcf8,2.4);fill.position.set(100,50,-120);scene.add(fill);
  const ground=new THREE.Mesh(new THREE.PlaneGeometry(1200,1200),new THREE.ShadowMaterial({color:0x000000,opacity:.36}));ground.rotation.x=-Math.PI/2;ground.position.y=-.3;ground.receiveShadow=true;scene.add(ground);
  const grid=new THREE.GridHelper(450,30,0x593042,0x25222e);grid.position.y=-.2;grid.material.transparent=true;grid.material.opacity=.55;scene.add(grid);
  let object=new THREE.Group();scene.add(object);let demo=true,exploded=false,wire=false,auto=false,disposed=false,raf=0,visible=true,needFrames=80,lastTime=0,movingUntil=0;
  let parts=[];const vector=new THREE.Vector3();
  // Viewer-space Y is vertical (source STL Z after its existing display transform).
  // The plane hides the top portion; it never rewrites vertices or exports layers.
  let sectionFraction=null;
  const sectionPlane=new THREE.Plane(new THREE.Vector3(0,-1,0),0);
  const sectionBounds=new THREE.Box3(),originalSides=new WeakMap();
  function updateSectionPlane(bounds=null){if(sectionFraction===null)return;const box=bounds||sectionBounds.setFromObject(object);if(box.isEmpty())return;sectionPlane.constant=box.min.y+(box.max.y-box.min.y)*sectionFraction;}
  function configureSection(material){if(!originalSides.has(material))originalSides.set(material,material.side);const enabled=sectionFraction!==null;material.clippingPlanes=enabled?[sectionPlane]:null;material.clipShadows=enabled;material.side=enabled?THREE.DoubleSide:originalSides.get(material);material.needsUpdate=true;}
  function disposeObject(){scene.remove(object);object.traverse(child=>{child.geometry?.dispose();if(Array.isArray(child.material))child.material.forEach(m=>m.dispose());else child.material?.dispose();});object=new THREE.Group();scene.add(object);parts=[];}
  function mesh(geometry,color,roughness=.36,metalness=.48){const m=new THREE.Mesh(geometry,new THREE.MeshStandardMaterial({color,roughness,metalness,wireframe:wire}));configureSection(m.material);m.castShadow=true;m.receiveShadow=true;return m;}
  function addPart(m,y,offset=0){m.position.y=y;object.add(m);parts.push({mesh:m,base:m.position.clone(),offset:new THREE.Vector3(0,offset,0),target:m.position.clone()});return m;}
  function showDemo(){disposeObject();demo=true;exploded=false;const base=addPart(mesh(new THREE.CylinderGeometry(61,64,12,8),0x242128,.29,.73),6,0);base.rotation.y=Math.PI/8;
    addPart(mesh(new THREE.CylinderGeometry(57,60,3,64),0xe12a4d,.3,.46),13.5,15);
    addPart(mesh(new THREE.CylinderGeometry(53,56,10,64),0x38343d,.28,.65),20,29);
    const plate=addPart(mesh(new THREE.CylinderGeometry(50,50,5,64),0xc7bbc9,.26,.77),27.5,47);
    const inlay=addPart(mesh(new THREE.CylinderGeometry(43,43,1,64),0x262129,.66,.26),30.5,47);
    for(let i=0;i<3;i++){const pin=addPart(mesh(new THREE.CylinderGeometry(3,3,9,20),0xf0ced6,.23,.8),35,64);pin.position.x=Math.cos(i*Math.PI*2/3)*31;pin.position.z=Math.sin(i*Math.PI*2/3)*31;parts[parts.length-1].base.copy(pin.position);parts[parts.length-1].target.copy(pin.position);}
    const ring=mesh(new THREE.TorusGeometry(54,0.65,8,100),0xff365b,.22,.3);ring.rotation.x=Math.PI/2;addPart(ring,25.3,29);
    object.rotation.y=-.2;frameObject();onStatus('Socle de démonstration · 128 × 128 × 39,5 mm · assemblage illustratif');request();return{demo:true};
  }
  function frameObject(){const box=new THREE.Box3().setFromObject(object);updateSectionPlane(box);const size=box.getSize(new THREE.Vector3()),center=box.getCenter(new THREE.Vector3());const max=Math.max(...size.toArray(),1);controls.target.copy(center);camera.near=Math.max(.01,max/1000);camera.far=max*100;camera.position.copy(center).add(new THREE.Vector3(max*1.3,max*.9,max*1.7));camera.updateProjectionMatrix();controls.minDistance=max*.2;controls.maxDistance=max*8;controls.update();const groundY=box.min.y-.2;ground.position.y=groundY;grid.position.y=groundY+.05;grid.scale.setScalar(Math.max(max/140,1));request();}
  function loadSTL(buffer,unit='mm'){const info=inspectSTL(buffer,unit);const geometry=new STLLoader().parse(buffer);geometry.computeBoundingBox();geometry.computeVertexNormals();const center=geometry.boundingBox.getCenter(new THREE.Vector3());const factor=unit==='inch'?25.4:1;disposeObject();demo=false;exploded=false;
    const model=mesh(geometry,0xd8c4d2,.37,.33);model.scale.setScalar(factor);model.position.set(-center.x*factor,-geometry.boundingBox.min.z*factor,center.y*factor);model.rotation.x=-Math.PI/2;object.add(model);frameObject();onStatus(`${info.dims.map(x=>x.toLocaleString('fr-FR',{maximumFractionDigits:1})).join(' × ')} mm · ${info.triangles.toLocaleString('fr-FR')} triangles · préparation non validée`);return info;
  }
  function explode(value){if(!demo){onStatus('Un STL unique ne constitue pas un assemblage découpé.');return false;}exploded=!!value;parts.forEach(p=>p.target.copy(p.base).add(exploded?p.offset:new THREE.Vector3()));movingUntil=performance.now()+1200;if(!motion)parts.forEach(p=>p.mesh.position.copy(p.target));controls.target.y=exploded?43:18;request();return true;}
  function resize(){if(disposed)return;const width=Math.max(1,container.clientWidth),height=Math.max(1,container.clientHeight);renderer.setSize(width,height,false);camera.aspect=width/height;camera.updateProjectionMatrix();request();}
  function request(){needFrames=90;if(!raf&&!disposed)raf=requestAnimationFrame(tick);}
  function tick(time){raf=0;if(disposed||!visible||document.hidden){lastTime=0;return;}const dt=Math.min((time-lastTime)/1000||.016,.05);lastTime=time;
    let animating=false;if(demo){for(const p of parts){if(p.mesh.position.distanceToSquared(p.target)>.001){if(motion)p.mesh.position.lerp(p.target,1-Math.exp(-dt*9));else p.mesh.position.copy(p.target);animating=true;}}}
    controls.autoRotate=auto&&motion;controls.autoRotateSpeed=.65;controls.update(dt);updateSectionPlane();renderer.render(scene,camera);needFrames--;
    if((auto&&motion)||animating||needFrames>0||time<movingUntil)raf=requestAnimationFrame(tick);
  }
  controls.addEventListener('change',()=>{needFrames=Math.max(needFrames,12);if(!raf&&!disposed)raf=requestAnimationFrame(tick);});controls.addEventListener('start',request);
  const resizeObserver=new ResizeObserver(resize);resizeObserver.observe(container);
  const visibility=()=>{if(!document.hidden)request();};document.addEventListener('visibilitychange',visibility);
  const intersection=new IntersectionObserver(entries=>{visible=entries[0].isIntersecting;if(visible)request();},{threshold:.02});intersection.observe(container);
  function reset(){if(demo){controls.target.set(0,exploded?43:18,0);camera.position.set(175,125,205);controls.update();request();}else frameObject();}
  function setWireframe(value){wire=!!value;object.traverse(m=>{if(m.material)m.material.wireframe=wire;});request();}
  function setAutoRotate(value){auto=!!value;request();}
  function setSection(fraction){
    if(disposed)return;
    if(fraction!==null&&(typeof fraction!=='number'||!Number.isFinite(fraction)||fraction<0||fraction>1))throw new RangeError('La coupe 3D attend une fraction de 0 à 1, ou null pour la désactiver.');
    sectionFraction=fraction;updateSectionPlane();
    object.traverse(child=>{if(Array.isArray(child.material))child.material.forEach(configureSection);else if(child.material)configureSection(child.material);});
    onStatus(fraction===null?'Coupe 3D désactivée · géométrie du fichier inchangée':`Coupe 3D à ${Math.round(fraction*100)} % de la hauteur affichée · visualisation sans fermeture des faces coupées`);
    request();
  }
  function setMotion(value){motion=!!value;if(!motion){parts.forEach(p=>p.mesh.position.copy(p.target));controls.enableDamping=false;}else controls.enableDamping=true;request();}
  function dispose(){if(disposed)return;disposed=true;cancelAnimationFrame(raf);controls.dispose();resizeObserver.disconnect();intersection.disconnect();document.removeEventListener('visibilitychange',visibility);scene.traverse(child=>{child.geometry?.dispose();if(Array.isArray(child.material))child.material.forEach(m=>m.dispose());else child.material?.dispose();});renderer.dispose();renderer.domElement.remove();}
  showDemo();resize();return{loadSTL,showDemo,reset,explode,setWireframe,setAutoRotate,setSection,setMotion,dispose};
}
