# PT Camera — ECE 5240 Midterm Project

本工程模拟理想 PT 相机的图像位置、地面 FOV、LOS 遮挡和测量噪声。用独立控制变量实验验证相机位置、朝向、目标运动与环境的影响；三维动画展示综合运动。

**[最终报告 PDF](report/main.pdf)** · **[报告 TEX](report/main.tex)** · **[三维动画](results/media/pt_motion.gif)** · **[视频 MP4](results/media/pt_motion.mp4)**

**[下载完整工程](https://github.com/SxLiu9/MidtermProject/raw/refs/heads/main/downloads/PT-camera-final-project.zip)** · **[下载 Overleaf 报告包](https://github.com/SxLiu9/MidtermProject/raw/refs/heads/main/downloads/PT-camera-final-report.zip)**

下载工程解压后，双击根目录 `index.html` 查看结果与视频，无需启动服务器。

## 运行与复现

已验证环境：Python 3.12.14。Python 依赖已固定版本。MP4 导出需要系统 FFmpeg；报告编译需要 pdfLaTeX。

```sh
python -m pip install -r requirements.txt
python -m unittest discover -s tests -v
python run.py                         # 全部控制变量实验、CSV、图和报告数值
python run.py --media --report --package  # 再生成视频、PDF和最终ZIP
python scripts/verify_artifacts.py
```

从其他目录也可用 `python /path/to/MidtermProject/run.py`。当前工程没有网络服务。每次执行覆盖相同实验产物，不混入随机日期版本。`results/config_used.json` 和配置SHA-256标记本次参数；报告 `metrics.tex` 由同一运行结果生成。

## 唯一维护结构

```text
run.py                       实验、媒体、报告及打包入口
config/experiments.json       相机、场景、扫描、采样和媒体参数
ptcamera/
  model.py                   旋转、投影、FOV、LOS、噪声、投影Jacobian
  config.py                  参数加载和单位转换
  experiments.py             控制变量实验与解析比较
  media.py                   三维综合运动的MP4/GIF
  artifacts.py               报告数值、离线页面和ZIP
tests/test_camera.py         10项几何/统计测试
scripts/verify_artifacts.py  数据、图像、视频与报告完整性核验
results/
  data/                      每个实验的CSV
  figures/                   PNG和矢量PDF
  media/                     MP4、GIF、帧图、逐帧测量
  summary.json               解析对比指标
  config_used.json            当前运行配置
report/
  main.tex / main.pdf         当前最终报告
  metadata.tex               姓名和课程
  metrics.tex                自动生成的数值
downloads/                  完整工程及独立Overleaf报告包
```

旧的重复入口、早期Notebook、旧报告、旧ZIP和存在目标/障碍物重叠的图已从当前版本移除。历史版本仍可通过Git记录找回。

## 实验与证据

| 实验 | 唯一变化 | 输出和验证 |
|---|---|---|
| 高度 | 4、6、8、10、12 m | 垂直向下时面积 `abH²/f²`，投影尺度 `fx/H` |
| Pan | −60°至60° | 目标集合改变、footprint面积不变；LOS几何固定 |
| Tilt | 125°至175° | footprint面积和目标投影改变，验证图像边界交点 |
| 目标运动 | 固定相机，目标沿直线移动 | 601个时刻，解析进出FOV时间与分类比较 |
| 遮挡 | 固定相机和目标，只变障碍物高度 | 51个高度，解析临界高度2.8 m；接触边界算遮挡 |
| 噪声 | 六档sigma | 每档10000次观测，固定种子4810，对比径向RMS |
| 灵敏度 | 中心差分步长 | 三个正深度点的解析Jacobian与数值差分 |
| 综合视频 | pan、tilt、两个目标同时运动 | 120帧，仅用于直观展示，不代替控制变量实验 |

### 当前关键结果

- 高度4→12 m，面积34.56→311.04 m²；最大相对误差约2.06×10⁻¹⁶。
- Pan扫描最大相对面积变化约4.12×10⁻¹⁶。
- 目标理论进出时间0.9282/11.0718 s；0.02 s采样得到0.94/11.06 s，全部601个分类正确。
- 障碍物临界高度2.8 m；全部51个高度分类与解析式一致。
- 非零噪声条件的最大相对径向RMSE偏差约0.905%。
- Jacobian中心差分步长10⁻⁵ m时最大分量误差约1.02×10⁻¹³。

结果是选定条件下的合成模型验证，数值精度不等于真实相机测量精度。

## 坐标、参数与适用范围

距离在内部使用米，角度使用弧度；配置中角度使用度并统一转换。图像展示坐标是毫米，不是像素。`image_height_m`是图像平面尺寸，`position_m[2]`才是相机离地高度。

`R=Rz(pan)Rx(tilt)` 从相机映射到世界；世界到相机使用 `q=R.T(X-C)`。Tilt=180°垂直向下。FOV要求正深度且投影在图像范围内。地面footprint只有在四条角点射线都向下时才是有限四边形；否则返回缺失值。未实现地平线附近的有限工作区裁剪。

测量为二维图像位置；先判断FOV和LOS，再加可选高斯噪声。不可见点用NaN与状态表示。新增Jacobian是局部投影导数，不是图像速度测量，也不是不连续可见性门限的导数。

配置中的解析比较针对明确的基准几何。改变基准坐标、轨迹或障碍物后，需同步修改对应解析参考；不要只改参数后沿用旧结论。特别是当前遮挡临界值公式假定目标位于箱体Y范围后方且视线穿过箱体X范围。

## 报告与提交

报告采用Technical Report Style：11 pt、单栏、1.5行距、1英寸页边距，含摘要、引言、理论/方法、Procedure、Results、单段结论和编号IEEE风格引用。当前PDF总计9页，含标题和参考文献。

课程已确认是 **ECE 5240**；姓名尚未提供，请在 `report/metadata.tex` 填写后重新编译。最终报告、原创源码、参数和媒体均包含在下载包中。正式提交前应阅读并确认技术叙述、作者信息和引用。

此版本未实现真实照片标定、检测器、畸变、电机动力学、图像速度测量或闭环追踪。这些不是当前Project传感器仿真的强制功能；报告明确限定适用范围。
