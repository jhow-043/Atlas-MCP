# Fase 3 — Vectorization, RAG e Tools Avançadas

**Status:** APROVADO  
**Data:** 2026-02-23  
**Versão:** 1.0  
**Repositório:** `https://github.com/jhow-043/Atlas-MCP.git`

---

## 1. Objetivo da Fase

Implementar o diferencial do Atlas MCP: a **camada de vectorização semântica com RAG** sobre pgvector, substituindo o mock de `search_context` por busca vetorial real, e entregando as tools `plan_feature` e `analyze_bug`.

Escopo principal:

- Chunking semântico por seções Markdown (headers `##`/`###`), preservando hierarquia
- Interface abstrata `EmbeddingProvider` com implementações OpenAI API e Sentence Transformers (local)
- `VectorStore` — repositório pgvector com busca por similaridade cosine + filtros de metadata
- `IndexingService` — orquestrador que conecta chunker → embedder → store
- Hook na `GovernanceService`: documentos `APPROVED` são indexados, `DEPRECATED` são removidos
- Tool `search_context` conectada ao pipeline real (query → embed → search → format)
- Tools `plan_feature` e `analyze_bug` usando workflow context + busca vetorial
- Testes de integração E2E do pipeline completo

Ao final desta fase, o servidor fornecerá **busca semântica real** sobre o contexto do projeto — ADRs, documentação, convenções — respondendo queries do LLM com resultados vetoriais rankeados por similaridade.

---

## 2. Tarefas (8/8)

| # | Tipo | Branch | Tarefa | Output |
|---|------|--------|--------|--------|
| D1 | `INF` | `INF/P3-D1` | pgvector Extension + Schema + Codec asyncpg. Migrations v5 (extension), v6 (tabela chunks), v7 (índice HNSW). Registro de type codec `vector` no asyncpg. ADR-004. | Schema pgvector funcional, codec registrado |
| D2 | `FET` | `FET/P3-D2` | Chunking semântico Markdown. `ChunkData` dataclass, `MarkdownChunker` — split por headers com hierarquia de seções, merge de chunks pequenos, subdivisão de chunks grandes. | Chunker testado e funcional |
| D3 | `FET` | `FET/P3-D3` | `EmbeddingProvider` interface abstrata + `OpenAIEmbeddingProvider` + `SentenceTransformerEmbeddingProvider` + factory `create_embedding_provider()`. | Providers testados com mocks |
| D4 | `FET` | `FET/P3-D4` | `VectorStore` (repositório pgvector) — `store_chunks()`, `search()` (similarity + filters), `delete_by_document()`, `get_stats()`. | Store funcional com queries pgvector |
| D5 | `FET` | `FET/P3-D5` | `IndexingService` orquestrando chunker→embedder→store. Hook em `GovernanceService` via callback `on_status_change`: APPROVED→indexa, DEPRECATED→remove. | Pipeline de indexação funcional |
| D6 | `FET` | `FET/P3-D6` | `search_context` — implementação real substituindo mock. Pipeline: query→embed→pgvector similarity→format. Fallback gracioso sem DB. Mesma assinatura. | Tool conectada ao RAG real |
| D7 | `FET` | `FET/P3-D7` | Tools `plan_feature` e `analyze_bug`. Iniciam workflow context + buscam contexto vetorial + retornam plano/análise estruturada em JSON. | 2 novas tools registradas |
| D8 | `TST` | `TST/P3-D8` | Testes de integração E2E do pipeline (chunk→embed→store→search). Testes de governance→indexing. ADR-004, README, CHANGELOG atualizados. | Suite E2E, docs completos |

---

## 3. Dependências

| Tarefa | Depende de |
|--------|-----------|
| D1 (Schema pgvector) | — (infraestrutura independente) |
| D2 (Chunker) | — (lógica pura, sem dependências) |
| D3 (Embeddings) | — (interface + providers independentes) |
| D4 (VectorStore) | D1 (schema pgvector precisa existir) |
| D5 (IndexingService) | D2 (chunker) + D3 (embedder) + D4 (store) |
| D6 (search_context) | D3 (embedder) + D4 (store) |
| D7 (plan_feature, analyze_bug) | D6 (search_context real) |
| D8 (Testes + Docs) | D1–D7 |

**Grafo de dependências:**

```
D1 (schema) ──────────────────┐
D2 (chunker) ────────┐        │
D3 (embeddings) ─────┤── D5 ──┤── D8
                      │        │
               D4 (store) ─── D6 ── D7
```

---

## 4. Outputs Esperados

| Artefato | Localização |
|----------|-------------|
| Migrations pgvector | `src/atlas_mcp/persistence/migrations.py` (v5–v7) |
| Vector codec helper | `src/atlas_mcp/persistence/vector_codec.py` |
| ADR-004 | `docs/adr/ADR-004-embedding-provider-interface.md` |
| Chunker semântico | `src/atlas_mcp/vectorization/chunker.py` |
| Embedding providers | `src/atlas_mcp/vectorization/embeddings.py` |
| Vector store | `src/atlas_mcp/vectorization/store.py` |
| Indexing service | `src/atlas_mcp/vectorization/indexing.py` |
| Tool plan_feature | `src/atlas_mcp/tools/plan_feature.py` |
| Tool analyze_bug | `src/atlas_mcp/tools/analyze_bug.py` |
| Testes integração E2E | `tests/integration/test_vectorization.py` |
| Testes governance→index | `tests/integration/test_indexing_governance.py` |

### Estrutura de diretórios esperada (novos arquivos):

```
Atlas-MCP/
├── src/atlas_mcp/
│   ├── persistence/
│   │   └── vector_codec.py      # Registro de tipo vector no asyncpg
│   ├── vectorization/
│   │   ├── __init__.py           # Exports públicos
│   │   ├── chunker.py            # MarkdownChunker, ChunkData
│   │   ├── embeddings.py         # EmbeddingProvider (ABC), OpenAI, SentenceTransformer
│   │   ├── store.py              # VectorStore (CRUD pgvector)
│   │   └── indexing.py           # IndexingService (orquestrador)
│   └── tools/
│       ├── plan_feature.py       # Tool: plan_feature
│       └── analyze_bug.py        # Tool: analyze_bug
├── tests/
│   ├── unit/
│   │   ├── test_chunker.py
│   │   ├── test_embeddings.py
│   │   ├── test_vector_store.py
│   │   ├── test_indexing_service.py
│   │   ├── test_plan_feature.py
│   │   └── test_analyze_bug.py
│   └── integration/
│       ├── test_vectorization.py
│       └── test_indexing_governance.py
└── docs/
    └── adr/
        └── ADR-004-embedding-provider-interface.md
```

---

## 5. Critérios de Validação

| # | Critério | Método de Verificação |
|---|----------|----------------------|
| 1 | `uv run ruff check .` sem erros | Execução direta |
| 2 | `uv run ruff format --check .` sem reformatações | Execução direta |
| 3 | `uv run mypy src/` — Success em todos os source files | Execução direta |
| 4 | `uv run pytest` — todos passam, cobertura ≥ 80% | pytest-cov |
| 5 | Pipeline E2E: documento APPROVED → chunked → embedded → searchable | Teste integração |
| 6 | `search_context` retorna resultados reais (não mock) com DB | Teste automatizado |
| 7 | `plan_feature` e `analyze_bug` registradas e funcionais | Teste automatizado |
| 8 | Fallback gracioso quando DB/embedding provider indisponível | Teste automatizado |
| 9 | Migration v5 cria extensão pgvector sem erro | Teste integração |
| 10 | Migration v6–v7 cria tabela chunks + índice HNSW | Teste integração |

---

## 6. Novas Dependências

| Pacote | Tipo | Uso |
|--------|------|-----|
| `openai>=1.0` | Core dependency | API de embeddings OpenAI (text-embedding-3-small) |
| `sentence-transformers>=2.0` | Optional (`local-embeddings`) | Embeddings locais sem API externa |
| `numpy>=1.26` | Core dependency | Operações com vetores de embeddings |

---

## 7. Decisões Arquiteturais

| Decisão | Justificativa |
|---------|---------------|
| Interface abstrata `EmbeddingProvider` | Desacopla providers, permite troca sem alterar código consumidor |
| Chunking semântico por seções Markdown | Preserva hierarquia semântica; `section_path` como metadata de filtragem |
| Índice HNSW sobre ivfflat | Melhor performance de busca sem necessidade de treinamento; bom para volume moderado |
| Dimensão do vetor dinâmica | Cada provider declara `dimension`; schema sem dimensão fixa permite flexibilidade |
| Hook via callback na GovernanceService | Acoplamento baixo; IndexingService registra callback sem dependência direta |
| Factory `create_embedding_provider()` | Seleção de provider via configuração (env var), não hardcode |
| Fallback gracioso em search_context | Se DB ou embedder indisponível, retorna erro informativo ao invés de crash |

---

## 8. Riscos da Fase

| Risco | Mitigação |
|-------|-----------|
| OpenAI API indisponível ou com custo | Provider local (Sentence Transformers) como alternativa; testes com mock |
| Sentence Transformers pesado (~400MB) | Dependência opcional; não bloqueio para rodar servidor |
| Dimensões incompatíveis entre providers | Cada provider declara `dimension`; VectorStore valida consistência |
| Performance de chunking em docs grandes | Limite de 2000 chars/chunk; subdivisão por parágrafos |
| HNSW index lento para indexar muitos docs | Volume esperado é moderado; se crescer, avaliar ivfflat |
| Type codec vector no asyncpg | ADR-003 já prevê; implementar com `set_type_codec` |

---

## 9. Observações

- O `search_context` deve manter **backward compatibility** na assinatura (query, filters, limit, similarity_threshold)
- `plan_feature` e `analyze_bug` foram adiados da Fase 2 por dependência no workflow context e vectorization
- O pipeline de indexação é **event-driven**: só reage a transições de status na GovernanceService
- Testes unitários usam mocks para embedding APIs e DatabaseManager; testes de integração requerem Docker
