# System Architecture

GptOmni uses a modern, decoupled architecture consisting of a serverless frontend and a robust containerized backend for machine learning processing.

## High-Level Architecture

```mermaid
graph TD
    User([User]) -->|HTTP/WebSockets| Frontend
    
    subgraph Vercel [Frontend - Vercel]
        Frontend[Next.js App]
        UI[React Components]
        Frontend --> UI
    end
    
    Frontend -->|REST API / SSE| Backend
    
    subgraph HuggingFace [Backend - Hugging Face Spaces]
        Backend[FastAPI Server]
        Pipeline[9-Stage Intelligence Pipeline]
        Embedder[Sentence-Transformers]
        Reranker[Cross-Encoder]
        
        Backend --> Pipeline
        Pipeline <--> Embedder
        Pipeline <--> Reranker
    end
    
    subgraph External Services
        OpenRouter[OpenRouter API]
        Serper[Serper API - Web Search]
        Supabase[(Supabase PostgreSQL)]
    end
    
    Pipeline <-->|LLM Inference| OpenRouter
    Pipeline <-->|Live Search| Serper
    Backend <-->|Auth & Chat History| Supabase
    Frontend <-->|JWT Auth| Supabase
```

## Component Details

### 1. Frontend (Next.js)
* **Role:** Manages user interface, session state, and streaming data rendering.
* **Key Components:**
  * **Chat UI:** Handles user input and renders Markdown responses.
  * **Intelligence Engine Panel:** Parses Server-Sent Events (SSE) to update pipeline stages visually in real-time.
  * **Authentication:** Integrates with Supabase Auth for user sign-in.

### 2. Backend (FastAPI)
* **Role:** Orchestrates the 9-stage pipeline and heavy ML operations.
* **Key Components:**
  * **Streaming Endpoint (`/api/chat`):** Streams JSON chunks via Server-Sent Events (SSE) so the frontend can update stage-by-stage without waiting for the full pipeline to finish.
  * **ML Services:** Loads PyTorch models (`all-MiniLM-L6-v2` and `ms-marco-MiniLM-L-6-v2`) into RAM upon startup to perform semantic similarity matching and cross-encoder reranking on retrieved web data.

### 3. Database (Supabase)
* **Role:** Provides Row-Level Security (RLS) PostgreSQL storage and JWT authentication.
* **Schema:**
  * `conversations`: Stores chat sessions (id, user_id, title, created_at).
  * `messages`: Stores individual messages (id, conversation_id, role, content, run_id).

### 4. OpenRouter API
* **Role:** Multiplexer for LLM access. It automatically handles failovers. The backend uses different models for different tasks (e.g., small fast models for Intent parsing, large models for Final Generation).
