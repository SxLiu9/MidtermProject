# PT Camera 完整实验工程

## 快速开始

本工程提供课程针孔相机模型、FOV、长方体遮挡与高斯测量噪声实验。

1. 解压工程，双击根目录 `index.html` 查看已生成的图片与动画，无需安装 Python。
2. 要重新运行，在工程目录执行：

```sh
python -m pip install -r requirements.txt
python -m unittest discover -s tests -v
python explain_run.py
python simulate.py
```

- `camera.py`：数学模型，包括旋转、投影、地面视场、LOS 与噪声。
- `explain_run.py`：易读入口，三个实验，输出到 `results/`，终端打印结果。
- `simulate.py`：完整演示入口，含 41 帧 GIF，输出到 `outputs/`。
- `experiments.ipynb`：嵌入输出的 Notebook；重新运行需 Jupyter 环境。
- `tests/`：四项模型验证。
- `outputs/` 与 `results/`：预先生成的图片、动画、数据。
- `requirements.txt`：运行依赖，使用 Python 3.11 或更新版本。

绘图在后台保存，不会弹出窗口。图像平面坐标单位是毫米，世界坐标单位是米。
模型未包含真实图像渲染、马达动力学、图像速度、真实相机标定。场景为合成点目标与静态障碍物。

---

# PT camera midterm simulation

Python implementation based on Silvia Ferrari's course handout *Pinhole Camera Model and Field-of-view (FOV)*. This is a new implementation, not Canvas source code. The supplied PDFs contain equations and descriptions rather than runnable PT camera code.

## Run

Use the existing checkout; no separate Git worktree is needed.

```sh
cd /workspace/MidtermProject
python -m pip install -r requirements.txt
python -m unittest discover -s tests -v
python simulate.py
```

Outputs in `outputs/`: `scene.png`, `pan_scan.gif`, `visibility.png`, `noise.png`, raw CSV tables and `summary.json`. Green ground targets are visible, red ones unavailable. Image coordinates are physical image-plane millimetres, not pixels. There is no web service to start.

## Model and conventions

World targets are on Z=0; camera default height is 8 m. All parameters are illustrative simulation assumptions, not measured calibration. Focal length 20 mm and image dimensions 36 by 24 mm. Pan is a right-handed rotation about world Z followed by tilt about the intermediate X axis. Camera-to-world rotation is R=Rz(pan)Rx(tilt), so q=R.T(X-C), followed by p=f(qx/qz,qy/qz). At tilt 180 degrees the camera looks straight down; at 140 degrees and zero pan it looks towards negative world Y.

The handout's printed rotation expressions around Eqs. (2) and (4) require careful convention reconciliation. This implementation explicitly defines the basis and inverse transform instead of copying inconsistent matrix ordering. Tests check known projections and ground-corner reprojection. FOV additionally requires positive camera depth. A corner ray not intersecting the ground in its forward direction has no finite ground footprint; it is returned as NaN, not an invented bounded polygon.

Eq. (3) projection and Eq. (8) FOV are the implemented core. Unavailable measurements follow Eq. (9), represented by NaN plus a validity mask. Occlusion is an extension using segment/axis-aligned-box intersection. Noise is an extension: independent, zero-mean Gaussian noise on both image coordinates, applied after visibility selection. The simulated radial image RMSE should be sqrt(2)*sigma. This does not imply a distance-dependent image-noise law or real-camera accuracy.

The document's image velocity/Jacobian and motor dynamics, Eqs. (6)-(7) and (10)-(12), are not implemented. The animation is a prescribed sequence of poses, not a dynamically controlled trajectory. No real images, object detector, lens distortion, or lighting simulation is included. A calibrated ground-plane assumption is essential if later recovering world coordinates from images; general monocular depth is not observable from a single image point alone.

## Experiments and interpretation

1. Analytic geometry tests: known image coordinates, points behind the camera, FOV corners.
2. Pan sweep: same targets and camera height, compare FOV membership with actual visibility after occlusion.
3. Noise sweep: 10000 measurements per condition, fixed seed 4810, compare radial RMSE with its theoretical value.
4. GIF: synchronized ground footprint and image measurements during a pan sweep.

These demonstrate synthetic model consistency, not validation against a physical camera. For the final report, add height/tilt sweeps, target motion and an analytic projection sensitivity study if required by your course level. Write your own result analysis; cite the course handout and identify all extensions and assumptions.

## Viewing results / 查看输出

The script uses Matplotlib's noninteractive Agg backend: it saves files and does not open plotting windows. This is expected in a cloud environment.

- Run `python simulate.py` from the repository root (or use the script's absolute path from any directory). Outputs always default to the `outputs` folder beside the script.
- Open `outputs/index.html` in a browser after downloading the complete outputs folder. It displays static figures and the animation without a server.
- Open `experiments.ipynb` in Jupyter or VS Code to view embedded figures. Its first code cell reruns experiments; subsequent cells display results.
- `outputs/overview.png` combines the three static result figures.
- Optional output location: `python simulate.py --output-dir /tmp/pt-camera-results`.

Green/red points mean visible/unavailable; unavailable includes both outside FOV and occluded targets. Ground coordinates are metres; image coordinates are millimetres. Noise RMSE is a two-dimensional radial error, with theoretical value sqrt(2)*sigma.


## 修正公式的报告与真实照片方案

- [修正后的 TEX](report/main_corrected.tex)
- [已编译 PDF（10 页）](report/main_corrected.pdf)
- [Media 与真实照片接入方案](report/REAL_IMAGE_MEDIA_PLAN.md)
- [Overleaf 和编译说明](report/README.md)

报告描述现有结果，并明确标注未完成的实验。真实照片接入为建议方案，尚未实现或验证。
