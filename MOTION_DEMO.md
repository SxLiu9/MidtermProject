# PT camera 的“运动”怎么仿真？

## 原来的 GIF

`outputs/pan_scan.gif` 由 `simulate.py` 生成：`np.linspace(-40, 40, 41)` 给出41个pan角，每帧固定高度8m、tilt140度、四个静态目标和同一个障碍物，仅改变pan。每帧重新做旋转、投影、FOV、LOS，再绘制俯视图与图像平面；以10fps输出GIF。播放时循环是GIF的重复，不代表物理系统瞬间从+40度返回-40度。

它是离散姿态扫描，不是电机动力学，也不是目标运动仿真。可见数量是当前场景和几何模型的计算输出，尚无独立真实传感器数据。

## 新增三维运动演示

运行：

```sh
python motion_demo.py
```

需要已有Python依赖和系统FFmpeg（导出MP4）。现成文件无需安装任何依赖即可播放：

- [MP4](outputs/motion/pt_motion.mp4)
- [GIF](outputs/motion/pt_motion.gif)
- [预览](outputs/motion/preview.png)
- 解压工程后打开 `outputs/motion/index.html`，可以暂停/拖动MP4时间轴。
- [逐帧CSV](outputs/motion/measurements.csv)

左侧显示三维相机本体（橙色示意外壳）、视锥和地面footprint（蓝色）、遮挡物（灰色）以及两个运动目标。相机光心固定，外壳朝向和光轴随pan/tilt变化。目标轨迹独立于相机运动，无反馈追踪。右上显示有效测量，右下显示相机角度和当前时刻。红色虚线表示不可观测；状态区分OCCLUDED和OUTSIDE FOV。

为避免混淆，噪声关闭。目标均位于障碍物占据区域外。世界视窗覆盖整段动画中的footprint。

## 时间模型

设T=12秒，采样频率10Hz，theta=2*pi*t/T：

```
pan(t)  = 35 sin(theta)             degrees
tilt(t) = 147 + 8 sin(theta + 0.7)  degrees
C(t)    = (0, 0, 8)                metres
X0(t)   = (-1+5 cos(theta), -8+1.5 sin(theta), 0)
X1(t)   = (3 sin(theta+1.3), -11+2 cos(theta+1.3), 0)
```

每帧先更新相机与目标状态，然后由`camera.py`计算q=R^T(X-C)、图像投影、FOV和LOS。图像点和可见状态是模型输出，不是手工绘制轨迹。运行生成120帧、12秒MP4/GIF，及240行逐目标测量。

这是**给定轨迹的运动学仿真**：有时间、连续变化的位置/姿态和每帧测量。它不包含电机电压、惯量、摩擦或反馈控制。运动学可视化仍依赖数学模型；增加三维图形不会自动提供独立验证。

## 怎样验证？

- 已知几何/特殊姿态用解析结果检验投影；
- 噪声用统计预测检验；
- 若要验证真实相机精度，应采集独立真实图像并比较标记的预测/实测像素；
- 这段演示主要用于理解动态过程，同时改变相机和目标，因此不能替代分别控制变量的height/tilt/target实验。

`report/main_corrected.pdf` 是此前实验状态的报告快照，尚未纳入本次动态演示。后续正式报告需加入新方法与结果后重新编译。
