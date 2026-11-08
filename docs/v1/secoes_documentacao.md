# SIT, entrega v1: seções novas da documentação

Texto para colar no documento cumulativo do grupo, depois da seção de arquitetura da v0.
Os números da coleta saem do `outputs/coleta/resumo.txt` e foram conferidos no `leituras.csv`.
O que ainda está entre colchetes depende de uma medição ou de um teste que não foi feito.

---

## 6 Implementação do protótipo (v1)

### 6.1 Hardware

| Componente | Modelo | Função | Ligação |
|---|---|---|---|
| Microcontrolador | ESP32-S3 DevKit | leitura dos sensores, Wi-Fi, cliente MQTT, saída serial e acionamento da bomba | USB-C do notebook (5 V), que também leva os dados pela serial |
| Sensor de umidade do solo | capacitivo v2.0 | umidade relativa do substrato | AOUT → GPIO4 (ADC1), 3V3 |
| Sensor de temperatura e umidade do ar | AM2302 (DHT22) | temperatura (°C) e umidade relativa (%) do ar | DATA → GPIO5, 3V3 |
| Atuador | mini bomba submersa JT100, 5 V, 130-220 mA, 1-1,5 L/min | irrigação | vermelho no 5V, preto no coletor do transistor |
| Chave da bomba | transistor NPN MPSA42 (TO-92, pinagem E-B-C) + resistor de 1 kΩ + diodo 1N4007 | liga a bomba a partir do GPIO6; o diodo, em antiparalelo com a bomba, absorve o pico de tensão no desligamento | base ← 1 kΩ ← GPIO6; emissor no GND; coletor no negativo da bomba |

O sensor de solo usa o ADC1 porque o ADC2 do ESP32 fica indisponível com o Wi-Fi ligado. O sensor
capacitivo foi escolhido no lugar do resistivo por não sofrer corrosão dos eletrodos em contato
contínuo com o solo úmido.

O MPSA42 foi o transistor disponível. Ele é de alta tensão e ganho baixo (hFE mínimo de 40 entre
10 e 30 mA): com 1 kΩ na base (IB ≈ 2,5 mA), conduz no pior caso cerca de 100 mA, menos que os
130-220 mA da bomba. O transistor não satura, a bomba recebe menos de 5 V e gira mais fraca. Serve
para a demonstração; a melhoria é um resistor de 470 Ω ou a troca por BC337, TIP120 ou um MOSFET
de nível lógico.

Invólucro impresso em 3D, em PETG amarelo, com quatro peças impressas sem suporte (cerca de 9 h 37 min
de impressão somadas, pela estimativa do fatiador): caixa da eletrônica (173,8 × 88,8 × 42 mm) com
tampa ventilada (o AM2302 fica por cima da tampa, fora do calor interno), reservatório de ~540 mL
acoplado à caixa por encaixe rabo de andorinha, com a bomba no fundo, e uma coroa que se apoia na boca
do vaso, guia a mangueira até o solo e passa o cabo do sensor. O modelo é paramétrico, em Python
(`codes/modelo3d/pecas.py`), e os STL ficam em `outputs/modelo3d/`.

### 6.2 Calibração do sensor de solo

A leitura do ADC (12 bits) é convertida para porcentagem por interpolação linear entre o sensor no ar
(0 %) e o sensor na água (100 %), limitada a 0-100 %:

| Condição | Valor bruto do ADC | Porcentagem |
|---|---|---|
| no ar | ~3560 (medido) | 0 % |
| na água | [preencher após medir; o firmware usa 1300, provisório] | 100 % |
| terra seca, antes das regas (13/10) | 2645 | 40 % |
| terra encharcada, depois das regas (13/10) | ~1490 | 91 % |

Cada leitura é a média de 20 amostras espaçadas de 10 ms, para reduzir o ruído do ADC. A porcentagem
é relativa (do ar à água) e não corresponde ao conteúdo volumétrico de água; a calibração específica
para o substrato, por pesagem de amostras, fica para depois do plantio.

### 6.3 Comunicação IoT (MQTT e USB)

A estação manda cada leitura por dois caminhos ao mesmo tempo:

- pelo Wi-Fi, publicando num broker MQTT (`broker.hivemq.com:8883`, com TLS; público, usado na fase de testes);
- pelo cabo USB, imprimindo o mesmo JSON na serial (115200 baud), lido no notebook pelo coletor
  `codes/coleta/coletor_serial.py`, que grava os CSV mesmo sem rede.

Essa redundância cabo/Wi-Fi garante os dados e a demonstração quando a rede falha.

| Tópico (`sit/ufc-pi4/estacao01/...`) | Sentido | Conteúdo |
|---|---|---|
| `leituras` | estação → assinantes | JSON a cada 30 s |
| `status` | estação → assinantes | `online` / `offline`, retido; `offline` é a *last will*, publicada pelo broker se a estação cair |
| `bomba/cmd` | dashboard → estação | segundos de irrigação (`1` liga por 1 s, `0` desliga) |
| `bomba/estado` | estação → assinantes | `ligada` / `desligada`, retido |

Exemplo do formato de uma mensagem em `leituras` (a mesma linha sai na serial):

```json
{"ts":1760300000,"solo_bruto":2210,"solo_pct":59,"temp_c":29.4,"umid_ar_pct":61.8,"rssi":-63}
```

`ts` é o horário Unix sincronizado por NTP (`a.st1.ntp.br`, fuso de Brasília); sem rede, ele sai
`null` e o coletor registra a hora de chegada no notebook (`recebido_em`). `rssi` é a intensidade do
sinal Wi-Fi recebido pela estação, usada para avaliar o enlace. Pela serial, a estação também aceita
os comandos `l` (lê agora) e um número N (liga a bomba por N s; `0` desliga).

Segurança do atuador: o firmware limita cada acionamento a 3 s (cerca de 50-75 mL na vazão nominal),
qualquer que seja a origem do comando, para que um comando errado não esvazie o reservatório nem
encharque o vaso. No boot, a bomba começa desligada.

### 6.4 Dashboard

O dashboard é uma página web própria (`codes/dashboard/index.html`), aberta no Chrome ou no Edge, que
recebe os dados de duas fontes, escolhidas na tela (detalhes em `docs/v1/dashboard.md`):

- MQTT pelo WebSocket do HiveMQ, pelo Wi-Fi: `wss://broker.hivemq.com:8884/mqtt`, com reserva em
  `ws://broker.hivemq.com:8000/mqtt` para redes que bloqueiam a 8884 (como a do notebook usado nos testes);
- USB pela Web Serial do Chrome (115200 baud), sem depender de rede;
- AUTO: usa o MQTT e, se ficar 90 s sem leitura ou a conexão cair, mostra a USB. É a redundância
  Wi-Fi + cabo.

Como o JSON é o mesmo nas duas fontes, a troca não muda a tela. Cada valor aparece com o estado (ideal,
atenção ou alerta) e o motivo, segundo as faixas da seção 6.6. O painel mostra ainda a estação
online/offline (tópico `status`, com last will), o RSSI, o estado da bomba com o botão de rega de 1 a
3 s (publica em `bomba/cmd` ou envia pela serial), gráficos da sessão com as faixas coloridas e as
regas marcadas, o histórico carregado dos CSV e o log das mensagens MQTT. A porta serial abre em um
programa por vez: com o coletor gravando pela USB, o dashboard usa o MQTT.

Figura 3: `outputs/renders/dashboard_preview.png`, visão geral do painel, e
`outputs/renders/dashboard_preview_mqtt.png`, log MQTT com o eco do comando. As duas capturas usam
**dados de teste** do `codes/dashboard/simulador_teste.py`, no tópico `sit/ufc-pi4/teste-dashboard`;
não são medições da estação.

### 6.5 Testes e coleta

Montagem: vaso de 10 cm de diâmetro por 8 cm de altura com terra (ainda sem planta), sensor de solo
inserido até a marca da placa, AM2302 sobre a tampa da caixa.

Procedimento: coleta contínua em 13/10/2026, das 21:11 às 22:14, com leitura a cada 30 s, gravada
pelo coletor serial. O Wi-Fi da estação ainda não estava configurado, então todos os dados vieram pela
USB (`ts` nulo e RSSI 0). O solo começou com a terra seca e recebeu duas regas pedidas de 3 s pela
bomba, às 21:15 e às 21:17, acionadas pelo notebook via serial. O log não registra o desligamento da
bomba antes dos reinícios da estação, então não é possível confirmar que ela parou em 3 s. A coleta
parou às 22:14, quando o notebook encerrou o coletor por falta de memória.

Resultados (de `outputs/coleta/resumo.txt`, conferidos no `leituras.csv`):

- Período de coleta: 13/10/2026, 21:11 a 22:14 (1,0 h)
- Leituras recebidas: 121 de 126 esperadas, perda de 4,0 %. As 5 perdas caem nas duas lacunas em volta
  das regas: a estação reiniciou pouco antes da primeira rega e depois de cada acionamento da bomba.
- Irrigações: 2 pela bomba (pedidas de 3 s cada), 0 manuais
- Falhas do AM2302: 0
- Faixas observadas: solo 40-91 % (média 88,6 %; bruto 1490-2645), temperatura 24,4-27,1 °C (média
  25,6 °C), umidade do ar 60,6-74,5 % (média 70,0 %), RSSI 0 (sem Wi-Fi)

Figura 1: `outputs/coleta/serie_temporal.png`, umidade do solo, temperatura e umidade do ar ao longo
da coleta, com as irrigações marcadas. Depois das duas regas, o solo foi de 40 % a 88 % em cerca de
3 min e ficou estável em 91 % até o fim: o vaso encharcou, e a dose passou a 1 s. Em 1 h não houve
secagem visível. Na segunda metade da coleta, a temperatura subiu de 24,4 para 27,1 °C e a umidade do
ar passou de cerca de 63 % para 73-74 %.

Figura 2: `outputs/coleta/comunicacao.png`, RSSI e intervalo entre mensagens recebidas. O RSSI ficou
em 0 porque não havia Wi-Fi; os títulos da figura falam em MQTT, mas nesta coleta as mensagens
chegaram pela serial. O intervalo ficou em 30 s, com duas exceções: cerca de 3 min entre 21:13 e
21:16 e 52 s às 21:17, as lacunas dos reinícios.

### 6.6 Faixas iniciais do tomateiro

Sem planta, as faixas entram como valores iniciais configuráveis, a ajustar por estágio depois do
plantio:

| Variável | Ideal | Alerta | Referência |
|---|---|---|---|
| Temperatura do ar | 20-30 °C | < 10 °C ou > 35 °C | ótimo de 18-25 °C na média diária (FAO); temperatura base de 10 °C (Belli et al., 2025); crítica de 35 °C no vegetativo, 30 °C na floração e 27 °C no pegamento (Martelli et al., 2024) |
| Umidade do ar | 60-80 % | > 90 % (risco de fungos) ou < 40 % | 60-85 % conforme o estágio (Kasera e Acharjee, 2024); os limites de alerta são valores iniciais do grupo |
| Umidade do solo (relativa) | 50-80 % | < 40 % (seco) ou > 90 % (encharcado) | irrigar antes de esgotar 40 % da água disponível (FAO-56, p = 0,40); correspondência a calibrar no substrato |

As faixas viram regras em três etapas: na v1, aparecem nos gráficos do dashboard; na v2, um alerta
dispara após 3 leituras seguidas fora da faixa (proposta); na v3, o modo automático irriga uma dose de
1 s quando o solo cai abaixo de 40 %, respeitando um intervalo mínimo entre regas.

### 6.7 Dificuldades e soluções

| Problema | Causa | Solução |
|---|---|---|
| ADC2 indisponível com Wi-Fi | o rádio Wi-Fi ocupa o ADC2 do ESP32 | sensor de solo no ADC1 (GPIO4) |
| Leituras trocadas ou vazias | fios dos sensores em GPIOs diferentes dos do firmware | sketch `diagnostico_pinos` e religação |
| Bomba mais fraca | o MPSA42 tem ganho baixo e não satura a 130-220 mA | serve para a demo; trocar por 470 Ω, BC337, TIP120 ou MOSFET |
| Vaso encharcado | regas pedidas de 3 s (≈ 50-75 mL na vazão nominal); o log não confirma que a bomba parou antes do reset | dose de 1 s; conferir se a bomba desliga no tempo |
| ESP reinicia ~15 s após ligar a bomba | reset por watchdog (TG0WDT), provável ruído na USB nativa | a coleta continua após o reset; solução em teste: [preencher] |

### 6.8 Próximos passos

- Plantio do tomateiro e calibração do sensor de solo no substrato.
- v2: análise dos dados coletados e das bases públicas de tomateiro já exploradas (EDA01/EDA02, testbed
  de Parma) e modelo leve de decisão de irrigação, quantizado para rodar no ESP32 (TinyML).
- v3: atuação automática, com limiar, dose e intervalo mínimo entre regas.
- Broker próprio com autenticação e TLS no lugar do broker público.
- Troca do MPSA42 por um MOSFET de nível lógico e solução definitiva para o reinício com a bomba.

### Referências desta seção

- Allen, R. G. et al. *Crop evapotranspiration.* FAO Irrigation and Drainage Paper 56. Roma: FAO, 1998.
- Belli, L. et al. Smart agriculture dataset in a tomato cultivation under different irrigation regimes. *Data in Brief*, v. 60, 111521, 2025.
- FAO. Crop Information: Tomato (Land and Water Division).
- Kasera, R. K.; Acharjee, T. A comprehensive IoT edge based smart irrigation system for tomato cultivation. *Internet of Things*, v. 28, 101356, 2024.
- Martelli, A. et al. Smart irrigation for management of processing tomato: a machine learning approach. *Irrigation Science*, 2024. doi:10.1007/s00271-024-00993-9.
