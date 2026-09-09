# Catálogo de dados

`data/raw/` é **imutável**: os `.zip` originais ficam intactos e versionados. Todo dado
derivado nasce de script ou notebook versionado e vai para `data/interim/` ou
`data/processed/`, que o git ignora por serem reproduzíveis.

Para extrair localmente:

```bash
python -c "import zipfile,glob; [zipfile.ZipFile(z).extractall('data/interim') for z in glob.glob('data/raw/*.zip')]"
```

---

## 1. Testbed evolutivo de cultivo de tomate — **fonte principal**

`IoT Dataset from an Evolving Tomato Cultivation Te.zip` (19,3 MB)

Oddi, Belli, Davoli, Preite, Galaverni, Rodolfi, Ganino, Ferrari.
*IoT Dataset from an Evolving Tomato Cultivation Testbed.* Mendeley Data, V1, 2026.
DOI **10.17632/h8sfcf9487.1**.

Testbed real em Parma (Itália), **três temporadas (2023, 2024, 2025)**, até **5 linhas de
cultivo**, sensores comerciais sobre LoRaWAN, **amostragem de 10 minutos**. É a base de
treinamento do modelo.

| Arquivo | Dispositivo | Variáveis | 2023 | 2024 | 2025 |
| :-- | :-- | :-- | :-: | :-: | :-: |
| `soil<ano>.csv` | Milesight EM500 SMTC | condutividade elétrica (µS/cm), umidade (%RH), temperatura (°C) do solo | ✓ | ✓ | ✓ |
| `environmental<ano>.csv` | Milesight EM500 CO2 | CO₂ (ppm), pressão barométrica (hPa), temperatura do ar (°C), umidade do ar (%RH) | ✓ | ✓ | ✓ |
| `water_meter<ano>.csv` | Talkpool OY1310 | volume de água (m³), 1 por linha + 1 geral | ✓ | ✓ | ✓ |
| `indicators<ano>.csv` | plataforma Agriware | GDD e *heat units* por 6 métodos, diário (T_base 10 °C, T_cutoff 32 °C) | ✓ | ✓ | ✓ |
| `water_valve2023.csv` / `valve_controller<ano>.csv` | Milesight UC512 | estado da válvula (aberta/fechada) | ✓ | ✓ | ✓ |
| `pressure<ano>.csv` | Milesight EM500 PP | pressão da água (kPa) | – | ✓ | ✓ |
| `water_potential2024.csv` | — | potencial hídrico | – | ✓ | – |
| `stem2025.csv` | DL-ISD-001 (dendrômetro de caule) | diâmetro do caule (mm), faixa 5–25 mm | – | – | ✓ |
| `fruit2025.csv` | DL-IFD-001 (dendrômetro de fruto) | tamanho do fruto (mm), faixa 7–45 mm | – | – | ✓ |
| `leaf_temperature2025.csv` | DL-ILT-001 | temperatura da folha (°C), 2 por linha | – | – | ✓ |

Colunas comuns: `timestamp` (ms), identificador do dispositivo, `line` (número da linha) e
os valores. Em 2025 os sensores de solo estão em **duas profundidades** (15 cm e 30 cm).

> **Atenção ao usar:** a cobertura de sensores **cresce ao longo dos anos**. Um modelo que
> dependa de dendrômetro ou temperatura de folha só pode ser treinado com 2025 e não terá
> equivalente no protótipo físico. Prefira o subconjunto de variáveis que o nó ESP32
> consegue medir: umidade e temperatura do solo, temperatura e umidade do ar, pressão e
> volume de água.

---

## 2. STUARD — cultivo sob diferentes regimes de irrigação

`IoT-based Dataset of a Tomato Cultivation Under Different Irrigation Regimes.zip` (0,9 MB)

Belli *et al.* Três linhas de tomate irrigadas com **100%, 60% e 30%** da recomendação
Irriframe. Amostragem de 10 minutos; sensores de solo a 20 cm de profundidade.

| Arquivo | Conteúdo |
| :-- | :-- |
| `stuard_soil_data.csv` | condutividade elétrica, umidade e temperatura do solo, por linha |
| `stuard_environmental_data.csv` | umidade do ar, temperatura, CO₂, pressão, bateria |
| `stuard_water_meter_data.csv` | volume de água (m³) por linha |
| `indicators.csv` | GDD e *heat units* diários |

Valor para o projeto: é o **contraste direto entre políticas hídricas**. Serve para
caracterizar o que é sub-irrigação e super-irrigação e para calibrar a faixa adequada de
umidade — a referência do critério "conforto hídrico".

---

## 3. AgriDataValue — dados meteorológicos

`AgriDataValue - Environmental Data Useful for Smart Irrigation.zip` (3,5 MB)

Planilhas de estação meteorológica (P18 BIORO, 2024–2025) e dados horários Open-Meteo para
milho. **Cultura diferente** — uso previsto apenas como referência de variáveis
meteorológicas e para experimentar cálculo de evapotranspiração. Não é base de treino.

---

## 4. Irrigation-Dataset

`Irrigation-Dataset.zip` (0,1 MB) — uma planilha `second dataset collected.xlsx`, sem
documentação de origem. **Procedência não verificada**; não usar sem antes rastrear a
fonte. Mantido apenas como registro.

---

## Notas de qualidade a verificar na v1

Antes de treinar qualquer modelo, o notebook de exploração deve reportar:

- taxa de amostras faltantes por sensor e por temporada;
- lacunas longas (sensor fora do ar) e como serão tratadas;
- valores fora de faixa física e sensores estagnados;
- alinhamento temporal entre solo, ambiente e hidrômetro (fusos e *timestamps* em ms);
- se o volume do hidrômetro é acumulado ou incremental — e a conversão para lâmina.
