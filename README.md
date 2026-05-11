# Cat Follow

一个静态 HTML 小项目：从猫咪动作视频生成 `sprite.webp`，并让猫咪根据鼠标所在方向转头。

## 在线文档

项目说明/需求文档：

[飞书 Wiki 文档](https://qcnne9c7efa3.feishu.cn/wiki/L95ZwS0pWiErnuk8GYvcktMDnYf?from=from_copylink)

## 功能

- 使用视频抽帧生成 `contact_sheet_labeled.png`，用于人工校准猫咪实际朝向。
- 生成透明背景的 `sprite.webp` 和正面预览帧 `frame_front.webp`。
- 使用非线性的 `ANGLE_KEYS` 将鼠标方向映射到真实校准帧。
- 支持左上、右上、顶部等边界区域的特殊帧衔接，避免经过正脸帧导致“复位”。
- 仅在猫咪主体中间的小区域回正，鼠标在顶部或周围区域时继续按方向转头。

## 文件说明

- `index.html`：最终静态页面。
- `sprite.webp`：猫咪转头 sprite 图集。
- `frame_front.webp`：正面帧预览。
- `contact_sheet_labeled.png`：带源帧编号的 contact sheet，用于校准 `ANGLE_KEYS`。
- `build_assets.py`：从视频抽帧、抠图并生成资源的脚本。
- `tests/`：资源质量、角度映射、复位区和顶部衔接等检查脚本。

## 本地运行

在项目目录启动静态服务：

```powershell
python -m http.server 8123 --bind 127.0.0.1
```

浏览器打开：

```text
http://127.0.0.1:8123/index.html
```

## 重新生成资源

项目根目录执行：

```powershell
python .\build_assets.py
```

生成结果会覆盖：

- `sprite.webp`
- `frame_front.webp`
- `contact_sheet_labeled.png`

## 检查

可以运行以下脚本检查关键行为：

```powershell
python tests\test_angle_mapping.py
python tests\test_frame_density.py
python tests\test_mask_quality.py
python tests\test_reset_zone.py
python tests\test_top_seam_transition.py
python tests\test_transition_smoothing.py
```

## 备注

`ANGLE_KEYS` 必须基于 `contact_sheet_labeled.png` 的真实朝向校准，不应使用 `angle / 360 * frameCount` 这类线性映射。
