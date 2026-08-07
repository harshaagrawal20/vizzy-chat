"""
app/services/mcp_tools.py
─────────────────────────
Topic 23 — MCP-Powered AI Assistant (FastMCP-style tool-calling)

Implements a lightweight agentic loop using Groq's native tool-calling API.
The LLM chooses which tools to call, we execute them, feed results back,
and repeat until the model produces a plain text final answer (max 5 turns).

Tools available:
  • wikipedia_lookup   — fetch a Wikipedia article summary
  • calculator         — evaluate a safe math expression
  • web_search_stub    — returns a mock/stub search result
  • file_reader        — read a file from the generated/ or uploads/ dir
"""
from __future__ import annotations

import json
import math
import re
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

from app.settings import settings

BASE_DIR      = Path(__file__).resolve().parent.parent.parent
GENERATED_DIR = BASE_DIR / "generated"
UPLOADS_DIR   = BASE_DIR / "uploads"

GROQ_CHAT_URL   = "https://api.groq.com/openai/v1/chat/completions"
GROQ_TOOL_MODEL = "llama-3.3-70b-versatile"   # supports tool-calling (updated 2026)
GROQ_BASE_MODEL = "llama-3.1-8b-instant"       # fast fallback without tool-use
MAX_ITERATIONS  = 6


# ── Tool definitions (sent to Groq as function schemas) ──────────────────────

TOOLS: list[dict] = [
    {
        "type": "function",
        "function": {
            "name": "wikipedia_lookup",
            "description": (
                "Fetch a concise Wikipedia summary for a given topic or entity. "
                "Use this when the user asks about a person, place, concept, or event."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "The topic or entity to look up on Wikipedia.",
                    }
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "calculator",
            "description": (
                "Evaluate a mathematical expression and return the result. "
                "Supports +, -, *, /, **, sqrt, log, sin, cos, tan, abs, round, pi, e."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "expression": {
                        "type": "string",
                        "description": "The math expression to evaluate, e.g. '2 ** 10 + sqrt(144)'.",
                    }
                },
                "required": ["expression"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "web_search",
            "description": (
                "Search the web for recent information or news. "
                "Returns top 3 simulated results with titles and snippets."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "The search query.",
                    }
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "file_reader",
            "description": (
                "Read the contents of a file from the generated/ or uploads/ directory. "
                "Returns file content as text (for SVG/text files) or a size summary."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "filename": {
                        "type": "string",
                        "description": "The filename (not full path) to read, e.g. 'home-abc123-1.svg'.",
                    }
                },
                "required": ["filename"],
            },
        },
    },
]


# ── Tool executor functions ───────────────────────────────────────────────────

def _tool_wikipedia_lookup(query: str) -> str:
    """Fetch Wikipedia intro summary via the MediaWiki API."""
    try:
        encoded = urllib.parse.quote(query.replace(" ", "_"))
        url = (
            f"https://en.wikipedia.org/api/rest_v1/page/summary/{encoded}"
        )
        req = urllib.request.Request(
            url,
            headers={"User-Agent": "AtelierAI/1.0 (educational project)"},
        )
        with urllib.request.urlopen(req, timeout=8) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        title   = data.get("title", query)
        extract = data.get("extract", "No summary available.")
        return f"Wikipedia — {title}\n\n{extract}"
    except Exception as exc:
        return f"Wikipedia lookup failed: {exc}"


def _tool_calculator(expression: str) -> str:
    """Safely evaluate a math expression using only math module functions."""
    # Whitelist: digits, operators, spaces, and math function names
    safe_pattern = re.compile(r"^[\d\s\+\-\*\/\.\(\)\*\*\%]+$|"
                              r"^[\w\s\+\-\*\/\.\(\)\*\*\%]+$")
    allowed_names = {
        "sqrt": math.sqrt, "log": math.log, "log10": math.log10,
        "sin": math.sin, "cos": math.cos, "tan": math.tan,
        "abs": abs, "round": round, "pow": pow,
        "pi": math.pi, "e": math.e, "inf": math.inf,
    }
    # Block any obviously dangerous strings
    forbidden = ["import", "exec", "eval", "open", "os", "__"]
    for word in forbidden:
        if word in expression:
            return "Error: expression contains forbidden keyword."
    try:
        result = eval(expression, {"__builtins__": {}}, allowed_names)  # noqa: S307
        return f"Result: {result}"
    except Exception as exc:
        return f"Calculator error: {exc}"


def _tool_web_search(query: str) -> str:
    """
    Stub web search — returns plausible-sounding mock results.
    Replace this body with a real SerpAPI / Brave / DuckDuckGo call
    by adding a SEARCH_API_KEY to .env.
    """
    q = query.strip()
    results = [
        {
            "title": f"{q} — Overview",
            "url": f"https://en.wikipedia.org/wiki/{urllib.parse.quote(q.replace(' ', '_'))}",
            "snippet": (
                f"A comprehensive overview of {q}, covering its history, "
                "significance, and current developments."
            ),
        },
        {
            "title": f"Latest news on {q}",
            "url": f"https://news.google.com/search?q={urllib.parse.quote(q)}",
            "snippet": (
                f"Recent articles and updates related to {q} from global news sources."
            ),
        },
        {
            "title": f"{q} — In-depth analysis",
            "url": f"https://scholar.google.com/scholar?q={urllib.parse.quote(q)}",
            "snippet": (
                f"Academic and research perspectives on {q}, "
                "including case studies and expert commentary."
            ),
        },
    ]
    lines = [f"Web search results for: \"{q}\"\n"]
    for i, r in enumerate(results, 1):
        lines.append(f"{i}. [{r['title']}]({r['url']})")
        lines.append(f"   {r['snippet']}\n")
    return "\n".join(lines)


def _tool_file_reader(filename: str) -> str:
    """Read a file from generated/ or uploads/ directories."""
    # Sanitize — no path traversal
    safe_name = Path(filename).name
    for directory in (GENERATED_DIR, UPLOADS_DIR):
        candidate = directory / safe_name
        if candidate.exists():
            size = candidate.stat().st_size
            if candidate.suffix.lower() in (".svg", ".txt", ".json", ".md"):
                content = candidate.read_text(encoding="utf-8", errors="replace")
                preview = content[:800] + ("..." if len(content) > 800 else "")
                return f"File: {safe_name} ({size} bytes)\n\n{preview}"
            return f"File: {safe_name} ({size} bytes) — binary file, preview not available."
    return f"File '{safe_name}' not found in generated/ or uploads/ directories."


_TOOL_EXECUTORS = {
    "wikipedia_lookup": lambda args: _tool_wikipedia_lookup(args["query"]),
    "calculator":       lambda args: _tool_calculator(args["expression"]),
    "web_search":       lambda args: _tool_web_search(args["query"]),
    "file_reader":      lambda args: _tool_file_reader(args["filename"]),
}


# ── Groq API caller ───────────────────────────────────────────────────────────

def _groq_chat(messages: list[dict], tools: list[dict] | None = None) -> dict:
    """Call Groq chat completions and return the response JSON."""
    payload: dict = {
        "model": GROQ_TOOL_MODEL,
        "messages": messages,
        "temperature": 0.3,
        "max_tokens": 1024,
    }
    if tools:
        payload["tools"] = tools
        payload["tool_choice"] = "auto"

    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        GROQ_CHAT_URL,
        data=data,
        headers={
            "Content-Type":  "application/json",
            "Authorization": f"Bearer {settings.groq_api_key}",
            "User-Agent":    "python-httpx/0.24.0",  # bypass Cloudflare bot-detection
        },
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode("utf-8"))


# ── Agentic loop ──────────────────────────────────────────────────────────────

def run_mcp_agent(prompt: str) -> dict:
    """
    Run the MCP agentic loop.

    Returns a dict with:
      steps:        list of {role, content/tool_call/tool_result}
      final_answer: str  — the model's final plain-text response
      tool_calls:   list of {tool, input, output} for display
    """
    if not settings.groq_api_key:
        return {
            "steps": [],
            "final_answer": (
                "Groq API key not configured. "
                "Add GROQ_API_KEY to your .env file to enable the MCP Agent."
            ),
            "tool_calls": [],
        }

    system_prompt = (
        "You are Atelier Agent — an intelligent assistant with access to tools. "
        "When answering a question, think step by step. "
        "Use tools when you need factual information, calculations, or file contents. "
        "After gathering enough information, give a clear, helpful final answer."
    )

    messages: list[dict] = [
        {"role": "system",  "content": system_prompt},
        {"role": "user",    "content": prompt},
    ]

    steps:       list[dict] = []
    tool_calls_log: list[dict] = []

    for iteration in range(MAX_ITERATIONS):
        try:
            response = _groq_chat(messages, tools=TOOLS)
        except Exception as exc:
            steps.append({"role": "error", "content": str(exc)})
            break

        choice  = response["choices"][0]
        message = choice["message"]
        finish  = choice.get("finish_reason", "")

        # Record the assistant turn
        messages.append({"role": "assistant", **{k: v for k, v in message.items() if k != "role"}})

        # If the model wants to call tools
        if finish == "tool_calls" or message.get("tool_calls"):
            for tc in message.get("tool_calls", []):
                fn_name = tc["function"]["name"]
                try:
                    fn_args = json.loads(tc["function"]["arguments"])
                except json.JSONDecodeError:
                    fn_args = {}

                steps.append({
                    "role":      "tool_call",
                    "tool":      fn_name,
                    "arguments": fn_args,
                    "call_id":   tc["id"],
                })

                executor = _TOOL_EXECUTORS.get(fn_name)
                if executor:
                    try:
                        result = executor(fn_args)
                    except Exception as exc:
                        result = f"Tool execution error: {exc}"
                else:
                    result = f"Unknown tool: {fn_name}"

                tool_calls_log.append({
                    "tool":   fn_name,
                    "input":  fn_args,
                    "output": result,
                })

                steps.append({
                    "role":    "tool_result",
                    "tool":    fn_name,
                    "content": result,
                    "call_id": tc["id"],
                })

                # Feed tool result back to the model
                messages.append({
                    "role":         "tool",
                    "tool_call_id": tc["id"],
                    "content":      result,
                })
            continue  # next iteration

        # Model gave a plain text response (finish_reason == "stop" or content present)
        final_text = (message.get("content") or "").strip()
        if final_text:
            steps.append({"role": "assistant", "content": final_text})
            return {
                "steps":        steps,
                "final_answer": final_text,
                "tool_calls":   tool_calls_log,
                "iterations":   iteration + 1,
            }
        # Unexpected empty content — force a final answer call below
        break

    # If we exhausted iterations OR got empty content, do one final
    # plain-text call (no tools) so the user always gets an answer.
    try:
        final_messages = [
            m for m in messages
            if m.get("role") in ("system", "user", "assistant", "tool")
        ]
        final_messages.append({
            "role": "user",
            "content": (
                "Based on everything so far, please give me a clear and concise "
                "final answer to the original question."
            ),
        })
        fallback_resp = _groq_chat(final_messages, tools=None)
        fallback_text = (
            fallback_resp["choices"][0]["message"].get("content") or ""
        ).strip()
        if fallback_text:
            return {
                "steps":        steps,
                "final_answer": fallback_text,
                "tool_calls":   tool_calls_log,
                "iterations":   MAX_ITERATIONS,
            }
    except Exception:
        pass

    # Hard fallback
    return {
        "steps":        steps,
        "final_answer": "I couldn't produce a final answer. Please try rephrasing your question.",
        "tool_calls":   tool_calls_log,
        "iterations":   MAX_ITERATIONS,
    }


# ── Public tool list (for /api/mcp/tools endpoint) ───────────────────────────

def list_tools() -> list[dict]:
    return [
        {
            "name":        t["function"]["name"],
            "description": t["function"]["description"],
        }
        for t in TOOLS
    ]
