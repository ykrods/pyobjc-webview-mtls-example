"""
"""
import sys
import asyncio
import threading

from datetime import datetime
from logging import getLogger

from aiohttp import web
from pathlib import Path


logger = getLogger(__name__)


def get_resources_path():
    try:
        # NOTE: sys._MEIPASS is provided by pyinstaller
        return (Path(sys._MEIPASS).parent / 'Resources/_r/').resolve()
    except Exception:
        return Path("_resources").resolve()


async def api_now(request):
    return web.json_response({'now': datetime.now().isoformat()})


async def static_handler(request):
    STATIC_DIR = get_resources_path()
    path = request.path.replace("..", ".")  # TODO: sanitize relative path
    if path == "/":
        path = "/index.html"

    if path == "/favicon.ico":
        return web.Response(body="", status=404)

    logger.debug(path)
    return web.FileResponse(STATIC_DIR / path[1:])


async def on_startup(app):
    print("on_startup")


async def on_cleanup(app):
    print("on_cleanup")


def app():
    app = web.Application()
    app.add_routes([
        web.get('/api/now', api_now),
        web.get('/{p:\S*}', static_handler),
    ])
    app.on_startup.append(on_startup)
    app.on_cleanup.append(on_cleanup)

    return app


class AioHTTPServer:
    """Manage server thread and asyncio event loop"""

    def __init__(self):
        self._loop = None

    def start(self, host='127.0.0.1', port=18760, ctx=None):
        assert self._loop is None

        self.app = app()
        self.runner = web.AppRunner(self.app)

        self._loop = asyncio.new_event_loop()
        self._loop.run_until_complete(self.runner.setup())

        self.site = web.TCPSite(self.runner, host, port, ssl_context=ctx)
        self._loop.run_until_complete(self.site.start())

        self._thread = threading.Thread(target=self._loop.run_forever)
        self._thread.start()
        # print(f"Serving HTTP on {HOST}:{PORT}")

    def stop(self):
        self._loop.call_soon_threadsafe(self._loop.stop)
        self._thread.join()
        self._loop.run_until_complete(self.runner.cleanup())
        # XXX: How to ensure closing?
        self._loop.close()
