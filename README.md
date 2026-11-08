# SIT: Sistema IoT de Irrigação Inteligente para Cultivo de Tomate

Projeto de TI0179 (Internet das Coisas) + PI4, UFC. Equipe: Alisson Jaime Sales Barros, Gabriel Vaz de
Oliveira, José Ferreira Lessa e Matheus Rocha Gomes da Silva.

**Ideia:** uma estação com ESP32-S3 mede a umidade do solo e a temperatura e umidade do ar, aciona uma
bomba e envia tudo por MQTT (Wi-Fi) e USB para um dashboard próprio. Com os dados de um dataset público de
cultivo de tomate, vamos treinar um modelo que indique o **melhor momento de regar**.

## Situação

| Entrega | Foco | Estado |
|---|---|---|
| v1 (14/10) | estação, coleta, MQTT, dashboard, peças impressas | entregue (branch `entrega-v1`) |
| v2 (09/11) | análise de dados, IA, tomada de decisão e documentação cumulativa | notebooks de EDA e modelo prontos; falta a documentação |
| v3 | atuação automática (limiar, dose, intervalo mínimo entre regas) | previsto |

Marcos da disciplina: **M1** problema e dataset; **M2** exploração dos dados, baseline e primeiro modelo;
**M3** validação (avaliação experimental, análise de erros e escolha do modelo).

## Dados e modelo

- Dataset: *IoT Dataset from an Evolving Tomato Cultivation Testbed* (Parma, Itália), em
  `data/IoT Dataset from an Evolving Tomato Cultivation Te.zip`. Fonte:
  <https://data.mendeley.com/datasets/h8sfcf9487/2>. É a única base usada no projeto.
- Como a estação só terá sensor de solo e de ar (temperatura e umidade), a modelagem usa os anos de
  **2024 e 2025**, só da **linha 3**, a única irrigada por limiar de umidade do solo.
- A análise que justifica essas escolhas (qual sensor é de 15 e de 30 cm, fases de irrigação, chuva não registrada,
  escala para o sensor de 7 cm, clima de Parma contra Fortaleza) está em `notebooks/analise.ipynb`. Ela gera a tabela
  `data/processed/linha3_10min.csv`, usada na modelagem.
- Modelo (`notebooks/modelo.ipynb`, v2/M3): decide "regar agora" (liga a bomba). Alvo: uma rega começa na próxima hora.
  Compara dois limiares e cinco modelos, treinando em um ano e testando no outro. Fica com uma regressão logística de três entradas
  (índice de umidade `u`, VPD e VPD médio de 3 h), salva em `outputs/modelo/regar_logistica.json`.

## Estrutura

```
codes/
  firmware/     código da ESP32-S3 (sit_estacao é o principal; teste_sensores e diagnostico_pinos são de bancada)
  coleta/       coletores USB e MQTT que gravam CSV, e gráficos da coleta
  dashboard/    painel web (index.html) e simulador de dados de teste
  modelo3d/     modelo paramétrico das peças impressas (pecas.py) e renders
  eda_01/       EDA inicial: panorama de todos os CSVs do dataset (substituída por notebooks/analise.ipynb)
  eda_02/       EDA inicial: umidade do solo, irrigação e ambiente em 2025 (idem)
notebooks/      análise de dados (analise.ipynb) e modelagem (modelo.ipynb)
data/           dataset (zip), externo/ (chuva e clima ERA5 em CSV) e processed/ (tabela tratada da linha 3)
docs/
  v1/           especificação técnica, documentação, dashboard e roteiro da apresentação da v1
  referencias/  artigos (papers/) e links úteis
  relatorios/   relatórios das análises
  disciplina/   material da disciplina
  links/        atalhos para os documentos compartilhados do grupo
outputs/        resultados: coleta, eda01, eda02, modelo3d (STL e G-code) e renders
```

## Como usar

**Análises** (Python com pandas, numpy, matplotlib e jupyter):

1. Extrair o zip dentro de `data/`, de modo a ficar `data/IoT Dataset from an Evolving Tomato Cultivation Te/2025/…`.
   Os CSV extraídos não vão para o Git.
2. Abrir e rodar `notebooks/analise.ipynb` e depois `notebooks/modelo.ipynb`. O notebook baixa a chuva e o clima (reanálise ERA5, via Open-Meteo) na
   primeira execução e guarda em `data/externo/`; as execuções seguintes não precisam de internet.

**Estação:** copiar `codes/firmware/sit_estacao/secrets.example.h` para `secrets.h`, preencher o Wi-Fi
(2,4 GHz) e gravar `sit_estacao.ino` pela Arduino IDE (bibliotecas: DHT sensor library, Adafruit Unified
Sensor, PubSubClient).

**Coleta:** `python codes/coleta/coletor_serial.py` (USB) ou `coletor_mqtt.py` (precisa do `paho-mqtt`),
depois `python codes/coleta/graficos.py`.

**Dashboard:** abrir `codes/dashboard/index.html` no Chrome ou Edge. Detalhes em `docs/v1/dashboard.md`.

**Peças 3D:** `pip install manifold3d trimesh` e `python codes/modelo3d/pecas.py`.

Especificação completa do hardware, dos tópicos MQTT e do formato dos dados: `docs/v1/especificacao_tecnica.md`.
