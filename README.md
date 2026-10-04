# ExchangePrep

面向 HKU 本科生的海外学习申请规划项目，属于 COMP1110 小组项目。目标是把分散在院校、HKU 和政府网页中的信息，整理成包含办理入口、截止规则、材料和来源的行动指引，再交给时间线与软件整合模块。

**本仓库目前交付的是联网信息收集模块及其网页 Demo。** 已支持暑校、寒校、学期交换；推荐评分、完整可行性判断、依赖图调度和最终软件尚未实现。早期讨论中的 Pathloom 是旧名称，当前使用 ExchangePrep。

本说明按截至 **2026-10-04** 的代码及项目讨论整理。接手时先运行离线示例，再按下方 JSON 合同对接；原来的详细使用说明保留为 [DEMO_GUIDE.md](DEMO_GUIDE.md)。

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
  → 后续时间线模块 → 最终软件（待对接）
```

当前已有功能：

- 支持 OpenAI 或 DeepSeek 提取；搜索可使用 OpenAI、Brave、本机浏览器或指定官网的定向模式。
- DeepSeek + 本机浏览器会先检索小红书公开索引中的 HKU 学生经验，再寻找官方要求。社媒摘要只作发现线索，不能单独证明本年度 DDL。
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
| [requirements.txt](requirements.txt) | Python 依赖 |
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
$env:EXCHANGEPREP_SEARCH_PROVIDER = 'browser'
$secureKey = Read-Host '请输入 DeepSeek API Key' -AsSecureString
$env:DEEPSEEK_API_KEY = [System.Net.NetworkCredential]::new('', $secureKey).Password
Remove-Variable secureKey
.\.venv\Scripts\python.exe -m uvicorn app:app --host 127.0.0.1 --port 8000
```

需要本机 Edge／Chrome；没有时安装 Playwright Chromium：

```powershell
.\.venv\Scripts\python.exe -m playwright install chromium
```

网页选择 DeepSeek，输入条件并发起调查。首次可先填具体项目官网，确认读取和提取可用，再留空测试自动发现。完整调查可能需要数分钟；模型请求会按服务账户计费。更改密钥或配置后须重启服务。

其他模型、搜索配置见 [详细指南](DEMO_GUIDE.md)。自动搜索顺序为 Brave Key → OpenAI Key → DeepSeek 浏览器模式；若只想使用 DeepSeek，请显式设置 `browser`。当前代码默认模型为 `deepseek-flash`／`gpt-5-mini`，可用 `DEEPSEEK_MODEL`／`OPENAI_MODEL` 覆盖；实际可用性取决于提供商账户。旧 `PATHLOOM_*` 变量兼容，但 `EXCHANGEPREP_*` 优先。

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

## 5. 时间线板块如何接手

先用离线 JSON 跑通任务展示和解析，再接实时接口：

1. 用 `(programme.id, step.id)` 区分任务；`prerequisites` 是同一项目内的步骤 ID，不能跨项目直接合并。
2. 检查每项 `deadline.state`，仅对可用的已核实规则自动处理。`fixed` 还须有合法 `date`；未知时区不可擅自补成某天 23:59。
3. `kind` 为 `fixed | window | rolling | relative | unknown | none`。`window` 目前没有独立起止字段，`relative` 提供 `trigger`／`raw` 文本而无统一事件偏移量，不能全部当作固定日期。`none` 表示无固定截止，不表示任务不需要做。
4. 补充依赖图的环路检查、拓扑排序和条件分支判断。当前仅清理不存在的前置 ID，尚未证明整个流程是正确 DAG。
5. 判断 `applies_if` 的个人适用性，再结合办理耗时和缓冲倒推时间。当前 `Programme.dates`、`budget` 等主要是文字，尚无完整结构化项目起止时间、币种、任务耗时或排期字段；需要扩展时先共同约定 Schema。
6. 保留 `evidence`、`notes`、来源和待确认项，使用户可以查看为什么这样安排。待核实参考日期不会被自动补成 `deadline.date`。

必须区分三条申请路径：普通寒暑校 SAO（外校申请后 HKU 登记）、SAP／Specialty（先 HKU 提名）、HKUWW／学院学期交换（校内选拔、提名、外校申请）。具体分支依据来源和条件确认，不能强制套同一条流程。

本模块不计算“建议最晚开始时间”、关键路径、冲突日程、推荐分数或处理时间风险；这些是下一板块的工作。

## 6. 整合与评估板块如何接手

| 板块 | 当前可复用内容 | 接下来负责 |
| --- | --- | --- |
| 联网收集与提取 | 搜索／读取／核验流水线、知识库、JSON 输出 | 改进覆盖和证据质量，维护公开资料 |
| 推荐与时间线 | `ResearchResult`、申请任务与前置线索 | 资格／时间／预算可行性、依赖图、排期、风险与排序 |
| 软件整合与 UI | FastAPI 接口和网页 Demo | 接入规划结果、等待与失败反馈、完整用户流程和可用性测试 |
| 验证集与实验 | `sources`、`search_log`、字段状态及现有回归测试 | 建立小规模人工核验案例，测准确率／召回率、来源有效率、过期信息误用及冲突识别 |
| 需求／报告 | 当前功能边界与可追溯数据 | 研究问题、需求验证、对照实验、课程报告和展示；由团队共同协调 |

以上按此前讨论的接口关系整理，不指定成员姓名或新增分工。运行时仍以实时搜索为主；验证集用于评估，不需要先手工建立全球项目数据库。

整合时注意：`/api/research` 是耗时同步调用，当前无任务队列、进度 API、取消、历史存储、账户系统或提醒功能。前端需要给调查留足等待时间；作为模块接入已有服务时，确认调用方式及超时策略。现有服务是本地 Demo，公开 GitHub 仓库不等于已部署网站。

语言选择只影响界面和新请求；已有结果不会随切换自动翻译。英文调查可能追加一次翻译模型调用，原始证据、URL、数字和机器状态保持原样，翻译校验失败则保留原文并提示。

## 7. 已知限制与验证方式

- 当前调查上限为 1–3 个项目、最多 28 个成功读取的在线页面；搜索动作和补搜有上限，不能保证所有项目／步骤齐全。
- 只读取公开内容，不使用用户登录态。需要登录时提供网址；验证码、403、未索引社媒、动态网页等可能导致缺项。
- 搜索结果和历史目录是线索，不是当前事实；公开网页、模型输出和依赖版本会变化。PDF 是一次结果快照。
- 当前冲突检查只覆盖部分同类步骤的不同日期；引文匹配也不能证明模型解释正确。不能声称已完成全面语义交叉核验或人工验证集评估。
- 已有测试主要是规则、模拟模型／HTTP，以及本地浏览器显示检查；测试通过不代表真实模型与联网搜索端到端成功。

运行现有测试：

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

首次验证建议：确认 `/api/config` 的 `knowledge_base_available` 为 `true`；检查 `/api/sample` 可解析、知识库查询有结果；配置个人 Key 后运行一次实时调查，回读 `provider`、`sources[].read_status`、关键字段证据及导出 JSON。没有搜到或未能核实也应保留原因，不把空结果解释为“项目不存在”。

**发布前验证（2026-10-04）：48 项现有测试通过，知识库和离线接口已检查；本次未调用真实付费模型。** 后续修改应按影响范围复测，实时端到端表现需另行评估。
