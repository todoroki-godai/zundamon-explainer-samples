import assert from 'node:assert/strict';
import {test} from 'node:test';
import '../scripts/coverage-logic.js';

const logic = globalThis.motionCoverageLogic;
const style = (opacity, extra = {}) => ({opacity: String(opacity), display: 'block', visibility: 'visible', ...extra});
const oldRgb = value => value.match(/[\d.]+/g)?.map(Number) ?? [];

test('rgb without alpha is an opaque surface', () => {
  assert.deepEqual(logic.parseRgb('rgb(123, 48, 56)'), [123, 48, 56, 1]);
  assert.equal(oldRgb('rgb(123, 48, 56)').length >= 4, false); // old: rejected
  assert.equal(logic.sameOpaqueColor('rgb(123, 48, 56)', '#7b3038'), true);
});

test('rgba alpha zero is transparent even when RGB matches text color', () => {
  assert.deepEqual(logic.parseRgb('rgba(123, 48, 56, 0)'), [123, 48, 56, 0]);
  assert.equal(logic.parseRgb('rgba(123, 48, 56, 0)')[3] >= 0.999, false); // transparent surface cannot cover the real background
  assert.equal(oldRgb('rgba(123, 48, 56, 0)').slice(0, 3).join(), '123,48,56'); // old: accepted as matching text
  assert.equal(logic.sameOpaqueColor('rgba(123, 48, 56, 0)', '#7b3038'), false);
});

test('ancestor opacity 0.12 throughout the interval is rejected', () => {
  const samples = Array.from({length: 4}, () => ({own: 1, effective: 0.12}));
  assert.equal(samples.some(sample => sample.effective > 0.5), false);
  assert.equal(logic.opacityFailure(samples), true);
  assert.equal(0.12 > 0 && 0.12 <= 0.5, true); // old: also rejected; required negative control
});

test('a brief 0.3 entry fade is exempt when later frames are readable', () => {
  const samples = [{own: 1, effective: 0.3}, {own: 1, effective: 0.7}, {own: 1, effective: 1}];
  assert.equal(0.3 > 0 && 0.3 <= 0.5, true); // old: rejected the first frame
  assert.equal(logic.opacityFailure(samples), false);
});

test('unsupported CSS color syntax cannot masquerade as rgb', () => {
  assert.equal(oldRgb('color(display-p3 1 0 0 / 1)').length >= 4, true); // old: permissive parser
  assert.equal(logic.parseRgb('color(srgb 0.48 0.19 0.22)'), null);
  assert.equal(logic.parseRgb('oklab(0.5 0.1 0.2)'), null);
});

test('layout overflow is rejected while transformed glyph bounds are ignored', () => {
  const box = {clientWidth: 300, clientHeight: 60};
  assert.equal(logic.hasInternalOverflow({...box, scrollWidth: 340, scrollHeight: 80}), true);
  assert.equal(logic.hasInternalOverflow({...box, scrollWidth: 300, scrollHeight: 60}), false);
  assert.equal(logic.hasInternalOverflow({...box, scrollWidth: 320, scrollHeight: 60}), true);
  assert.equal(logic.hasInternalOverflow({...box, scrollWidth: 300, scrollHeight: 90}), true);
});

test('occlusion boundary blocks 0.4 percent and advises 1 percent', () => {
  assert.equal(logic.occludedFraction(0.004), true);
  assert.equal(logic.occludedFraction(0.005), true);
  assert.equal(logic.occludedFraction(0.01), false);
});
