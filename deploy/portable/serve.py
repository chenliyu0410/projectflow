"""Portable demo server: one loopback process serving the built web app and the API under /api.

Replaces nginx (Docker) and the Vite dev server (isolated preview), so the package needs no Node.
"""
import argparse
import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse

HOST = '127.0.0.1'


def create(api, web_root):
    root = Path(web_root).resolve()

    # Starlette does not run a mounted app's lifespan; the index worker and attachment lock live there.
    @asynccontextmanager
    async def lifespan(application):
        async with api.router.lifespan_context(api):
            yield

    application = FastAPI(lifespan=lifespan, docs_url=None, redoc_url=None, openapi_url=None)
    application.mount('/api', api)

    @application.get('/{path:path}', include_in_schema=False)
    def web(path: str):
        # Reject before touching the filesystem: on Windows '//host/share' or 'C:' would open a network or other drive.
        parts = path.split('/')
        if path.startswith('/') or ':' in path or '\\' in path or '..' in parts:
            raise HTTPException(404)
        target = (root / path).resolve()
        if not target.is_relative_to(root):
            raise HTTPException(404)
        if target.is_file():
            return FileResponse(target)
        # Missing build files are real 404s; anything else is a client-side route.
        if path.startswith('assets/'):
            raise HTTPException(404)
        return FileResponse(root / 'index.html')

    return application


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--port', type=int, required=True)
    parser.add_argument('--web', type=Path, required=True)
    args = parser.parse_args()
    if not (args.web / 'index.html').is_file():
        parser.error('找不到網頁檔案（web/index.html）')
    import uvicorn
    from app.main import create_app
    os.environ.setdefault('PF_ACCEPTANCE_MODE', 'true')
    uvicorn.run(create(create_app(), args.web), host=HOST, port=args.port, log_level='warning')


if __name__ == '__main__':
    main()
