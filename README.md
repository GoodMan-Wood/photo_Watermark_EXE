Photo Watermark - Python (PySide6) Scaffold

这是一个最小脚手架，用于在 Windows 上开发 Photo Watermark 应用（基于 PySide6 + Pillow）。

快速开始
1. 创建并激活虚拟环境（Windows PowerShell 示例）：

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

2. 运行应用：

```powershell
python app.py
```

模板（Templates）
- 右侧面板新增 Template 分组：
	- 下拉框列出已有模板
	- Apply：应用选中的模板
	- Save As…：将当前水印设置保存为新模板（保存在 %APPDATA%/PhotoWatermark/templates）
	- Manage…：打开管理对话框，可对模板执行重命名/删除
- 应用会自动记住上次使用的模板，并在下次启动时自动加载。

说明
- `app.py`：程序入口，创建 Qt 主窗口
- `src/ui/main_window.py`：包含基本 UI 布局（缩略图列表、预览、控制面板）
- `src/core/image_processor.py`：图像合成函数占位
- `src/io`：文件管理与缩略图生成占位
- `development_plan.md` 与 `architecture.md`：项目计划与架构文档

