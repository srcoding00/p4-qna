# Run the selected AuroraStay POC

The notebook's backend and frontend writer cells match `backend_files/` and `frontend_files/`. The selected pipeline uses `text-embedding-3-small`, FAISS MMR, K=5, fetch_k=20, lambda=0.7, and the same generation prompt as the evaluated notebook. The staff interface always displays supporting excerpts. Runtime settings live in `backend_files/settings.json`; only credentials come from environment variables.

## Export the index

In the notebook, run the deployment index export cell with the selected `vectorstore` still in memory. It writes `backend_files/faiss_index/index.faiss`, `index.pkl`, and `manifest.json`, plus the non-secret server settings. It does not write credentials. The backend refuses an index whose manifest identifies a different embedding model.

## Install and run locally

From the project folder, in a dedicated environment:

```bash
python3 -m venv .venv-deploy
source .venv-deploy/bin/activate
python -m pip install -r backend_files/requirements.txt -r frontend_files/requirements.txt
```

Set `OPENAI_API_KEY` and `OPENAI_API_BASE` in the backend terminal using your endpoint credentials. The endpoint must support both the configured chat model and embeddings. Do not put credentials in settings.json or notebook output.

Start the backend:

```bash
cd backend_files
python -m gunicorn --workers 1 --timeout 120 --bind 127.0.0.1:7860 'app:create_app()'
```

In a second terminal, activate the deployment environment and run from the project folder:

```bash
python -m streamlit run frontend_files/app.py
```

`BACKEND_URL` defaults to `http://localhost:7860`; set it to the backend's reachable URL when running in separate containers or hosts. The backend and frontend Dockerfiles use Python 3.12 and no longer download a local Hugging Face model. Docker builds and remote hosting have not been verified here.

## Check the service

```bash
curl http://localhost:7860/
curl -X POST http://localhost:7860/v1/answer_with_relevant_chunks \
  -H 'Content-Type: application/json' \
  -d '{"query":"What is the pet fee at ASH-CHI Loop?"}'
```

All three POST endpoints accept only `query`. `/v1/relevant_chunks` returns evidence, `/v1/answer` returns the answer, and `/v1/answer_with_relevant_chunks` returns both. Server settings cannot be changed through request parameters. This app does not compute benchmark composite scores at runtime.

Run offline checks after installing backend requirements and pytest:

```bash
python -m pytest tests/test_deployment.py -q
```

The notebook's GitHub publishing cells are retained but have not been executed. Complete the local index export and service check before publishing.

## IDE launcher

Alternatively, activate the environment where deployment requirements were installed and run from the project directory in two terminals:

```bash
python run_local.py backend
```

```bash
python run_local.py frontend
```

The backend launcher reads credentials from local `config.json` and supplies them only to the backend process. The frontend opens at `http://localhost:8501`; the backend binds to `127.0.0.1:7860`. Stop each process with Ctrl+C. This starts local services only.

## Deployment bundle and Codespaces

Create the deployment-only bundle from the project directory:

```bash
python scripts/package_deployment.py
```

The ZIP at `dist/aurora-stays-deployment.zip` contains the backend, frontend, trusted FAISS index, non-secret settings, Compose configuration, and a Codespaces dev container. It excludes `config.json`, real `.env` files, raw PDFs, notebooks, and evaluation outputs. It includes a SHA-256 checksum inventory. The index itself contains policy excerpts required for retrieval.

Extract the ZIP to the root of the intended GitHub repository, preserving hidden files such as `.devcontainer/`. Commit these extracted files, then create a Codespace for that repository. The dev container supplies Python and Docker. Add `OPENAI_API_KEY` and `OPENAI_API_BASE` as Codespaces secrets for that repository and restart the Codespace so they are available in its terminal. Alternatively, for local Docker, copy `.env.example` to `.env` and set the values there. Never commit `.env`.

In a terminal at the extracted repository root:

```bash
docker compose up --build -d
docker compose ps
docker compose logs --tail=50 backend frontend
```

The frontend waits for the backend health check before starting and connects to it over the private Compose network. Open forwarded port **8501** from Codespaces' Ports panel. Keep the forwarded interface private for this internal POC. The backend does not need an externally forwarded port. Outside Codespaces, open `http://localhost:8501`.

Repeat the Miami and unsupported Austin questions to validate the hosted path. The API endpoint must be reachable from the hosted environment; successful local inference alone does not verify that connectivity.

To stop both services:

```bash
docker compose down
```

This prepares a Codespaces-hosted demo, not persistent managed hosting. This environment has no Docker executable, so container builds and Codespaces startup remain unverified. No GitHub repository, Codespace, or public endpoint was created by the preparation step.
