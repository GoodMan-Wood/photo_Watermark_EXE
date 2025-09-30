Photo Watermark（Windows 桌面版）

一个轻量、离线、易用的本地图片批量加水印工具。基于 Python、PySide6 与 Pillow 开发，支持实时预览、九宫格定位、拖拽导入、模板管理以及批量导出。

## 功能总览

- 文件导入
  - 拖拽单张图片到左侧列表，或通过“Import Files/Folder”导入
  - 支持一次性选择多张图片或导入整个文件夹（当前为非递归）
  - 左侧显示缩略图 + 文件名，点击可切换预览
- 支持格式
  - 输入：JPEG、PNG、BMP、TIFF（PNG 透明通道支持）
  - 输出：可选 JPEG 或 PNG
- 导出
  - 导出时选择输出文件夹；为防覆盖，默认禁止导出到原文件夹
  - 命名规则：Original（原名）/ Prefix（前缀）/ Suffix（后缀）
    - 仅当选择 Prefix/Suffix 时才显示对应输入框
    - 默认前缀为 `wm_`，默认后缀为 `_watermarked`
  - JPEG 质量可调（1-100）
  - 可按宽度/高度/百分比缩放导出尺寸
  - 批量导出带进度与取消；成功/部分失败有提示
- 文本水印
  - 单行文本输入
  - 字体：系统字体、字号，粗体/斜体
  - 颜色：调色板选择
  - 透明度：0-100%
  - 样式：描边（大小可调）、阴影（颜色与透明度可调）
- 布局与变换
  - 实时预览：所有调整即时反映
  - 位置：
    - 预设九宫格（四角、边中、中心）
    - 预览图上支持鼠标拖拽到任意位置
  - 旋转：-180° ~ 180°
- 模板管理
  - 保存当前所有水印设置为模板
  - 加载/管理/重命名/删除模板
  - 程序启动时自动加载上次使用的模板
- 快捷键
  - Ctrl+A：选中左侧列表全部
  - Esc：清除当前选择

## 安装与运行

环境要求（推荐）：
- Windows 10/11
- Python 3.9 及以上

1) 创建虚拟环境并安装依赖（PowerShell）

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

2) 启动应用

```powershell
python app.py
```

## 使用指南（快速上手）

1) 导入图片
- 拖拽单张图片到左侧列表，或点击底部按钮导入文件/文件夹（非递归）

2) 编辑水印
- Text：输入水印文本（单行）；旁边可选择颜色与九宫格位置
- Style：设置字体、字号、粗体/斜体、描边与阴影
- Transform：透明度与旋转
- 直接在中间预览图上拖动位置，可与九宫格定位配合使用

3) 导出
- 点击“Export Current…”导出当前预览图片
- 点击“Export All…”批量导出左侧列表中的图片（弹出进度窗口，可取消）
- 导出前选择输出文件夹；若与源文件夹相同，将被阻止以防覆盖
- 命名规则：
  - Original：保留原文件名
  - Prefix：给文件名前加前缀（默认 `wm_`）
  - Suffix：给文件名后加后缀（默认 `_watermarked`）
- 格式与质量：可选 JPEG/PNG；JPEG 可设置质量
- 尺寸：按宽度/高度/百分比缩放（保持长宽比）

4) 模板
- Template 区域：
  - Save As…：保存当前设置为模板
  - 下拉 + Apply：选择并应用模板
  - Manage…：重命名/删除模板
- 程序会自动记住并加载上一次使用的模板

## 打包为独立 EXE（可选）

你可以使用 PyInstaller 生成本地可执行文件（无需安装 Python 即可运行）。

1) 安装 PyInstaller（在虚拟环境中）
```powershell
pip install pyinstaller
```

2) 生成可执行文件（示例）
- 方式一（单文件 onefile，启动更慢、体积更大）：
```powershell
pyinstaller --noconfirm --windowed --name PhotoWatermark --onefile app.py
```
- 方式二（目录 onedir，启动更快、体积更小）：
```powershell
pyinstaller --noconfirm --windowed --name PhotoWatermark app.py
```
生成的可执行文件位于 `dist/PhotoWatermark/`（或同名 `.exe`）。

提示：
- 若使用自定义图标，添加 `--icon assets/icon.ico`
- 如遇到缺少 Qt 平台插件（如 "windows"）的问题，请先执行 `pip install -r requirements.txt` 并重新打包

也可以使用提供的脚本/工作流：
- 本地脚本（PowerShell）：`scripts/build_windows.ps1`（可加 `-OneFile`）
- GitHub Actions：`.github/workflows/windows-release.yml`（推送 tag 如 `v1.0.0` 自动出包）

## 常见问题（FAQ）

- 导出到源目录被阻止？
  - 为防止覆盖原图，应用默认禁止导出到源目录，请选择其他目录
- 缩略图不显示或加载很慢？
  - 首次会生成缓存（PNG），完成后再次打开更快
- 文字在 4K 屏上偏小或缩放异常？
  - 这是 Qt 的高 DPI 行为；如有需要可在系统缩放设置或显卡设置中调整
- 文件夹导入不包含子文件夹？
  - 当前为非递归导入，如需要递归导入可在后续版本中开启
- 是否联网/上传图片？
  - 不会。应用全程本地离线处理，不会联网或上传你的图片

## 目录结构（简要）

- `app.py`：程序入口
- `src/ui/main_window.py`：主窗口与 UI 逻辑（导入/预览/控制/导出/模板）
- `src/core/image_processor.py`：预览与导出时的水印绘制
- `src/io/`：导出、缩略图与文件管理
- `src/templates/template_manager.py`：模板的保存/加载/列出/删除
- `src/config/config_store.py`：配置存储（%APPDATA%/PhotoWatermark/config.json）
- `requirements.txt`：依赖清单

## 开发与贡献

欢迎提交 Issue 或 PR 来报告问题与提出改进建议。如果你希望扩展功能（例如：递归导入、更多导出格式、图形水印等），可以开一个讨论条目描述需求与场景。

## 许可证

本仓库当前未声明开源许可证。如需公开发布，请根据你的意图补充 LICENSE 文件（例如 MIT、Apache-2.0 等）。

