# RAG-gq (English)

[中文](./README.md) | [English](./README_EN.md)

`RAG-gq` is a practical RAG project for enterprise report QA (annual reports, research reports, investor documents). It provides an end-to-end pipeline from PDF parsing to final answers.

Typical use cases:

- Enterprise knowledge QA prototypes
- Multi-document retrieval with evidence grounding
- RAG strategy experiments (retrieval, reranking, prompting)

## What it can do

- PDF parsing via Docling or MinerU
- Parsed report normalization into unified text structures
- Vector retrieval (full-corpus or company-scoped)
- Optional LLM reranking
- Structured answer schemas (`string`, `boolean`, `number`, `name`, `names`)
- Streamlit UI with debug panel

## Project structure

```text
RAG-gq/
├─ src/
│  ├─ pipeline.py
│  ├─ retrieval.py
│  ├─ reranking.py
│  ├─ questions_processing.py
│  ├─ ingestion.py
│  └─ ...
├─ data/
│  ├─ stock_data/
│  └─ test_set/
├─ docs/
├─ app.py
└─ requirements.txt
```

## Quick start

### 1) Install environment

```bash
python -m venv .venv312
.\.venv312\Scripts\Activate.ps1
pip install -r requirements.txt
```

### 2) Configure `.env`

Minimum settings (Agicto example):

- `AGICTO_API_KEY`
- `AGICTO_BASE_URL`
- `AGICTO_CHAT_MODEL`
- `EMBEDDING_PROVIDER=agicto`

Recommended optional settings:

- `AGICTO_EMBEDDING_MODEL`
- `RERANK_PROVIDER=agicto`
- `RERANK_MODEL` (falls back to `AGICTO_CHAT_MODEL` if omitted)

If using MinerU parsing, also configure:

- `MINERU_API_KEY`
- `MINERU_SUBMIT_URL`
- `MINERU_RESULT_URL_TEMPLATE`

## Running the project

### Option A: main pipeline

```bash
python -m src.pipeline
```

Typical flow:

1. Parse PDFs
2. Normalize parsed reports
3. Export Markdown
4. Chunk text
5. Build vector databases
6. Process questions and write answers

### Option B: UI mode

```bash
streamlit run .\app.py
```

After startup, use the URL printed in your terminal (usually localhost on port 8501).

## Data

Example dataset: `data/stock_data/`

- `questions.json` for input questions
- `pdf_reports/` as source PDFs
- `answers_*.json` as sample outputs

Intermediate artifacts (`debug_data`, `databases`, etc.) are ignored by `.gitignore` by default.

## Current status

This repo has been hardened with recent fixes including:

- Provider alignment across embedding / reranking / QA
- Compatibility for both `text/kind` and `question/schema`
- Fallback handling when `pages` is missing
- Reranking failure degradation instead of hard crash
- Streamlit UI with multi-dataset support and debug panel

## Scope and limitations

This repository currently prioritizes practical execution and debugging over full production engineering.

For production adoption, consider adding:

- Test coverage and regression baselines
- Logging/observability/tracing
- Centralized config and secret management
- More granular resilience and retry policies
