import test from 'node:test';
import assert from 'node:assert/strict';
import { DEFAULTS, smoothstep, settings, captureAmount, releaseAmount, envelope, spatialWeight, applyLightPixel } from './light-envelope.js';
import * as shipped from './shipped/light-kernel.min.js';

test('Interpolation is monotone and bounded with exact endpoints', () => {
  let previous = -1;
  for (let i = -100; i <= 1100; i++) {
    const v = smoothstep(i / 1000); assert.ok(v >= 0 && v <= 1); assert.ok(v >= previous); previous = v;
  }
  assert.equal(smoothstep(-20), 0); assert.equal(smoothstep(20), 1);
});
test('Interpolation has no value or first-slope jump at endpoints', () => {
  const h = 1e-5;
  assert.ok(Math.abs(smoothstep(h) - smoothstep(0)) < 1e-8);
  assert.ok(Math.abs(smoothstep(1) - smoothstep(1-h)) < 1e-8);
  assert.ok((smoothstep(h)-smoothstep(0))/h < 1e-3);
  assert.ok((smoothstep(1)-smoothstep(1-h))/h < 1e-3);
});
test('Capture, hold, release close exactly and respect their intervals', () => {
  assert.equal(captureAmount(0),0); assert.equal(captureAmount(1.4),1);
  assert.equal(releaseAmount(2.6),0); assert.equal(releaseAmount(3.6),1);
  assert.equal(envelope(0),0); assert.equal(envelope(2),1); assert.equal(envelope(4),0);
  let prior=0;
  for(let t=.5;t<=1.4;t+=.001){const q=envelope(t);assert.ok(q>=prior-1e-12);prior=q;}
  prior=1;
  for(let t=2.6;t<=3.6;t+=.001){const q=envelope(t);assert.ok(q<=prior+1e-12);prior=q;}
});
test('Protected coordinates and explicit mask retain every input RGB byte', () => {
  for(const t of [0,.7,1.4,2,2.9,3.6,9]) for(const rgb of [[0,0,0],[1,128,254],[255,255,255]]) {
    for(const y of [DEFAULTS.protectFromY,.5,1]) assert.deepEqual(applyLightPixel(rgb,.5,y,t),rgb);
    assert.deepEqual(applyLightPixel(rgb,.5,.04,t,{},true),rgb);
  }
});
test('Spatial boundary is continuous and strictly zero at protection edge', () => {
  assert.equal(spatialWeight(.5,DEFAULTS.protectFromY),0);
  assert.ok(spatialWeight(.5,DEFAULTS.protectFromY-1e-6)<1e-8);
  assert.ok(spatialWeight(.5,.04)>0.5);
});
test('Effect changes permitted pixels and remains inside RGB range', () => {
  const original=[100,100,100]; assert.notDeepEqual(applyLightPixel(original,.5,.04,2),original);
  for(let v=0;v<=255;v++) for(const c of applyLightPixel([v,v,v],.5,.04,2)) assert.ok(c>=0 && c<=255);
});
test('Invalid timing and nonfinite input fail clearly', () => {
  assert.throws(()=>settings({captureEnd:3,releaseStart:2}),RangeError);
  assert.throws(()=>settings({radiusX:0}),RangeError);
  assert.throws(()=>envelope(NaN),TypeError);assert.throws(()=>applyLightPixel([1,2,300],0,0,2),TypeError);
});
test('The shipped artifact reproduces the original fixture on a grid', () => {
  for(const t of [0,.5,.8,1.4,2,2.9,3.6,4]) for(const x of [0,.3,.5,1]) for(const y of [0,.04,.12,.132,.5,1]) {
    assert.equal(shipped.envelope(t),envelope(t));
    assert.deepEqual(shipped.applyLightPixel([40,92,141],x,y,t),applyLightPixel([40,92,141],x,y,t));
  }
});
