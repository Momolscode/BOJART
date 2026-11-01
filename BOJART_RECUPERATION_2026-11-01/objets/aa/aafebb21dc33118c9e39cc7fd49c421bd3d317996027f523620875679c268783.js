import * as THREE from 'three';
import {OrbitControls} from '../vendor/OrbitControls.js';
import {STLLoader} from '../vendor/STLLoader.js';
import {inspectSTL} from './viewer.js';
import {PREPARATION_ORIENTATIONS} from './preparation.js';

// Source STL axes become the selected machine axes first. Only then is machine
// Z displayed vertically (world Y). Every orientation is a proper rotation.
export function buildOrientationMatrix(id = 'xyz') {
  const orientation = PREPARATION_ORIENTATIONS.find(item => item.id === id);
  if (!orientation) throw new RangeError('Orientation d’encombrement inconnue.');
  const rows = Array.from({length:3}, () => [0,0,0]);
  orientation.axes.forEach((axis,index) => { rows[index][axis] = orientation.signs[index]; });
  return new THREE.Matrix4().set(...rows[0],0,...rows[1],0,...rows[2],0,0,0,0,1);
}

/** Pure placement used by both the viewer and geometric verification. */
export function placementForBounds(min, max, unit = 'mm', orientationId = 'xyz') {
  if (!['mm','inch'].includes(unit)) throw new RangeError('Unité du STL à préciser : mm ou inch.');
  for (const values of [min,max]) if (!Array.isArray(values) || values.length !== 3 || Array.from(values).some(value => typeof value !== 'number' || !Number.isFinite(value))) throw new RangeError('Bornes du maillage invalides.');
  if (max.some((value,index) => value < min[index])) throw new RangeError('Bornes du maillage inversées.');
  const factor = unit === 'inch' ? 25.4 : 1;
  const original = new THREE.Box3(new THREE.Vector3(...min),new THREE.Vector3(...max));
  const orientation = buildOrientationMatrix(orientationId).scale(new THREE.Vector3(factor,factor,factor));
  const oriented = original.clone().applyMatrix4(orientation);
  const size = oriented.getSize(new THREE.Vector3()),center = oriented.getCenter(new THREE.Vector3());
  const machineMatrix = new THREE.Matrix4().makeTranslation(-center.x,-center.y,-oriented.min.z).multiply(orientation);
  const matrix = new THREE.Matrix4().makeRotationX(-Math.PI/2).multiply(machineMatrix);
  return {matrix,dimensionsMm:size.toArray(),worldBounds:original.clone().applyMatrix4(matrix)};
}

function validVolume(value) {
  if (value === null) return null;
  if (!Array.isArray(value) || value.length !== 3 || Array.from(value).some(n => typeof n !== 'number' || !Number.isFinite(n) || n <= 0 || n > 10000)) throw new RangeError('Le volume utile attend trois dimensions positives en millimètres.');
  return [...value];
}

function disposeTree(object) {
  object.traverse(child => {
    child.geometry?.dispose();
    if (Array.isArray(child.material)) child.material.forEach(material => material.dispose());
    else child.material?.dispose();
  });
}

export async function createPreparationViewport(container,{motion=true,onStatus=()=>{}}={}) {
  let renderer;
  try { renderer = new THREE.WebGLRenderer({antialias:true,alpha:true,powerPreference:'high-performance'}); }
  catch { throw new Error('L’affichage 3D nécessite WebGL 2. Le rapport dimensionnel reste disponible.'); }
  renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1,1.6));
  renderer.setClearColor(0x000000,0);
  renderer.toneMapping = THREE.ACESFilmicToneMapping;
  renderer.toneMappingExposure = 1.25;
  renderer.shadowMap.enabled = true;
  renderer.shadowMap.type = THREE.PCFSoftShadowMap;
  renderer.domElement.setAttribute('aria-label','STL dans le volume utile déclaré de la machine');
  renderer.domElement.style.cssText = 'display:block;width:100%;height:100%;position:absolute;inset:0';
  container.prepend(renderer.domElement);

  const scene = new THREE.Scene();
  const camera = new THREE.PerspectiveCamera(36,1,.1,10000);
  const controls = new OrbitControls(camera,renderer.domElement);
  controls.enableDamping = !!motion;
  controls.dampingFactor = .075;
  controls.maxPolarAngle = Math.PI*.86;
  controls.target.set(0,70,0);
  camera.position.set(350,275,400);
  scene.add(new THREE.AmbientLight(0xc4b7d6,1.55));
  const key = new THREE.DirectionalLight(0xffeae0,3.7);
  key.castShadow = true;
  key.shadow.mapSize.set(1024,1024);
  key.shadow.normalBias = .2;
  scene.add(key);scene.add(key.target);
  const rim = new THREE.DirectionalLight(0xfa315d,2.1);
  scene.add(rim);
  const fill = new THREE.DirectionalLight(0xa7a9ff,1.6);
  scene.add(fill);

  const grid = new THREE.GridHelper(20,20,0x78405a,0x342533);
  grid.material.transparent = true;grid.material.opacity = .4;grid.position.y = -.18;grid.visible = false;
  scene.add(grid);
  let cage = new THREE.Group();scene.add(cage);
  let model = null,sourceBounds = null,sourceUnit = 'mm',orientationId = 'xyz',placement = null,volume = null;
  let wire = false,disposed = false,visible = true,raf = 0,remainingFrames = 0,lastTime = 0;
  let targetPosition = null,targetLook = null;

  function request(frames = 40) {
    remainingFrames = Math.max(remainingFrames,frames);
    if (!raf && !disposed && visible && !document.hidden) raf = requestAnimationFrame(tick);
  }
  function tick(time) {
    raf = 0;
    if (disposed || !visible || document.hidden) { lastTime = 0;return; }
    const dt = Math.min((time-lastTime)/1000 || .016,.05);lastTime = time;
    let easing = false;
    if (targetPosition && targetLook) {
      if (motion) {
        camera.position.lerp(targetPosition,1-Math.exp(-dt*10));
        controls.target.lerp(targetLook,1-Math.exp(-dt*10));
        easing = camera.position.distanceToSquared(targetPosition) > .01 || controls.target.distanceToSquared(targetLook) > .01;
      } else { camera.position.copy(targetPosition);controls.target.copy(targetLook); }
      if (!easing) { camera.position.copy(targetPosition);controls.target.copy(targetLook);targetPosition=null;targetLook=null; }
    }
    controls.update(dt);renderer.render(scene,camera);remainingFrames--;
    if ((easing || remainingFrames > 0) && !raf) raf = requestAnimationFrame(tick);
  }

  function bounds() {
    const box = new THREE.Box3();
    if (placement) box.union(placement.worldBounds);
    if (volume) box.union(new THREE.Box3(new THREE.Vector3(-volume[0]/2,0,-volume[1]/2),new THREE.Vector3(volume[0]/2,volume[2],volume[1]/2)));
    return box;
  }
  function frameAll(animate = true) {
    const box = bounds();grid.visible = !box.isEmpty();
    if (box.isEmpty()) { request(2);return; }
    const size = box.getSize(new THREE.Vector3()),center = box.getCenter(new THREE.Vector3());
    const scale = Math.max(size.x,size.y,size.z,1);
    const fit = Math.max(1,1/Math.max(camera.aspect,.2));
    const distance = scale*(fit>1?fit:1);
    targetPosition = center.clone().add(new THREE.Vector3(distance*1.3,distance*.85,distance*1.7));
    targetLook = center.clone();
    if (!animate || !motion) { camera.position.copy(targetPosition);controls.target.copy(targetLook);targetPosition=null;targetLook=null; }
    camera.near = Math.max(.001,scale/10000);camera.far = Math.max(1000,distance*80);camera.updateProjectionMatrix();
    controls.minDistance = scale*.15;controls.maxDistance = distance*12;
    grid.scale.setScalar(Math.max(size.x,size.z,1)*1.35/20);
    key.position.copy(center).add(new THREE.Vector3(scale*.8,scale*1.4,scale));key.target.position.copy(center);
    key.shadow.camera.left = -scale;key.shadow.camera.right = scale;key.shadow.camera.top = scale;key.shadow.camera.bottom = -scale;key.shadow.camera.near = .1;key.shadow.camera.far = scale*6;key.shadow.camera.updateProjectionMatrix();
    rim.position.copy(center).add(new THREE.Vector3(-scale,scale*.6,-scale));
    fill.position.copy(center).add(new THREE.Vector3(scale*.9,scale*.4,-scale));
    controls.update();request(70);
  }
  function applyPlacement() {
    if (!model || !sourceBounds) { placement=null;return; }
    placement = placementForBounds(sourceBounds.min.toArray(),sourceBounds.max.toArray(),sourceUnit,orientationId);
    model.matrix.copy(placement.matrix);model.matrixWorldNeedsUpdate = true;
  }
  function clearModel() {
    if (disposed) return;
    if (model) { scene.remove(model);disposeTree(model); }
    model=null;sourceBounds=null;placement=null;
    frameAll(false);
  }
  function loadSTL(buffer,unit='mm') {
    if (disposed) throw new Error('Cet établi 3D est fermé.');
    const info = inspectSTL(buffer,unit);
    const geometry = new STLLoader().parse(buffer);
    geometry.computeBoundingBox();geometry.computeVertexNormals();
    clearModel();sourceUnit=unit;sourceBounds=geometry.boundingBox.clone();
    const material = new THREE.MeshStandardMaterial({color:0xdcc9d6,metalness:.23,roughness:.4,wireframe:wire,side:THREE.DoubleSide});
    model=new THREE.Mesh(geometry,material);model.matrixAutoUpdate=false;model.castShadow=true;model.receiveShadow=true;scene.add(model);
    applyPlacement();frameAll(false);
    onStatus('Fichier STL affiché · orientation d’encombrement · supports et tranchage à préparer.');
    return info;
  }
  function setBuildVolume(value) {
    if (disposed) return;
    const next = validVolume(value);
    if (JSON.stringify(next) === JSON.stringify(volume)) return;
    scene.remove(cage);disposeTree(cage);cage=new THREE.Group();scene.add(cage);volume=next;
    if (volume) {
      const [x,y,z] = volume;
      const box = new THREE.BoxGeometry(x,z,y);
      const edges = new THREE.EdgesGeometry(box);box.dispose();
      const frame = new THREE.LineSegments(edges,new THREE.LineBasicMaterial({color:0xd9769e,transparent:true,opacity:.75}));
      frame.position.y=z/2;cage.add(frame);
      const plate = new THREE.Mesh(new THREE.PlaneGeometry(x,y),new THREE.MeshStandardMaterial({color:0x231521,metalness:.15,roughness:.64,side:THREE.DoubleSide}));
      plate.rotation.x=-Math.PI/2;plate.position.y=-.25;plate.receiveShadow=true;cage.add(plate);
      const axes = new THREE.AxesHelper(Math.min(x,y,z)*.18);
      axes.rotation.x=-Math.PI/2;axes.position.set(-x/2,.05,y/2);cage.add(axes);
    }
    frameAll(true);
  }
  function setOrientation(id) {
    if (disposed) return;
    buildOrientationMatrix(id);
    if (id === orientationId) return;
    orientationId=id;applyPlacement();frameAll(true);
  }
  function setWireframe(value) { wire=!!value;if (model) model.material.wireframe=wire;request(2); }
  function setMotion(value) {
    motion=!!value;controls.enableDamping=motion;
    if (!motion && targetPosition) { camera.position.copy(targetPosition);controls.target.copy(targetLook);targetPosition=null;targetLook=null; }
    request(2);
  }
  function resize() {
    if (disposed) return;
    const width=Math.max(container.clientWidth,1),height=Math.max(container.clientHeight,1);
    renderer.setSize(width,height,false);camera.aspect=width/height;camera.updateProjectionMatrix();frameAll(false);
  }
  const onControlStart=()=>{targetPosition=null;targetLook=null;request(20);};
  const onControlChange=()=>request(12);
  controls.addEventListener('start',onControlStart);controls.addEventListener('change',onControlChange);
  const resizeObserver=new ResizeObserver(resize);resizeObserver.observe(container);
  const intersection=new IntersectionObserver(entries=>{visible=entries[0]?.isIntersecting!==false;if (visible)request(8);},{threshold:.01});intersection.observe(container);
  const visibility=()=>{if (!document.hidden)request(8);};document.addEventListener('visibilitychange',visibility);
  function dispose() {
    if (disposed) return;disposed=true;cancelAnimationFrame(raf);
    resizeObserver.disconnect();intersection.disconnect();document.removeEventListener('visibilitychange',visibility);
    controls.removeEventListener('start',onControlStart);controls.removeEventListener('change',onControlChange);controls.dispose();
    disposeTree(scene);renderer.dispose();renderer.domElement.remove();
  }
  resize();
  return {loadSTL,clearModel,setBuildVolume,setOrientation,reset:()=>frameAll(true),setWireframe,setMotion,dispose};
}
