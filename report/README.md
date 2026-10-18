# 修正公式的报告 / Formula-corrected report

- `main_corrected.tex`：基于用户上传的 `main.tex` 修正后的源文件。
- `main_corrected.pdf`：实际编译生成的 10 页 PDF，含标题页。
- `figures/`：报告引用的三张现有实验图。
- `REAL_IMAGE_MEDIA_PLAN.md`：media 与真实照片接入的建议方案；未声称已完成真实照片实验。

## 在 Overleaf 打开

将 `PT-camera-corrected-report.zip` 中的内容上传为一个项目；将 `main_corrected.tex` 设为 Main document，选择 pdfLaTeX。保留 `figures/` 文件夹结构。正文为英语，不需要中文字体。

## 本地编译

在本目录运行两次：

```sh
pdflatex -interaction=nonstopmode -halt-on-error main_corrected.tex
pdflatex -interaction=nonstopmode -halt-on-error main_corrected.tex
```

## 修订范围与限制

统一 camera-to-world 旋转与逆变换、消除相机位置符号混用；加入正深度 FOV 和地面交点条件；将实际测量明确为二维位置、LOS gate 与高斯噪声；区分几何验证和噪声验证；修正 pan 不改变固定倾角地面 footprint 形状/面积的结论；补充解析 Jacobian、运动关系与垂直向下面积公式，并明确其专项数值验证尚未完成。加入现有参数、数值结果、引用和独立标题页。

这是修正后的报告草稿，尚非完整项目：作者仍是 `Your Name`，课程编号需核实；高度/tilt 扫描、运动目标、独立遮挡实验和真实图像验证仍未完成。解析推导不代表代码已经实现 image velocity 或控制器。未来增加结果需重新压缩至 5–10 页。
