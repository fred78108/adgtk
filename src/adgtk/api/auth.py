"""Jupyter-style token authentication middleware."""

from __future__ import annotations

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import RedirectResponse

_SKIP_PREFIXES = ("/static", "/tasks/")
_SKIP_EXACT = {"/login", "/auth/login"}


class TokenAuthMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, token: str) -> None:
        super().__init__(app)
        self.token = token

    async def dispatch(self, request: Request, call_next):
        path = request.url.path

        if (path in _SKIP_EXACT
                or any(path.startswith(p) for p in _SKIP_PREFIXES)):
            return await call_next(request)

        # Valid session cookie — pass through
        if request.cookies.get("adgtk_token") == self.token:
            return await call_next(request)

        # Token in query string (first-time link) — set cookie and redirect
        if request.query_params.get("token") == self.token:
            clean_url = str(request.url).split("?")[0]
            response = RedirectResponse(url=clean_url, status_code=302)
            response.set_cookie(
                "adgtk_token", self.token, httponly=True, samesite="lax"
            )
            return response

        return RedirectResponse(
            url=f"/login?next={request.url.path}", status_code=302
        )
