import ast
from pathlib import PureWindowsPath
from flask import Flask, request, jsonify
from rag_utils import load_settings, load_vectorstore, retrieve, rag


def present_sources(chunks, answer=None):
    """Format the server's excerpt strings for display without changing LLM context."""
    sources = []
    for chunk in chunks:
        content, separator, metadata_text = chunk.partition("\n\nMetadata:\n")
        metadata = ast.literal_eval(metadata_text) if separator else {}
        source_path = str(metadata.get("source", ""))
        filename = PureWindowsPath(source_path).name if source_path else "Policy document"
        title = filename.removesuffix(".pdf").replace("_", " ").capitalize()
        section = str(metadata.get("section", ""))
        text = content.removeprefix("Content:\n")
        # Section is already shown in the expander caption.
        if section and text.startswith(section + "\n"):
            text = text[len(section) + 1:]
        sources.append({"document": title, "filename": filename,
                        "section": section, "text": text})
        if answer is not None and source_path:
            answer = answer.replace(source_path, filename)
    return sources, answer


def create_app(vectorstore=None, settings=None):
    app = Flask("AuroraStay")
    settings = load_settings() if settings is None else settings
    vectorstore = load_vectorstore(settings) if vectorstore is None else vectorstore

    @app.get("/")
    def home():
        return jsonify(status="ready", service="AuroraStay policy Q&A")

    def query_from_request():
        data = request.get_json(silent=True)
        if not isinstance(data, dict):
            raise ValueError("Send a JSON object containing query.")
        if set(data) - {"query"}:
            raise ValueError("Only query is accepted; model settings are configured on the server.")
        query = data.get("query")
        if not isinstance(query, str) or not query.strip():
            raise ValueError("Enter a non-empty question.")
        if len(query) > 4000:
            raise ValueError("Question must be 4000 characters or fewer.")
        return query.strip()

    def respond(mode):
        try:
            query = query_from_request()
        except ValueError as error:
            return jsonify(error=str(error)), 400
        try:
            if mode == "chunks":
                chunks = retrieve(query, vectorstore, settings)
                sources, _ = present_sources(chunks)
                return jsonify(query=query, relevant_chunks=sources)
            answer, chunks = rag(query, vectorstore, settings)
            sources, answer = present_sources(chunks, answer)
            result = {"query": query, "answer": answer}
            if mode == "both":
                result["relevant_chunks"] = sources
            return jsonify(result)
        except Exception:
            # Avoid returning credentials, endpoint URLs, or upstream error details.
            return jsonify(error="Unable to answer now. Please try again."), 502

    @app.post("/v1/relevant_chunks")
    def relevant_chunks():
        return respond("chunks")

    @app.post("/v1/answer_with_relevant_chunks")
    def answer_with_relevant_chunks():
        return respond("both")

    @app.post("/v1/answer")
    def answer():
        return respond("answer")

    return app


if __name__ == "__main__":
    create_app().run(host="127.0.0.1", port=7860)
