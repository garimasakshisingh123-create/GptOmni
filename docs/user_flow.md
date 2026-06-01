# User Flow Diagram

This document illustrates how a user interacts with the system and how the request flows through the various stages of the Intelligence Engine before the response is returned.

## Main Interaction Flow

```mermaid
sequenceDiagram
    actor User
    participant UI as Frontend (Next.js)
    participant API as Backend (FastAPI)
    participant Search as Serper API
    participant ML as Local ML (Embed/Rerank)
    participant LLM as OpenRouter API

    User->>UI: Types query (e.g. "What is inflation?")
    UI->>API: POST /api/chat (Streaming Request)
    
    API->>UI: Emit Stage 1 (Intent Analysis)
    API->>LLM: Analyze intent (Factual vs Conversational)
    LLM-->>API: Returns "Factual"
    
    API->>UI: Emit Stage 2 (Query Optimization)
    API->>LLM: Generate search queries
    LLM-->>API: Returns queries ["causes of inflation", "inflation economics"]
    
    API->>UI: Emit Stage 3 (Web Search)
    API->>Search: Execute queries
    Search-->>API: Returns raw web snippets & links
    
    API->>UI: Emit Stage 4 (Reranking)
    API->>ML: Embed & Cross-Encode snippets against original query
    ML-->>API: Returns top-K most relevant snippets
    
    API->>UI: Emit Stage 5 (Context Assembly)
    API->>API: Builds Evidence Block from snippets
    
    API->>UI: Emit Stage 6 (Generation)
    API->>LLM: Generate Answer + Extract Claims based on Evidence
    LLM-->>API: Returns Draft Answer and [Claim 1, Claim 2]
    
    API->>UI: Emit Stage 7 (Verification)
    API->>LLM: Verify Claims against Evidence Block
    LLM-->>API: Returns True/False for each claim
    
    API->>UI: Emit Stage 8 (Refinement)
    API->>API: Annotates Answer (Flags unverified claims)
    
    API->>UI: Emit Stage 9 (Final Delivery)
    API->>UI: Streams final Markdown text and citations to user screen
    UI-->>User: Displays fully grounded answer with verification status
```

## Key User Actions
1. **New Chat:** User starts a session. Supabase creates a conversation record.
2. **Sending a Message:** Initiates the SSE connection.
3. **Intelligence Engine Inspection:** User can click the "Intelligence Engine" dropdown in the UI to see the real-time logs of the sequence diagram above.
4. **Saving:** Once the SSE stream finishes, the frontend sends a `POST /api/messages` to persist the Assistant's reply.
