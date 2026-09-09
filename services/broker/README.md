# Broker MQTT (Mosquitto)

Configuração do broker: autenticação por usuário/senha, ACL restringindo cada dispositivo
aos seus próprios tópicos, e TLS previsto para a v3.

**Nenhuma credencial entra no repositório.** O arquivo de senhas e o `.env` são locais,
gerados a partir dos exemplos versionados.

Tópicos e QoS: ver o contrato no [README principal](../../README.md#contrato-de-mensagens-mqtt-preliminar).
Comandos de atuação e eventos de irrigação usam QoS 1; telemetria usa QoS 0 ou 1.
