# SIT v1: contrato de integração

> **ATUALIZAÇÃO 13/10 21:20, vale sobre as seções 4 a 6.**
>
> **Firmware gravado.** O firmware que está na placa é o `codes/firmware/sit_estacao/sit_estacao.ino` atual, sem mudanças de protocolo:
> - MQTT público `broker.hivemq.com:1883`, tópicos `sit/ufc-pi4/estacao01/{leituras,status,bomba/cmd,bomba/estado}`.
> - O mesmo JSON de leitura sai pelo Serial USB: `{"ts":..,"solo_bruto":..,"solo_pct":..,"temp_c":..,"umid_ar_pct":..,"rssi":..}`, sem o campo "tipo".
> - A bomba imprime `Bomba LIGADA por N s` / `Bomba desligada`.
> - Comando: o número de segundos, em `bomba/cmd` ou no Serial.
> - Leitura a cada 30 s.
>
> **Redundância.** A estação manda os dados por Wi-Fi (MQTT) **e** pelo cabo USB (Serial).
>
> **Dashboard.**
> - O principal é uma página web própria, `codes/dashboard/`, que recebe os dados de duas fontes, à escolha:
>   - MQTT via WebSocket seguro do HiveMQ (`wss://broker.hivemq.com:8884/mqtt`);
>   - USB via Web Serial do Chrome.
> - O ThingsBoard fica opcional, para depois.
>
> **Coleta.**
> - O `codes/coleta/coletor_serial.py` está rodando agora e grava `outputs/coleta/leituras.csv` e `eventos.csv`.
> - Hardware testado: AM2302 no GPIO5, solo no GPIO4 e bomba no GPIO6 funcionando.
> - Às 21:15 e às 21:17 houve regas de 3 s. A bomba encheu demais o vaso; a próxima rega será de 1 s.
> - Todo acionamento da bomba faz a ESP reiniciar uns 15 s depois (reset TG0WDT, provável ruído na USB nativa). A bomba desliga antes e a coleta continua.

Fonte única de verdade para firmware, ThingsBoard, coleta, montagem, renders e slides da entrega v1.
Se algo aqui precisar mudar, avise o orquestrador e os agentes afetados antes de mudar o código.

## 1. Projeto

- **SIT, Sistema IoT de Irrigação Inteligente para Cultivo de Tomate** (UFC, TI0179 Internet das Coisas + PI4).
- **Entrega v1: 14/10/2026 (amanhã).** Pede coleta de dados, MQTT, gráficos e dashboard numa plataforma IoT.
  A plataforma preferida é o ThingsBoard, porque a monitora usa e sabe explicar. Outra plataforma vale se tiver MQTT, dashboard e uma interface boa.
- Equipe: Alisson Jaime Sales Barros, Gabriel Vaz de Oliveira, José Ferreira Lessa, Matheus Rocha Gomes da Silva.
- **Ainda não há sementes.** O plantio do tomateiro vem depois, então a v1 coleta dados do solo (vaso com terra, sem planta) e do ar.
  Limiares do tomateiro entram como **valores iniciais configuráveis**, a calibrar quando plantarmos.
- Visão de longo prazo (v2/v3): análise dos datasets de tomateiro (testbed de Parma, já explorado em EDA01/EDA02),
  modelo leve que caiba no ESP32 (TinyML) decidindo a irrigação, e atuação automática.

## 2. Hardware (fixo; as peças já estão sendo impressas)

| Item | Modelo | Ligação |
|---|---|---|
| Microcontrolador | ESP32-S3 DevKit (estilo DevKitC-1) | USB do notebook (5 V). Serial na porta COM/UART |
| Umidade do solo | capacitivo v2.0 | VCC 3V3, GND, AOUT → **GPIO4** (ADC1_CH3; o ADC2 não funciona com Wi-Fi) |
| Temperatura e umidade do ar | AM2302 (DHT22, pull-up interno) | vermelho 3V3, preto GND, amarelo → **GPIO5** |
| Bomba | mini bomba submersa JT100, 5 V, 130-220 mA, 1-1,5 L/min, mangueira 5 mm de diâmetro externo | vermelho → pino 5V, preto → coletor |
| Chave da bomba | **MPSA42** (marcação "A42", TO-92, pinagem **E-B-C** com a face reta para a frente) + **1 kΩ** + **1N4007** | base ← 1 kΩ ← **GPIO6**; emissor → GND; coletor → preto da bomba; diodo em antiparalelo com a bomba (listra no 5V, outra ponta no coletor) |

Notas:
- O MPSA42 é de alta tensão e ganho baixo (hFE mín. 40 a 10-30 mA). Com 1 kΩ (IB ≈ 2,5 mA) ele não satura a 130-220 mA, então a bomba
  recebe menos que 5 V e gira mais fraca. Serve para a demo. Melhora com 470 Ω ou trocando por BC337, TIP120 ou MOSFET logic-level.
- O orçamento de energia é a USB do notebook: ESP32-S3 com Wi-Fi (picos de ~300 mA) mais a bomba. Se a ESP reiniciar ao ligar a bomba (brownout), usar uma porta USB 3.
- Rede: **Wi-Fi 2,4 GHz** (o ESP32-S3 não usa 5 GHz). No campus, usar o roteador do celular em 2,4 GHz. Eduroam (WPA2-Enterprise) fora do escopo.
- Notebook: alimenta a estação, roda o coletor serial (backup offline) e mostra o dashboard na apresentação.

## 3. Peças impressas (PETG **amarelo**; `codes/modelo3d/pecas.py`, STL em `outputs/modelo3d/`)

**NÃO alterar `pecas.py` nem os STL: as peças já estão imprimindo.** Geometria (mm), origem no canto da caixa:

- `caixa_base`: x 0..173,8 · y 0..88,8 · z 0..42. Rabos de andorinha salientes na face y=0, indo até y=-4.
  - Rasgo da USB na face x=0, centrado em y=44,4, aberto de z=12 até o topo, com 16 de largura.
  - Três rasgos de cabo (8 de largura, de z=28 ao topo) na face x=173,8, em y≈17,8 / 44,4 / 71,0.
  - Dentro, a protoboard 165×80 fica no fundo, com a ESP32 na ponta x=0 (USB virada para o rasgo).
  - Transistor, resistor e diodo ficam na ponta x≈170, perto dos rasgos de cabo.
- `caixa_tampa`: impressa com a aba para cima; na montagem vira, com a placa em z 42..44 e a aba entrando na caixa.
  - O AM2302 (≈59×27) vai por cima, perto de x=12..72, centrado em y=44,4, preso com 2 abraçadeiras.
  - O cabo entra pelo furo em x≈77,7. A ventilação fica na outra metade.
- `reservatorio` (~540 mL): mesma largura em x e 88,4 de profundidade. Encaixa pelos rabos de andorinha na face y=0 da caixa e ocupa y -88,4..0, z 0..42.
  - A bomba fica no fundo, perto da ponta x≈150.
  - Mangueira e fio da bomba saem por cima, nessa ponta. Sem tampa: a `reservatorio_tampa` **não será usada**.
- `coroa_vaso`: anel para vaso com boca de 100 mm de diâmetro externo. O vaso tem 10 cm de diâmetro e 8 cm de altura.
  - Impressa com a aba para baixo; na montagem **vira**: o lábio interno apoia na borda do vaso.
  - A guia da mangueira (furo de 5,5 mm) aponta para dentro do vaso.
  - O rasgo do lado oposto passa o cabo do sensor de solo.

## 4. Plataforma IoT: ThingsBoard (API de dispositivo via MQTT)

- `secrets.h`: `WIFI_SSID`, `WIFI_SENHA`, `TB_HOST`, `TB_PORTA` (1883), `TB_TOKEN` (access token do dispositivo).
  - Host configurável: um colega está criando a conta agora e ainda não se sabe qual servidor será usado.
  - O agente thingsboard confirma e documenta os hosts válidos.
- MQTT: client id livre, **usuário = TB_TOKEN**, senha vazia. QoS 0 na telemetria.
- Dispositivo: nome **`SIT-estacao01`**. Perfil de dispositivo: **`SIT Estacao Tomate`** (regras de alarme).

| Tópico | Sentido | Uso |
|---|---|---|
| `v1/devices/me/telemetry` | ESP → TB | telemetria (JSON plano) |
| `v1/devices/me/attributes` | ESP → TB | atributos de cliente, publicados ao conectar |
| `v1/devices/me/attributes` (assinado) | TB → ESP | mudanças de atributos compartilhados |
| `v1/devices/me/attributes/request/1` → `.../attributes/response/+` | ida e volta | busca os atributos compartilhados no boot |
| `v1/devices/me/rpc/request/+` → `v1/devices/me/rpc/response/{id}` | ida e volta | RPC do dashboard |

### 4.1 Telemetria (chaves exatas)

| Chave | Tipo | Quando |
|---|---|---|
| `solo_bruto` | int 0-4095 | a cada leitura |
| `solo_pct` | int 0-100 (relativo: 0 = no ar, 100 = na água) | a cada leitura |
| `temp_c` | float, 1 casa | a cada leitura (**omitir a chave** se o AM2302 falhar; nunca mandar null) |
| `umid_ar_pct` | float, 1 casa | idem |
| `rssi` | int dBm | a cada leitura |
| `bomba` | int 0/1 | a cada leitura e a cada mudança |
| `irrigacao_s` | int | quando a bomba liga (duração pedida, já limitada) |
| `origem` | string `rpc` / `auto` / `serial` | junto com `irrigacao_s` |

Intervalo de leitura padrão: **60 s**. Cada leitura do solo é a média de 20 amostras.
A hora vem do NTP; o TB usa a hora de chegada, e o `ts` em ms é opcional.

### 4.2 Atributos

- **Cliente** (ESP → TB, ao conectar): `fw_versao`, `placa`, `sensores`, `ip`, `mac`, `intervalo_leitura_s`, `solo_seco`, `solo_molhado`, `bomba_max_s`.
- **Compartilhados** (dashboard → ESP; o ESP aplica e confirma no Serial):

| Atributo | Padrão | Significado |
|---|---|---|
| `modo_auto` | `false` | irrigação automática ligada/desligada (desligada até haver planta) |
| `limiar_seco_pct` | 40 | abaixo disto, no modo auto, irriga uma dose |
| `dose_s` | 3 | segundos por irrigação (~50-75 mL) |
| `intervalo_min_irrigacao_min` | 30 | espera mínima entre irrigações automáticas (na demo dá para pôr 1-2) |
| `intervalo_leitura_s` | 60 | período de leitura (10-3600) |

### 4.3 RPC (métodos aceitos pelo firmware)

| Método | Params | Efeito | Resposta |
|---|---|---|---|
| `setValue` (apelidos `setPump`, `setState`) | `true` / `false` | true liga por `dose_s`; false desliga | estado atual (bool) |
| `getValue` (apelidos `getPump`, `getState`) | nenhum | | estado atual (bool) |
| `irrigar` | número de segundos, ou `{"segundos": N}` | liga N s | `{"ok":true,"segundos":N}` |
| `lerAgora` | nenhum | força uma leitura e a publica | `{"ok":true}` |

**Segurança do atuador (no firmware, independe do comando):** cada acionamento dura no máximo **5 s** (`BOMBA_MAX_S`).
O modo auto respeita `intervalo_min_irrigacao_min`. A bomba começa desligada no boot.

## 5. Serial USB (backup offline e coletor no notebook)

- 115200 baud. **Cada leitura** sai numa linha JSON:
  `{"tipo":"leitura","ts":1760300000,"solo_bruto":2210,"solo_pct":59,"temp_c":29.4,"umid_ar_pct":61.8,"rssi":-63,"bomba":0}`
  - `ts` = Unix em segundos, ou `null` sem NTP.
  - `temp_c` e `umid_ar_pct` saem `null` se o AM2302 falhar (no serial pode null; no TB omite).
- **Cada mudança da bomba** sai numa linha JSON: `{"tipo":"evento","ts":...,"bomba":"ligada","segundos":3,"origem":"rpc"}`. Ao desligar, `"bomba":"desligada"`.
- As outras linhas são texto livre e não começam com `{`.
- Comandos: `l` (lê agora), `N` (liga a bomba N s), `0` (desliga), `cal seco` e `cal molhado` (grava a calibração na NVS a partir da leitura atual), `status`.

## 6. CSV da coleta (schema que o `codes/coleta/graficos.py` já lê; não mudar)

- `outputs/coleta/leituras.csv`: `recebido_em,ts,solo_bruto,solo_pct,temp_c,umid_ar_pct,rssi`
- `outputs/coleta/eventos.csv`: `recebido_em,topico,valor`. Bomba: `topico` = `sit/ufc-pi4/estacao01/bomba/estado`, `valor` = `ligada`/`desligada`.
- Produtores: `codes/coleta/coletor_serial.py` (USB, novo) e `codes/thingsboard/exportar_thingsboard.py` (REST, novo).

## 7. Faixas do tomateiro (valores iniciais; o agente de slides valida com referências)

| Variável | Ideal | Alerta | Uso |
|---|---|---|---|
| Temperatura do ar | 20-30 °C | < 10 °C ou > 35 °C (pegamento de frutos cai acima de ~32 °C) | alarme no TB + cores no dashboard |
| Umidade do ar | 60-80 % | > 90 % (risco de doenças fúngicas) ou < 40 % | alarme no TB + cores |
| Umidade do solo (relativa) | 50-80 % | < 40 % (seco) / > 90 % (encharcado) | modo auto + alarme |

O sensor de solo é relativo (ar-água). A correspondência com a umidade volumétrica, ou com a capacidade de campo, sai da calibração no substrato depois do plantio.

## 8. Identidade visual (slides, renders, dashboard)

Amarelo do filamento. Paleta:

| Uso | Cor |
|---|---|
| Amarelo PETG | `#F5C400` |
| Amarelo escuro | `#C99700` |
| Tinta (texto escuro quente) | `#1E1B16` |
| Creme (fundo claro) | `#FBF6E6` |
| Tomate (acento) | `#D2452C` |
| Folha (acento) | `#2E7D32` |

Texto escuro sobre amarelo; nunca texto amarelo sobre fundo claro. Escrever em pt-BR e evitar travessão (—) no texto corrido.

## 9. Donos dos arquivos (cada agente escreve só no que é seu)

| Agente | Escreve em |
|---|---|
| hardware | `docs/v1/montagem.md`, `outputs/diagramas/**` |
| firmware | `codes/firmware/**` (preservar os valores existentes em `secrets.h`; só acrescentar chaves) |
| thingsboard | `codes/thingsboard/**`, `codes/coleta/coletor_serial.py`, `docs/v1/thingsboard.md`. `graficos.py` só com mudanças compatíveis |
| renders | `outputs/renders/**`, `codes/modelo3d/render/**` (novo; nunca `pecas.py`) |
| slides | o deck (artifact), `docs/v1/roteiro_apresentacao.md`, `docs/entrega_v1_secoes.md` (atualizar para ThingsBoard) |

Status de cada agente: `C:\Users\aliss\AppData\Local\Temp\claude\C--GitHub\6329b45b-7ba7-499b-bc02-fa057318124f\scratchpad\equipe\status_<agente>.md`.
Só o próprio agente escreve o seu; todos podem ler.

Regras:
- Nada de commit ou push.
- Nunca copiar segredos (senha do Wi-Fi, token) para outro arquivo ou saída.
- **Nunca inventar dados medidos.** Onde faltar medição, usar `[preencher]`. Dado simulado ou de replay vai rotulado como tal.
