"""webSearch 原型的 FastAPI Web 界面与 JSON API。"""

from __future__ import annotations

from html import escape
from typing import Any

from fastapi import FastAPI, Query
from fastapi.responses import HTMLResponse, Response

from orchestrator import Orchestrator
from services.snapshot import snapshot_state


app = FastAPI(title="webSearch", version="0.1.0")


def _run_query(user_query: str) -> dict[str, Any]:
	orchestrator = Orchestrator()
	state = orchestrator.run(user_query)
	return snapshot_state(state)


def _render_counts(state: dict[str, Any]) -> str:
	return f"""
<div class="metrics">
    <div class="metric"><span>轮次</span><strong>{state.get('_round', 0)}</strong></div>
    <div class="metric"><span>任务</span><strong>{len(state.get('tasks', []))}</strong></div>
    <div class="metric"><span>摘要</span><strong>{len(state.get('summaries', []))}</strong></div>
    <div class="metric"><span>已核验</span><strong>{len(state.get('verified_results', []))}</strong></div>
</div>
"""


def _render_reflection(state: dict[str, Any]) -> str:
	reflection = state.get("reflection", {})
	if not isinstance(reflection, dict):
		reflection = {"gap": str(reflection), "next_action": "", "failed_urls": []}
	failed_urls = reflection.get("failed_urls", [])
	failed_urls_text = ", ".join(failed_urls) if isinstance(failed_urls, list) and failed_urls else "None"
	return f"""
<section class="panel">
    <h2>反思</h2>
    <ul>
        <li><strong>缺口：</strong>{reflection.get('gap', '无')}</li>
        <li><strong>下一步：</strong>{reflection.get('next_action', '整理最终报告。')}</li>
        <li><strong>是否继续：</strong>{reflection.get('should_continue', False)}</li>
        <li><strong>失败链接：</strong>{failed_urls_text}</li>
    </ul>
</section>
"""


def _render_report(state: dict[str, Any]) -> str:
	report = state.get("final_report", "")
	return f"""
<section class="panel">
    <h2>最终报告</h2>
    <pre>{escape(str(report))}</pre>
</section>
"""


def render_page(query: str = "", body_html: str = "") -> str:
	return f"""
<!doctype html>
<html lang="en">
<head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title>webSearch</title>
    <style>
        :root {{ color-scheme: dark; }}
        body {{ margin: 0; font-family: Arial, sans-serif; background: #0f172a; color: #e2e8f0; }}
        .wrap {{ max-width: 960px; margin: 0 auto; padding: 48px 20px; }}
        .card {{ background: rgba(15, 23, 42, 0.85); border: 1px solid #334155; border-radius: 18px; padding: 24px; box-shadow: 0 24px 80px rgba(0,0,0,.35); }}
        h1 {{ margin: 0 0 8px; font-size: 2.2rem; }}
        p.sub {{ margin: 0 0 24px; color: #94a3b8; }}
        form {{ display: grid; gap: 12px; }}
        input[type=text] {{ width: 100%; padding: 14px 16px; border-radius: 12px; border: 1px solid #475569; background: #020617; color: #e2e8f0; font-size: 1rem; }}
        button {{ width: fit-content; padding: 12px 18px; border: 0; border-radius: 999px; background: linear-gradient(135deg, #38bdf8, #818cf8); color: #fff; font-weight: 700; cursor: pointer; }}
        pre {{ white-space: pre-wrap; word-break: break-word; background: #020617; border: 1px solid #334155; border-radius: 14px; padding: 18px; margin-top: 20px; overflow-x: auto; }}
        .hint {{ color: #94a3b8; font-size: .92rem; margin-top: 10px; }}
        .metrics {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(120px, 1fr)); gap: 12px; margin-top: 22px; }}
        .metric {{ border: 1px solid #334155; border-radius: 14px; padding: 14px; background: #020617; }}
        .metric span {{ display: block; color: #94a3b8; font-size: .84rem; margin-bottom: 8px; }}
        .metric strong {{ font-size: 1.4rem; }}
        .panel {{ margin-top: 22px; border: 1px solid #334155; border-radius: 14px; background: #020617; padding: 18px; }}
        .panel h2 {{ margin: 0 0 12px; font-size: 1.05rem; }}
        .panel ul {{ margin: 0; padding-left: 20px; color: #cbd5e1; }}
    </style>
</head>
<body>
    <div class="wrap">
        <div class="card">
            <h1>webSearch</h1>
            <p class="sub">多智能体研究检索界面</p>
            <form method="get" action="/search">
                <input type="text" name="query" value="{query}" placeholder="请输入研究问题" autocomplete="off" />
                <button type="submit">开始检索</button>
            </form>
            <div class="hint">该页面会运行当前多智能体流程，并展示最终报告。</div>
            {body_html}
        </div>
    </div>
</body>
</html>
"""


@app.get("/", response_class=HTMLResponse)
def home() -> HTMLResponse:
	return HTMLResponse(render_page())


@app.get("/search", response_class=HTMLResponse)
def search(query: str = Query(..., min_length=1)) -> HTMLResponse:
    state = _run_query(query)

    body_html = (
        _render_counts(state)
        + _render_reflection(state)
        + _render_report(state)
    )
    return HTMLResponse(render_page(query=query, body_html=body_html))


@app.get("/api/search")
def api_search(query: str = Query(..., min_length=1)) -> dict[str, Any]:
	state = _run_query(query)
	return {
		"query": query,
		"rounds": state.get("_round", 0),
		"tasks": state.get("tasks", []),
		"search_results": state.get("search_results", []),
		"documents": state.get("documents", []),
		"summaries": state.get("summaries", []),
		"verified_results": state.get("verified_results", []),
		"reflection": state.get("reflection", {}),
		"final_report": state.get("final_report", ""),
	}


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/favicon.ico", include_in_schema=False)
def favicon() -> Response:
    return Response(status_code=204)


def handle_http_query(user_query: str) -> dict:
	return _run_query(user_query)


def build_http_app() -> FastAPI:
    return app
