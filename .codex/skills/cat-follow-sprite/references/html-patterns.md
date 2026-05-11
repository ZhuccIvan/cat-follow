# HTML Patterns

Use these snippets when implementing the final static page.

## Angle Interpolation

```js
function wrapFrameDistance(from, to) {
  const raw = to - from;
  const forward = (raw + FRAME_COUNT) % FRAME_COUNT;
  const backward = forward - FRAME_COUNT;
  return Math.abs(forward) <= Math.abs(backward) ? forward : backward;
}

function interpolateFrame(start, end, angle) {
  const t = (angle - start.angle) / (end.angle - start.angle);
  const span = wrapFrameDistance(start.frame, end.frame);
  return Math.round((start.frame + span * t + FRAME_COUNT) % FRAME_COUNT);
}
```

## Top Seam Guard

```js
const TOP_SEAM_LEFT_MIN = 54;
const TOP_SEAM_RIGHT_MAX = 12;

function isTopSeamTransition(from, to) {
  return (from >= TOP_SEAM_LEFT_MIN && to <= TOP_SEAM_RIGHT_MAX) ||
    (from <= TOP_SEAM_RIGHT_MAX && to >= TOP_SEAM_LEFT_MIN);
}
```

Adjust constants after inspecting the contact sheet. The goal is to prevent animation paths from passing through front-facing frames at the top seam.
