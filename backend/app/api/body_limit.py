"""Bound optional workflow bodies before JSON/multipart parsing or disk spooling."""
from starlette.responses import JSONResponse


class WorkspaceBodyLimit:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        path = scope.get("path", "")
        protected = path.startswith(("/api/v1/auth/", "/api/v1/admin/", "/api/v1/research/imports", "/api/v1/support/"))
        if scope["type"] != "http" or not protected or scope["method"] not in ("POST", "PATCH"):
            return await self.app(scope, receive, send)
        maximum = 270000 if path.startswith("/api/v1/research/imports") else 65536
        messages, size = [], 0
        while True:
            message = await receive()
            if message["type"] == "http.disconnect":
                return
            size += len(message.get("body", b""))
            if size > maximum:
                return await JSONResponse({"detail": "Request is too large."}, status_code=413)(scope, receive, send)
            messages.append(message)
            if not message.get("more_body", False):
                break
        async def replay():
            return messages.pop(0) if messages else await receive()
        await self.app(scope, replay, send)
