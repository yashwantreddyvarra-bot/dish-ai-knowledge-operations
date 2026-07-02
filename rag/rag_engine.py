# ─────────────────────────────────────────────────────────────────
#  rag/rag_engine.py  — Layer 3: RAG (Retrieval-Augmented Generation)
#  Ingests enriched manifests into ChromaDB, semantic search + GPT answer.
# ─────────────────────────────────────────────────────────────────
import os, json, subprocess, sys
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from config.settings import (
    OPENAI_API_KEY, LLM_MODEL, DB_DIR, CHROMA_COLLECTION, CHUNK_OVERLAP,
)

import importlib.util
for pip_name, mod_name in [("chromadb", "chromadb"),
                           ("sentence-transformers", "sentence_transformers")]:
    if not importlib.util.find_spec(mod_name):
        subprocess.check_call([sys.executable, "-m", "pip", "install", pip_name, "--quiet"])

import chromadb
from chromadb.utils import embedding_functions

os.makedirs(DB_DIR, exist_ok=True)
_EMBED_MODEL = "all-MiniLM-L6-v2"


def _get_ef():
    return embedding_functions.SentenceTransformerEmbeddingFunction(model_name=_EMBED_MODEL)


def _get_collection(name=CHROMA_COLLECTION):
    client = chromadb.PersistentClient(path=DB_DIR)
    return client.get_or_create_collection(
        name=name, embedding_function=_get_ef(), metadata={"hnsw:space": "cosine"})


def _make_chunk_text(steps, title):
    lines = [f"Workflow: {title}"]
    for s in steps:
        lines.append(f"Step {s['step']}: {s.get('llm_caption') or s.get('label','')}")
    return "\n".join(lines)


def chunk_manifest(manifest):
    steps = manifest.get("screenshots", [])
    title = manifest.get("workflow_title", manifest.get("product_name", "Workflow"))
    ts = manifest.get("recorded_at", datetime.now().isoformat())
    chunks, window = [], 3
    for i in range(0, len(steps), window - CHUNK_OVERLAP):
        win = steps[i:i + window]
        if not win:
            break
        ids = [s["step"] for s in win]
        chunks.append({
            "id": f"{title[:30].replace(' ', '_')}__steps_{ids[0]}-{ids[-1]}",
            "text": _make_chunk_text(win, title),
            "metadata": {
                "workflow": title, "step_start": ids[0], "step_end": ids[-1],
                "step_labels": " | ".join(s.get("llm_caption") or s.get("label", "") for s in win),
                "screenshot": win[0].get("screenshot", ""),
                "all_screenshots": json.dumps([s.get("screenshot", "") for s in win]),
                "recorded_at": ts,
            }})
    print(f"  🔪 Chunked into {len(chunks)} pieces")
    return chunks


def ingest_manifest(manifest_path, workflow_title=None, collection_name=CHROMA_COLLECTION):
    with open(manifest_path, encoding="utf-8") as f:
        manifest = json.load(f)
    if workflow_title:
        manifest["workflow_title"] = workflow_title
    chunks = chunk_manifest(manifest)
    if not chunks:
        print("  ⚠️ No chunks"); return 0
    col = _get_collection(collection_name)
    col.upsert(ids=[c["id"] for c in chunks],
               documents=[c["text"] for c in chunks],
               metadatas=[c["metadata"] for c in chunks])
    print(f"  ✅ Ingested {len(chunks)} chunks into '{collection_name}'")
    return len(chunks)


def retrieve(query, n_results=4, collection_name=CHROMA_COLLECTION):
    col = _get_collection(collection_name)
    res = col.query(query_texts=[query], n_results=min(n_results, col.count() or 1),
                    include=["documents", "metadatas", "distances"])
    return [{"text": d, "metadata": m, "similarity": round(1 - dist, 3)}
            for d, m, dist in zip(res["documents"][0], res["metadatas"][0], res["distances"][0])]


def ask(question, collection_name=CHROMA_COLLECTION, n_results=4):
    key = OPENAI_API_KEY or os.environ.get("OPENAI_API_KEY", "")
    if not key:
        raise ValueError("OPENAI_API_KEY not set")
    hits = retrieve(question, n_results, collection_name)
    if not hits:
        return "No relevant documentation found. Ingest a manifest first."
    blocks = [f"[Source {i} — {h['metadata'].get('workflow','')} "
              f"Steps {h['metadata'].get('step_start','')}-{h['metadata'].get('step_end','')}]\n{h['text']}"
              for i, h in enumerate(hits, 1)]
    from openai import OpenAI
    client = OpenAI(api_key=key)
    resp = client.chat.completions.create(
        model=LLM_MODEL, max_tokens=600,
        messages=[
            {"role": "system", "content": "Answer using ONLY the provided documentation. Be concise and step-by-step. If not in context, say so."},
            {"role": "user", "content": f"Context:\n\n{chr(10).join(blocks)}\n\nQuestion: {question}"},
        ])
    return resp.choices[0].message.content.strip()


def collection_stats(collection_name=CHROMA_COLLECTION):
    col = _get_collection(collection_name)
    return {"collection": collection_name, "total_chunks": col.count(),
            "db_path": DB_DIR, "embed_model": _EMBED_MODEL}


if __name__ == "__main__":
    from config.settings import BASE_OUT
    enriched = f"{BASE_OUT}/manifest_enriched.json"
    plain = f"{BASE_OUT}/manifest.json"
    use = enriched if os.path.exists(enriched) else plain
    if not os.path.exists(use):
        print("No manifest yet. Run capture first."); sys.exit(0)
    ingest_manifest(use, workflow_title="Adding a product and assigning it to a menu")
    print("Stats:", collection_stats())
    q = "How do I add a product to a menu in DISH POS?"
    print(f"\n❓ {q}")
    for h in retrieve(q, 2):
        print(f"  [{h['similarity']}] {h['text'][:120]}...")
