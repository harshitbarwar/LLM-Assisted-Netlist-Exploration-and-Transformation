from __future__ import annotations

import argparse
import os

from dotenv import load_dotenv

from .backend import BackendSession


def main() -> None:
    load_dotenv()
    parser = argparse.ArgumentParser()
    parser.parse_args()
    session = BackendSession(_default_config())

    for line in _iter_stdin_lines():
        request = line.strip()
        if not request:
            continue

        result = session.process_query(request)
        print(result["block"], flush=True)


def _iter_stdin_lines():
    try:
        while True:
            line = input()
            yield line
    except EOFError:
        return


if __name__ == "__main__":
    main()


def _default_config() -> dict:
    return {
        "provider": os.getenv("LLM_PROVIDER", "groq"),
        "groq": {"api_key": "", "model": os.getenv("GROQ_MODEL", "")},
        "openai": {"api_key": "", "model": os.getenv("OPENAI_MODEL", "")},
        "anthropic": {"api_key": "", "model": os.getenv("ANTHROPIC_MODEL", "")},
        "generation": {
            "temperature": float(os.getenv("LLM_TEMPERATURE", "0.2")),
            "max_output_tokens": int(os.getenv("LLM_MAX_TOKENS", "4096")),
        },
    }
