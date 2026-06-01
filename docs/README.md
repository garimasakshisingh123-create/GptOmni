# GptOmni Documentation

## Overview
**GptOmni** is an advanced, verifiable AI chat application designed to provide highly accurate, grounded, and halluciation-free responses. It achieves this by employing a sophisticated **9-stage Intelligence Pipeline** that intercepts user queries, retrieves live web data, generates answers, and mathematically verifies its own claims before delivering the final response to the user.

## Tech Stack
* **Frontend:** Next.js, Tailwind CSS (Deployed on Vercel)
* **Backend:** FastAPI, Python (Deployed on Hugging Face Spaces)
* **Database:** Supabase (PostgreSQL)
* **AI Provider:** OpenRouter (Free Tier Models like Llama 3.2, Gemma 4, GPT-OSS)
* **Web Search:** Serper API
* **Local ML:** PyTorch, Sentence-Transformers (Embeddings), Cross-Encoders (Reranking)

## The 9-Stage Intelligence Pipeline
The core of GptOmni's accuracy lies in its Intelligence Engine pipeline, which runs on the backend for every factual query:

1. **Intent Analysis**: Determines if the query is conversational, factual, or arithmetic.
2. **Query Optimization**: Generates optimized search queries if external facts are needed.
3. **Web Search**: Uses Serper API to find relevant articles and snippets.
4. **Reranking**: Uses local Cross-Encoder ML models to score and filter the most relevant search snippets.
5. **Context Assembly**: Constructs a verified evidence block from the highest-scoring snippets.
6. **Generation**: The primary LLM generates an initial answer and extracts specific factual claims made in that answer.
7. **Verification**: A secondary LLM acts as an auditor, checking each claim against the evidence block to detect hallucinations.
8. **Refinement**: If claims fail verification, the answer is rewritten or flagged to ensure accuracy.
9. **Final Delivery**: The validated response is streamed to the frontend, along with full provenance (sources and verification scores).

## Features
* **Real-time Streaming**: Responses stream in real-time, just like standard ChatGPT.
* **Intelligence Engine UI**: A collapsible panel in the UI that lets users see exactly what the AI is thinking at every stage of the 9-step pipeline.
* **Verifiable Provenance**: Every factual claim is backed by cited sources, visible to the user.
* **Persistent Sessions**: Chat history is saved to Supabase securely.
