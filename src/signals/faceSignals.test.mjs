import { headPoseFromMatrix } from './faceSignals.js';
import assert from 'node:assert';

// identity
let { yaw, pitch } = headPoseFromMatrix([
  1, 0, 0, 0,
  0, 1, 0, 0,
  0, 0, 1, 0,
  0, 0, 0, 1,
]);
assert.ok(Math.abs(yaw) < 1e-6 && Math.abs(pitch) < 1e-6, `identity: ${yaw}, ${pitch}`);

// +30 deg rotation about Y axis (column-major)
const a = (30 * Math.PI) / 180;
const c = Math.cos(a), s = Math.sin(a);
// column-major Ry = [[c,0,-s,0],[0,1,0,0],[s,0,c,0],[0,0,0,1]] transposed columns
({ yaw, pitch } = headPoseFromMatrix([
  c, 0, s, 0,
  0, 1, 0, 0,
  -s, 0, c, 0,
  0, 0, 0, 1,
]));
assert.ok(Math.abs(Math.abs(yaw) - 30) < 0.5, `yaw: ${yaw}`);
assert.ok(Math.abs(pitch) < 0.5, `pitch: ${pitch}`);

console.log('ALL OK');
