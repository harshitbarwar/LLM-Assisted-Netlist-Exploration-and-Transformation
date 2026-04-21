from __future__ import annotations

import json
import os
import re
from typing import Any, Dict, Optional

SYSTEM_PROMPT = """
You are an EDA assistant. Parse the user's natural-language request
and return a JSON command from this list:

{"command": "READ_DESIGN",   "args": {"path": "..."}}
{"command": "WRITE_DESIGN",  "args": {"path": "..."}}
{"command": "MAX_DEPTH",     "args": {"from": "...", "to": "..."}}
{"command": "PATH_QUERY",    "args": {"from":"...","to":"...","through":"..."}}
{"command": "INSERT_GATE",   "args": {"type":"...","pattern":"...","extra_input":"..."}}
{"command": "REPLACE_GATE",  "args": {"pattern":"...","new_type":"..."}}
{"command": "REMOVE_DEAD",   "args": {}}
{"command": "OPTIMIZE_CONE", "args": {"output":"...","max_depth": N}}

Return only the JSON. No explanation.
""".strip()


def get_command(request: str, config: Dict[str, Any]) -> Dict[str, Any]:
    provider = config.get("provider", "")
    api_key = _api_key_for(provider, config)
    if api_key:
        try:
            return _parse_with_llm(request, config)
        except Exception:
            pass
    return _parse_rule_based(request)


def _api_key_for(provider: str, config: Dict[str, Any]) -> Optional[str]:
    if provider == "openai":
        return config.get("openai", {}).get("api_key") or os.getenv("OPENAI_API_KEY")
    if provider == "anthropic":
        return config.get("anthropic", {}).get("api_key") or os.getenv("ANTHROPIC_API_KEY")
    if provider == "groq":
        return (
            config.get("groq", {}).get("api_key")
            or os.getenv("GROQ_API_KEY")
            or os.getenv("API_KEY")
            or os.getenv("api_key")
        )
    return None


def _parse_with_llm(request: str, config: Dict[str, Any]) -> Dict[str, Any]:
    provider = config.get("provider")
    if provider == "openai":
        from openai import OpenAI

        client = OpenAI(api_key=_api_key_for(provider, config))
        response = client.chat.completions.create(
            model=config["openai"]["model"],
            temperature=config.get("generation", {}).get("temperature", 0.2),
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": request},
            ],
        )
        content = response.choices[0].message.content
    elif provider == "anthropic":
        import anthropic

        client = anthropic.Anthropic(api_key=_api_key_for(provider, config))
        response = client.messages.create(
            model=config["anthropic"]["model"],
            max_tokens=config.get("generation", {}).get("max_output_tokens", 4096),
            temperature=config.get("generation", {}).get("temperature", 0.2),
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": request}],
        )
        content = response.content[0].text
    elif provider == "groq":
        from groq import Groq

        client = Groq(api_key=_api_key_for(provider, config))
        response = client.chat.completions.create(
            model=config["groq"]["model"],
            temperature=config.get("generation", {}).get("temperature", 0.2),
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": request},
            ],
        )
        content = response.choices[0].message.content
    else:
        raise ValueError("Unsupported provider")

    return json.loads(content)


def _parse_rule_based(request: str) -> Dict[str, Any]:
    text = request.strip()

    match = re.search(r"testcase\s+(\w+)", text, re.IGNORECASE)
    if match:
        return {"command": "SET_CASE", "args": {"name": match.group(1)}}

    match = re.search(r"(read|load)\s+(?:design\s+)?(.+\.v)", text, re.IGNORECASE)
    if match:
        return {"command": "READ_DESIGN", "args": {"path": match.group(2).strip()}}

    match = re.search(r"write\s+(?:design\s+)?(.+\.v)", text, re.IGNORECASE)
    if match:
        return {"command": "WRITE_DESIGN", "args": {"path": match.group(1).strip()}}

    match = re.search(r"(?:what\s+is\s+)?(?:the\s+)?max\s+depth\s+from\s+(\w+)\s+to\s+(\w+)", text, re.IGNORECASE)
    if match:
        return {"command": "MAX_DEPTH", "args": {"from": match.group(1), "to": match.group(2)}}

    match = re.search(r"path\s+from\s+(\w+)\s+to\s+(\w+)\s+through\s+(\w+)", text, re.IGNORECASE)
    if match:
        return {
            "command": "PATH_QUERY",
            "args": {"from": match.group(1), "to": match.group(2), "through": match.group(3)},
        }

    match = re.search(r"insert\s+(\w+)\s+gate\s+on\s+(\w+)\s+with\s+(\w+)", text, re.IGNORECASE)
    if match:
        return {
            "command": "INSERT_GATE",
            "args": {"type": match.group(1), "pattern": match.group(2), "extra_input": match.group(3)},
        }

    match = re.search(r"replace\s+gate\s+(\w+)\s+with\s+(\w+)", text, re.IGNORECASE)
    if match:
        return {"command": "REPLACE_GATE", "args": {"pattern": match.group(1), "new_type": match.group(2)}}

    if re.search(r"remove\s+dead", text, re.IGNORECASE):
        return {"command": "REMOVE_DEAD", "args": {}}

    match = re.search(r"optimize\s+cone\s+of\s+(\w+)\s+to\s+depth\s+(\d+)", text, re.IGNORECASE)
    if match:
        return {"command": "OPTIMIZE_CONE", "args": {"output": match.group(1), "max_depth": int(match.group(2))}}

    return {"command": "UNKNOWN", "args": {"request": request}}
