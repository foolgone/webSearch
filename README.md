# webSearch

webSearch 是一个小型的多智能体 research 原型，用来搜索网页、抓取页面、总结证据、核验结论，并决定是否进入下一轮研究。

整个流程拆成 6 个角色：
- Planner
- Search
- Crawl
- Summarize
- Verify
- Reflection

所有 agent 共享同一个 `ResearchState`，编排器负责执行循环、状态快照和最终报告组装。

## 功能

- 支持 CLI 模式，适合快速跑一轮研究
- 支持 FastAPI Web UI，方便在浏览器里使用
- 支持 JSON API，方便集成和调试
- 支持多轮执行，并由 Reflection 决定是否继续
- 提供共享缓存、限流、快照、日志和配置能力
- 提供运行级可观测性，包括 run_id、阶段耗时和结构化事件
- 提供固定 benchmark 入口，方便做输出结构和回归检查
- 最终报告以人类可读文本输出，不直接展示原始 JSON

## 技术基石对照

下面这张表区分了“计划中提到的基石”和“当前项目里已经真正落地的基石”。

| 技术 | 项目里是否使用 | 目前用途 | 说明 |
| --- | --- | --- | --- |
| LangGraph | 否 | 暂未接入 | 当前用的是自定义的轻量工作流图 [graph.py](graph.py)；如果后续需要更复杂编排，可以再迁移。 |
| FastAPI | 是 | Web UI、JSON API | 用于提供浏览器界面和接口，见 [interface/http_app.py](interface/http_app.py)。 |
| OpenAI API | 否 | 暂未接入 | 目前没有直接调用 OpenAI API，agent 逻辑仍是本地实现。 |
| Tavily | 否 | 暂未接入 | 当前搜索使用的是本地 `httpx` + DuckDuckGo HTML 抓取，不依赖 Tavily。 |
| Crawl4AI | 否 | 暂未接入 | 当前抓取与正文提取由 `httpx` 和 `BeautifulSoup4` 完成。 |
| Beautiful Soup | 是 | HTML 解析、正文提取 | 用于清洗和抽取网页正文，见 [tools/parse.py](tools/parse.py)。 |
| Docker | 暂未接入项目代码 | 运行环境可选项 | 目前仓库里还没有 Dockerfile 或容器部署脚本，但可以后续补充。 |

如果按“当前可运行版本”来总结，这个项目的核心基石是：Python、FastAPI、httpx、BeautifulSoup4、pytest、setuptools，以及自定义编排层。那些更偏平台化或商业化的组件，比如 LangGraph、OpenAI API、Tavily、Crawl4AI，目前还属于计划参考，不是已落地依赖。

## 环境要求

- Python 3.11 或更高版本

## 安装

建议先用你自己的环境管理器准备依赖，然后按需以可编辑模式安装项目：

```bash
python -m pip install -U pip
python -m pip install -e .
```

## 配置

如果你想覆盖默认值，可以把 `.env.example` 复制为 `.env`。

支持的环境变量：

- `WEBSEARCH_MODEL_PROVIDER`
- `WEBSEARCH_MODEL_NAME`
- `WEBSEARCH_MAX_ROUNDS`
- `WEBSEARCH_REQUEST_TIMEOUT`
- `WEBSEARCH_MAX_CONCURRENCY`
- `WEBSEARCH_USER_AGENT`
- `WEBSEARCH_POSTGRES_DSN`
- `WEBSEARCH_POSTGRES_SCHEMA`

## 使用方法

运行一次命令行搜索：

```bash
python main.py "example topic"
```

启动 Web UI：

```bash
python main.py --web --host 127.0.0.1 --port 8000
```

如果你已经安装了包入口，也可以直接运行：

```bash
websearch "example topic"
```

运行固定 benchmark：

```bash
python main.py --benchmark
```

## HTTP 接口

- `GET /` - Web UI 首页
- `GET /search?query=...` - 运行工作流并以 HTML 渲染报告
- `GET /api/search?query=...` - 以 JSON 返回工作流状态
- `GET /api/runs/{run_id}` - 查询某次运行的最新 checkpoint
- `POST /api/runs/{run_id}/resume?query=...` - 基于最新 checkpoint 恢复并继续执行
- `GET /health` - 健康检查

## 项目结构

- `agents/` - Planner、Search、Crawl、Summarize、Verify、Reflection
- `interface/` - HTTP 和 MCP 入口
- `services/` - 共享配置、日志和快照工具
- `tools/` - 搜索、抓取、解析、引用、缓存和限流工具
- `tests/` - 单元测试和集成测试

## 校验

运行测试套件：

```bash
python -m pytest -q
```

## 说明

- 外部搜索和抓取依赖网络访问以及站点行为。
- 第一版保持了较轻量的图结构实现，但控制流是明确的，并且已经有测试覆盖。
- Web UI 会主动渲染人类可读报告，而不是直接输出原始 JSON。
