"""Real LLM provider backed by the OpenAI API.

Falls back defensively: if a call errors (bad key, rate limit, network),
callers should catch and use MockProvider instead - see factory.py's
`get_provider_with_fallback` used by the agents at call time, not just once
at startup, so a mid-demo API hiccup degrades gracefully instead of crashing.
"""

import json
from typing import Any

from openai import OpenAI

from app.agents.prompts import EXTRACTION_SYSTEM_PROMPT, RECOMMENDATION_SYSTEM_PROMPT
from app.config import settings
from app.llm.provider import LLMProvider


class OpenAIProvider(LLMProvider):
    name = "openai"

    def __init__(self) -> None:
        self._client = OpenAI(api_key=settings.openai_api_key)
        self._model = settings.openai_model

    def _chat_json(self, system_prompt: str, user_prompt: str) -> dict[str, Any]:
        resp = self._client.chat.completions.create(
            model=self._model,
            temperature=0.2,
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        )
        return json.loads(resp.choices[0].message.content)

    def extract_claims(
        self, message: str, client_id: str, client_name: str, known_predicates: list[str] | None = None
    ) -> list[dict[str, Any]]:
        known = ", ".join(known_predicates) if known_predicates else "(none yet)"
        user_prompt = (
            f"client_id: {client_id}\nclient_name: {client_name}\n"
            f"KNOWN PREDICATES for this client (reuse exactly when applicable): {known}\n"
            f"message: {message}"
        )
        data = self._chat_json(EXTRACTION_SYSTEM_PROMPT, user_prompt)
        return data.get("claims", [])

    def recommend(self, question: str, evidence_brief: str, context: dict[str, Any]) -> dict[str, Any]:
        user_prompt = (
            f"Question: {question}\n\nEvidence brief:\n{evidence_brief}\n\n"
            f"Context: {json.dumps(context)}"
        )
        return self._chat_json(RECOMMENDATION_SYSTEM_PROMPT, user_prompt)

    def summarize(self, client_name: str, active_claims: list[dict[str, Any]]) -> str:
        claims_text = "\n".join(f"- {c['predicate']}: {c['value']}" for c in active_claims) or "(none)"
        resp = self._client.chat.completions.create(
            model=self._model,
            temperature=0.3,
            messages=[
                {"role": "system", "content": "You write brief, concrete account-status summaries for AP account managers. 2-4 sentences, no fluff."},
                {"role": "user", "content": f"Client: {client_name}\nActive memory:\n{claims_text}\n\nSummarize what AP currently knows about this client."},
            ],
        )
        return resp.choices[0].message.content.strip()
