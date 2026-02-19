# ADR-002: Uso de uv como Gerenciador de Pacotes

**Data:** 2026-02-19  
**Status:** APPROVED  
**Autor:** jhow-043  
**Tags:** tooling, gerenciador-de-pacotes, uv, infraestrutura

---

### Contexto

O projeto precisa de um gerenciador de pacotes Python confiável, rápido e com lockfile determinístico para garantir reprodutibilidade de ambientes.

As opções avaliadas foram `pip` + `pip-tools`, `poetry` e `uv`.

### Decisão

Adotar **uv** como gerenciador de pacotes e ambientes Python do projeto.

### Alternativas Consideradas

| Alternativa | Prós | Contras |
|-------------|------|---------|
| **pip + pip-tools** | Padrão da comunidade, amplamente suportado | Lento, sem gestão de ambientes, lockfile frágil |
| **Poetry** | Popular, lockfile robusto, gestão de ambientes | Lento em resolução, problemas com monorepos, overhead de configuração |
| **uv** | Extremamente rápido (10-100x vs pip), lockfile determinístico, gestão de ambientes, compatível com `pyproject.toml`, mantido pela Astral (mesmo time do Ruff) | Projeto relativamente novo, menor adoção |

### Consequências

**Positivas:**
- Instalação de dependências extremamente rápida (melhora DX e CI)
- Lockfile determinístico (`uv.lock`) garante reprodutibilidade
- Gestão integrada de ambientes virtuais e versões Python
- Compatível com padrões `pyproject.toml` (PEP 621)
- Sinergia com Ruff (mesmo ecossistema Astral)

**Negativas:**
- Projeto mais novo, menor base de conhecimento na comunidade
- Pode ter edge cases não cobertos com pacotes menos populares

**Riscos:**
- Descontinuação ou mudança de direção do projeto — mitigação baixa: o `uv` é mantido pela Astral (empresa bem financiada) e é compatível com `pip`, facilitando migração se necessário

---

### Referências

- [uv — Documentação oficial](https://docs.astral.sh/uv/)
- [Astral (mantenedora do uv e Ruff)](https://astral.sh/)
