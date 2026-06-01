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

## Intelligence Engine Pipeline Design

The 9-stage pipeline is the core mechanism of GptOmni, ensuring that all factual responses are grounded in verified external data.

```mermaid
graph TD
    classDef llm fill:#f9d0c4,stroke:#333,stroke-width:2px;
    classDef logic fill:#d4e6f1,stroke:#333,stroke-width:2px;
    classDef external fill:#d5f5e3,stroke:#333,stroke-width:2px;

    Start([User Query]) --> Stage1
    
    subgraph Phase 1: Planning & Retrieval
        Stage1[1. Intent Analysis]:::llm
        Stage2[2. Query Optimization]:::llm
        Stage3[3. Web Search]:::external
        Stage4[4. Content Reranking]:::logic
        Stage5[5. Context Assembly]:::logic
        
        Stage1 -->|If Factual| Stage2
        Stage1 -->|If Conversational| Stage6
        Stage2 --> Stage3
        Stage3 --> Stage4
        Stage4 --> Stage5
    end
    
    Stage5 --> Stage6
    
    subgraph Phase 2: Generation & Verification
        Stage6[6. Generation & Claim Extraction]:::llm
        Stage7[7. Claim Verification]:::llm
        Stage8[8. Answer Refinement]:::logic
        
        Stage6 --> Stage7
        Stage7 --> Stage8
    end
    
    Stage8 --> Stage9
    Stage9[9. Final Delivery]:::logic --> End([Final Response & Sources])
    
    %% Note styling and attachments
    class Stage1,Stage2,Stage6,Stage7 llm;
    class Stage4,Stage5,Stage8,Stage9 logic;
    class Stage3 external;
```

### Pipeline Stage Breakdown
* **Stage 1 (Intent Analysis):** A fast LLM (e.g., Llama 3.2 3B) categorizes the user prompt.
* **Stage 2 (Query Optimization):** The LLM translates the prompt into 2-3 optimal Google search queries.
* **Stage 3 (Web Search):** The Serper API executes the queries in parallel, fetching the top 10 results for each.
* **Stage 4 (Reranking):** Local `Sentence-Transformers` and `Cross-Encoder` models score the raw snippets against the original query to find the most relevant chunks.
* **Stage 5 (Context Assembly):** High-scoring snippets are concatenated into an Evidence Block.
* **Stage 6 (Generation):** A large, high-capacity LLM (e.g., Gemma 4 31B) reads the Evidence Block, generates an answer, and strictly extracts the factual claims made in its own answer.
* **Stage 7 (Verification):** A mid-size reasoning LLM acts as an auditor, strictly cross-referencing each extracted claim against the Evidence Block to output a boolean `True` (verified) or `False` (hallucinated).
* **Stage 8 (Refinement):** Python logic annotates the answer, inserting footnotes for verified claims and warnings for unverified claims.
* **Stage 9 (Final Delivery):** The payload is finalized and streamed down to the client.
