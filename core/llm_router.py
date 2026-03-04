# core/llm_router.py
# LLM fallback router: decides which tool to call or returns a chat reply
# IMPORTANT: If the API is unavailable/quota-limited, we gracefully return chat fallback.

import os
import json
from dotenv import load_dotenv
from openai import OpenAI

from core.tools import TOOL_REGISTRY

load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

SYSTEM = """You are Jarvis: concise, helpful, slightly witty.
Pick the best action:
- If a tool can do it, call the tool with correct arguments.
- Otherwise reply normally.
Only use the provided tools.
"""

# NOTE: This 'tools' format matches SDKs that expect tools[i].name at top level.
TOOLS = [
    {
        "type": "function",
        "name": "open_app",
        "description": "Open an application on Windows. Known apps: chrome, edge, vscode, notepad, calculator, spotify.",
        "parameters": {
            "type": "object",
            "properties": {"name": {"type": "string"}},
            "required": ["name"],
        },
    },
    {
        "type": "function",
        "name": "tell_time",
        "description": "Get the current local time.",
        "parameters": {"type": "object", "properties": {}},
    },
    {
        "type": "function",
        "name": "web_search",
        "description": "Open a browser and search the web for a query.",
        "parameters": {
            "type": "object",
            "properties": {"query": {"type": "string"}},
            "required": ["query"],
        },
    },
    {
        "type": "function",
        "name": "save_note",
        "description": "Save a short note.",
        "parameters": {
            "type": "object",
            "properties": {"content": {"type": "string"}},
            "required": ["content"],
        },
    },
    {
        "type": "function",
        "name": "list_notes",
        "description": "List saved notes (most recent first).",
        "parameters": {"type": "object", "properties": {}},
    },
    {
        "type": "function",
        "name": "set_timer",
        "description": "Set a countdown timer in seconds.",
        "parameters": {
            "type": "object",
            "properties": {"seconds": {"type": "integer"}},
            "required": ["seconds"],
        },
    },
]

def llm_route(text: str) -> dict:
    """
    Returns:
      - {"type":"tool","tool":callable,"args":{...}}  OR
      - {"type":"chat","reply":"..."}
    """
    try:
        response = client.responses.create(
            model="gpt-4.1-mini",
            input=[
                {"role": "system", "content": SYSTEM},
                {"role": "user", "content": text},
            ],
            tools=TOOLS,
        )
    except Exception as e:
        # Quota/billing/network/etc → don't crash routing
        return {
            "type": "chat",
            "reply": "My cloud brain is unavailable right now (API quota/billing). I can still run basic commands.",
        }

    # Tool call objects differ slightly across SDK versions; handle both patterns.
    tool_calls = []
    if hasattr(response, "output") and response.output:
        tool_calls = [item for item in response.output if getattr(item, "type", None) == "tool_call"]

    if tool_calls:
        call = tool_calls[0]
        name = getattr(call, "name", None)
        args = getattr(call, "arguments", {}) or {}

        if isinstance(args, str):
            try:
                args = json.loads(args)
            except Exception:
                args = {}

        fn = TOOL_REGISTRY.get(name)
        if not fn:
            return {"type": "chat", "reply": f"I tried to use an unknown tool: {name}."}

        return {"type": "tool", "tool": fn, "args": args}

    reply = getattr(response, "output_text", None) or "…"
    return {"type": "chat", "reply": reply}
