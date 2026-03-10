# clu_client.py
import aiohttp
import asyncio
import json

class CLUClient:
    """
    Async Azure CLU client for querying a project deployment.
    """

    def __init__(self, endpoint: str, key: str, project: str, deployment: str):
        self.endpoint = endpoint.rstrip("/")
        self.key = key
        self.project = project
        self.deployment = deployment
        self.session = None

    async def _ensure_session(self):
        if self.session is None:
            self.session = aiohttp.ClientSession(headers={
                "Ocp-Apim-Subscription-Key": self.key,
                "Content-Type": "application/json"
            })

    async def query(self, text: str, top: int = 5) -> dict:
        """
        Send a text query to CLU async and get the response.
        Returns a dict with 'answers' or empty dict on failure.
        """
        await self._ensure_session()
        url = f"{self.endpoint}/language/:query-knowledgebases?projectName={self.project}&deploymentName={self.deployment}"

        payload = {
            "query": text,
            "top": top
        }

        try:
            async with self.session.post(url, json=payload) as resp:
                if resp.status != 200:
                    print(f"⚠️ CLU request failed: {resp.status}")
                    return {}
                data = await resp.json()
                return data
        except Exception as e:
            print(f"⚠️ CLUClient error: {e}")
            return {}

    async def close(self):
        if self.session:
            await self.session.close()
            self.session = None
