# Entrega v0 — Descrição da aplicação (09/09/2026)

Vale 20% da nota. Corresponde à **Fase 1 / marco M1** da disciplina: definir o problema,
o dataset e a hipótese inicial.

## Arquivos

| Arquivo | O que é |
| :-- | :-- |
| [`SIT-v0-descricao-informal.md`](SIT-v0-descricao-informal.md) | **Fonte da verdade.** É este arquivo que se edita. |
| `SIT-v0-descricao-informal.docx` | **Gerado** a partir do `.md`. É o que se entrega e se cola no Google Docs. Não editar à mão — a próxima geração sobrescreve. |
| [`comparacao-versoes.md`](comparacao-versoes.md) | O que mudou em relação à versão do grupo, e por quê. Base para a discussão em equipe. |
| [`versao-do-grupo-2026-09-08.md`](versao-do-grupo-2026-09-08.md) | **Arquivo histórico.** Transcrição do Google Docs do grupo antes da reescrita. Não editar. |
| `google-doc-do-grupo.url` | Atalho para o Google Docs compartilhado (intacto, não foi alterado). |
| `figuras/arquitetura-sit.png` | **Gerada** por `tools/gerar_figura_arquitetura.py`. É a Figura 1 do documento vigente. |
| `figuras/versao-do-grupo/` | **Arquivo histórico.** Figura de arquitetura extraída do Google Docs do grupo. Não é usada no documento vigente. |
| `../../assets/brasao-ufc.png` | Brasão da UFC da capa, extraído do template do professor. Compartilhado por todas as entregas. |

## Regerar os artefatos

```bash
python tools/gerar_figura_arquitetura.py
python tools/md2docx.py docs/entregas/v0-descricao-da-aplicacao/SIT-v0-descricao-informal.md
```

## Pendências antes de entregar

- [ ] Completar os dados bibliográficos das referências 3 a 8 e 10.
- [ ] Decidir entre sensor de vazão YF-S401 e bomba peristáltica calibrada (RF04).
- [ ] Colar o conteúdo no Google Docs do grupo (ou anexar o `.docx`), conforme combinado.
