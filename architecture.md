架构与数据模型 — Photo Watermark（Python 版）

概述
本文件描述使用 Python 与 Qt（建议 PySide6）实现的水印桌面应用的架构与数据模型。目标是把 PCD 的功能与验收标准落地为可实现的模块、接口契约、线程模型和测试要点，便于后续编码与评审。

目录
- 1. 高层模块划分
- 2. 数据模型与 JSON 合约
- 3. 图像处理流水线与接口契约
- 4. 线程与并发模型（Qt 注意事项）
- 5. 缩略图与缓存策略
- 6. 错误处理、日志与回退策略
- 7. 验收标准与关键测试用例
- 8. 配置存储与版本迁移

1. 高层模块划分
- UI 层（src/ui）
  - main_window.py：主窗口，布局管理（左侧缩略图列表、中心预览、右侧参数面板）。
  - widgets.py：可复用控件（缩略图项、预览控件、颜色选择、文件选择等）。

- 核心处理层（src/core）
  - watermark.py：表示 WatermarkConfig、生成绘制指令、坐标变换工具。
  - image_processor.py：将 ImageItem 与 WatermarkConfig 合成为最终图片（提供同步与异步接口）。

- IO 与文件管理（src/io）
  - file_manager.py：导入（文件/目录/拖拽）、导出、命名规则、路径验证（禁止导出到源目录默认）。
  - thumbnailer.py：异步缩略图生成与缓存管理。

- 模板管理（src/templates）
  - template_manager.py：CRUD 模板，JSON 序列化/反序列化，版本字段。

- 应用配置与持久化（src/config）
  - config_store.py：读写 %APPDATA%/PhotoWatermark/config.json，保存上次设置与模板索引。

- 工具与公共模块（src/utils）
  - helpers.py、logging.py、image_utils.py（尺寸计算、坐标转换、文件名清洗等）。

2. 数据模型与 JSON 合约
（字段示例与类型）

- ImageItem
  - id: str (UUID)
  - path: str (absolute)
  - filename: str
  - width: int
  - height: int
  - mime: str

- WatermarkConfig (JSON schema 核心部分)
  - version: int
  - type: "text" | "image"
  - text: str
  - font: { family: str, size: int, weight: str ("normal"|"bold"), italic: bool }
  - color: str (hex 如 "#RRGGBB" 或 rgba "rgba(r,g,b,a)")
  - opacity: float (0.0 - 1.0)
  - shadow: { enabled: bool, offset: [int,int], blur: int, color: str }
  - stroke: { enabled: bool, width: int, color: str }
  - imagePath: str (本地路径，若 type=="image")
  - imageScale: float (0.0-1.0)
  - rotation: float (degrees)
  - anchor: enum(九宫格)
  - position: { x: float, y: float } (相对坐标 0.0-1.0)

- ExportConfig
  - outputFolder: str
  - filenameRule: { mode: "original"|"prefix"|"suffix", prefix: str, suffix: str }
  - format: "jpeg"|"png"
  - jpegQuality: int (0-100)
  - resize: { mode: "none"|"width"|"height"|"percent", value: int }

JSON 版本化：每个模板与配置文件应保存 `version` 字段，便于未来升级兼容处理。

3. 图像处理流水线与接口契约
目标：将高层操作（例如“对 ImageItem 应用 WatermarkConfig 并导出为 JPEG/PNG”）封装为明确、可测试的函数。

核心函数（伪签名）

def render_preview_qimage(image_path: str, watermark: WatermarkConfig, preview_size: (int,int)) -> QImage:
    """在 Qt 环境中使用 QPainter 将水印渲染到缩放后的预览图上，返回 QImage 供 UI 直接显示。"""

def compose_image_pil(image_path: str, watermark: WatermarkConfig, output_size: Optional[(int,int)] = None) -> PIL.Image:
    """使用 Pillow 在 full resolution（或按 output_size）下合成最终输出图像，返回 PIL.Image 对象以便保存。"""

def export_image(image_item: ImageItem, watermark: WatermarkConfig, export_config: ExportConfig) -> ExportResult:
    """执行文件名计算、路径检查、调用 compose_image_pil 并写磁盘；返回成功/错误信息。"""

接口要点
- 预览渲染：优先使用 QImage + QPainter，以避免在 UI 线程进行重量级 Python -> PIL 转换。若需要一致性，可通过 QImage -> bytes -> PIL.Image 转换在导出时复用参数。
- 导出渲染：使用 Pillow 完成最终合成（便于控制 JPEG 质量、PNG alpha 保持、EXIF/元数据处理）。
- 单一职责：image_processor 只关心合成，不做路径/命名决策；file_manager 负责命名与写入逻辑。

4. 线程与并发模型（Qt 注意事项）
- Qt 所有 UI 操作必须在主线程执行（包含 QPixmap/QImage 的某些操作）。
- 推荐模型：
  - 主线程：UI、用户交互、QPainter 预览更新（绘制到 QPixmap/QImage 并通过信号传回 UI）。
  - 后台线程池（concurrent.futures.ThreadPoolExecutor）：用于缩略图生成、批量导出、磁盘 IO 和重度 CPU 图像合成（但避免直接操作 Qt 对象）。
  - 使用 Qt 信号（pyqtSignal / Signal）在 worker 与 UI 之间传递结果（如缩略图路径、导出进度）。

注意事项：
- 若 worker 需要生成可在 UI 显示的 QImage，建议 worker 返回原始字节或 PIL.Image，再在主线程将其转换为 QImage/QPixmap 并显示，避免跨线程创建 Qt 资源。

5. 缩略图与缓存策略
- 缩略图尺寸：例如 256x256（保持纵横比，填充或透明背景）。
- 缓存位置：%APPDATA%/PhotoWatermark/cache/thumbnails，文件名使用 sha1(path)+尺寸。
- 缓存失效：若源文件修改时间 > 缓存时间戳则重新生成。
- 异步生成：导入时立刻在 UI 列表占位，后台任务生成缩略图并通过信号更新 UI。

6. 错误处理、日志与回退策略
- 导入失败：记录并在 UI 列表标记为错误（可展开查看错误原因）。
- 导出失败：记录单文件错误，继续处理其余文件；最终弹窗显示汇总错误并提供重试选项。必要时把失败文件移动到专用子目录并写入日志。 
- 日志：使用 Python logging，按级别输出到控制台与文件（%APPDATA%/PhotoWatermark/logs/app.log），保留最近 N 天。

7. 验收标准与关键测试用例
- 单元测试
  - image_processor.compose_image_pil：覆盖 alpha 混合、旋转、缩放与透明度参数。
  - file_manager.filename_generation：测试前缀/后缀/原名、非法字符清洗、冲突计数策略。

- 集成测试
  - 导入目录（包含混合类型）→ 应只列出支持格式。
  - 应用文本水印（半透明、右下角）→ 导出 PNG，使用像素抽样验证水印位置与 alpha。 

8. 配置存储与版本迁移
- 存储位置：Windows 使用 `%APPDATA%/PhotoWatermark/`，其中包含 `config.json`, `templates/` (模板单文件或模板索引), `cache/`, `logs/`。
- 结构示例：
  - config.json
  - templates/index.json
  - templates/<template-id>.json
  - cache/thumbnails/

- 迁移策略：当 config.json 的 `schema_version` 与当前不一致，程序应自动备份旧文件并尝试迁移或提示用户。

附录：建议的 Python 包（写入 `requirements.txt`）
- PySide6
- Pillow
- opencv-python (可选，用于特殊格式或性能加速)
- tqdm (可选，导出时进度显示脚本用途)
