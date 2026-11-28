"""Owner-run proof against a configured deployment; never print tokens or claim a payment.

Set VIVA_BASE_URL, VIVA_EMAIL, VIVA_PASSWORD (researcher account). Uses the same login,
batch and WebSocket routes as the browser. Creates only an empty research import batch.
"""
import asyncio
import json
import os
import urllib.parse

import httpx
from websockets.asyncio.client import connect


async def verify():
    base = os.environ["VIVA_BASE_URL"].rstrip("/")
    origin = urllib.parse.urlsplit(base)
    if origin.scheme != "https" and origin.hostname not in ("localhost", "127.0.0.1"):
        raise RuntimeError("Use HTTPS for a deployed target")
    async with httpx.AsyncClient(base_url=base, timeout=30, headers={"Origin": base}) as client:
        response = await client.get("/research")
        response.raise_for_status()
        assert "Research &amp; Evidence" in response.text or "Research &amp;" in response.text
        response = await client.post("/api/v1/auth/login", json={"email": os.environ["VIVA_EMAIL"], "password": os.environ["VIVA_PASSWORD"]})
        response.raise_for_status()
        token = response.json()["access_token"]
        response = await client.post("/api/v1/research/imports", headers={"Authorization": "Bearer "+token})
        response.raise_for_status()
        batch = response.json()
        url = base.replace("https://", "wss://", 1).replace("http://", "ws://", 1)+f"/api/v1/research/imports/{batch['id']}/live"
        async with connect(url, origin=base, open_timeout=15) as socket:
            await socket.send(json.dumps({"token": token}))
            status = json.loads(await asyncio.wait_for(socket.recv(), timeout=15))
            assert status["type"] == "status" and status["id"] == batch["id"] and status["status"] == "ready"
        await client.post("/api/v1/auth/logout", headers={"Authorization": "Bearer "+token})
    print("PASS: research HTML, deployed login/RBAC, import creation and authenticated WebSocket upgrade/status.")


if __name__ == "__main__":
    try:
        asyncio.run(verify())
    except Exception as error:
        print("FAIL:", type(error).__name__, "(details suppressed to protect credentials)")
        raise SystemExit(1)
