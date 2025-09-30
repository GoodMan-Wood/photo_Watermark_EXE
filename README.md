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

说明
- `app.py`：程序入口，创建 Qt 主窗口
- `src/ui/main_window.py`：包含基本 UI 布局（缩略图列表、预览、控制面板）
- `src/core/image_processor.py`：图像合成函数占位
- `src/io`：文件管理与缩略图生成占位
- `development_plan.md` 与 `architecture.md`：项目计划与架构文档

