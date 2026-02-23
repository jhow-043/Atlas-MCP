# ADR-004 — Interface Abstrata de Embedding Provider

## Status

APPROVED

## Contexto

O Atlas MCP precisa gerar embeddings vetoriais para indexar documentos e realizar busca semântica (RAG). Existem diferentes provedores de embeddings com trade-offs distintos:

- **OpenAI API** (`text-embedding-3-small`): alta qualidade, requer API key, custo por token, baixa latência
- **Sentence Transformers** (`all-MiniLM-L6-v2`): gratuito, roda local, sem dependência externa, modelo ~80MB, mais lento

O sistema precisa suportar ambos os provedores sem acoplamento direto, permitindo troca via configuração.

## Decisão

Criar uma **interface abstrata `EmbeddingProvider`** (ABC) com método `embed()` e `embed_batch()`, e uma **factory `create_embedding_provider()`** para instanciação via configuração.

Implementações concretas:

1. `OpenAIEmbeddingProvider` — usa `openai` SDK, modelo `text-embedding-3-small` (1536 dimensões)
2. `SentenceTransformerEmbeddingProvider` — usa `sentence-transformers`, modelo configurável (384 dimensões default)

Cada provider declara sua `dimension` como property, permitindo que o `VectorStore` valide consistência.

## Consequências

### Positivas

- Desacoplamento: código consumidor depende apenas da interface, não do provider concreto
- Flexibilidade: troca de provider via variável de ambiente (`EMBEDDING_PROVIDER`)
- Testabilidade: fácil criar mock da interface para testes unitários
- Extensibilidade: novos providers (Cohere, Gemini, etc.) sem alterar código existente

### Negativas

- Dimensões diferentes entre providers requerem atenção ao trocar (reindexação necessária)
- Dependência `openai` adicionada ao core; `sentence-transformers` como optional
- Overhead de abstração para um sistema com poucos providers iniciais

## Alternativas Consideradas

1. **Hardcode com OpenAI apenas** — Rejeitado: sem flexibilidade, dependência de API externa obrigatória
2. **Uso de LangChain embeddings** — Rejeitado: dependência pesada demais para um wrapper simples
3. **Custom HTTP client** — Rejeitado: reimplementa o que os SDKs já fornecem

## Tags

`vectorization`, `embeddings`, `architecture`, `P3-D3`
