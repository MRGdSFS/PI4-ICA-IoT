# SIT: especificação técnica (v1)

Referência do que está implementado na estação, no firmware, na coleta e no dashboard. Em caso de
dúvida entre este texto e o código, vale o código (`codes/firmware/sit_estacao/sit_estacao.ino`).

## 1. Projeto

- **SIT, Sistema IoT de Irrigação Inteligente para Cultivo de Tomate** (UFC, TI0179 Internet das Coisas + PI4).
- Equipe: Alisson Jaime Sales Barros, Gabriel Vaz de Oliveira, José Ferreira Lessa, Matheus Rocha Gomes da Silva.
- Ainda não há planta. A v1 coleta dados do solo (vaso com terra) e do ar. As faixas do tomateiro entram
  como valores iniciais configuráveis, a calibrar após o plantio.
- O dashboard é próprio (`codes/dashboard/`). O ThingsBoard foi avaliado e descartado.
- Visão de longo prazo: modelo de decisão de irrigação treinado com o dataset público de tomateiro
  (testbed de Parma) e, depois, atuação automática. Ver o [README](../../README.md).

## 2. Hardware

| Item | Modelo | Ligação |
|---|---|---|
| Microcontrolador | ESP32-S3 DevKit | USB do notebook (5 V), que também leva a serial |
| Umidade do solo | capacitivo v2.0 | VCC 3V3, GND, AOUT → **GPIO4** (ADC1; o ADC2 não funciona com Wi-Fi) |
| Temperatura e umidade do ar | AM2302 (DHT22, pull-up interno) | vermelho 3V3, preto GND, amarelo → **GPIO5** |
| Bomba | mini bomba submersa JT100, 5 V, 130-220 mA, 1-1,5 L/min, mangueira de 5 mm | vermelho → pino 5V, preto → coletor do transistor |
| Chave da bomba | **MPSA42** (TO-92, pinagem E-B-C) + 1 kΩ + 1N4007 | base ← 1 kΩ ← **GPIO6**; emissor → GND; coletor → preto da bomba; diodo em antiparalelo com a bomba (listra no 5V, outra ponta no coletor) |

Notas:
- O MPSA42 é de alta tensão e ganho baixo (hFE mín. 40 a 10-30 mA). Com 1 kΩ (IB ≈ 2,5 mA) ele não satura a
  130-220 mA, então a bomba recebe menos de 5 V e gira mais fraca. Serve para a demonstração. Melhora com
  470 Ω ou trocando por BC337, TIP120 ou MOSFET de nível lógico.
- Orçamento de energia: tudo sai da USB do notebook (ESP32-S3 com Wi-Fi, picos de ~300 mA, mais a bomba).
  A ESP reinicia ~15 s depois de cada acionamento (reset TG0WDT, provável ruído na USB nativa); problema em aberto.
- Rede: Wi-Fi 2,4 GHz (o ESP32-S3 não usa 5 GHz). Eduroam (WPA2-Enterprise) fora do escopo; no campus, usar
  o roteador do celular.

## 3. Peças impressas

PETG amarelo, geradas por `codes/modelo3d/pecas.py` (paramétrico); STL e G-code em `outputs/modelo3d/`.
Medidas em mm, origem no canto da caixa.

- `caixa_base`: 173,8 × 88,8 × 42. Rabos de andorinha na face y=0. Rasgo da USB na face x=0 (16 de largura,
  de z=12 ao topo) e três rasgos de cabo (8 de largura) na face x=173,8. Protoboard 165×80 no fundo, com a
  ESP32 na ponta x=0; transistor, resistor e diodo na ponta x≈170.
- `caixa_tampa`: impressa com a aba para cima e virada na montagem. O AM2302 (≈59×27) vai por cima, preso com
  2 abraçadeiras; o cabo entra pelo furo em x≈77,7; a ventilação fica na outra metade.
- `reservatorio` (~540 mL): encaixa pelos rabos de andorinha na face y=0 da caixa. A bomba fica no fundo,
  perto da ponta x≈150; mangueira e fio saem por cima. Sem tampa.
- `coroa_vaso`: anel para vaso de 100 mm de diâmetro externo (vaso de 10 cm × 8 cm). Impressa com a aba
  para baixo e virada na montagem. Guia da mangueira (furo de 5,5 mm) e rasgo para o cabo do sensor de solo.
- `reservatorio_tampa`: gerada pelo script, mas **não é usada** na montagem.

## 4. Comunicação

A cada **30 s** a estação gera uma leitura (o solo é a média de 20 amostras do ADC) e a envia por dois
caminhos ao mesmo tempo: Wi-Fi (MQTT) e USB (serial).

### 4.1 MQTT

- Broker público `broker.hivemq.com`, **porta 8883 com TLS** (o firmware usa `setInsecure()`: criptografa
  sem validar o certificado). Dashboard por WebSocket: `wss://…:8884/mqtt`, com reserva em `ws://…:8000/mqtt`.
- Credenciais da rede em `codes/firmware/sit_estacao/secrets.h` (copiar de `secrets.example.h`; não vai
  para o Git).

| Tópico (`sit/ufc-pi4/estacao01/…`) | Sentido | Conteúdo |
|---|---|---|
| `leituras` | estação → assinantes | JSON a cada 30 s |
| `status` | estação → assinantes | `online` / `offline`, retido; `offline` é a *last will* |
| `bomba/cmd` | dashboard → estação | segundos de irrigação (`N` liga por N s; `0` desliga) |
| `bomba/estado` | estação → assinantes | `ligada` / `desligada`, retido |

### 4.2 Formato da leitura (MQTT e serial)

```json
{"ts":1760300000,"solo_bruto":2210,"solo_pct":59,"temp_c":29.4,"umid_ar_pct":61.8,"rssi":-63}
```

- `ts`: Unix em segundos (NTP, fuso de Brasília), ou `null` sem rede.
- `temp_c` e `umid_ar_pct`: `null` se o AM2302 falhar.
- `solo_pct`: relativo, 0 = sensor no ar, 100 = na água (ver seção 6).
- `rssi`: dBm do Wi-Fi (0 sem conexão).

### 4.3 Serial USB

- 115200 baud. Cada leitura sai como uma linha JSON (formato acima).
- A bomba imprime texto livre: `Bomba LIGADA por N s` e `Bomba desligada`. Outras linhas (boot, Wi-Fi, MQTT)
  também são texto e não começam com `{`.
- Comandos: `l` (lê agora) e `N` (liga a bomba por N s; `0` desliga).

### 4.4 Segurança do atuador

- Cada acionamento dura no máximo **3 s** (`BOMBA_MAX_MS`), qualquer que seja a origem do comando.
  Na prática, usar **1 s** por rega: 3 s encharcaram o vaso de 10 cm.
- O desligamento é feito por um temporizador de hardware (`esp_timer`), que atua mesmo se o loop travar.
- A bomba começa desligada no boot (o pino é zerado antes do `pinMode`).

## 5. Coleta e CSV

- `codes/coleta/coletor_serial.py` (USB, funciona sem Wi-Fi) e `codes/coleta/coletor_mqtt.py` (assina o
  broker) gravam no mesmo formato; `codes/coleta/graficos.py` gera gráficos e `resumo.txt` a partir deles.
- `outputs/coleta/leituras.csv`: `recebido_em,ts,solo_bruto,solo_pct,temp_c,umid_ar_pct,rssi`
- `outputs/coleta/eventos.csv`: `recebido_em,topico,valor` (bomba: `topico` = `…/bomba/estado`, `valor` = `ligada`/`desligada`)
- A porta serial abre em um programa por vez: com o coletor na USB, o dashboard usa o MQTT.

## 6. Calibração do sensor de solo

Interpolação linear entre o ar (`SOLO_SECO` = 3560, medido) e a água (`SOLO_MOLHADO` = 1300, **provisório,
ainda não medido**), limitada a 0-100 %. É uma escala relativa; a calibração no substrato, por pesagem, fica
para depois do plantio.

## 7. Faixas iniciais do tomateiro

| Variável | Ideal | Alerta |
|---|---|---|
| Temperatura do ar | 20-30 °C | < 10 °C ou > 35 °C |
| Umidade do ar | 60-80 % | > 90 % (fungos) ou < 40 % |
| Umidade do solo (relativa) | 50-80 % | < 40 % (seco) ou > 90 % (encharcado) |

Referências e justificativas em [secoes_documentacao.md](secoes_documentacao.md) (seção 6.6).

## 8. Identidade visual (dashboard, slides, renders)

Amarelo do filamento. Texto escuro sobre amarelo; nunca texto amarelo sobre fundo claro.

| Uso | Cor |
|---|---|
| Amarelo PETG | `#F5C400` |
| Amarelo escuro | `#C99700` |
| Tinta (texto escuro quente) | `#1E1B16` |
| Creme (fundo claro) | `#FBF6E6` |
| Tomate (acento) | `#D2452C` |
| Folha (acento) | `#2E7D32` |
