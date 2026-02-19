# Segurança — Atlas MCP

## Reportando Vulnerabilidades

Se você descobrir uma vulnerabilidade de segurança neste projeto, por favor **não abra uma issue pública**.

Em vez disso, envie um e-mail para: **jhowworks.ti@gmail.com**

### O que incluir no relatório

- Descrição da vulnerabilidade
- Passos para reproduzir
- Impacto potencial
- Sugestão de correção (se houver)

### Tempo de Resposta

- **Confirmação de recebimento:** até 48 horas
- **Avaliação inicial:** até 7 dias
- **Correção:** será tratada com prioridade máxima

### Política de Divulgação

Seguimos a prática de **divulgação responsável**:

1. O reporter é notificado quando a correção está pronta
2. A correção é publicada antes da divulgação pública
3. O reporter recebe crédito na release notes (se desejar)

## Versões Suportadas

| Versão | Suportada |
|--------|-----------|
| 0.x.x  | ✅ (atual) |

## Boas Práticas

Este projeto segue as seguintes práticas de segurança:

- Dependências auditadas regularmente via Dependabot
- Análise estática com Ruff (regras de segurança Bandit/S)
- Type checking estrito com mypy
- CI automatizado com validação em cada PR
