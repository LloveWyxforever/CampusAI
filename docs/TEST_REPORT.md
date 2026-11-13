# CampusAI 测试报告

## DeepSeek 接入复查（2026-11-13）

确认现有代码已使用 AsyncOpenAI 调用 DeepSeek 官方地址，聊天携带历史和检索资料，开启 stream=True 并将 delta 转发前端。根目录 .env 与 .env.example 三项配置齐全；复查时真实 .env 的 Key 与模型均为空，因此资料摘录提示符合设计。后端以绝对项目路径加载 .env，进程环境变量优先；修改 .env 需 stop 后 start。

本次仅修正配置首尾空格处理及空服务地址回退，没有改动现有数据库、聊天和上传资料。设置接口只返回配置状态、地址与模型，不返回密钥；前端没有读取后端 .env；.env 已被 Git 忽略。

新增真实 OpenAI SDK + httpx MockTransport 测试，验证请求路径 /models、/chat/completions、Bearer 认证、SSE 流式解析与保存、401 错误不会退回演示、前端响应不含测试密钥。共 **8 passed**。测试使用临时数据库和临时上传目录，没有使用用户数据库。模拟 HTTP 不代表真实 DeepSeek 联网成功；尚缺真实 API Key，未执行真实付费 API 请求。

测试日期：2026-11-13（北京时间）。Windows 11、Python 3.14.7、Node.js 24.19.0、npm 11.17.0。

## 已完成并测试通过

| 项目 | 结果与证据 |
|---|---|
| 前端类型检查与构建 | `npm.cmd run build` 成功；React/TypeScript/Vite/Tailwind/Lucide 正常生成静态资源 |
| 本地前后端服务 | 实际启动 FastAPI，同端口提供 React 页面；GET `/` 和 `/api/health` 返回 200 |
| Windows 管理入口 | 实际执行 manage.ps1 start、check、stop，再次 start 成功；BAT 使用该入口；未实际通过资源管理器双击验收 |
| 安全停止 | 校验 PID、程序路径、命令行和创建时间，处理已验证的 Windows venv Python 子进程；停止后端口 8000 监听消失 |
| SQLite | 初始化、读写、完整性检查、级联删除及 FTS5 删除通过；实际重启后测试记录仍存在 |
| 访问保护 | 无效访问码 401、跨站 Origin 403，有效访问码通过 |
| 输入验证 | 无效校区、错误扩展名、超 10 MB 拒绝；路径穿越文件名不作为存储路径 |
| 四种解析 | UTF-8 Markdown、GB18030 TXT、DOCX、含文字 PDF 通过；空白 PDF 返回 OCR 提示 |
| 中文全文检索 | 指定演示口令可检索，校区隔离通过，删除资料后索引清除 |
| 历史与重新生成 | 消息追加、历史读取、重生成替换最后回答、对话删除通过 |
| 真实网络增量输出 | `scripts/smoke_test.py` 对运行中的服务接收 34 个事件，约 3.00 秒分批返回 |
| 停止保存 | 实际断开 HTTP 流，数据库最终 interrupted，部分内容保留 |
| 资料来源 | 返回并保存入库文件名、校区、来源说明和片段 |
| DeepSeek 请求契约 | 假 SDK 验证流式参数和 system/user/assistant/user 上下文；不代表真实 API 成功 |
| 未配置 API 提示 | 设置测试明确返回缺密钥，资料摘录模式明确标识未调用 AI |
| 局域网接口 | 本机访问物理网卡当前 IPv4 的 health 返回 200；监听 0.0.0.0:8000，不代表实体手机通过 |

后端命令：`backend\.venv\Scripts\python -m pytest backend/tests -q` → **5 passed**。一条 Starlette TestClient 对 httpx 的未来弃用警告，不影响本次测试。

真实 HTTP 冒烟命令：`backend\.venv\Scripts\python scripts/smoke_test.py` → 页面、健康检查、上传、检索、来源、历史、分块、断开持久化均通过。成功测试清理了自身记录；早期失败测试留下的一组演示资料和聊天可能保留在本地，均明确标记为虚构测试材料。

## 已完成但未验收

- 首页、聊天、知识库和设置四页已实现并通过构建；浏览器控制返回 `No browser is available` 且列表为空，桌面控制返回 `Computer Use native pipe is unavailable`，无法执行实际页面点击和视觉检查。
- 新建、历史、复制、删除、重生成、停止、上传、筛选前端操作已实现，对应接口通过；浏览器操作链未验收。
- Markdown、表格、列表、代码块通过 react-markdown + remark-gfm 实现，默认不执行 HTML；实际视觉排版未验收。
- 手机 767px 断点、抽屉导航、动态视口高度、底部输入框和触摸按钮已实现；Android、iPhone、平板及软键盘效果未实机测试。
- 共享访问码保护已实现，非多用户权限或公网部署方案。
- 尝试打开浏览器面板失败，最终系统打开浏览器调用被工具策略拒绝；因此不声称已看到浏览器窗口。用户可手动访问 localhost:8000。

## 需要用户配置

1. 有效 DeepSeek API Key 与额度。当前密钥为空，真实连接、模型列表、真实多轮生成和 API 错误场景未联网验证。
2. 真实模型名称：填密钥重启，在设置测试取得当前列表，再填 DEEPSEEK_MODEL 重启。未写死未经验证的模型。
3. 正式学校资料。只提供明确标为虚构的演示文件；学校政策、专业、设施等回答质量取决于上传资料，没有伪造官方知识库。
4. 实体手机和可信同一 Wi-Fi；需电脑防火墙允许私有网络访问且无客户端隔离。脚本没有修改 Windows 系统设置。

## 未实现

按任务书不开发 P2：实时搜索、官网采集、复杂 Agent、多 Agent、向量库、复杂权限、云部署、原生 App。可选 PWA 和扫描文件 OCR 未实现。

## 修复记录

- npm 全局缓存 EEXIST：使用项目独立缓存，切换镜像完成下载并保存 lockfile。
- PowerShell 向 Python 传引号失败：改为 db_check.py，复测检查成功。
- Windows venv 父子进程：增加逐个身份验证，复测停止后无端口监听。
- 手机 HTTP 下 randomUUID 兼容：提供临时消息 ID 兜底。
- 流式实测初次未观察到分批：调整资料摘录间隔并重启，实际网络分块与中断持久化通过。

最终需按 README 在电脑浏览器与实体手机运行完整流程，并配置 API 后补真实模型验收。未把上述待验收项标为通过。
