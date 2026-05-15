"""webSearch 原型的程序入口。"""

from __future__ import annotations

import argparse

import uvicorn

from interface.http_app import build_http_app
from orchestrator import Orchestrator


def main() -> None:
	parser = argparse.ArgumentParser(description="webSearch 原型")
	parser.add_argument("query", nargs="*", help="CLI 模式下的研究问题")
	parser.add_argument("--web", action="store_true", help="启动 FastAPI Web 界面")
	parser.add_argument("--host", default="127.0.0.1")
	parser.add_argument("--port", type=int, default=8000)
	args = parser.parse_args()

	if args.web:
		uvicorn.run(build_http_app(), host=args.host, port=args.port, reload=False)
		return

	orchestrator = Orchestrator()
	user_query = " ".join(args.query).strip() or input("请输入研究问题：").strip()
	result = orchestrator.run(user_query)
	print(result["final_report"])


if __name__ == "__main__":
	main()
