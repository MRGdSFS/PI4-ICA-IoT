# Documentação

| Pasta | Conteúdo |
| :-- | :-- |
| `disciplina/` | Material das disciplinas: slides de introdução (fases do projeto e marcos M1–M6) e o template oficial da descrição informal. |
| `entregas/` | Uma pasta por entrega. O `.md` é a fonte da verdade; o `.docx` é gerado por `tools/md2docx.py` e é o que se entrega. |
| `pesquisa/papers/` | Artigos de referência em PDF. |
| `pesquisa/notas/` | Notas de pesquisa, links e sensores candidatos. |

## Entregas

- **[v0 — Descrição da aplicação](entregas/v0-descricao-da-aplicacao/SIT-v0-descricao-informal.md)** (09/09) — problema, requisitos, arquitetura preliminar, dataset.
- v1 (14/10), v2 (11/11), v3 (25/11), v4 (07/12) — ver o calendário no [README](../README.md#entregas).

## Regenerar os artefatos

```bash
python tools/gerar_figura_arquitetura.py
python tools/md2docx.py docs/entregas/v0-descricao-da-aplicacao/SIT-v0-descricao-informal.md
```

## Referências recuperadas

Dois PDFs estavam corrompidos no repositório (2 bytes, danificados por conversão de fim de
linha antes do `.gitattributes` existir) e foram removidos. Precisam ser baixados de novo:

- *Hybrid Artificial Neural Network Activation Function to Reduce Water Wastage in Agricultural Irrigation*
- *Improved grey wolf optimization-based artificial neural network for irrigation need prediction*
