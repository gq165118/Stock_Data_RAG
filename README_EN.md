# RAG-gq Project Overview (English)

[中文](./README.md) | [English](./README_EN.md)

This repository is a practical RAG (Retrieval-Augmented Generation) project for question answering over enterprise reports (annual reports, research reports, investor documents). It supports a full pipeline from PDF parsing to final answers:

- PDF parsing (Docling / MinerU)
- Report normalization (page-level JSON)
- Markdown export and chunking
- Vector database ingestion
- Retrieval + optional LLM reranking
- Final QA generation

The current version has been stabilized around the `data/stock_data` example workflow.

---

## 1. Repository Structure

```text
RAG-gq/
├─ src/
│  ├─ pipeline.py
│  ├─ pdf_mineru.py
│  ├─ parsed_reports_merging.py
│  ├─ text_splitter.py
│  ├─ ingestion.py
│  ├─ retrieval.py
│  ├─ reranking.py
│  ├─ questions_processing.py
│  └─ api_requests.py
├─ data/
│  ├─ stock_data/
│  └─ test_set/
├─ docs/
│  └─ notes/
├─ requirements.txt
└─ README.md
```

---

## 2. Environment Setup

Recommended: Python 3.12

```bash
python -m venv .venv312
.\.venv312\Scripts\Activate.ps1
pip install -r requirements.txt
```

---

## 3. `.env` Configuration

This project is configuration-driven. For your current setup, Agicto is used as the main provider.

Key variables:

- `AGICTO_API_KEY`
- `AGICTO_BASE_URL`
- `AGICTO_CHAT_MODEL` (e.g. `deepseek-v4-flash`)
- `EMBEDDING_PROVIDER=agicto`
- `AGICTO_EMBEDDING_MODEL` (embedding model)
- `RERANK_PROVIDER=agicto` (optional)
- `RERANK_MODEL` (optional; falls back to `AGICTO_CHAT_MODEL`)

For MinerU parsing:

- `MINERU_API_KEY`
- `MINERU_SUBMIT_URL`
- `MINERU_RESULT_URL_TEMPLATE`

---

## 4. Data and Reproducibility

`data/stock_data/` contains a runnable example dataset:

- `questions.json` (input questions)
- `pdf_reports/` (source PDFs)
- `answers_*.json` (generated outputs)

Intermediate artifacts (`debug_data`, `databases`, etc.) are ignored by `.gitignore` to keep the repo manageable.

---

## 5. How to Run

Run the main pipeline:

```bash
python -m src.pipeline
```

Typical stage flow:

1. Parse PDFs
2. Merge parsed outputs into page-level JSON
3. Export Markdown
4. Chunk markdown files
5. Build vector DBs
6. Process questions and generate answers

You can control stage execution through settings in `src/pipeline.py`.

---

## 6. Stability Improvements Included

Recent fixes include:

- Provider alignment for embeddings (avoid unintended DashScope fallback)
- Input compatibility for both `text/kind` and `question/schema`
- Retrieval fallback when `content.pages` is missing
- Reranking failure fallback (pipeline continues instead of crashing)
- Agicto support for reranking path

---

## 7. FAQ

### Q1: `subset.csv not found ... fallback to new_challenge_pipeline=False`
This is a compatibility fallback message. It is expected in datasets that only provide `questions.json` with `text/kind` fields.

### Q2: Why do I still see DashScope-related errors?
Usually one sub-path (often reranking) is still using a default provider. Check `RERANK_PROVIDER`, `EMBEDDING_PROVIDER`, and runtime defaults.

```bash
git remote set-url origin git@github.com:<your-username>/<repo>.git
git push -u origin main
```

---

## 8. Notes

This project currently prioritizes **practical execution and debugging** over strict production architecture. For next-step improvements, consider:

- Unified provider/config abstraction
- Better tracing/metrics
- Minimal regression tests for the full pipeline
