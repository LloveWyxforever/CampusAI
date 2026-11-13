# CampusAI 校园智能助手

[在线交互展示](https://LloveWyxforever.github.io/CampusAI/) · [GitHub 仓库](https://github.com/LloveWyxforever/CampusAI)

GitHub Pages 提供静态交互演示，明确标注未调用 AI，不接收密钥或上传资料。完整 DeepSeek 聊天和校园知识库需按下文在本地运行。推送 main 分支后 GitHub Actions 自动构建展示页；本地构建默认仍使用完整应用。

本地运行的河北农业大学校园问答应用。React + TypeScript + Vite + Tailwind CSS + Lucide；Python FastAPI + Pydantic + OpenAI SDK；SQLite FTS5 中文三元组检索。无需 Docker、云服务器或独立向量库。

## 第一次启动

1. 项目目录为 `D:\CampusAI`。已在本机安装前后端依赖。
2. 双击根目录 **start.bat**（也可使用 scripts 下同名脚本）。首次启动需要联网安装缺失依赖，随后构建页面并初始化数据库。
3. 浏览器自动打开 `http://localhost:8000`。使用启动窗口显示的 Access code 登录；也可在根目录 `.env` 查看 `CAMPUSAI_ACCESS_CODE`。访问码属于本地凭据，不要分享给无关人员。
4. 双击 **stop.bat** 停止服务；双击 **check.bat** 检查环境、数据库、服务和配置状态。

启动脚本要求 Python 3.11+ 与 Node.js 20.19+。正式本地演示使用已构建的 React 静态资源与 FastAPI 同端口运行；无需同时保留 Vite 开发服务器。开发时可分别运行 `backend\.venv\Scripts\python -m uvicorn app.main:app --app-dir backend --host 0.0.0.0 --port 8000` 与在 frontend 目录运行 `npm.cmd run dev`。

## 配置 DeepSeek（需要自己的有效密钥和账户额度）

在电脑上用记事本打开根目录 `.env`，填写：

```dotenv
DEEPSEEK_API_KEY=你的密钥
DEEPSEEK_BASE_URL=https://api.deepseek.com
DEEPSEEK_MODEL=
CAMPUSAI_ACCESS_CODE=保留启动时自动生成的值
```

保存，先 stop.bat 再 start.bat。在页面「应用设置」点击 **测试 API 连接**。程序通过 SDK 读取实际可用模型列表，不预设模型名称。把返回的一个模型名称填入 `DEEPSEEK_MODEL`，再次停止并启动，再测试一次。完整连接测试会发送极短聊天请求，可能产生少量 API 费用。

**不要将密钥发到聊天、写入前端或上传 GitHub。** 网页只显示是否配置，不读取或显示密钥。`.env` 已被 Git 忽略。应用不会在线修改密钥，也没有实时网页搜索。

未配置密钥时，仍能测试上传、检索、聊天记录和资料片段流式展示。回答会显著标注「资料摘录模式 · 未调用 AI」；这不是真实 AI 生成。无相关资料会明确无法确认。配置了密钥但网络/API 失败时显示错误，不伪装成功回答。

## 使用知识库

在「校园知识库」上传 PDF、DOCX、TXT 或 Markdown，选择分类、校区并填写来源。支持 UTF-8 与 GB18030 文本；DOCX 提取段落和表格；PDF 提取文本层，不含 OCR。单个文件限制 10 MB、PDF 300 页、解析文本 200 万字符，DOCX 解压限 30 MB。

系统切分为约 800 字片段，保留重叠，在 SQLite FTS5 中建立中文 trigram 索引；短查询使用参数化 LIKE 兜底。依据当前校区检索，通用资料同时参与。没有选择校区时可检索全部，但 AI 提示词要求在设施问题上先询问校区。资料来源以真实入库文件名和上传者来源说明展示；来源说明并非系统已经核实。

`knowledge/demo/功能演示资料.md` 是**明确标注的虚构功能测试资料**，不是河北农业大学政策或通知。项目未预置未经核实的学校地址、电话或设施信息。请自行上传有权使用的正式公开文件，比赛现场需提前检查资料时效和准确性。

## 手机与局域网

手机和电脑连接同一可信 Wi-Fi，打开启动/check 窗口显示的 `http://电脑IPv4:8000`，输入同一个访问码。系统可能列出 VPN/虚拟网卡地址，请选实际 Wi-Fi 或以太网地址。电脑、服务和网络必须持续运行，手机不能在电脑关闭后访问。

应用监听 `0.0.0.0:8000`。若手机打不开，检查电脑私有网络防火墙是否允许 Python 端口 8000；必要时由电脑使用者手动允许私有网络访问。校园网的客户端隔离也可能阻止手机访问，可使用同一手机热点连接。脚本不会自行修改防火墙或 Windows 设置。

访问码是第一版的基本共享保护，无多用户隔离、权限体系与 HTTPS。仅适合可信局域网，不要端口映射到公网。普通 HTTP 手机浏览器可能禁用剪贴板，可长按选取复制。

## 数据与维护

| 位置 | 内容 |
|---|---|
| `.env` | 后端密钥、模型、共享访问码 |
| `data/campusai.db` | 对话、资料元数据、文本和 FTS5 索引 |
| `knowledge/uploads/` | 按随机 ID 保存的上传文件 |
| `knowledge/demo/` | 可手动上传的功能演示资料 |
| `logs/server.log`、`logs/server-error.log` | 服务启动与错误日志，不记录密钥 |
| `data/service.json` | 本应用进程 PID 与创建时间 |
| `backend/.venv/`、`frontend/node_modules/` | 本机依赖 |

备份：先停止服务，再复制 data 和 knowledge，以及私下保管的 .env。不要上传未获授权的个人资料。删除文档会移除原文件和当前索引，但既有聊天已经保存的引用快照会保留；如需移除历史引用，请一并删除相关对话。普通文件删除不等于安全擦除。

所有聊天共用一个本地空间；只有持访问码的设备能查看、上传、删除。Markdown 默认不执行 HTML，来源 URL 只作为文字保存，后端不抓取任意 URL；API 地址限官方 DeepSeek HTTPS 地址；SQL 使用参数绑定；上传文件名不会作为存储路径。停止脚本只停止身份校验一致的应用进程，端口冲突时会报错，不会杀其他进程。

依赖复现：前端用 `npm.cmd ci`；后端可用 `backend\.venv\Scripts\python -m pip install -r backend/requirements.lock.txt`（锁定了本次 Windows/Python 环境版本）。日常启动仅在依赖缺失时安装，重复启动不会清空已有数据。

## 测试与比赛演示

测试：`backend\.venv\Scripts\python -m pytest backend/tests -q`；前端：进入 frontend 执行 `npm.cmd run build`。详细结果与未验证项见 [测试报告](docs/TEST_REPORT.md)。

建议演示顺序：

1. 赛前配置 DeepSeek，测试连接、额度和网络；提前上传真实学校资料。
2. 开启 CampusAI，展示首页与校区选择。
3. 上传演示 Markdown，在保定校区提问「星禾读书会的活动口令是什么？」；展示「青苗向阳」和引用，并明确说明这是虚构功能演示。
4. 配置成功后，追问「把刚才的资料整理为表格」，展示多轮、Markdown、来源与流式输出。
5. 展示停止、重新生成、复制、切换历史记录与刷新后持久保存。
6. 手机同 Wi-Fi 打开电脑地址，展示独立手机导航、知识库筛选和聊天。
7. 没有 API 或网络时只演示明确标注的资料摘录功能，不把它说成 DeepSeek 生成。

已实现 P0/P1 的页面、接口和资料能力。P2（实时搜索、官网采集、Agent、多 Agent、向量库、复杂权限、云端和原生 App）未开发。真实 DeepSeek 调用与实体手机验收需要有效 API 配置和现场设备。
