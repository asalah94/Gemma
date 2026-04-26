# Local MedGemma via Ollama
# No Google Cloud / Vertex AI required

import requests
from cache import cache

# Ollama local API endpoints
OLLAMA_CHAT_URL = "http://localhost:11434/api/chat"

# Your installed model name (from ollama list)
MODEL_NAME = "alibayram/medgemma:4b"


def _normalize_content(content) -> str:
    """
    Normalize message content from various formats to plain string.
    Handles OpenAI-style list: [{"type": "text", "text": "..."}]
    """
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for item in content:
            if isinstance(item, dict):
                parts.append(item.get("text", ""))
            else:
                parts.append(str(item))
        return "\n".join(p for p in parts if p)
    if isinstance(content, dict):
        return content.get("text", str(content))
    return str(content)


@cache.memoize()
def medgemma_get_text_response(
    messages: list,
    temperature: float = 0.1,
    max_tokens: int = 4096,
    stream: bool = False,
    top_p: float | None = None,
    seed: int | None = None,
    model: str = MODEL_NAME
):
    """
    Sends a chat request to the local Ollama MedGemma model
    and returns the generated response text.
    """

    # Normalize messages: extract plain text from OpenAI-style content lists
    normalized_messages = [
        {
            "role": msg.get("role", "user"),
            "content": _normalize_content(msg.get("content", ""))
        }
        for msg in messages
    ]

    options = {
        "temperature": temperature,
        "num_predict": max_tokens,
    }
    if top_p is not None:
        options["top_p"] = top_p
    if seed is not None:
        options["seed"] = seed

    payload = {
        "model": model,
        "messages": normalized_messages,
        "stream": stream,
        "options": options
    }

    try:
        response = requests.post(
            OLLAMA_CHAT_URL,
            json=payload,
            stream=stream,
            timeout=300
        )

        response.raise_for_status()

        data = response.json()

        return data.get("message", {}).get("content", "")

    except requests.exceptions.JSONDecodeError:
        print(
            f"Error: Failed to decode JSON from Ollama. "
            f"Status: {response.status_code}, Response: {response.text}"
        )
        raise

    except requests.exceptions.RequestException as e:
        print(f"Ollama request failed: {e}")
        raise
