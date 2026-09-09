# ARQUIVO — Versão do grupo (Google Docs), como estava em 08/09/2026

> **Este arquivo é um registro histórico. Não editar e não usar como fonte.**
>
> Transcrição fiel do Google Docs compartilhado do grupo
> (`docs/entregas/v0-descricao-da-aplicacao/google-doc-do-grupo.url`) no estado em que se
> encontrava em 08/09/2026, antes da reescrita.
>
> O documento vigente da entrega é
> [`SIT-v0-descricao-informal.md`](SIT-v0-descricao-informal.md). O Google Docs original
> **não foi alterado** — continua intacto no Drive.
>
> Guardado para que a equipe possa comparar as duas versões e discutir cada mudança. As
> diferenças e os motivos estão em [`comparacao-versoes.md`](comparacao-versoes.md).

---

UNIVERSIDADE FEDERAL DO CEARÁ
DEPARTAMENTO DE ENGENHARIA DE TELEINFORMÁTICA
ENGENHARIA DE COMPUTAÇÃO
INTERNET DAS COISAS

**Descrição Informal da Aplicação**

**SIT - Sistema \IoT de Irrigação Inteligente de Tomates**

*Alisson Jaime Sales*
*Gabriel Vaz de Oliveira*
*José Ferreira Lessa*
*Matheus Rocha Gomes da Silva*

## GLOSSÁRIO

| Termo | Definição |
| :-: | :-: |
| **IoT** | **Internet das Coisas. Integração de sensores, atuadores, comunicação e software para monitorar e agir sobre o mundo físico.** |
| **MQTT** | **Protocolo leve de mensagens baseado em publicação/assinatura, adequado para sistemas IoT.** |
| **Broker MQTT** | **Servidor responsável por receber e distribuir mensagens entre os dispositivos e a aplicação.** |

## HISTÓRICO DE REVISÕES

| Data | Versão | Descrição | Responsável |
| :-: | :-: | :-: | :-: |
| **07/09** | **0** | **Descrição inicial da aplicação, requisitos, arquitetura e plano das entregas.** | **Equipe completa** |

## INTRODUÇÃO

**A irrigação é um dos principais fatores para o desenvolvimento adequado de culturas agrícolas, porém estratégias baseadas em horários ou quantidades fixas de água podem não considerar as condições reais do solo e do ambiente. O projeto propõe o desenvolvimento de um sistema de irrigação inteligente para o cultivo de tomate, capaz de monitorar variáveis como umidade do solo e temperatura e utilizar essas informações para auxiliar na decisão de quando realizar a irrigação. Dessa forma, busca-se utilizar a água de maneira mais eficiente, mantendo condições adequadas para o desenvolvimento da planta.**

## DESCRIÇÃO DA APLICAÇÃO

**A aplicação consistirá em um sistema IoT de irrigação automatizada para uma planta de tomate. Sensores instalados no cultivo serão utilizados para monitorar principalmente a umidade do solo e a temperatura, além de outras variáveis ambientais que possam contribuir para a tomada de decisão. Os dados coletados serão processados pelo sistema para determinar a necessidade de irrigação, acionando uma bomba de água por meio de um dispositivo de controle, como relé ou transistor. O sistema deverá permitir o monitoramento das condições do cultivo e o acionamento automático da irrigação, formando um ciclo de medição, decisão, atuação e nova medição. A aplicação poderá ser integrada à disciplina de Redes IoT por meio da comunicação entre o dispositivo de aquisição e os demais componentes do sistema, utilizando protocolo de comunicação adequado, como MQTT.**

## PÚBLICO ALVO

**O sistema tem como público-alvo pequenos e médios produtores agrícolas, especialmente aqueles que cultivam hortaliças e buscam automatizar o processo de irrigação. A solução também pode ser aplicada em ambientes de cultivo de pequena escala, como hortas domésticas, escolares ou experimentais, nos quais seja desejável monitorar as condições do solo e reduzir o desperdício de água.**

## APLICATIVOS SEMELHANTES

**Tabela 01. Aplicativos semelhantes**

| Referência/Solução | O que faz | Diferencial do SIT |
| :-: | :-: | :-: |
| Belli et al. (2024/2025) — dataset e artigo sobre cultivo com regimes diferentes | Registra ambiente, solo, água e indicadores agronômicos em três linhas com 100%, 60% e 30% da recomendação Irriframe. | Usa apenas um canteiro/vaso e dois sensores obrigatórios; a decisão é local, com MQTT e componentes acessíveis. |
| Galaverni et al. (2025) — sistema IoT de análise de dados | Integra dados heterogêneos na plataforma Agriware e analisa a resposta de plantas a regimes de irrigação. | Prioriza um MVP didático, transparente e auditável; a IA será opcional e posterior à regra determinística. |
| Oddi et al. (2024/2026) — arquitetura e testbed evolutivo | Mostra coleta IoT, monitoramento, automação e comparação de políticas de irrigação ao longo de campanhas agrícolas. | Reduz a complexidade para uma zona, preserva o ciclo medir–decidir–atuar e documenta critérios de aceitação para cada entrega. |
| Smart agriculture / sistemas comerciais de irrigação | Automatizam horários ou irrigação por sensores, geralmente com aplicativo, nuvem e controladores proprietários. | Código, tópicos MQTT, dados e limiares serão documentados, permitindo reprodução e inspeção pela turma. |

## 5 DESCRIÇÃO DO SISTEMA

### 5.1 Requisitos da Aplicação

**A aplicação deverá fornecer serviços de monitoramento das condições do cultivo, processamento das informações coletadas pelos sensores e controle automatizado da irrigação. O sistema deverá receber dados dos sensores, avaliar a necessidade de fornecimento de água e acionar ou manter desligado o mecanismo de irrigação de acordo com a estratégia definida. Também deverá permitir o acompanhamento das principais variáveis do cultivo e dos eventos de irrigação realizados.**

#### 5.1.1 Requisitos Funcionais

**Tabela 02. Requisitos Funcionais da Aplicação**

| ID | Requisitos funcionais | Descrição |
| :-: | :-: | :-: |
| RF01 | Coletar umidade do solo | O sistema deverá medir periodicamente a umidade do solo |
| RF02 | Coletar a temperatura | O sistema deverá registrar a temperatura do ambiente e do solo |
| RF03 | Transmitir dados | O sistema deverá enviar as medições para o broker MQTT |
| RF04 | Decidir a irrigação | O sistema deverá comparar as métricas medidas com os limites configurados |
| RF05 | Acionar a bomba | O sistema deverá ligar e desligar a bomba automaticamente a partir da decisão |
| RF06 | Exibir informações | O usuário deverá visualizar a umidade, a temperatura e o estado da bomba |
| RF07 | Permitir controle manual | O usuário deverá conseguir ativar ou desativar a bomba manualmente |
| RF08 | Registrar eventos | O sistema deverá registrar medições, acionamentos e falhas |

#### 5.1.2 Requisitos Não-Funcionais

**Tabela 01. Requisitos Não-Funcionais da Aplicação**

| ID | Requisitos Não-Funcionais | Descrição |
| :-: | :-: | :-: |
| RNF01 | Segurança | O sistema deverá utilizar autenticação no broker MQTT |
| RNF02 | Confiabilidade | A bomba deverá ser desligada após o tempo máximo configurado |
| RNF03 | Tolerância a falhas | O sistema deverá tratar falhas de sensor e de comunicação |
| RNF04 | Usabilidade | O painel deverá apresentar as informações de forma clara |
| RNF05 | Manutenibilidade | Sensores, regras e atuadores deverão ser organizados de forma modular |
| RNF06 | Desempenho | As medições deverão ser realizadas em intervalos regulares, definidos pela equipe |

### 5.2 Descrição da arquitetura do sistema (pode mudar ao longo do tempo)

A arquitetura do sistema será composta por sensores de umidade do solo e temperatura, um microcontrolador IoT, um circuito de acionamento, uma bomba de água, um broker MQTT e um painel de monitoramento. O microcontrolador realizará a coleta das medições e a decisão local sobre a irrigação. Os dados também serão enviados ao broker MQTT para visualização e registro. O painel poderá enviar comandos manuais ao microcontrolador. Bibliotecas dos sensores, o protocolo MQTT e o broker serão componentes reutilizados, enquanto a lógica de decisão e a integração entre os módulos serão desenvolvidas pela equipe.

**Figura 1 – Arquitetura geral do sistema SIT.**
**Fonte: elaboração própria, com auxílio de ferramenta de inteligência artificial.**

## 6 REFERÊNCIAS OU BIBLIOGRAFIA

1. **Oddi, Giulia; Belli, Laura; Davoli, Luca; Preite, Luca; Galaverni, Martina; rodolfi, margherita; Ganino, Tommaso; Ferrari, Gianluigi (2026), "IoT Dataset from an Evolving Tomato Cultivation Testbed", Mendeley Data, V1, doi: 10.17632/h8sfcf9487.1**
