# Aurora Stays Policy Q&A

Internal staff Q&A proof of concept using hotel policy documents, OpenAI embeddings, FAISS MMR retrieval, a Flask API, and Streamlit.

## Selected configuration

| Setting | Value |
|---|---|
| Embedding model | text-embedding-3-small |
| Retrieval | MMR |
| Returned chunks | 5 |
| Candidate chunks | 20 |
| Relevance weight | 0.7 |
| Generation model | gpt-4o-mini |
| Temperature / top-p / output limit | 0 / 1 / 512 |
| Exported index | 180 chunks, 1536 dimensions |

## Run in GitHub Codespaces

1. Create a Codespace for this repository.
2. Add repository-enabled Codespaces secrets `OPENAI_API_KEY` and `OPENAI_API_BASE`, then restart the Codespace to load them.
3. In the repository terminal, run:

```bash
docker compose up --build -d
docker compose ps
```

Open forwarded port **8501**, keeping it private for this internal POC. The frontend connects to the backend through the Compose network. Only port 8501 needs forwarding.

The configured endpoint must support the selected embedding and generation models. For local Docker, copy `.env.example` to `.env` and set your credentials. Do not commit `.env`.

## Validation

The held-out 10-question assessment achieved average faithfulness 0.984, recall 0.926, precision 0.778, and relevancy 0.872. Seven questions passed all four metrics. These are small-benchmark results, not a guarantee of complete answers. Staff should verify material policy conditions against cited excerpts.

Backend and frontend were smoke-tested locally. Container builds and Codespaces startup remain unverified. This repository includes the trusted retrieval index, which contains policy excerpts, but excludes raw PDFs, notebooks, evaluation outputs, and API credentials. Load only this trusted index because its document store uses pickle.

See [DEPLOYMENT.md](DEPLOYMENT.md) for details. The `run_local.py` convenience launcher requires a local `config.json` from the development workspace; use Compose and environment secrets for this deployment repository.
