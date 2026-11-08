# SIT v1: painel web (dashboard)

Painel próprio da estação SIT, em `codes/dashboard/index.html`. É uma página só, sem instalação: recebe os dados por **MQTT (Wi-Fi)** ou pela **USB (cabo, Web Serial)**, mostra os valores atuais, os gráficos com as faixas do tomateiro, o histórico da coleta e o log das mensagens MQTT, e manda o comando de irrigação.

| Arquivo | O que é |
|---|---|
| `codes/dashboard/index.html` | o painel (HTML, CSS e JS num arquivo; carrega só o mqtt.js 5.10.1 e as fontes do Google por CDN) |
| `codes/dashboard/simulador_teste.py` | publica **dados de teste** num tópico separado, para ensaiar sem a estação |
| `outputs/renders/dashboard_preview.png` | print do painel com dados de teste (marcado "DADOS DE TESTE") |
| `outputs/renders/dashboard_preview_mqtt.png` | print do log de mensagens MQTT, também com dados de teste |

## 1. Como abrir

1. Dê dois cliques em `codes/dashboard/index.html`, ou arraste o arquivo para o **Chrome** ou o **Edge**. Precisa ser Chrome ou Edge no computador, porque o Firefox e o Safari não têm Web Serial.
2. O painel abre no modo **AUTO** e conecta sozinho ao broker. A fonte em uso fica destacada na barra "Fonte", com a etiqueta "EM USO", e o selo do topo mostra "AO VIVO".
3. No projetor, use `Ctrl +` para ampliar.

Se o Chrome bloquear algo por ser arquivo local, sirva a pasta: `python -m http.server 8765` dentro de `codes/dashboard` e abra `http://localhost:8765`.

Parâmetros opcionais na URL:
- `?base=sit/ufc-pi4/teste-dashboard`: outro tópico base (modo teste, com faixa preta "MODO TESTE").
- `?fonte=mqtt|usb|auto`: fonte inicial.
- `?broker=ws://broker.hivemq.com:8000/mqtt`: força um endereço de broker.

## 2. Fontes de dados

### Wi-Fi (MQTT)
- Broker público HiveMQ. O painel assina `sit/ufc-pi4/estacao01/#`: `leituras` (JSON a cada 30 s), `status` (online/offline, retido, com last will), `bomba/estado` (retido) e `bomba/cmd`.
- O painel tenta primeiro `wss://broker.hivemq.com:8884/mqtt`. Se não houver resposta em 8 s, cai sozinho para `ws://broker.hivemq.com:8000/mqtt` e lembra qual funcionou.
  - **Na rede de casa do notebook (13/10), as portas 1883 e 8884 estão bloqueadas** (testado também fora do sandbox) e a 8000 funciona.
  - O mesmo broker atende nas duas portas, então os dados são os mesmos.
- O botão "Desconectar" do canal MQTT derruba a conexão de propósito, útil para mostrar a redundância.

### Cabo (USB, Web Serial)
- Clique em "Conectar USB" (ou em "Cabo · USB") e escolha a porta da ESP32 (COM11 neste notebook), a 115200 baud.
- O painel lê as linhas JSON de leitura, as linhas `Bomba LIGADA por N s` / `Bomba desligada` e as mensagens de boot.
  - O boot aparece como "a ESP32 reiniciou", com o motivo, por exemplo `TG0WDT_SYS_RST`.
  - Linhas como "MQTT desconectado" e o Wi-Fi que falhou também viram aviso na tela.
- Se o cabo cair ou a ESP reiniciar, o painel tenta reabrir a porta a cada 3 s.
- **A porta COM só pode ser aberta por um programa de cada vez.** Se o `codes/coleta/coletor_serial.py` estiver rodando na COM11, o painel mostra "Porta ocupada". O mesmo vale para o Monitor Serial do Arduino. Escolha um dos dois:
  - **painel com a USB:** encerre o coletor (Ctrl+C). Para não perder dados, use "Ver tabela" e depois "Exportar leituras da sessão", que gera um CSV no mesmo formato do `leituras.csv`. Ao terminar, religue o coletor.
  - **coletor com a USB:** deixe o painel no MQTT e acompanhe o histórico pelo CSV (seção 3).
- Não abra o `leituras.csv` no Excel com o coletor rodando: o Excel trava o arquivo e o coletor para com erro.

### AUTO
- Usa o MQTT. Se o MQTT ficar **90 s sem leitura** (ou desconectar) e a USB estiver aberta, passa a mostrar a USB e avisa.
- Quando o MQTT volta a mandar leitura, retorna ao MQTT.
- A mesma leitura que chega pelos dois caminhos aparece uma vez só, com "via MQTT + USB".

## 3. O que a tela mostra

- **Valores atuais**:
  - umidade do solo (% relativo e valor bruto do ADC), temperatura e umidade do ar;
  - cada um com a régua colorida das faixas, a marca do valor atual e o status com ícone: ideal, atenção ou alerta;
  - a falha do AM2302 aparece como "falha no AM2302".
- **Estação**:
  - online/offline pelo tópico `status`;
  - "offline (last will)" quando o broker avisa que a estação caiu;
  - embaixo, o estado de cada canal (Wi-Fi/MQTT e Cabo/USB) e o horário do último reinício visto pela USB.
- **Sinal Wi-Fi (RSSI)** em dBm com barras e qualidade. O valor 0 significa estação sem Wi-Fi.
- **Bomba**:
  - estado (ligada/desligada, com contagem regressiva) e última rega;
  - campo de **1 a 3 s** e o botão **"Irrigar N s"**, que publica o número em `sit/ufc-pi4/estacao01/bomba/cmd` (QoS 0, sem retenção) ou envia pela serial, conforme a fonte;
  - "Parar" envia 0;
  - o painel avisa quando a estação confirma, pelo `bomba/estado` ou pela linha da USB, e também quando não confirma em 8 s;
  - o firmware limita cada acionamento a 3 s (na prática, use 1 s).
- **Gráficos**:
  - umidade do solo, temperatura, umidade do ar e RSSI, com as **faixas do tomateiro** (especificação técnica, seção 7) em verde (ideal), amarelo (atenção) e vermelho claro (alerta);
  - as regas aparecem como gota e linha vertical;
  - passe o mouse (ou use as setas do teclado) para ver o valor, a hora, o valor bruto e por onde chegou;
  - o intervalo vai de 15 min a "tudo";
  - "Ver tabela" mostra os números.
- **Histórico (CSV)**:
  - "Carregar CSV…" e escolha `outputs/coleta/leituras.csv` e `eventos.csv` juntos;
  - os gráficos passam a mostrar a coleta, com as regas do `eventos.csv`. Exemplo: as regas de 13/10 às 21:15 e 21:17;
  - "acompanhar arquivo" relê o CSV a cada 15 s, útil com o coletor rodando.
- **Mensagens MQTT recebidas**:
  - hora, tópico e payload de cada mensagem;
  - etiquetas de leitura, retida, bomba e "comando enviado por este painel".
  - É a prova visual do MQTT funcionando.
- **Linhas da USB**: o que a ESP32 imprime no cabo.

A sessão ao vivo fica guardada no navegador e sobrevive a um F5; o botão "Limpar sessão" fica na tabela.

## 4. Ensaio com dados de teste (sem a estação)

```
python codes/dashboard/simulador_teste.py --historico 60 --intervalo 5
```
Depois abra `codes/dashboard/index.html?base=sit/ufc-pi4/teste-dashboard`.

- O simulador publica **dados sintéticos**, no formato do firmware, só em `sit/ufc-pi4/teste-dashboard`. Ele se recusa a publicar no tópico real.
- Ele responde ao "Irrigar" como o firmware: `ligada` e, N s depois, `desligada`. A umidade simulada sobe a cada rega.
- O painel mostra a faixa "MODO TESTE · DADOS DE TESTE" o tempo todo.
- Ctrl+C encerra e publica "offline". `--limpar` apaga as mensagens retidas do tópico de teste.
- **Nunca** publique dados falsos nem comandos em `sit/ufc-pi4/estacao01`: o `bomba/cmd` real liga a bomba.

## 5. Antes da apresentação (checklist)

1. **Wi-Fi da estação**:
   - hoje o `secrets.h` está igual ao exemplo (SSID "nome-da-rede"), então a estação não entra no Wi-Fi e não publica no MQTT. O log serial mostra "falhou" e "MQTT desconectado";
   - pôr o SSID e a senha do hotspot do celular (2,4 GHz) e regravar (dono: firmware);
   - conferir no painel: canal MQTT conectado, estação "Online" e uma leitura a cada 30 s.
2. **Rede**:
   - a estação usa a porta 8883 (MQTT com TLS); redes de universidade e de casa às vezes bloqueiam as portas do broker. No hotspot do celular costuma passar;
   - teste antes: se o painel mostrar "Online" e leituras chegando, está ok.
3. Notebook com internet (hotspot ou rede do campus). O painel cai sozinho para a porta 8000 se a 8884 estiver bloqueada.
4. Abrir o painel uns minutos antes, para os gráficos da sessão já terem pontos. Deixar `leituras.csv` e `eventos.csv` à mão para o histórico.
5. Decidir quem fica com a COM11: o painel (recomendado durante a demo, para a redundância) ou o coletor.

## 6. Roteiro de demonstração (3 a 4 min)

1. **Visão geral:** painel aberto em AUTO. Mostrar a barra "Fonte", com o MQTT "EM USO" e a USB conectada, e o selo "AO VIVO".
2. **MQTT funcionando:**
   - no card "Mensagens MQTT recebidas", esperar uma leitura (a cada 30 s) e mostrar o tópico `sit/ufc-pi4/estacao01/leituras` com o JSON;
   - explicar `status`, que é retido e tem last will, e os tópicos da bomba.
3. **Dados e faixas do tomateiro:**
   - cartões e gráficos com ideal, atenção e alerta;
   - lembrar que o vaso ainda está sem planta e que os limiares são iniciais, a calibrar.
4. **Histórico:** "Carregar CSV…", escolher `leituras.csv` e `eventos.csv` e mostrar as duas regas de 3 s em 13/10, quando a umidade passou de ~40 % para ~90 %.
5. **Atuação (opcional, só se a equipe decidir):**
   - "Irrigar 1 s". O log mostra o comando enviado, `bomba/estado` ligada e depois desligada, e a gota aparece no gráfico;
   - o vaso já está úmido, então 1 s no máximo;
   - a ESP costuma reiniciar ~15 s depois de acionar a bomba (problema conhecido). O painel mostra o reinício, e o status pode passar por offline e voltar a online, o que serve para explicar o last will;
   - para não arriscar, faça esta parte no modo teste (seção 4).
6. **Redundância:**
   - clicar "Desconectar" no canal MQTT, que simula a queda do Wi-Fi. O AUTO passa na hora para a USB e os dados continuam;
   - clicar "Conectar" de novo.
   - Com mais tempo, desligar o hotspot: em ~20 s chega "offline (last will)" e, sem leitura por 90 s, o AUTO mostra a USB.
7. **Só Wi-Fi:** tirar o cabo do notebook e ligar a estação no powerbank. Ela reinicia, reconecta em ~30 s e o painel segue pelo MQTT; o canal USB fica "reconectando".

Plano B sem internet: modo "Cabo · USB". Os dados vêm pelo cabo e tudo funciona menos o MQTT; o painel avisa que a biblioteca MQTT não carregou.

## 7. Redundância

| Situação | Como fica |
|---|---|
| Wi-Fi + cabo | A estação manda o mesmo JSON pelo MQTT e pela USB. O AUTO usa o MQTT e, se ele parar, mostra a USB. O comando da bomba vai pelo canal em uso. |
| Só Wi-Fi (powerbank) | Estação longe do notebook, alimentada pelo powerbank. O painel recebe tudo pelo MQTT, inclusive em outro computador ou no celular (só o MQTT, porque Web Serial é só no computador). |
| Só cabo (sem internet) | Modo "Cabo · USB": dados e comando pela serial; histórico pelo CSV ou pela exportação da sessão. |

## 8. Problemas conhecidos e cuidados

- **Broker público:** qualquer pessoa pode ler e publicar nestes tópicos, inclusive em `bomba/cmd`. A trava de 3 s do firmware limita o estrago. Próximo passo: broker com usuário e senha (HiveMQ Cloud ou Mosquitto próprio).
- Depois de cada acionamento da bomba, a ESP reinicia (reset TG0WDT).
  - No `serial_bruto.log` de 13/10 não aparece a linha "Bomba desligada" entre o "Bomba LIGADA por 3 s" e o reinício.
  - Vale o firmware/hardware conferir se a bomba ficou ligada até o reset. Isso explicaria o vaso encharcado.
- Sem NTP (sem Wi-Fi) o `ts` vem `null`; aí o painel usa a hora de chegada, igual ao `graficos.py`.
- O `coletor_mqtt.py` usa a mesma porta do firmware (8883, TLS). Se a rede bloquear, use o `coletor_serial.py`.

## 9. O que foi testado (14/10, Chrome headless e paho-mqtt, só no tópico de teste)

- **Conexão:**
  - o painel abre como `file://` em contexto seguro, com Web Serial e seletor de arquivos disponíveis;
  - cai de `wss://…:8884` para `ws://…:8000` em ~10 s;
  - o único aviso no console é a falha esperada da 8884.
- **MQTT de ponta a ponta (simulador no tópico de teste):**
  - 78 de 78 leituras recebidas;
  - cartões iguais à última leitura publicada: solo % e bruto, temperatura, umidade e RSSI;
  - status online retido e, depois, offline;
  - "Irrigar 2 s" publicado em `sit/ufc-pi4/teste-dashboard/bomba/cmd`, com ligada e desligada, rega marcada no gráfico e o eco no log.
- **USB:** as 270 linhas reais do `serial_bruto.log` de 13/10 foram interpretadas sem abrir a porta:
  - 121 leituras;
  - "Bomba LIGADA por 3 s" seguida de reboot;
  - reset TG0WDT detectado;
  - estação sem Wi-Fi e MQTT desconectado.
- **Histórico:** cópias do `leituras.csv` (121 linhas) e do `eventos.csv` deram 121 pontos e 2 regas marcadas.
- **Layout:**
  - 1440 px e 390 px (celular) sem rolagem horizontal;
  - JS validado com `node --check`; nenhum erro de JavaScript.
- **Não testado:** abrir a COM11 de verdade pelo painel, porque o teste automático não escolhe porta. A bomba real não foi acionada.
