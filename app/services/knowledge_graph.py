"""
app/services/knowledge_graph.py
────────────────────────────────
Topic 25 — Knowledge Graph Extraction with LLMs

Uses Groq (llama-3.3-70b-versatile) to extract entities and relationships
from conversation text as (subject, predicate, object) triples.

Graph is built with networkx and rendered as an interactive HTML widget
using pyvis — zero extra server required.
"""
from __future__ import annotations

import json
import urllib.request
from pathlib import Path

from app.settings import settings

GROQ_CHAT_URL  = "https://api.groq.com/openai/v1/chat/completions"
GROQ_KG_MODEL  = "llama-3.3-70b-versatile"   # updated model (llama3-70b-8192 decommissioned)

BASE_DIR    = Path(__file__).resolve().parent.parent.parent
GRAPHS_DIR  = BASE_DIR / "generated" / "graphs"


def _ensure_graphs_dir() -> None:
    GRAPHS_DIR.mkdir(parents=True, exist_ok=True)


# ── Groq extraction call ──────────────────────────────────────────────────────

def extract_triples_from_text(text: str) -> list[dict]:
    """
    Call Groq to extract (subject, predicate, object) triples from text.
    Returns a list of dicts: [{subject, predicate, object}, ...]
    Falls back to empty list on any failure.
    """
    if not settings.groq_api_key:
        return []

    system = (
        "You are a knowledge graph extraction engine. "
        "Given text, extract factual (subject, predicate, object) triples. "
        "Return ONLY a valid JSON array of objects, each with keys: "
        "\"subject\", \"predicate\", \"object\". "
        "Extract 5-15 meaningful triples. No markdown, no explanation — just the JSON array."
    )
    user = f"Extract knowledge graph triples from this text:\n\n{text[:3000]}"

    payload = json.dumps({
        "model":       GROQ_KG_MODEL,
        "messages":    [
            {"role": "system", "content": system},
            {"role": "user",   "content": user},
        ],
        "temperature": 0.1,
        "max_tokens":  1024,
    }).encode("utf-8")

    req = urllib.request.Request(
        GROQ_CHAT_URL,
        data=payload,
        headers={
            "Content-Type":  "application/json",
            "Authorization": f"Bearer {settings.groq_api_key}",
            "User-Agent":    "python-httpx/0.24.0",  # bypass Cloudflare bot-detection
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        raw_text = data["choices"][0]["message"]["content"].strip()
        # Strip markdown fences if present
        if raw_text.startswith("```"):
            raw_text = raw_text.split("```")[1]
            if raw_text.startswith("json"):
                raw_text = raw_text[4:]
        triples = json.loads(raw_text)
        if isinstance(triples, list):
            return [
                t for t in triples
                if isinstance(t, dict)
                and "subject" in t and "predicate" in t and "object" in t
            ]
    except Exception:
        pass
    return []


# ── Graph building ─────────────────────────────────────────────────────────────

def build_graph(triples: list[dict]):
    """Build a networkx DiGraph from a list of triples."""
    try:
        import networkx as nx  # type: ignore
    except ImportError:
        return None

    G = nx.DiGraph()
    for triple in triples:
        subj = str(triple.get("subject", "")).strip()
        pred = str(triple.get("predicate", "")).strip()
        obj  = str(triple.get("object",  "")).strip()
        if subj and pred and obj:
            G.add_edge(subj, obj, label=pred)
    return G


# ── pyvis rendering ────────────────────────────────────────────────────────────

def render_graph_html(triples: list[dict], conversation_id: int | None = None) -> str:
    """
    Render an interactive graph HTML string using pyvis.
    Returns raw HTML that can be embedded in an <iframe srcdoc=...>.
    Falls back to a plain JSON display if pyvis/networkx are not installed.
    """
    _ensure_graphs_dir()

    if not triples:
        return _empty_graph_html()

    try:
        import networkx as nx          # type: ignore
        from pyvis.network import Network  # type: ignore
    except ImportError:
        return _fallback_html(triples)

    G = build_graph(triples)
    if G is None or G.number_of_nodes() == 0:
        return _empty_graph_html()

    net = Network(
        height="500px",
        width="100%",
        bgcolor="#0f0f1a",
        font_color="#e0e0ff",
        directed=True,
    )
    net.from_nx(G)

    # Style nodes
    for node in net.nodes:
        node["color"]       = "#7c5cfc"
        node["font"]        = {"color": "#ffffff", "size": 14}
        node["borderWidth"] = 2
        node["border"]      = "#a78bfa"
        node["shape"]       = "dot"
        node["size"]        = 18

    # Style edges (add labels from graph)
    for edge in net.edges:
        src  = edge.get("from", "")
        dst  = edge.get("to", "")
        lbl  = G.edges.get((src, dst), {}).get("label", "")
        edge["label"]       = lbl
        edge["color"]       = {"color": "#a78bfa", "highlight": "#c4b5fd"}
        edge["font"]        = {"color": "#c4b5fd", "size": 11, "align": "middle"}
        edge["arrows"]      = "to"
        edge["smooth"]      = {"type": "curvedCW", "roundness": 0.2}

    net.set_options(json.dumps({
        "physics": {
            "enabled": True,
            "forceAtlas2Based": {
                "gravitationalConstant": -50,
                "centralGravity": 0.01,
                "springLength": 120,
                "springConstant": 0.08,
            },
            "solver": "forceAtlas2Based",
            "stabilization": {"iterations": 150},
        },
        "interaction": {
            "hover": True,
            "tooltipDelay": 200,
            "navigationButtons": True,
        },
    }))

    html_str = net.generate_html(notebook=False)
    return html_str


def _empty_graph_html() -> str:
    return """<!DOCTYPE html><html><body style="background:#0f0f1a;display:flex;
align-items:center;justify-content:center;height:100vh;margin:0;">
<p style="color:#a78bfa;font-family:sans-serif;font-size:1.1rem;">
No knowledge graph data yet. Send a message to extract entities.</p>
</body></html>"""


def _fallback_html(triples: list[dict]) -> str:
    rows = "".join(
        f"<tr><td>{t.get('subject','')}</td>"
        f"<td style='color:#a78bfa'>{t.get('predicate','')}</td>"
        f"<td>{t.get('object','')}</td></tr>"
        for t in triples
    )
    return f"""<!DOCTYPE html><html>
<head><style>
body{{background:#0f0f1a;color:#e0e0ff;font-family:sans-serif;padding:1rem}}
table{{width:100%;border-collapse:collapse}}
td{{padding:.4rem .6rem;border-bottom:1px solid #2d2d4e}}
</style></head>
<body><h3 style="color:#a78bfa">Knowledge Triples</h3>
<table><tr><th>Subject</th><th>Predicate</th><th>Object</th></tr>
{rows}</table></body></html>"""


# ── Convenience: extract from messages text ───────────────────────────────────

def extract_for_conversation(messages: list[dict]) -> list[dict]:
    """
    Given a list of message dicts (with 'text' field),
    combine all text and extract triples.
    """
    combined = " ".join(
        m.get("text", "") or ""
        for m in messages
        if m.get("role") in ("user", "assistant") and m.get("text")
    )
    if not combined.strip():
        return []
    return extract_triples_from_text(combined)
