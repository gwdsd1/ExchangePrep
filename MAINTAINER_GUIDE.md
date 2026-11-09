# ExchangePrep 历史交接文档

本文保留早期开发记录、接口示例和组内交接资料。当前项目入口和操作说明见 [中文 README](README.zh.md)。

## 候选覆盖修复（2026-11-05）

- 先发现多个候选（目标为用户上限 + 2），读取候选概览并比较目的地、项目类型、目标年度、时间、专业、资格与预算，再深入整理申请材料。候选不足时允许少于目标，不把发现目标当作有效结果数量。
- 如果提取结果不足用户设置的 1–3 个项目，最多追加 **2 轮候选补搜，每轮 2 个不同查询**，优先寻找其他院校；补搜与已选项目的材料／日期缺项查询分开记录。详情核查导致项目被排除时，也可使用剩余补搜轮次。
- 已知不符合条件的项目不进入时间线；关键适用信息不足的候选单列为未确认。排除／未确认原因须附已读官方页面的有效原文引文，搜索摘要不能充当证据。相同名称／官网的项目去重；多份网页不计为多个案例。
- 新增可选 JSON 字段 `candidate_reviews`（候选名称、网址、状态、原因、证据）及 `coverage_summary`（结果不足说明）；旧数据仍可读取。网页默认显示不足说明，候选筛选详情可展开，原有访问警告继续默认折叠。
- 保留 DeepSeek、OpenAI、Brave 和旧浏览器检索；指定官网的 `manual` 模式仍只作定向调查，并说明未进行全网补搜。28 页、20 次官方 Search／40 次 Fetch 网络尝试的总上限不变，补搜共用预算，可能增加耗时及模型费用。
- 最多数量是调查目标与输出上限，不保证凑足；访问失败、未公布年度资料和搜索预算都可能造成不足。系统仍依赖模型判断语义适用性，原文引用匹配不等于完整资格审查。

## 搜索方式更新（2026-11-04）

- 网页选择 **DeepSeek**：默认使用官方 `POST /v1/tools/search` 查找网页、`POST /v1/tools/fetch` 读取正文，仍使用当前 DeepSeek 模型提取结构化要求。只需同一个个人 Key，无需升级为 V4 Pro。
- 网页选择 **OpenAI**：继续使用 OpenAI 的内置网页搜索与提取，不会把 OpenAI Key 发给 DeepSeek。
- Fetch 没有可用正文或发生可恢复错误时，使用已有公开 HTML 读取器补充；已知 PDF 沿用 PDF 读取器。登录入口只返回网址。认证／余额失败直接停止，Fetch 安全策略拒绝不以其他读取器绕过。
- 搜索摘要只作线索，只有 Fetch 或直接读取的正文进入证据校验。来源 `note` 标明实际读取方式；`provider` 标明 `search:deepseek`，搜索记录注明官方 Search API。
- 同一调查最多 20 次 Search、40 次 Fetch 网络尝试（包含重试），保留 28 页与智能体工具动作上限。只对连接／超时、408、429 和 5xx 做一次短重试。
- 旧 `browser`、`brave`、`manual` 搜索配置仍可在开发接口／运行配置中显式使用；公开网页的默认流程采用上面的提供商选择。

官方 Search／Fetch 各为 US$0.75／1,000 次成功请求，模型 Token 费用另计。失败或空搜索不按成功请求计费；价格以 [官方文档](https://api-docs.deepseek.com/guides/search/) 为准。不能保证所有网站可读或要求正确，仍需年度、适用性和来源核查。

## 整合版入口（2026-11-04）

本仓库已整合联网调查、依赖建模和时间线生成。信息收集／提取由 Wang Zhengwei 完成，时间线模块来自 Gao Huaze 的 [Kura-cybc/COMP1110](https://github.com/Kura-cybc/COMP1110)。

公开项目页：[gwdsd1.github.io/ExchangePrep](https://gwdsd1.github.io/ExchangePrep/)，不覆盖 GitHub 主页。独立子域名：[exchangeprep-gwdsd1.onrender.com/workspace](https://exchangeprep-gwdsd1.onrender.com/workspace)。前端使用 GitHub Pages，Python 与 Chromium 搜索后端使用 Render。访问者输入个人 Key 即可查询；冷启动或服务忙时请稍后重试。发布状态与限制见 [DEPLOYMENT.md](DEPLOYMENT.md)。

新版前端按课程 UI 原则强化了品牌和视觉层级；顶部支持中文／英文切换，模型回答采用所选语言。长访问警告和日期核查提示默认折叠，原始证据保留。设计对应关系见 [UI_DESIGN.md](UI_DESIGN.md)。

### 本地运行

1. **双击本目录的 `start.cmd`**，保留启动窗口；服务就绪后自动打开网页。首次使用需要 Python 3.11+、联网安装依赖；本机已有 Edge／Chrome 时无需另装搜索浏览器。
2. 在网页选择 DeepSeek／OpenAI，输入自己的 API Key，再填写目的地、日期、类型和需求。
3. 确认预计出发日期、每步估算耗时与缓冲，点击“搜索并生成时间线”。不用在 PowerShell 配置环境变量，也不用手动搬运 JSON。
4. 查看每个项目的任务顺序、建议／最晚开始、官方截止、资料来源及冲突；可下载完整 JSON 或时间线 Markdown。无 Key 时点击“体验离线完整流程”。

新入口是 `/workspace`；原详细调查页 `/`、队友的案例查看器 `/planner` 和已有 API 保留。`start.cmd` 自动选择空闲本地端口，仅监听 `127.0.0.1`。关闭启动窗口或按 Ctrl+C 停止服务。线上版本发布到 gwdsd1/ExchangePrep；不修改队友的远程仓库。

Key 通过 `X-API-Key` 请求头发送给本地后端，仅用于当前调用，不写入源码、文件、环境变量、下载结果或浏览器存储。模型调用发送给所选提供商，会按账户计费。公开部署通过 HTTPS，配置精确的 Pages 来源并限制并发，详见部署说明。

公开网页使用 `POST /api/workflow/jobs` 和轮询接口，避免长请求中断；保留同步开发接口 `POST /api/workflow`，接收 `WorkflowRequest`（`workflow.py`），完成实时调查与逐项目排期；`POST /api/workflow/sample` 使用固定离线 SAO 示例验证衔接，不模拟真实联网成功。每个项目单独建图，避免跨项目步骤 ID 重复。真实搜索找不到项目时保留空结果，不替换成示例。

排期的出发日期由用户填写；每步 7 天、额外缓冲 3 天是网页可修改的统一估算，并非官方耗时。只有已核实固定 DDL 才作为官方日期；往年、待核实、滚动和窗口规则保留核查提示。建议开始采用依赖约束下的最早可开始日期；最新开始窗口和 AHP 分数沿用队友模块。未知规则、条件分支和耗时仍需人工确认，生成时间线不代表完成了全面可行性认证。

验证命令：`.\.venv\Scripts\python.exe -m unittest discover -s tests -q`。本次使用模拟模型响应与离线资料验证两模块衔接、并发密钥隔离、历史日期处理和网页交互；真实付费模型调用需要个人 Key。

下面保留原项目的模块说明与命令行用法，适用于进一步开发。

面向 HKU 本科生的海外学习申请规划项目，属于 COMP1110 小组项目。目标是把分散在院校、HKU 和政府网页中的信息，整理成包含办理入口、截止规则、材料和来源的行动指引，再交给时间线与软件整合模块。

**本仓库目前交付的信息收集／提取模块、依赖建模与时间线生成模块及其网页 Demo。** 已支持暑校、寒校、学期交换；推荐评分与完整可行性判断中的排序部分由 AHP 提供，最终软件界面仍待整合。早期讨论中的 Pathloom 是旧名称，当前使用 ExchangePrep。

依赖建模部分（`planner/`）已经把提取结果转成有序、带日期与来源的计划：依赖图与环路检查、拓扑排序、倒推最晚开始时间与浮动时间、时效窗口冲突（例如雅思成绩在出发前过期）、AHP 优先级权重、按周时间线与 Markdown 附录。详见第 7 节与 [PLANNER_GUIDE.md](PLANNER_GUIDE.md)。

本说明按截至 **2026-10-04** 的代码及项目讨论整理；规划模块部分按 2026-10 的实现整理。接手时先运行离线示例，再按下方 JSON 合同对接；原来的详细使用说明保留为 [DEMO_GUIDE.md](DEMO_GUIDE.md)。

## 0. 第一次拿到这个仓库怎么看（组员入口）

只关心**依赖建模与时间线**这部分时，最短路径是：

```powershell
git clone <仓库地址>
cd ExchangePrep
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt

# 方式一：一键跑四个案例，并把交付件写到 output\
powershell -NoProfile -ExecutionPolicy Bypass -File .\run_planner_demo.ps1

# 方式二：直接看某一份已经生成好的结果（不需要装任何依赖）
#   output\timeline_main_case.md      正式案例：时间线 + 冲突 + 来源引文（报告附录）
#   output\timeline_valid_score.md    对照组：同样的流程，成绩仍有效
#   output\timeline_cycle_example.md  反例：依赖写反了，系统拒绝排期
#   output\timeline_main_case.json    机器可读的计划（交给整合模块）

# 方式三：网页里交互查看
.\.venv\Scripts\python.exe -m uvicorn app:app --host 127.0.0.1 --port 8000
# 浏览器打开 http://127.0.0.1:8000/planner ，顶部下拉切换案例
```

不需要 API Key：时间线与可行性计算是纯离线算法。只有“联网调查”页面需要 Key（见第 4 节）。
完整的技术说明、算法公式与字段表见 [PLANNER_GUIDE.md](PLANNER_GUIDE.md)，详细操作与常见问题见 [我的部分说明.md](我的部分说明.md)。

分工与进度：**依赖建模与时间线生成**（Gao Huaze）已完成，见第 7 节；**联网信息收集与要求提取**（Wang Zhengwei）已完成，见第 1 节；验证集、整合与最终报告由其余组员负责。

## 1. 当前模块做什么

输入学生的目的地、可用时间、项目类型、专业、兴趣、国籍、居住地等条件，输出 `ResearchResult` JSON：

```text
学生条件
  → 检索本地 HKU 知识库，取得相关段落和公开链接
  → 搜索项目线索、院校网页及 HKU／政府资料
  → 读取 HTML／PDF 正文和详情链接
  → 大模型提取项目、申请步骤及原文证据
  → 程序检查证据、来源、日期、缺失字段和部分冲突
  → 按项目补搜缺项，补充带来源的待核实参考内容
  → 网页展示／下载 JSON
  → 依赖建模与时间线生成（planner/：依赖图 → 倒推排期 → AHP 排序 → 时间线）
  → 最终软件（界面接入待对接）
```

依赖建模与时间线生成的输入输出：

```text
任务集（含前置／截止／材料／证据）+ 锚点日期 + 学生档案 + AHP 判断
  → 依赖图与环路检查 → 拓扑排序 → 正推／倒推 → 浮动时间与关键路径
  → 时效窗口校验（如成绩在出发前过期）→ 冲突与待核实项
  → 优先级排序与推荐开始日 → 按周时间线（JSON + Markdown 附录）
```

当前已有功能：

- 支持 OpenAI 或 DeepSeek 提取；搜索默认使用 DeepSeek 官方 Search／Fetch，也可使用 OpenAI、Brave、本机浏览器或指定官网的定向模式。
- DeepSeek 默认通过官方 Search API 检索小红书公开索引中的 HKU 学生经验，再寻找官方要求。社媒摘要只作发现线索，不能单独证明本年度 DDL。
- 读取公开网页、PDF，以及部分网页预加载数据中的正文；记录访问失败或需要登录的入口。
- 按操作、入口、截止规则、材料分别保留状态和证据；缺少确认时给出参考内容与核查事项。
- 本地 Markdown 知识库覆盖 HKUWW、寒暑校登记／提名、材料、学分、资助、LoA、保险及十国签证线索。修改后下次查询即生效。
- 中英文界面及模型输出语言选择；可下载 `exchangeprep_research_result.json`，查看来源、搜索记录和知识库匹配。

知识库整理了 16 篇相关公众号文章及官方补充资料；它是资料摘要，未穷尽公众号历史文章或全部外链。具体申请年度和适用条件以各条目为准。

## 2. 文件导览

仓库根目录直接放置原 `ExchangePrep_webinformationcollection` 中的项目文件，克隆后在根目录运行即可。

| 文件 | 用途／接手入口 |
| --- | --- |
| [app.py](app.py) | FastAPI 服务、网页和 HTTP 接口；整合组员先看这里 |
| [models.py](models.py) | Pydantic 输入／输出合同；时间线、前端和验证集共同依据 |
| [research.py](research.py) | 搜索编排、网页读取、模型提取、核验、缺项补搜和翻译；主入口 `research()` |
| [browser_search.py](browser_search.py) | Playwright 启动独立 Edge／Chrome／Chromium，读取 Bing／Google 公开搜索结果 |
| [knowledge_base.py](knowledge_base.py) | 按词项和章节检索知识库、筛选相关国家及链接，不依赖向量数据库 |
| [hku_knowledge_base_template.md](hku_knowledge_base_template.md) | 已填充的知识库；第 7 节集中列出仍需人工补齐的信息 |
| [static/index.html](static/index.html) | 单文件网页 Demo、语言切换、来源显示及 JSON 下载 |
| [sample.json](sample.json) | 离线 SAO 流程示例；不是具体暑校，也不是本次联网调查或评估标准答案 |
| [tests/](tests/) | 现有接口、核验、知识库、补缺内容、语言和浏览器显示测试 |
| [requirements.txt](requirements.txt) | Python 依赖（规划核心只用标准库 + pydantic，无需新增） |
| [planner/](planner/) | 依赖建模与时间线生成模块：依赖图、倒推排期、AHP、白话解释层、时间线输出；接手入口见 [PLANNER_GUIDE.md](PLANNER_GUIDE.md) |
| [planner/cases/](planner/cases/) | 三个可复现案例 JSON：正式案例、可行性对照案例、环路反例（任务带中文名与一句话说明） |
| [planner/sample_anchors.json](planner/sample_anchors.json) | 给 `sample.json` 补锚点日期的示例（研究模块不含出发日期） |
| [output/](output/) | 一键脚本生成的交付件：案例计划 JSON／Markdown、研究快照计划、查看器用 JSON |
| [run_planner_demo.ps1](run_planner_demo.ps1) | 一键演示脚本：跑完四个案例、导出交付件并执行规划模块测试 |
| [static/planner.html](static/planner.html) | 时间线查看器网页（`/planner`）：只给普通学生看——每一步做什么、哪天开始、最晚哪天、有什么问题；技术内容收在折叠区 |
| [tests/test_planner.py](tests/test_planner.py) | 规划模块回归测试（71 项，其中 2 项 NetworkX 交叉验证为可选） |
| [requirements-planner-optional.txt](requirements-planner-optional.txt) | 可选的 NetworkX 交叉验证依赖 |
| [DEMO_GUIDE.md](DEMO_GUIDE.md) | 原 README，保留详细运行、搜索策略及使用限制说明 |
| [ExchangePrep · 项目申请调查 Demo.pdf](ExchangePrep%20%C2%B7%20%E9%A1%B9%E7%9B%AE%E7%94%B3%E8%AF%B7%E8%B0%83%E6%9F%A5%20Demo.pdf) | 已有网页调查结果快照；可能包含往年／待核实内容，不能代替接口或最新查询 |

发布时把原位于上级目录的知识库复制进本仓库，并将默认读取路径改为同目录，保证独立克隆后可用。今后请维护**本仓库内**的知识库；上级目录的旧副本不会自动同步。课程 PDF、proposal 和其他课程文件未纳入本仓库。

## 3. 快速运行

建议使用 Python 3.11（当前验证环境）。以下命令适用于 PowerShell：

```powershell
git clone https://github.com/gwdsd1/ExchangePrep.git
cd ExchangePrep
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

### 无密钥：先验证界面和接口

```powershell
.\.venv\Scripts\python.exe -m uvicorn app:app --host 127.0.0.1 --port 8000
```

打开 [本地 Demo](http://127.0.0.1:8000)，点击“查看离线示例”；也可查询知识库。接口定义见 [Swagger 文档](http://127.0.0.1:8000/docs)。这些操作无需模型 Key，不执行实时搜索。

### 仅有 DeepSeek Key：运行实时调查

先停止服务，在**同一个 PowerShell 窗口**设置变量，再启动：

```powershell
$env:EXCHANGEPREP_LLM_PROVIDER = 'deepseek'
$env:EXCHANGEPREP_SEARCH_PROVIDER = 'deepseek'
$secureKey = Read-Host '请输入 DeepSeek API Key' -AsSecureString
$env:DEEPSEEK_API_KEY = [System.Net.NetworkCredential]::new('', $secureKey).Password
Remove-Variable secureKey
.\.venv\Scripts\python.exe -m uvicorn app:app --host 127.0.0.1 --port 8000
```

只有显式启用旧 `browser` 搜索时需要本机 Edge／Chrome；没有时可安装 Playwright Chromium：

```powershell
.\.venv\Scripts\python.exe -m playwright install chromium
```

网页选择 DeepSeek，输入条件并发起调查。首次可先填具体项目官网，确认读取和提取可用，再留空测试自动发现。完整调查可能需要数分钟；模型请求会按服务账户计费。更改密钥或配置后须重启服务。

其他模型、搜索配置见 [详细指南](DEMO_GUIDE.md)。`auto` 在选择 DeepSeek 时使用官方 Search／Fetch；其他模型保留 Brave → OpenAI 搜索。旧浏览器模式可显式设置 `browser`。当前代码默认模型为 `deepseek-flash`／`gpt-5-mini`，可用 `DEEPSEEK_MODEL`／`OPENAI_MODEL` 覆盖；实际可用性取决于提供商账户。旧 `PATHLOOM_*` 变量兼容，但 `EXCHANGEPREP_*` 优先。

密钥只在个人运行环境配置，不放进源码、README、截图或导出文件。程序没有自动加载 `.env` 的逻辑。

## 4. 接口与数据合同

HTTP 与 Python 入口使用同一组 [models.py](models.py) 模型；当前 `schema_version` 为 `"1.0"`。不要依据早期聊天中的示意 JSON 写解析器。

| 接口 | 行为 |
| --- | --- |
| `GET /` | Demo 页面 |
| `GET /api/config` | 模型／搜索设置与 Key 是否存在、知识库是否可用；不返回 Key |
| `GET /api/sample` | 返回离线示例 `ResearchResult` |
| `GET /api/knowledge-base?query=成绩单` | 查询知识段落；无需 Key |
| `GET /api/knowledge-base/document` | 返回完整知识库 Markdown |
| `POST /api/research?provider=deepseek` | 接收 `ResearchRequest`，同步返回 `ResearchResult` |

请求示例（目标条件示意，不保证该年度存在符合要求的项目）：

```json
{
  "language": "zh",
  "destination": "United Kingdom",
  "start_date": "2027-06-01",
  "end_date": "2027-08-31",
  "programme_type": "summer_school",
  "major": "Computer Science",
  "year_of_study": 2,
  "interests": "AI",
  "nationality": "",
  "residence": "Hong Kong",
  "budget": "",
  "programme_url": null,
  "max_programmes": 1
}
```

必填：`destination`、`start_date`、`end_date`、`programme_type`。类型为 `summer_school | winter_school | exchange`；结束日期不能早于开始日期。`language` 默认为 `zh`，可设 `en`；项目数为 1–3。国籍等条件缺失时，相应签证适用性仍需确认。

直接给时间线模块调用（同步 Python 入口）：

```python
from datetime import date
from models import ResearchRequest
from research import research

request = ResearchRequest(
    destination="United Kingdom",
    start_date=date(2027, 6, 1),
    end_date=date(2027, 8, 31),
    programme_type="summer_school",
    max_programmes=1,
)
result = research(request, provider="deepseek")
payload = result.model_dump(mode="json")  # 日期／时间也转成 JSON 兼容值
```

离线对接可直接读 `sample.json` 或调用 `/api/sample`，无需调用 `research()`。正式 HTTP 请求也需配置服务端 Key；输入校验失败返回 422，配置／流程中的 `ValueError` 返回 400，其他外部请求异常返回 502。

### 输出中最重要的字段

| 路径 | 含义／用法 |
| --- | --- |
| `request`、`generated_at`、`provider` | 本次条件、生成时间、实际模型及搜索方式 |
| `programmes[]` | 项目名称、官网、项目类型、目的地、日期、资格、费用、历史案例和申请步骤 |
| `programmes[].steps[]` | 核心交接任务：`id`、`category`、`title`、`action`、`channel`、`deadline`、`documents`、`prerequisites`、`applies_if`、`notes` |
| `sources[]` | 来源 ID、URL、标题、来源类别、读取时间、`read_status` 与备注 |
| `warnings`、`programmes[].unresolved_questions` | 本次限制及需要人工确认的问题 |
| `discovery_clues`、`search_log` | 社媒／搜索线索及检索记录；不能当作已读正文 |
| `knowledge_matches` | 本次使用的知识库段落及其链接 |

`action` 和 `channel` 是 `Fact`：`value`、`state`、`evidence`；`documents[]` 各有名称、说明、状态和证据。证据通过 `source_id` 对应 `sources[].id`，`quote` 保留原文。

**`Step` 本身没有统一的 `state`。** 一个步骤可以同时有已核实的操作、待核实的入口和未知日期；接手代码必须检查实际使用的字段状态。界面将“待核实”合并为每张步骤卡片的一条备注，JSON 中仍分别保留状态。

| `state` | 后续处理约定 |
| --- | --- |
| `verified` | 有通过当前规则检查的证据；仍须考虑年度、适用条件、来源类别和时区 |
| `needs_review` | 参考内容或证据／适用性不足；展示并交给用户确认 |
| `historical` | 往年／过期资料，只作历史参考 |
| `conflicting` | 发现相互冲突的信息，等待确认 |
| `unknown` | 未找到可确定内容；不得据此生成确定日期 |

`verified` 是原型规则的结果，不代表完全验证了含义或个人资格。核验主要检查引文是否存在于读到的正文、来源类别和日期；来源识别与冲突检测仍有限。本地知识库独立支撑的事实不能自证为本次官方核验。

## 5. 时间线板块如何接手（原交接要求，已由 `planner/` 实现）

> 下面这段是研究模块当初写给时间线板块的接手要求，现作为设计依据保留。每一条的落地位置写在条目末尾，实际用法见第 7 节。

先用离线 JSON 跑通任务展示和解析，再接实时接口：

1. 用 `(programme.id, step.id)` 区分任务；`prerequisites` 是同一项目内的步骤 ID，不能跨项目直接合并。 → `PlanningTask.id` 与 `programme_id` 原样保留。
2. 检查每项 `deadline.state`，仅对可用的已核实规则自动处理。`fixed` 还须有合法 `date`；未知时区不可擅自补成某天 23:59。 → `deadline_basis` 区分 `fixed`／`relative`／`none`／`unknown`，无法解析的一律报冲突。
3. `kind` 为 `fixed | window | rolling | relative | unknown | none`。`window` 目前没有独立起止字段，`relative` 提供 `trigger`／`raw` 文本而无统一事件偏移量，不能全部当作固定日期。`none` 表示无固定截止，不表示任务不需要做。 → 只写了 trigger 没有偏移量的相对截止会报 `relative_deadline_unresolved`，不会硬凑日期。
4. 补充依赖图的环路检查、拓扑排序和条件分支判断。当前仅清理不存在的前置 ID，尚未证明整个流程是正确 DAG。 → `planner/graph.py` 用 Kahn + DFS 证明 DAG 并列举环路；不存在的 ID 报 `unknown_predecessor`。
5. 判断 `applies_if` 的个人适用性，再结合办理耗时和缓冲倒推时间。当前 `Programme.dates`、`budget` 等主要是文字，尚无完整结构化项目起止时间、币种、任务耗时或排期字段；需要扩展时先共同约定 Schema。 → 新增附加合同 `planner/schema.py`（`duration`／`buffer_days`／`validity`／锚点），未改动 `models.py`；`applies_if` 目前只展示（已列入限制）。
6. 保留 `evidence`、`notes`、来源和待确认项，使用户可以查看为什么这样安排。待核实参考日期不会被自动补成 `deadline.date`。 → 时间线每项都带 `sources[].quote`，并有 `notes`／`notes_plain` 说明推导过程。

必须区分三条申请路径：普通寒暑校 SAO（外校申请后 HKU 登记）、SAP／Specialty（先 HKU 提名）、HKUWW／学院学期交换（校内选拔、提名、外校申请）。具体分支依据来源和条件确认，不能强制套同一条流程。

**本节列出的接手工作已经由 `planner/` 模块实现**：环路检查、拓扑排序、最晚开始时间、关键路径、时效窗口冲突与排序都已落地，`prerequisites`／`applies_if`／`evidence` 会被原样保留在时间线输出中。接口与用法见第 7 节与 [PLANNER_GUIDE.md](PLANNER_GUIDE.md)。

## 7. 依赖建模与时间线生成板块（已完成）

代码在 `planner/`，只依赖 `models.py` 的只读字段，**没有修改 `models.py` 或联网收集模块**，因此不存在破坏既有测试的风险。规划输入使用独立合同 `planner/schema.py`（`plan_schema_version = "1.0"`）：研究模块不提供的排期字段（办理耗时、缓冲、时效窗口、锚点日期）由人工或规则补充，缺失时以 `missing_duration`／`unknown_deadline` 记录，而不是补造。

### 三条必须遵守的规则

1. **状态三态**：`stated`（原文写明）／`inferred`（由规则推出）／`unknown`（未找到）。只有 `stated` 的锚点日期才用于倒推；`unknown` 一律列入待核实，绝不补成具体日期。
2. **锚点代替猜测**：相对截止写作 `{"anchor": "submission_deadline", "offset_days": -30}`，请求必须提供 `departure` 锚点。锚点无日期时报 `unknown_anchor` 冲突。
3. **时效窗口不是倒推边界**：`ValidityWindow` 只用于校验“证据在那一刻是否仍然有效”。雅思 24 个月有效期不能变成“必须在某天上考场”的截止日期（越晚考越晚过期），它只把“成绩在出发／开始前过期”变成阻塞冲突并给出最晚可用的签发日期。

### 算法流程

```text
PlanRequest（任务 + 锚点 + 学生档案 + AHP 判断）
  → 解析截止：fixed / relative(anchor+offset) / none / unknown
  → 依赖图：prerequisite 与 valid_until 两类边，自环忽略、缺失前置记为 dangling
  → 环路检查（Kahn 未覆盖部分再做 DFS 列举）→ 拓扑排序（同键排序，结果可复现）
  → 正推：最早开始／最早完成（含前置与 as_of）
  → 倒推：最晚完成 = min(自身截止, 各后继最晚开始, 规划地平线)
  → 浮动时间 = 最晚开始 − 最早开始；为 0 者构成关键路径（无 0 时用最长链）
  → 可行性判定：earliest_after_deadline / dependency_impossible / validity_expires_before_departure
  → AHP 权重 × 四准则（impact/urgency/flexibility/effort）→ 优先级分数
  → 就绪任务中取优先级最高者，得到合法且带排序理由的工作顺序
  → 按周分组、逐项附来源引文与冲突说明，输出 JSON + Markdown
```

### 命令行

```powershell
# 正式案例（会报出雅思成绩在出发前过期）
.\.venv\Scripts\python.exe -m planner.cli plan --case planner\cases\hkuww_main_round_2027.json

# 可行性对照案例（成绩仍有效）与环路反例
.\.venv\Scripts\python.exe -m planner.cli plan --case planner\cases\hkuww_main_round_2027_feasible.json
.\.venv\Scripts\python.exe -m planner.cli plan --case planner\cases\cycle_example.json

# 同时导出机器可读计划与报告附录
.\.venv\Scripts\python.exe -m planner.cli plan --case planner\cases\hkuww_main_round_2027.json `
  --json out\timeline.json --markdown out\timeline.md
```

`infeasible` 时退出码为 1，可用于评估脚本判定“该案例不可行”。

### HTTP 接口

| 接口 | 行为 |
| --- | --- |
| `GET /api/planner/cases` | 列出内置案例（案例 ID、任务数、基准日期） |
| `GET /api/planner/plan/{case_id}?as_of=&format=json\|markdown` | 生成计划；`as_of` 可覆盖基准日期 |
| `POST /api/planner/plan` | 直接提交完整 `PlanRequest` 生成计划 |
| `GET /api/planner/schema` | 发布规划合同 JSON Schema，供研究与整合模块对接 |

### 两套说法：程序看的与人看的

计划 JSON 里同一件事有两套字段：`deadline_source`／`state`／`conflict.detail`／`notes` 是精确、供程序与报告使用的说法；`deadline_source_plain`／`state_plain`／`conflict.detail_plain`／`notes_plain` 以及每个任务的 `title_plain`／`action_plain` 是给普通学生看的白话说法（例如「材料会在需要用到它之前就过期……请重新考一次」）。白话层只做翻译，不软化冲突、不新增日期。因此 `/planner` 页面可以完全不出现 `task_id`、状态枚举、AHP、critical path 这些字眼，而整合模块依旧拿到完整的结构化字段。详见 [PLANNER_GUIDE.md](PLANNER_GUIDE.md) 第 10 节。

从研究模块接手的最短路径：取 `ResearchResult`、补一份锚点 JSON 与按 `step.id` 索引的补充字段 JSON，再调用 `planner.schema.adapt_research_result(...)`，随后 `planner.timeline.build_plan(...)`。示例见 `planner/cli.py` 的 `--research` 分支；已内置的锚点示例见 [planner/sample_anchors.json](planner/sample_anchors.json)。

规划核心只依赖标准库与 pydantic，`requirements.txt` 无需新增。计划书提到的图库以**可选交叉验证**方式接入：[requirements-planner-optional.txt](requirements-planner-optional.txt) 安装 NetworkX 后，`NetworkXCrossCheckTests` 会在随机 DAG 上比对拓扑序合法性与最长链长度；未安装时这两项显示为 skipped。详见 [PLANNER_GUIDE.md](PLANNER_GUIDE.md) 第 9 节。

### 在自己电脑上查看

```powershell
# 一键：跑四个案例、导出交付件到 output\、再执行规划模块测试
powershell -NoProfile -ExecutionPolicy Bypass -File .\run_planner_demo.ps1

# 或起本地网页，交互式查看时间线、冲突、依赖边与来源
.\.venv\Scripts\python.exe -m uvicorn app:app --host 127.0.0.1 --port 8000
# 浏览器打开 http://127.0.0.1:8000/planner
```

`output\` 会得到正式案例的 `timeline_main_case.json`／`.md`、对照组与环路反例的 Markdown、从 `sample.json` 生成的研究快照计划，以及可粘贴进 [static/planner.html](static/planner.html) 的 `plan_for_viewer.json`。完整说明见 [PLANNER_GUIDE.md](PLANNER_GUIDE.md) 第 2.1 节。

## 8. 整合与评估板块如何接手

| 板块 | 当前可复用内容 | 接下来负责 |
| --- | --- | --- |
| 联网收集与提取 | 搜索／读取／核验流水线、知识库、JSON 输出 | 改进覆盖和证据质量，维护公开资料 |
| 推荐与时间线 | `ResearchResult`、申请任务与前置线索；`planner/` 的依赖图、倒推排期、AHP 与时间线输出 | 资格／时间／预算可行性中的预算与资格判断，排序权重的用户可调化 |
| 软件整合与 UI | FastAPI 接口和网页 Demo | 接入规划结果、等待与失败反馈、完整用户流程和可用性测试 |
| 验证集与实验 | `sources`、`search_log`、字段状态及现有回归测试 | 建立小规模人工核验案例，测准确率／召回率、来源有效率、过期信息误用及冲突识别 |
| 需求／报告 | 当前功能边界与可追溯数据 | 研究问题、需求验证、对照实验、课程报告和展示；由团队共同协调 |

以上按此前讨论的接口关系整理，不指定成员姓名或新增分工。运行时仍以实时搜索为主；验证集用于评估，不需要先手工建立全球项目数据库。

整合时注意：`/api/research` 是耗时同步调用，当前无任务队列、进度 API、取消、历史存储、账户系统或提醒功能。前端需要给调查留足等待时间；作为模块接入已有服务时，确认调用方式及超时策略。现有服务是本地 Demo，公开 GitHub 仓库不等于已部署网站。

语言选择只影响界面和新请求；已有结果不会随切换自动翻译。英文调查可能追加一次翻译模型调用，原始证据、URL、数字和机器状态保持原样，翻译校验失败则保留原文并提示。

## 9. 已知限制与验证方式

- 当前调查上限为 1–3 个项目、最多 28 个成功读取的在线页面；搜索动作和补搜有上限，不能保证所有项目／步骤齐全。
- 只读取公开内容，不使用用户登录态。需要登录时提供网址；验证码、403、未索引社媒、动态网页等可能导致缺项。
- 搜索结果和历史目录是线索，不是当前事实；公开网页、模型输出和依赖版本会变化。PDF 是一次结果快照。
- 当前冲突检查只覆盖部分同类步骤的不同日期；引文匹配也不能证明模型解释正确。不能声称已完成全面语义交叉核验或人工验证集评估。
- 已有测试主要是规则、模拟模型／HTTP，以及本地浏览器显示检查；测试通过不代表真实模型与联网搜索端到端成功。

规划模块自身的限制（对应报告 Limitations 一节）：

- **耗时与缓冲是估计值**，`basis` 为 `inferred_convention`／`inferred_similar_case` 的任务只表示“按惯例估算”，不是官方处理时长；`max_days` 采用保守上界，因此计划偏早而不是偏晚。
- **锚点由人工确认**：`departure`、`programme_start` 等来自外校学术日历，研究模块不会返回它们，必须由使用者或规则补齐；缺失时计划只报冲突，不补日期。
- **AHP 权重来自一组显式判断**（`planner/ahp.py` 的 `DEFAULT_COMPARISONS`），换一组判断权重就会变化；一致性比率会随计划一起输出，但权重本身仍需在报告中说明理由。
- **不覆盖的条件分支**：`applies_if` 只作展示与人工判断，条件任务的取舍尚未自动化；跨项目的资源冲突（同一周两场考试）也未建模。
- **不做签证与移民判断**：签证步骤只被排序，处理时长是保守惯例值，最终必须回到政府官网核对。
- **案例规模小**：三个内置案例用于回归与展示，不等于验证集；指标（来源覆盖率、阻塞冲突数）只对当前案例成立。

运行现有测试：

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

首次验证建议：确认 `/api/config` 的 `knowledge_base_available` 为 `true`；检查 `/api/sample` 可解析、知识库查询有结果；配置个人 Key 后运行一次实时调查，回读 `provider`、`sources[].read_status`、关键字段证据及导出 JSON。没有搜到或未能核实也应保留原因，不把空结果解释为“项目不存在”。

规划模块自检建议：先跑 `GET /api/planner/cases`，再对 `hkuww-main-round-s1-2027` 生成一次计划，确认它报出 1 条阻塞冲突（雅思成绩在出发前过期）且 14 个任务都有来源引文；随后对 `hkuww-main-round-s1-2027-valid-score` 确认无阻塞冲突；最后对 `reference-letter-cycle` 确认环路被拒绝而不是被排出一个看似合理的顺序。

**发布前验证（2026-10-04）：48 项现有测试通过，知识库和离线接口已检查；本次未调用真实付费模型。** 后续修改应按影响范围复测，实时端到端表现需另行评估。

**规划模块验证（2026-10）：全套 119 项测试中 114 项通过、3 项因沙箱权限报错、2 项可选交叉验证跳过。** 其中 71 项为 `tests/test_planner.py` 的规划模块测试（69 项通过、2 项 NetworkX 交叉验证因离线未安装而 skipped）。3 项错误来自既有测试（1 项写系统临时目录，2 项启动本机浏览器子进程），在当前沙箱环境下无写临时目录／建管道权限，与规划模块无关；在普通 Windows 环境下应可正常通过。
