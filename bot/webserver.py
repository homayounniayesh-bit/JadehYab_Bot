"""سرور ساده HTTP برای نگه داشتن بات بیدار روی هاستهای رایگان."""

from __future__ import annotations

from aiohttp import web


async def _index(request: web.Request) -> web.Response:
    return web.Response(text="🛣️ RoadRadar bot is alive", content_type="text/plain", charset="utf-8")


async def _health(request: web.Request) -> web.Response:
    return web.json_response({"status": "ok", "bot": "RoadRadar"})


def create_app() -> web.Application:
    app = web.Application()
    app.router.add_get("/", _index)
    app.router.add_get("/health", _health)
    return app


async def start_webserver(port: int) -> web.AppRunner:
    runner = web.AppRunner(create_app())
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()
    return runner
