import os
import requests
import streamlit as st

BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:7860").rstrip("/")
st.set_page_config(page_title="Aurora Stays", page_icon="🏨", layout="wide")
st.title("Aurora Stays")
st.write("Ask a question about AuroraStay hotel policies.")
query = st.text_input("Your question", placeholder="What is the pet fee at ASH-CHI Loop?")
if st.button("Ask", type="primary"):
    if not query.strip():
        st.warning("Please enter a question.")
    else:
        try:
            with st.spinner("Checking the hotel policies…"):
                response = requests.post(
                    f"{BACKEND_URL}/v1/answer_with_relevant_chunks",
                    json={"query": query.strip()}, timeout=90,
                )
                response.raise_for_status()
                result = response.json()
            st.subheader("Answer")
            st.write(result["answer"])
            st.subheader("Supporting policy excerpts")
            for i, chunk in enumerate(result["relevant_chunks"], start=1):
                title = chunk["document"]
                if chunk.get("section"):
                    title += " · " + chunk["section"]
                with st.expander(f"{i}. {title}"):
                    st.caption(chunk["filename"])
                    st.write(chunk["text"])
        except (requests.RequestException, ValueError, KeyError):
            st.error("Unable to get an answer. Please try again.")
