// Video frames are processed on-device only; only these numbers leave the browser:
// {t, face, gaze, smile, motion} per sample.
// Note: `gaze` means the head is roughly facing the camera (head pose), not true eye tracking.

export function headPoseFromMatrix(data) {
  const yaw = Math.atan2(-data[8], Math.sqrt(data[9] * data[9] + data[10] * data[10]));
  const pitch = Math.atan2(data[9], data[10]);
  const toDeg = (r) => (r * 180) / Math.PI;
  return { yaw: toDeg(yaw), pitch: toDeg(pitch) };
}

export async function createFaceSignalTracker(videoEl, { intervalMs = 100 } = {}) {
  try {
    const vision = await import('@mediapipe/tasks-vision');
    const fileset = await vision.FilesetResolver.forVisionTasks(
      'https://cdn.jsdelivr.net/npm/@mediapipe/tasks-vision@0.10.14/wasm'
    );
    const landmarker = await vision.FaceLandmarker.createFromOptions(fileset, {
      baseOptions: {
        modelAssetPath:
          'https://storage.googleapis.com/mediapipe-models/face_landmarker/face_landmarker/float16/1/face_landmarker.task',
        delegate: 'GPU',
      },
      runningMode: 'VIDEO',
      numFaces: 1,
      outputFaceBlendshapes: true,
      outputFacialTransformationMatrixes: true,
    });

    const samples = [];
    let startedAt = 0;
    let prevNose = null;
    let timer = null;
    let closed = false;

    const sample = () => {
      if (!videoEl || videoEl.readyState < 2) return; // camera frame not ready yet
      let result;
      try {
        result = landmarker.detectForVideo(videoEl, performance.now());
      } catch {
        return; // skip a bad frame rather than stopping the session
      }
      const t = +(((performance.now() - startedAt) / 1000).toFixed(3));
      const face = (result.faceLandmarks?.length ?? 0) > 0;
      if (!face) {
        prevNose = null;
        samples.push({ t, face: false, gaze: false, smile: 0, motion: 0 });
        return;
      }
      let gaze = false;
      if (result.facialTransformationMatrixes?.length > 0) {
        const { yaw, pitch } = headPoseFromMatrix(result.facialTransformationMatrixes[0].data);
        gaze = Math.abs(yaw) < 20 && Math.abs(pitch) < 20;
      }
      let smile = 0;
      const bs = result.faceBlendshapes?.[0]?.categories;
      if (bs) {
        const get = (name) => bs.find((c) => c.categoryName === name)?.score ?? 0;
        smile = (get('mouthSmileLeft') + get('mouthSmileRight')) / 2;
      }
      const nose = result.faceLandmarks[0][1];
      let motion = 0;
      if (prevNose) {
        const dx = nose.x - prevNose.x;
        const dy = nose.y - prevNose.y;
        motion = Math.min(1, Math.sqrt(dx * dx + dy * dy) * 10);
      }
      prevNose = { x: nose.x, y: nose.y };
      samples.push({ t, face: true, gaze, smile, motion });
    };

    return {
      start() {
        startedAt = performance.now();
        timer = setInterval(sample, intervalMs);
      },
      stop() {
        if (timer) clearInterval(timer);
        timer = null;
        if (!closed) { landmarker.close(); closed = true; }
        return samples;
      },
    };
  } catch {
    return null;
  }
}
