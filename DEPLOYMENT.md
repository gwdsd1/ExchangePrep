# ExchangePrep 公开部署

## 架构与入口

GitHub 项目：<https://github.com/gwdsd1/ExchangePrep>

GitHub Pages 静态入口：<https://gwdsd1.github.io/ExchangePrep/>

GitHub Pages 只提供 HTML、CSS、JavaScript；Python、Playwright 搜索和时间线计算运行在 Render Web Service。网页通过 HTTPS 调用云后端，不需要访问者在本地启动 Python。每位访问者填写自己的 DeepSeek／OpenAI API Key。

Render 独立子域名入口：<https://exchangeprep-gwdsd1.onrender.com/workspace>

项目路径 `/ExchangePrep/` 不覆盖 `https://gwdsd1.github.io/` 主页。

## Render 配置

仓库包含 Dockerfile，安装 Python 依赖与 Chromium。选择公开仓库部署，runtime 使用 Docker，实例明确选择 **Free**，不添加信用卡、不升级付费实例。服务监听 `$PORT`，健康检查路径 `/health`，只运行一个 Uvicorn worker。

`EXCHANGEPREP_ALLOWED_ORIGINS=https://gwdsd1.github.io` 允许 GitHub Pages 跨域访问。允许来源必须是精确 origin，不能带项目路径。Render 自身域名通过同源检查。不要设置共享模型 API Key。

源码可从公开仓库拉取，无需授予 Render 对 GitHub 私有仓库的权限。公开 URL 部署通常不支持自动部署，代码更新后需在 Render 手动部署最新提交。

## 前端发布

在完整项目环境运行：

```powershell
.\.venv\Scripts\python.exe build_pages.py --backend-url https://exchangeprep-gwdsd1.onrender.com
```

将 `docs/` 提交到 `main`，GitHub Pages 发布来源设置为 `main /docs`。`docs/static/config.js` 仅包含公开后端 URL，不包含任何 API Key。没有后端地址时，只允许体验静态离线示例，页面会明确提示实时服务未就绪，不会假装完成搜索。

## 请求与隐私

- 网页使用 `X-API-Key` HTTPS 请求头发送个人密钥；后端仅在调查线程内存中使用，不写入环境变量、源码或文件，不在结果中回传。
- 语言设置可以保存在浏览器；密钥不放进 localStorage／sessionStorage。密钥在刷新或点击清除后从页面移除。
- `POST /api/workflow/jobs` 提交调查，返回随机、不易猜测的任务标识；`GET /api/workflow/jobs/{id}` 查询状态／结果。任务标识是结果的临时访问凭据，不应分享。
- 免费实例同时只执行一项调查；忙时返回 429，请稍后重试。最多保留 4 项结果，完成结果在内存保存最多 30 分钟；服务重启后结果消失。
- Uvicorn 关闭访问日志，避免将结果访问凭据写入日志。模型提供商仍按其隐私与计费政策处理请求。
- 前端和 API 之间使用精确 CORS 来源限制，跨站来源被拒绝。任务错误消息不包含原始模型响应、请求头或密钥。

## 免费实例的实际限制

Render 免费服务在一段时间无访问后休眠，重新访问可能需要冷启动。查询可能因搜索引擎验证码、院校 403、网络或内存限制失败；免费实例并非生产级可用性保证。访问者自行承担模型调用费用。不要将“任何人可访问”理解为无限并发或承诺所有网页可读。

参考：[GitHub Pages 限制](https://docs.github.com/en/pages/getting-started-with-github-pages/creating-a-github-pages-site)、[Render 免费实例说明](https://render.com/docs/free)。

## 验证

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -q
```

上线后检查 `/health`、中英文静态页面、离线示例、跨域预检及真实请求任务状态。英文模式应把 `language=en` 传给提取模块，并使用英文时间线说明；原始证据与源网页标题保留原语言。没有真实 Key 时只能证明接口／排期／界面衔接，不能声称已验证付费模型全流程。

## 本次发布验证

2026-11-04：Render Free Docker 服务已上线，`/health` 返回正常。GitHub Pages 项目路径已连接公开后端，CORS 预检、英文离线步骤到时间线、异步请求与密钥认证失败消息已通过云端检查。浏览器实测中英文切换、默认折叠与展开均正常。127 项测试中 125 项通过、2 项可选测试跳过。未使用真实付费 Key 完成联网调查；不能将离线演示视为真实搜索准确率验证。
