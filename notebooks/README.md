# Notebooks — Inteligência Computacional

Ordem prevista, alinhada às fases da disciplina:

| Notebook | Fase | Objetivo |
| :-- | :-: | :-- |
| `01-exploracao-dados.ipynb` | 1 | Carregar o testbed, inventariar sensores por temporada, reportar qualidade (faltantes, lacunas, valores fora de faixa) e visualizar as séries. |
| `02-preparacao-features.ipynb` | 2 | Alinhamento temporal, reamostragem, janelas móveis (1 h / 3 h / 24 h), codificação cíclica de hora e estação, tempo desde a última irrigação. |
| `03-baseline.ipynb` | 2 | Persistência (previsão ingênua) e limiar fixo. **Nenhum modelo é avaliado sem estes dois números na mesa.** |
| `04-modelos.ipynb` | 3 | Regressão regularizada, *gradient boosting*, rede leve. Divisão **temporal** por temporada. |
| `05-analise-erros.ipynb` | 3 | Onde o modelo erra: por estágio, por hora do dia, por regime. Custo assimétrico do falso negativo hídrico. |
| `06-export-borda.ipynb` | 6 | Quantização e exportação; medição de tamanho e latência sob a restrição de ≤ 100 kB e ≤ 100 ms. |

Regras: seed fixa, divisão treino/teste **temporal** (nunca aleatória — vaza informação
futura), e todo dado derivado gravado em `data/interim/` ou `data/processed/`.
