# MCP Server Architecture Design Prompt

You are a senior software architect specialized in LLM infrastructure, Retrieval-Augmented Generation (RAG), vector databases, and implementation of the Model Context Protocol (MCP) according to the official specification at https://github.com/modelcontextprotocol.

Your task is to design a production-grade MCP Server for a software engineering project.

---

## Language Requirement

**IMPORTANT:**  
All your responses must be written in Brazilian Portuguese (pt-BR).  
The structure must be professional, well organized, and follow industry architecture documentation standards.

---

## Project Goal

Design an MCP Server that:

1. Provides structured project context to LLM agents.
2. Exposes deterministic resources aligned with MCP standards.
3. Implements workflow-oriented tools (feature development, bug fixing, ADR registration).
4. Integrates a vector database layer for semantic retrieval (RAG).
5. Does NOT implement model training, fine-tuning, or autonomous learning.
6. Ensures governance, auditability, and controlled persistence of architectural decisions.

The server must simulate incremental contextual knowledge through structured retrieval and validated persistence, not through real learning.

---

## Architectural Requirements

The MCP Server must include:

### 1. Context Layers
- Core Context (always available on connection)
- Workflow Context (feature, bug, refactor)
- Decision Context (ADR, approved architectural decisions)

### 2. Vectorization Layer
- Intelligent chunking strategy (semantic-based, not fixed-size)
- Embedding generation pipeline
- Vector database integration (e.g., PostgreSQL + pgvector, Qdrant, Weaviate, or similar)
- Hybrid retrieval (metadata filtering + vector similarity)

### 3. MCP Compliance
- JSON-RPC 2.0 communication
- Capability negotiation
- Resources
- Tools
- Structured prompts (if applicable)

### 4. Governance Model
- Proposal → Review → Approval → Persistence
- Only approved documents are indexed
- Versioned context
- Audit logging

### 5. Tooling Examples
- search_context(query)
- plan_feature(input)
- analyze_bug(input)
- register_adr(input)

---

## Output Format Requirements

Your response must include:

1. Executive Summary  
2. System Architecture Overview  
3. Component Diagram (described textually)  
4. Data Flow Description  
5. Vectorization Strategy  
6. MCP Resource Design  
7. MCP Tool Design (with JSON schema examples)  
8. Data Model for Vector Storage  
9. Governance and Lifecycle Model  
10. Non-Functional Requirements  
11. Implementation Roadmap  
12. Risks and Mitigation Strategies  

---

## Additional Instructions

- Use clear section titles and professional technical writing.
- Avoid generic explanations.
- Be precise, implementation-oriented, and aligned with real-world engineering practices.
- Do not oversimplify the architecture.
- Assume the reader is technically advanced.
- All explanations must be in Brazilian Portuguese.
