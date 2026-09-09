# O que mudou da versão do grupo para a versão vigente

Comparação entre [`versao-do-grupo-2026-09-08.md`](versao-do-grupo-2026-09-08.md)
(arquivo histórico) e [`SIT-v0-descricao-informal.md`](SIT-v0-descricao-informal.md)
(documento vigente da entrega).

O objetivo aqui é **discutir as mudanças com a equipe**, não impô-las. Cada linha traz o
motivo, para que a decisão seja do grupo.

---

## A mudança de fundo

O material corrompido das slides da disciplina (`docs/disciplina/TI0179-intro-slides.pdf`,
que estava no repositório com 2 bytes) foi recuperado, e ele muda o enquadramento:

1. **A professora já usa irrigação inteligente como o caso de estudo da disciplina** —
   inclusive com ESP32, BME280 e bomba peristáltica desenhados nos slides. O projeto não
   precisa se justificar como ideia; precisa se justificar como **engenharia**.
2. As slides definem **seis fases** e os marcos **M1–M6**. A **Fase 3 é "Virtual IoT"**:
   `dataset histórico → sensor virtual → pipeline MQTT real`. É um entregável esperado e
   estava **completamente ausente** da versão do grupo.
3. As slides dizem, textualmente: *"Do not simply maximize accuracy. The critical
   engineering question is: what kind of model is mathematically and computationally
   appropriate for eventual deployment on a constrained IoT device?"* Isso transforma a
   restrição de borda em **requisito**, não em detalhe de implementação.

---

## Mudanças ponto a ponto

| # | Versão do grupo | Problema | Versão vigente |
| :-: | :-- | :-- | :-- |
| 1 | Título "SIT - Sistema \IoT de Irrigação Inteligente de Tomates" | Erro de digitação (`\IoT`) no título do documento | "SIT — Sistema IoT de Irrigação Inteligente para Cultivo de Tomate" |
| 2 | Integrantes listados sem cargo | O template do professor pede "Nomes dos Integrantes **e Cargos**" | Tabela de integrante × frente conduzida, com nota de que as frentes não são exclusivas |
| 3 | Glossário com 3 termos (IoT, MQTT, Broker) | Não cobre nenhum termo agronômico nem de IC — e o documento inteiro depende deles | 17 termos, incluindo IC, QoS, Edge, sensor virtual, VWC, capacidade de campo, PMP, AFD, ETc, GDD, TinyML, baseline |
| 4 | Introdução: "estratégias fixas podem não considerar as condições reais" | Descreve o problema, mas não diz **por que precisa de IC**. Um limiar fixo já resolveria o que está escrito | Distingue automação **reativa** (limiar) de decisão **preditiva**, e mostra por que a segunda exige um modelo. Acrescenta a sensibilidade específica do tomateiro (podridão apical, rachadura) |
| 5 | Não declarava a pergunta de pesquisa | As slides formulam a pergunta explicitamente; deixá-la de fora perde alinhamento | Pergunta de engenharia em destaque, na formulação da disciplina |
| 6 | Não havia critério de sucesso | Sem critério, qualquer resultado "passa" | Critério triplo: menos água **+** sem perda de conforto hídrico **+** modelo que cabe no ESP32 |
| 7 | Sem o IoT Virtual | É a Fase 3 da disciplina | Sensor virtual como frente de desenvolvimento e como RF07 |
| 8 | "poderá ser integrada à disciplina de **Redes** IoT" | A integração é com **PI4 / Inteligência Computacional** | Seção 2.2 descreve o recorte de cada disciplina e o contrato MQTT como interface entre elas |
| 9 | Tabela "Aplicativos semelhantes" comparando com os **autores do dataset** | Belli, Galaverni e Oddi não são aplicações concorrentes — são a fonte dos dados. Faltavam comparáveis de verdade | 6 comparáveis, incluindo controladores comerciais (Rain Bird, Hunter, Netro) e projetos abertos genéricos de ESP32 |
| 10 | Diferencial declarado: *"usa apenas um canteiro/vaso e dois sensores obrigatórios"* | **Isso é uma limitação apresentada como vantagem.** É o tipo de frase que a banca questiona | Diferenciais reais: decisão adaptativa, medição do volume, comparação contra baseline, restrição de borda, sensor virtual, sistema aberto |
| 11 | Diferencial: *"a IA será opcional e posterior à regra determinística"* | Em uma disciplina de Inteligência Computacional, declarar a IA como opcional enfraquece o projeto | A IA é o componente que define o comportamento do sistema; o limiar é o **baseline a superar** |
| 12 | 8 requisitos funcionais | Faltavam: medição de volume, sensor virtual, modelo de IC, estimativa de lâmina, modo de operação, operação sem rede, comparação de estratégias, detecção de anomalia | 22 RFs, cada um com prioridade (E/I/D) e **entrega alvo** (v1–v4) |
| 13 | Nenhum requisito de medir a água aplicada | Sem hidrômetro ou bomba calibrada, "economia de água" é afirmação sem evidência. Era a lacuna mais grave | RF04 (essencial) + métrica de volume na seção 5.5 |
| 14 | 6 requisitos não funcionais sem número | RNF06 dizia *"em intervalos regulares, definidos pela equipe"* — isso não é um requisito, é adiar a decisão | 21 RNFs mensuráveis: ≤ 100 kB e ≤ 100 ms no ESP32, desligamento em 60 s, latência < 5 s, custo < R$ 400, amostragem 1 min / 10 min |
| 15 | Arquitetura em um parágrafo, sem figura | O template pede **figura** de alto nível com distribuição de funções por módulos | Figura 1 gerada por script + quatro camadas descritas + contrato de tópicos MQTT + exemplo de payload + tabela de materiais com custo |
| 16 | "O microcontrolador realizará a decisão local" | Estava certo, mas não estava justificado nem virava requisito | Elevado a decisão de projeto: a planta não pode depender de conectividade (RNF07, RF18) |
| 17 | Sem escopo, premissas ou restrições | Sem fronteira declarada, o escopo cresce sozinho até não caber no semestre | Seção 5.3, incluindo a limitação assumida: o ciclo do tomateiro é maior que o semestre, então não haverá validação de produtividade |
| 18 | Sem formulação do problema de IC | É a Fase 2 e o núcleo da disciplina de PI4 | Seção 5.4: previsão de umidade em horizonte curto, com o motivo de não usar classificação direta (o rótulo do dataset reflete a política do testbed, não a necessidade da planta) |
| 19 | Sem métricas | — | Seção 5.5, com critério de sucesso por dimensão |
| 20 | Sem plano de entregas | O grupo mencionava "critérios de aceitação para cada entrega" na tabela de comparação, mas eles não existiam | Seção 5.6, mapeando v0–v4 às fases e marcos M1–M6 |
| 21 | Sem riscos | — | Seção 5.7, com 7 riscos e mitigação — incluindo o risco de o modelo não transferir do solo do testbed para o substrato do vaso |
| 22 | 1 referência | — | 13 referências, com nota indicando quais precisam ter autores, volume, páginas e DOI conferidos antes do relatório final |
| 23 | Texto quase todo em **negrito** | Negrito em tudo é negrito em nada, e vinha de artefato de colagem | Negrito só onde há ênfase real |

---

## O que foi mantido da versão do grupo

Nem tudo mudou, e o que estava bom continua:

- O **nome e a sigla SIT**.
- A **escolha do tema e do dataset** (testbed de tomate de Parma) — está correta e é forte.
- O **público-alvo** (pequeno e médio produtor de hortaliças), apenas estratificado em
  primário, secundário e terciário.
- A **decisão local no microcontrolador** — o instinto estava certo, faltava justificar.
- O **MQTT** como protocolo.
- O **ciclo medir → decidir → atuar → nova medição**, que já estava na descrição da
  aplicação e virou o eixo do documento.

---

## Pontos que a equipe precisa fechar

1. **Confirmar as frentes de cada integrante** (tabela da capa) — foram propostas, não
   acordadas.
2. **Conferir as referências 3 a 8 e 10**, que estão sem dados bibliográficos completos.
3. **Decidir entre sensor de vazão YF-S401 e bomba peristáltica calibrada** para medir o
   volume — as duas atendem ao RF04, com custos e precisões diferentes.
4. **Rebaixar os dois PDFs corrompidos** listados em [`../../README.md`](../../README.md).
