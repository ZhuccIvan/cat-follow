---
name: cat-follow-sprite
description: Use when turning a cat or character video with a green/solid background into a static HTML mouse-following sprite, especially when contact sheet inspection, non-linear angle-to-frame calibration, transparent background keying, or top/diagonal seam fixes are needed.
---

# Cat Follow Sprite

## Overview

Build a static HTML character that turns toward the mouse from a source video. Treat the video as a calibrated pose atlas, not as evenly spaced angles.

## Required Workflow

1. Inspect the source video metadata with `ffprobe`.
2. Generate a labeled contact sheet before writing angle logic.
3. View the contact sheet and choose `ANGLE_KEYS` from actual head direction.
4. Generate transparent `sprite.webp` and `frame_front.webp`.
5. Implement `index.html` with calibrated frame lookup.
6. Verify center, up, right, down, left, left-up, left-down, and top seam behavior in a browser.

Use `scripts/build_cat_follow_assets.py` for the repeatable asset step:

```powershell
python "C:\Users\10955\.codex\skills\cat-follow-sprite\scripts\build_cat_follow_assets.py" `
  --video "G:\path\cat.mp4" `
  --out "G:\path\project" `
  --sample-step 4 `
  --frame-size 512 `
  --sprite-columns 16
```

The script writes:

- `contact_sheet_labeled.png`
- `sprite.webp`
- `frame_front.webp`
- `asset_report.json`
- timestamped sample frames under `workframes/`

## Calibration Rules

Never map frames as `angle / 360 * frameCount`.

Use contact-sheet labels to create explicit angle keys:

```js
const ANGLE_KEYS = [
  { angle: -180, frame: 42, sourceFrame: 168, label: "left" },
  { angle: -135, frame: 48, sourceFrame: 192, label: "left-up" },
  { angle: -90, frame: 56, sourceFrame: 224, label: "up" },
  { angle: -45, frame: 12, sourceFrame: 48, label: "right-up" },
  { angle: 0, frame: 22, sourceFrame: 88, label: "right" },
  { angle: 90, frame: 34, sourceFrame: 136, label: "down" },
  { angle: 180, frame: 42, sourceFrame: 168, label: "left" }
];
```

Keep source-frame labels in the table. They are the audit trail proving the mapping came from the contact sheet.

## Background Keying

Key only edge-connected green/solid background. Do not globally delete white, gray, or low-saturation pixels; those are often fur, shadows, eye highlights, or foot gaps.

After keying, protect the subject interior:

- Keep subject components inside the main subject bounding box.
- Preserve original RGB while resizing alpha separately.
- Convert final subject alpha to solid `255` inside and `0` outside to avoid semi-transparent stripe artifacts.
- Do not repair holes by horizontal color interpolation; it creates visible striping.

## HTML Behavior

Use a canvas drawing from `sprite.webp`. If the sprite has many frames, store it as a multi-row atlas to stay below WebP's `16383px` single-side limit:

```js
const FRAME_SIZE = 512;
const FRAME_COUNT = 61;
const SPRITE_COLUMNS = 16;
```

Draw with row/column coordinates:

```js
ctx.drawImage(
  sprite,
  (frame % SPRITE_COLUMNS) * FRAME_SIZE,
  Math.floor(frame / SPRITE_COLUMNS) * FRAME_SIZE,
  FRAME_SIZE,
  FRAME_SIZE,
  0,
  0,
  FRAME_SIZE,
  FRAME_SIZE
);
```

Avoid cross-fading neighboring transparent frames unless specifically requested. It can cause flashing at alpha edges.

## Reset Zone

Do not reset to front based on a generic canvas-center radius. Use a small subject-center ellipse, so top/head regions still look upward:

```js
function isInSubjectResetZone(x, y, rect) {
  const nx = (x - rect.left) / rect.width;
  const ny = (y - rect.top) / rect.height;
  const ex = (nx - 0.5) / 0.055;
  const ey = (ny - 0.53) / 0.075;
  return ex * ex + ey * ey <= 1;
}
```

## Top Seam Handling

If left-top and right-top require different source-frame clusters, do not animate through front frames between them. Add a seam guard:

```js
function isTopSeamTransition(from, to) {
  return (from >= 54 && to <= 12) || (from <= 12 && to >= 54);
}

function nextFrameTowards(from, to) {
  if (isTopSeamTransition(from, to)) return to;
  const delta = wrapFrameDistance(from, to);
  return (from + Math.sign(delta) + FRAME_COUNT) % FRAME_COUNT;
}
```

## Verification Checklist

Before claiming completion:

- View `contact_sheet_labeled.png`.
- View `frame_front.webp` over a checkerboard.
- Confirm alpha has only `0` and `255` in the subject frame.
- Verify angle mapping tests for top-left and top-right do not pass through front frames.
- Refresh the browser and check console errors.
- Move/test mouse at center, top, right, down, left, left-up, left-down, and top seam.

## Common Mistakes

| Mistake | Fix |
|---|---|
| Linear angle-to-frame mapping | Build `ANGLE_KEYS` from contact sheet labels |
| Global green/gray/white deletion | Flood-fill only edge-connected background |
| Interpolating repaired interior pixels | Preserve source RGB and only repair alpha |
| Single-row large WebP sprite | Use a multi-row atlas |
| Cross-fade transparent frames | Use integer-frame stepping |
| Large circular reset zone | Use a small subject-center ellipse |
| Top seam passes through frame `0..4` | Add a top seam guard |
