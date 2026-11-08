# SIT, entrega v1: roteiro da apresentação

- **Quando:** 14/10/2026, às 10h (TI0179 Internet das Coisas, UFC).
- **Deck:** https://claude.ai/artifact/2ZRr8HQBkiABVCHz3Bkik1 (16 slides; as falas completas estão nas notas de cada slide, no modo apresentação).
- **Duração alvo:** de 11 a 12 min de fala, mais as perguntas. Com a demonstração ao vivo, uns 13 min.
- **Equipe:** Alisson Jaime Sales Barros, Gabriel Vaz de Oliveira, José Ferreira Lessa e Matheus Rocha Gomes da Silva.

## 1. Divisão sugerida

| Integrante | Slides | Assunto | Tempo |
|---|---|---|---|
| Alisson | 1 a 4 | capa, problema, objetivo, arquitetura | ~3 min |
| Gabriel | 5 a 8 | hardware, circuito da bomba, protótipo 3D, peças | ~3 min |
| José | 9 a 12 | firmware, MQTT, dashboard (com a demo, se der), coleta | ~3,5 min |
| Matheus | 13 a 16 | resultados, faixas do tomateiro, dificuldades, próximos passos | ~3,5 min |

A divisão é só uma sugestão: troquem os blocos conforme quem fez cada parte. A disciplina pede que todos entendam o sistema inteiro, então cada um deve conseguir responder perguntas fora do próprio bloco.

Se o tempo apertar, cortem nesta ordem: a frase sobre o PETG (slide 7), os detalhes do diodo (slide 6) e as referências faladas do slide 14 (elas estão escritas no slide).

## 2. Checklist antes de começar (09h30)

1. **Wi-Fi da estação.** Na coleta de ontem a estação não conectou ao Wi-Fi (o log mostra "MQTT desconectado", `ts` nulo e RSSI 0). Para mostrar o MQTT, configurem a rede de 2,4 GHz no `secrets.h` (o roteador do celular serve) e regravem o firmware. Sem isso, a demo vai só pela USB, o que também funciona.
   - Testem a rede antes: na rede do notebook, as portas 1883 e 8884 do broker.hivemq.com deram timeout. O painel cai sozinho para `ws://broker.hivemq.com:8000/mqtt`, e o firmware usa a 8883 (TLS). No hotspot do celular costuma passar.
2. **Dashboard.** Abrir `codes/dashboard/index.html` no Chrome e testar as fontes Wi-Fi, cabo e AUTO (roteiro da demo em `docs/v1/dashboard.md`). A porta serial abre em um programa por vez: para usar a Web Serial, parem o coletor antes. O print do slide 11 é de dados de teste; se a professora perguntar, digam isso.
3. **Bomba.** Dose de 1 s, reservatório com água, vaso com terra e papel toalha por perto.
4. **Plano B.**
   - A rede da sala caiu: troquem a fonte do dashboard para a USB.
   - A ESP reiniciou depois da rega: é o problema conhecido do slide 15; esperem uns 20 s e ela volta sozinha.
5. **Deck.** Conferir se os renders já entraram nos slides 1, 5, 7 e 8 (o print do dashboard já está no 11). Se não entraram, os quadros vazios podem ser preenchidos no próprio editor (Adicionar imagem).

## 3. Falas por slide

As falas abaixo são as mesmas das notas do deck. Cada uma tem de 30 a 60 s.

### Slide 1, capa (Alisson, ~35 s)
Bom dia, professora e colegas. Somos o grupo do SIT, o Sistema IoT de Irrigação Inteligente para o cultivo de tomate: eu sou o Alisson, e comigo estão o Gabriel, o José e o Matheus. Hoje mostramos a entrega v1: uma estação que mede o solo e o ar, aciona uma bomba por comando e manda os dados por MQTT, pelo Wi-Fi, e pelo cabo USB até um dashboard web nosso. Vamos do problema à arquitetura, ao hardware e às peças impressas; depois firmware, comunicação, coleta, dificuldades e próximos passos.

### Slide 2, água, irrigação e tomateiro (Alisson, ~45 s)
A agricultura responde por cerca de 70 % da água doce retirada no mundo, segundo a FAO; irrigar melhor tem impacto direto. Escolhemos o tomate porque ele sente a irregularidade da água: falta ou excesso aparecem entre as causas de podridão apical e de rachadura de frutos. A pergunta do estudo de caso da disciplina resume o objetivo: dá para gastar menos água mantendo a umidade do solo adequada? E há dados reais para aprender: o testbed de tomateiro de Parma, com solo e ar medidos a cada 10 minutos em três regimes de irrigação (100 %, 60 % e 30 % da recomendação), que já exploramos nas EDAs.

### Slide 3, objetivo e escopo da v1 (Alisson, ~45 s)
O objetivo é monitorar o solo e o ar de um vaso de tomateiro e irrigar sob comando, com os dados chegando por MQTT e pela USB a um dashboard. A decisão automática de quando irrigar vem nas próximas entregas. A v1 pedia quatro coisas, e cada cartão diz onde elas estão no deck: coleta de dados, MQTT, gráficos e dashboard. Fomos um pouco além: bomba acionada por comando, redundância entre cabo e Wi-Fi e um invólucro impresso em 3D. Um ponto importante: ainda não há planta. O vaso tem só terra, e por isso os limiares do tomateiro entram como valores iniciais configuráveis.

### Slide 4, arquitetura (Alisson, ~55 s)
A arquitetura, da esquerda para a direita. No campo, o sensor capacitivo de solo, o AM2302 para temperatura e umidade do ar, e a bomba. Na borda, o ESP32-S3 lê tudo a cada 30 segundos e manda o mesmo JSON por dois caminhos: pelo Wi-Fi, para o broker MQTT público da HiveMQ; pelo cabo, como uma linha no serial. Na aplicação, o dashboard recebe de qualquer uma das duas fontes, por WebSocket seguro ou por Web Serial, e o coletor no notebook grava CSV. As setas duplas indicam o caminho de volta: o dashboard manda o comando da bomba, e o ESP liga pelo tempo pedido, limitado a 3 segundos pelo próprio firmware.

### Slide 5, hardware (Gabriel, ~45 s)
O hardware. O cérebro é um ESP32-S3 DevKit, alimentado pela USB do notebook. O sensor de solo é capacitivo e está no GPIO4, do ADC1, porque o ADC2 fica indisponível com o Wi-Fi ligado. O AM2302, que é o DHT22, mede temperatura e umidade do ar no GPIO5. A bomba é submersa, de 5 V, de 130 a 220 mA e 1 a 1,5 litro por minuto, chaveada por um transistor no GPIO6. Duas escolhas de projeto: o sensor capacitivo não tem eletrodo exposto, então não corrói como o resistivo; e o AM2302 fica sobre a tampa, longe do calor da placa.

### Slide 6, circuito da bomba (Gabriel, ~55 s)
O pino do ESP32 não fornece a corrente do motor, então um transistor NPN faz a chave. Com o GPIO6 em nível alto, passam uns 2,5 mA pela base, limitados pelo resistor de 1 kΩ; o transistor conduz e a bomba liga entre o 5 V e o coletor. O diodo 1N4007 fica em antiparalelo com a bomba, com a listra no 5 V: ao desligar, o motor, que é indutivo, gera um pico de tensão, e o diodo dá caminho para essa corrente, protegendo o transistor. A limitação é o MPSA42, o transistor que tínhamos: com ganho mínimo 40 ele conduz, no pior caso, uns 100 mA, menos do que a bomba pede, e ela gira mais fraca. A melhoria é baixar o resistor para 470 Ω ou trocar por BC337, TIP120 ou MOSFET de nível lógico.

### Slide 7, protótipo impresso em 3D (Gabriel, ~40 s)
Este é o protótipo como foi projetado: quatro peças em PETG amarelo, todas impressas sem suporte, somando cerca de 9 horas e meia de impressão pela estimativa do fatiador. O modelo é paramétrico, escrito em Python com manifold3d e trimesh: se uma medida muda, como o diâmetro do vaso ou a folga de um encaixe, rodamos o script e os STL saem atualizados. O PETG também aguenta melhor calor e umidade do que o PLA, o que ajuda numa estação ao lado de um vaso regado.

### Slide 8, peças e montagem (Gabriel, ~45 s)
A caixa guarda a protoboard com o ESP32, o transistor, o resistor e o diodo; a USB fica alinhada com um rasgo lateral e os cabos saem por três rasgos do outro lado. A tampa vira na montagem: o AM2302 vai por cima, preso com duas abraçadeiras, e a ventilação fica na outra metade. O reservatório, de uns 540 mL, encaixa na caixa por rabos de andorinha, com a bomba no fundo. E a coroa apoia na borda do vaso, guia a mangueira até a terra, por um furo de 5,5 mm, e passa o cabo do sensor de solo pelo lado oposto.

### Slide 9, firmware (José, ~55 s)
O firmware, escrito no Arduino para o ESP32-S3. No setup, a primeira coisa é deixar a bomba desligada, antes de configurar o pino, para ela não pulsar no boot; depois vêm o Wi-Fi, o relógio pelo NTP brasileiro e o MQTT. O loop não tem espera longa: garante a conexão MQTT, tentando a cada 5 segundos, processa os comandos que chegaram pelo MQTT ou pelo serial e desliga a bomba quando o tempo pedido acaba. A cada 30 segundos sai uma leitura: o solo é a média de 20 amostras do ADC, para reduzir o ruído, mais temperatura, umidade e horário. Tudo vira um JSON no serial e no MQTT. E a segurança do atuador está no próprio firmware: qualquer comando é limitado a 3 segundos de bomba, venha de onde vier.

### Slide 10, MQTT na prática (José, ~55 s)
Usamos MQTT, que é publish/subscribe: a estação publica no broker e quem quiser assina, sem um precisar conhecer o outro. Na fase de testes, o broker público da HiveMQ. São quatro tópicos. Em leituras sai o JSON a cada 30 segundos. Em status, a estação publica online, retido, e deixa registrado um last will: se cair sem avisar, o próprio broker publica offline. Em bomba/cmd ela recebe os segundos de rega, e zero desliga. Em bomba/estado confirma ligada ou desligada, também retido, para quem abrir o dashboard depois já ver o estado atual. O JSON, aqui num exemplo do formato, leva horário, valor bruto do ADC, umidade do solo, temperatura, umidade do ar e o RSSI do Wi-Fi.

### Slide 11, dashboard e redundância (José, ~50 s, mais a demo se houver tempo)
O dashboard é uma página web nossa, que abre direto no Chrome. Ele tem três modos de fonte: Wi-Fi, que assina os tópicos MQTT por WebSocket; cabo, que lê o mesmo JSON pela Web Serial; e AUTO, que usa o MQTT e, se ficar 90 segundos sem leitura ou a conexão cair, passa a mostrar a USB. Essa é a nossa redundância entre Wi-Fi e cabo. Na tela, cada valor aparece com o estado, ideal, atenção ou alerta, pelas faixas do tomateiro. Há o status online da estação, que vem do last will, o RSSI, a bomba com o botão de rega de 1 a 3 segundos, gráficos com as faixas, o histórico em CSV e o log das mensagens MQTT. Esta captura usa dados de teste do simulador, num tópico separado. [Se houver tempo: demonstração com uma rega de 1 segundo; o roteiro da demo está em `docs/v1/dashboard.md`.]

### Slide 12, coleta de dados e calibração (José, ~55 s)
A coleta: vaso de 10 por 8 cm só com terra, sensor enterrado até a marca e AM2302 sobre a tampa. O firmware lê a cada 30 segundos e o coletor serial, em Python, grava as leituras e os eventos da bomba em CSV, com a hora do notebook. A coleta foi ontem, das 21:11 às 22:14, quando o notebook encerrou o coletor por falta de memória; às 21:15 e às 21:17 pedimos duas regas de 3 segundos. A conversão é linear entre dois pontos. O valor bruto do ADC cai quando a terra fica mais úmida: no ar o sensor marcou cerca de 3560, que vira 0 %; o ponto de 100 % é o sensor na água, que ainda vamos medir, e por enquanto o firmware usa 1300. Na terra medimos 2645 com ela seca, ou 40 %, e cerca de 1490 com ela encharcada, ou 91 %: são as marcas na barra. É uma escala relativa, não umidade volumétrica; a calibração no substrato vem com o plantio.

### Slide 13, resultados da coleta (Matheus, ~50 s)
Os resultados da coleta de ontem, das 21:11 às 22:14: uma hora, com 121 das 126 leituras esperadas, ou seja, 4 % de perda, concentrada nas duas lacunas em volta das regas, quando a estação reiniciou. A coleta parou às 22:14 porque o notebook encerrou o coletor por falta de memória. No gráfico, o solo começa em 40 %. As duas regas, pedidas de 3 segundos, às 21:15 e às 21:17, levaram a umidade a 88 % em uns três minutos, e ela ficou estável em 91 % até o fim: o vaso encharcou, e por isso a dose passou a 1 segundo. A temperatura variou de 24,4 a 27,1 °C e a umidade do ar de 60,6 a 74,5 %. O AM2302 não teve nenhuma falha nas 121 leituras.

### Slide 14, faixas iniciais do tomateiro e regras (Matheus, ~60 s)
Sem planta, as faixas do tomateiro entram como valores iniciais, conferidos na literatura. Temperatura: ideal de 20 a 30 °C; alerta abaixo de 10 °C, a temperatura base do tomateiro, e acima de 35 °C, a crítica no estágio vegetativo. Na floração e no pegamento a crítica cai para 30 e 27 °C, então o limite vai ser ajustado por estágio. Umidade do ar: ideal de 60 a 80 %; alerta acima de 90 %, pelo risco de fungos, e abaixo de 40 %. Esses dois alertas são valores iniciais do grupo. Solo: como o sensor é relativo, ideal de 50 a 80 % e alerta abaixo de 40 %, seguindo a regra da FAO-56 de irrigar o tomate antes de esgotar 40 % da água disponível. Isso vira regra em três etapas: faixas nos gráficos agora, alerta após três leituras seguidas fora da faixa na v2 e irrigação automática na v3.

### Slide 15, dificuldades e soluções (Matheus, ~55 s)
Cinco dificuldades reais. Um: o ADC2 do ESP32 não funciona com o Wi-Fi ligado, então o solo foi para o ADC1. Dois: os fios dos sensores estavam em pinos diferentes dos do firmware; um sketch de diagnóstico mostrou os pinos ao vivo e corrigimos a ligação. Três: o MPSA42 tem ganho baixo e a bomba gira mais fraca; serve para a demo e a troca está prevista. Quatro: as regas de 3 segundos encharcaram o vaso, então a dose passou a 1 segundo. Como o log não mostra a bomba desligando antes do reset, estamos conferindo se ela para no tempo certo. Cinco, ainda aberto: todo acionamento da bomba reinicia a ESP uns 15 segundos depois, por watchdog, provavelmente ruído na USB nativa. A coleta continua depois do reset; a solução está em teste: [preencher com o que funcionou].

### Slide 16, próximos passos e encerramento (Matheus, ~45 s)
Para fechar: a v1 é a estação funcionando, com sensores, bomba por comando, MQTT e USB, dashboard e coleta. O próximo passo é o plantio, para calibrar o sensor no substrato e ajustar as faixas por estágio. Na v2 entra a inteligência: analisamos os nossos dados com o dataset de Parma, que já exploramos nas EDAs, e treinamos um modelo leve, que caiba no ESP32 com TinyML, para estimar a necessidade de irrigação. Na v3 a estação atua sozinha, com limiar, dose e intervalo mínimo entre regas, sempre com a trava de segurança do firmware. Obrigado! Ficamos à disposição para perguntas.

## 4. Perguntas prováveis da professora

**Por que MQTT e não HTTP?**
O MQTT é leve e funciona por publish/subscribe: a estação não precisa saber quem consome os dados. A conexão fica aberta, então o comando da bomba chega na hora, sem o dashboard ficar perguntando (polling). E ele traz last will e mensagens retidas, que usamos para o status online/offline e para o estado da bomba.

**O broker é público. E a segurança?**
É só para a fase de testes. Hoje qualquer pessoa que conheça o tópico poderia publicar em `bomba/cmd`; a proteção atual é a trava de 3 s no firmware, que limita o estrago de um comando errado. O próximo passo é um broker com usuário, senha e TLS (Mosquitto próprio ou HiveMQ Cloud), com permissão por tópico.

**Por que não usaram o ThingsBoard?**
Construímos um dashboard próprio. Ele recebe os dados por MQTT (WebSocket) e também pelo cabo USB (Web Serial), o que garante a demonstração mesmo sem rede, e mostra a conexão, as faixas do tomateiro e o comando da bomba do jeito que o projeto precisa.

**O sensor mede umidade volumétrica?**
Não. A escala é relativa, do sensor no ar (0 %) ao sensor na água (100 %), por interpolação linear. Hoje temos o ponto do ar (~3560, medido) e um valor provisório para a água (1300, ainda a medir). Na terra, a leitura foi 2645 seca (40 %) e ~1490 encharcada (91 %). Para umidade volumétrica seria preciso calibrar no substrato, pesando amostras secas e úmidas, o que fica para depois do plantio.

**Por que 4 % de perda?**
Foram 5 leituras de 126, todas nas duas lacunas em volta das regas: a estação reiniciou pouco antes da primeira rega (o log mostra o boot) e reiniciou de novo depois de cada acionamento da bomba. Fora dessas lacunas, a série é contínua.

**Por que a ESP reinicia quando a bomba liga?**
O log mostra reset por watchdog (TG0WDT) uns 15 s depois de cada acionamento. A hipótese é ruído ou queda de tensão na USB nativa do ESP32-S3 quando o motor parte. O log também não mostra a linha "Bomba desligada" antes do reset, então não dá para garantir que a bomba parou em 3 s: se o loop travou, ela pode ter ficado ligada até o watchdog reiniciar a placa, o que também explicaria o vaso encharcado. Estamos conferindo. A coleta continua depois do reset. Em teste: capacitores junto à bomba, alimentação separada para o motor e outra porta ou cabo USB. [Preencher com o que funcionou.]

**Por que leitura a cada 30 s?**
Para ver a resposta à rega, que acontece em poucos minutos. Na operação normal, a cada 10 min basta (é o intervalo do testbed de Parma) e economiza energia e dados; o intervalo é uma constante no firmware.

**Como a IA entra no projeto?**
Na v2 vamos treinar um modelo leve com o dataset de Parma (solo, ar e irrigação em três regimes) e com os nossos dados, para estimar a umidade futura ou a necessidade de irrigação. O modelo é quantizado para rodar no próprio ESP32-S3 (TinyML, por exemplo com TensorFlow Lite for Microcontrollers) e comparado com a regra por limiar, que serve de linha de base.

**O que impede a bomba de esvaziar o reservatório ou encharcar o vaso?**
A trava de 3 s por comando, no firmware, e a dose de 1 s. Na v3, o modo automático ainda respeita um limiar e um intervalo mínimo entre regas. O desligamento é feito por um temporizador de hardware (`esp_timer`), que atua mesmo se o loop travar; o que ainda não sabemos é por que a placa reinicia depois do acionamento.

**O MQTT funcionou de verdade?**
O firmware publica no broker sempre que há Wi-Fi. Na coleta de ontem a rede ainda não estava configurada na estação, por isso os dados vieram pela USB. [Preencher: resultado do teste com Wi-Fi feito antes da apresentação.]

**Por que o RSSI saiu zero e o `ts` nulo?**
Porque o Wi-Fi ainda não estava configurado na coleta. Sem rede não há NTP, então o firmware manda `ts` nulo e o coletor usa a hora de chegada no notebook (`recebido_em`). Com Wi-Fi, `ts` vem do NTP e o RSSI mostra a qualidade do enlace.

**E se o Wi-Fi cair durante a operação?**
A estação continua lendo e mandando pela USB. O Wi-Fi reconecta sozinho e o MQTT tenta de novo a cada 5 s. Enquanto isso, o broker publica `offline` em `status` (last will), e o dashboard pode trocar para o cabo.

**Por que o AM2302 fica fora da caixa?**
Para não medir o calor da placa e do transistor. Ele fica sobre a tampa ventilada.

**Por que sensor capacitivo?**
Ele não tem eletrodo exposto, então não corrói como o resistivo em contato contínuo com solo úmido.

**Por que o MPSA42?**
Era o transistor disponível. Serve para a demonstração, mas não satura na corrente da bomba. Com resistor de 470 Ω ou com BC337, TIP120 ou um MOSFET de nível lógico, a bomba recebe os 5 V completos.

**De onde vêm as faixas do tomateiro?**
FAO (ótimo de 18-25 °C na média diária), Belli et al. (2025; temperatura base de 10 °C), Martelli et al. (2024; temperaturas críticas por estágio), Kasera e Acharjee (2024; umidade do ar de 60-85 % por estágio) e FAO-56 (fração de esgotamento p = 0,40 para o tomate). Os limites de alerta da umidade do ar (> 90 % e < 40 %) são valores iniciais do grupo, a ajustar com a planta.

## 5. Referências

- Allen, R. G.; Pereira, L. S.; Raes, D.; Smith, M. *Crop evapotranspiration: guidelines for computing crop water requirements.* FAO Irrigation and Drainage Paper 56. Roma: FAO, 1998.
- Belli, L. et al. Smart agriculture dataset in a tomato cultivation under different irrigation regimes. *Data in Brief*, v. 60, 111521, 2025.
- FAO. AQUASTAT, sistema global de informação sobre água e agricultura.
- FAO. Crop Information: Tomato (Land and Water Division).
- Kasera, R. K.; Acharjee, T. A comprehensive IoT edge based smart irrigation system for tomato cultivation. *Internet of Things*, v. 28, 101356, 2024.
- Martelli, A. et al. Smart irrigation for management of processing tomato: a machine learning approach. *Irrigation Science*, 2024. doi:10.1007/s00271-024-00993-9.
- Rocha, A.; Mulas, M. TI0179, Integrated Project in Computational Intelligence and IoT: course introduction (estudo de caso de irrigação inteligente).
