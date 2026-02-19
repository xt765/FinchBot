# System Architecture

This document provides a deep dive into FinchBot's system architecture, core components, and their interactions.

## 1. Overall Architecture

FinchBot is built on **LangChain** and **LangGraph**, serving as an Agent system with persistent memory and dynamic tool scheduling. The system consists of three core components:

1.  **Agent Core (Brain)**: Responsible for decision-making, planning, and tool scheduling.
2.  **Memory System (Memory)**: Responsible for the storage and retrieval of long-term information.
3.  **Tool Ecosystem (Tools)**: Responsible for interacting with the external world (filesystem, network, shell).

```mermaid
graph TD
    User[User] --> CLI[CLI Interface]
    CLI --> Agent[Agent Core (LangGraph)]
    
    subgraph Core [Agent Core]
        Planner[Planner]
        Executor[Executor]
        Context[Context Builder]
    end
    
    Agent --> Context
    Context --> SystemPrompt[System Prompt]
    
    Agent --> Memory[Memory System]
    subgraph MemSys [Memory System]
        Manager[Memory Manager]
        SQLite[(SQLite Structured)]
        Vector[(Vector Semantic)]
        Sync[Data Sync Service]
    end
    
    Manager --> SQLite
    Manager --> Vector
    SQLite <--> Sync <--> Vector
    
    Agent --> Tools[Tool Ecosystem]
    subgraph ToolSys [Tools]
        File[File Operations]
        Web[Web Search]
        Shell[Shell Execution]
        Custom[Custom Tools]
    end
```

## 2. Core Components

### 2.1 Agent Core

*   **Implementation**: `src/finchbot/agent/core.py`
*   **State Management**: Based on `LangGraph`'s `StateGraph`, maintaining conversation state (`messages`).
*   **Persistence**: Uses `SqliteSaver` (`checkpoints.db`) to save state snapshots, supporting resume and history rollback.
*   **Context Construction (`ContextBuilder`)**:
    *   Dynamically assembles the system prompt, including:
        *   **Identity**: `SYSTEM.md` (Role definition)
        *   **Memory Guide**: `MEMORY_GUIDE.md` (Memory usage guidelines)
        *   **Skills**: Dynamically loaded skill descriptions
        *   **Tools**: `TOOLS.md` (Tool documentation)
        *   **Runtime Info**: Current time, OS, Python version, etc.

### 2.2 Memory System

FinchBot implements an advanced **Layered Memory Architecture** designed to solve LLM context window limits and long-term forgetting issues.

*   **Implementation**: `src/finchbot/memory/`
*   **Layered Design**:
    1.  **Structured Layer (SQLite)**:
        *   **Role**: Source of Truth.
        *   **Content**: Full text, metadata (tags, source), category, importance score.
        *   **Advantage**: Supports precise queries (e.g., filtering by time, category).
    2.  **Semantic Layer (Vector Store)**:
        *   **Role**: Fuzzy retrieval and association.
        *   **Content**: Embedding vectors of text.
        *   **Tech Stack**: ChromaDB + FastEmbed (Local lightweight models).
        *   **Advantage**: Supports natural language semantic search (e.g., "that Python library I mentioned last time").

*   **Core Services**:
    *   **DataSyncManager**: Ensures eventual consistency between SQLite and Vector Store.
    *   **ImportanceScorer**: Automatically evaluates memory importance (0.0-1.0) for cleanup and prioritization.
    *   **RetrievalService**: Hybrid retrieval strategy combining vector similarity and metadata filtering.

### 2.3 Tool Ecosystem

*   **Implementation**: `src/finchbot/tools/`
*   **Registration Mechanism**:
    *   **ToolRegistry**: Singleton registry managing all available tools.
    *   **Lazy Loading**: Default tools (File, Search, etc.) are automatically registered when the Agent starts.
*   **Security Sandbox**:
    *   **File Operations**: Restricted to the workspace (`workspace`) to prevent unauthorized system access.
    *   **Shell Execution**: High-risk commands (rm -rf /) are disabled by default, with timeout control.

## 3. Data Flow

### 3.1 Conversation Flow
1.  User input -> Received by CLI.
2.  Agent loads history state (Checkpoint).
3.  ContextBuilder constructs current Prompt (including relevant memory).
4.  LLM generates response or tool call request.
5.  If tool call -> Execute tool -> Return result to LLM -> Loop.
6.  LLM generates final response -> Display to user.

### 3.2 Memory Write Flow (Remember)
1.  Agent calls `remember` tool.
2.  `MemoryManager` receives content.
3.  Automatically calculates `category` and `importance`.
4.  Writes to SQLite, generating a unique ID.
5.  Async/Sync call to Embedding Service, writing vector to ChromaDB.

### 3.3 Memory Retrieval Flow (Recall)
1.  Agent calls `recall` tool (Query: "What is my API Key").
2.  `RetrievalService` converts query to vector.
3.  Search Top-K similar results in Vector Store.
4.  (Optional) Combine with SQLite for metadata filtering.
5.  Return results to Agent.
