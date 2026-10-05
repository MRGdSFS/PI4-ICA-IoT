import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

# ============================================================
# CONFIGURAÇÃO
# ============================================================

from config import LINHAS
from config import OUTPUT_DIR

# ============================================================
# FUNÇÕES AUXILIARES
# ============================================================

from utils import carregar_csv
from utils import salvar_figura
from utils import encontrar_coluna
from utils import mostrar_colunas
from utils import print_titulo
from utils import pausar_seguir

# ============================================================
# 1. CARREGAMENTO DOS DADOS PRINCIPAIS
# ============================================================

from _1_carregamento import carregar_dados

print_titulo("1. CARREGAMENTO DOS DADOS")

dados = carregar_dados(carregar_csv, mostrar_colunas)

pausar_seguir()

# ============================================================

# 2. VERIFICAÇÃO TEMPORAL

# ============================================================

from _2_verificacao_temporal import verificacao_temporal

print_titulo("2. VERIFICAÇÃO DA SÉRIE TEMPORAL")

verificacao_temporal(dados)

pausar_seguir()

# ============================================================
# 3. CONSTRUÇÃO DA SÉRIE TEMPORAL INTEGRADA
# ============================================================

import _3_integracao_datasets as secao_3

print_titulo("3. CONSTRUÇÃO DA SÉRIE TEMPORAL INTEGRADA")

"""
A série integrada será construída utilizando o dataset de
solo como base temporal.

O solo possui dois sensores por linha. Portanto, cada registro
da base é identificado por:

    line + generated_by + datetime

Os datasets de válvula e hidrômetro possuem identificação
de linha. Sua integração será realizada por:

    line + datetime

O identificador generated_by de cada dataset será preservado
com um nome específico, evitando perda de informação ou
ambiguidade.

O dataset ambiental não possui identificação de linha.
Sua integração será realizada somente por:

    datetime

O alinhamento temporal utiliza a tolerância definida em
TOLERANCIA_ALINHAMENTO.
"""

# ------------------------------------------------------------
# Verificação
# ------------------------------------------------------------

(
soil,
coluna_linha_soil,
coluna_humidade,
coluna_temperatura_solo
) = secao_3.verificacao(dados)

# ------------------------------------------------------------
# RENOMEAÇÃO DAS VARIÁVEIS DO SOLO
# ------------------------------------------------------------

soil = soil.rename(
    columns={
        coluna_linha_soil: "line",
        coluna_humidade: "soil_humidity",
        coluna_temperatura_solo: "soil_temperature"
    }
)

soil = (
    soil
    .dropna(subset=["datetime"])
    .sort_values(
        ["line", "generated_by", "datetime"]
    )
    .reset_index(drop=True)
)

# ------------------------------------------------------------
# VERIFICAÇÃO DOS SENSORES
# ------------------------------------------------------------

print("\nSensores de solo por linha:")

sensores_por_linha = (
    soil
    .groupby("line")["generated_by"]
    .nunique()
)

print(
    sensores_por_linha
    .to_string()
)

# ------------------------------------------------------------
# 3.1 INTEGRAR VÁLVULA
# ------------------------------------------------------------

if "valve" in dados:
    integrada = secao_3.integrar_valvula(dados, soil)
else:
    integrada = soil.copy()
    print("\nDataset de válvula não encontrado.")

# ------------------------------------------------------------
# 3.2 INTEGRAR HIDRÔMETRO
# ------------------------------------------------------------

if "water_meter" in dados:
    integrada = secao_3.integrar_hidrometro(dados, soil, integrada)
else:
    print("\nDataset de hidrômetro não encontrado.")

# ------------------------------------------------------------
# 3.3 INTEGRAR DADOS AMBIENTAIS
# ------------------------------------------------------------

if "environmental" in dados:
    integrada = secao_3.integrar_ambiental(dados, soil, integrada)
else:
    print("\nDataset ambiental não encontrado.")

# ------------------------------------------------------------
# 3.4 RESULTADO FINAL
# ------------------------------------------------------------

print_titulo("SÉRIE TEMPORAL INTEGRADA", False)

print(f"Total de registros: {len(integrada)}")

print("\nColunas finais:")

for coluna in integrada.columns:
    print(f"  - {coluna}")


# ------------------------------------------------------------
# 3.5 VERIFICAÇÃO POR LINHA E SENSOR
# ------------------------------------------------------------

print("\nRegistros por linha e sensor:")

if "line" in integrada.columns:

    registros_grupo = (
        integrada
        .groupby(
            ["line", "generated_by"]
        )
        .size()
    )

    print(
        registros_grupo
        .to_string()
    )

else:

    print(
        "ERRO: coluna 'line' não encontrada "
        "na série integrada."
    )

# ------------------------------------------------------------
# 3.6 AMOSTRA
# ------------------------------------------------------------

print("\nPrimeiros registros da série integrada:")

print(integrada.head(5).to_string(index=False))

# ------------------------------------------------------------
# 3.7 SALVAR
# ------------------------------------------------------------

arquivo_saida = (OUTPUT_DIR /"03_serie_temporal_integrada.csv")

integrada.to_csv(arquivo_saida,index=False)

print(f"\nArquivo salvo em:\n{arquivo_saida.resolve()}")

pausar_seguir()

# ============================================================
# 4. QUALIDADE DOS DADOS RELEVANTES AO PROBLEMA
# ============================================================

from _4_qualidade import teste_qualidade

print_titulo("4. QUALIDADE DOS DADOS RELEVANTES")

qualidade_df, qualidade_solo_df = teste_qualidade(integrada)

print(qualidade_df.to_string(index=False))
print(qualidade_solo_df.to_string(index=False))

qualidade_df.to_csv     (OUTPUT_DIR / "04_qualidade_dados_relevantes.csv",index=False)
qualidade_solo_df.to_csv(OUTPUT_DIR / "04_qualidade_sensores_solo.csv"   ,index=False)

pausar_seguir()

# ============================================================
# 5. ANÁLISE DA UMIDADE DO SOLO
# ============================================================

import  _5_analise_umidade as secao05

print_titulo("5. DINÂMICA DA UMIDADE DO SOLO")

# ------------------------------------------------------------
# Preparação
# ------------------------------------------------------------

soil_analysis = secao05.preparacao(soil)

# ------------------------------------------------------------
# Estatísticas gerais
# ------------------------------------------------------------

print("\nEstatísticas gerais da umidade do solo:")

secao05.estatisticas_gerais(soil_analysis)

# ------------------------------------------------------------
# Estatísticas por linha
# ------------------------------------------------------------

if "line" in soil_analysis.columns:
    secao05.estatisticas_por_linha(soil_analysis)
else:
    print("\nColuna 'line' não encontrada!")

# ------------------------------------------------------------
# Estatísticas por sensor
# ------------------------------------------------------------

if (
    "line" in soil_analysis.columns
    and "generated_by" in soil_analysis.columns
   ):
    secao05.estatisticas_por_sensor(soil_analysis)
else:
    print("Coluna 'line' ou 'generated_by' não encontrada(s)!")
    
# ------------------------------------------------------------
# Gráfico geral por linha
# ------------------------------------------------------------

secao05.graf_por_linha(soil_analysis)

# ------------------------------------------------------------
# Gráficos por sensor
# ------------------------------------------------------------

secao05.graf_por_sensor(soil_analysis)

pausar_seguir()

# ============================================================
# 6. DINÂMICA TEMPORAL DA UMIDADE DO SOLO
# ============================================================

print_titulo("6. DINÂMICA TEMPORAL DA UMIDADE DO SOLO")

drying = soil_analysis.copy()

# ------------------------------------------------------------
# Preparação
# ------------------------------------------------------------

drying = drying.sort_values(
    ["line", "generated_by", "datetime"]
).reset_index(drop=True)

# ------------------------------------------------------------
# 6.1 FREQUÊNCIA DE AMOSTRAGEM DOS SENSORES
# ------------------------------------------------------------

print_titulo("FREQUÊNCIA DE AMOSTRAGEM DOS SENSORES", False)

drying["intervalo_min"] = (
    drying
    .groupby(["line", "generated_by"])["datetime"]
    .diff()
    .dt.total_seconds()
    / 60
)

frequencia_sensor = (
    drying
    .groupby(["line", "generated_by"])["intervalo_min"]
    .describe(
        percentiles=[
            0.01,
            0.05,
            0.25,
            0.50,
            0.75,
            0.95,
            0.99
        ]
    )
)

print("\nIntervalos entre leituras (minutos):")
print(frequencia_sensor.to_string())

frequencia_sensor.to_csv(
    OUTPUT_DIR / "06_frequencia_sensor.csv"
)

print("\nIntervalo mediano por linha e sensor:")

for (linha, sensor), grupo in (
    drying.groupby(["line", "generated_by"])
):

    valores = grupo["intervalo_min"].dropna()

    if valores.empty:
        continue

    print(
        f"  Linha {linha} | Sensor {sensor}: "
        f"{valores.median():.3f} min"
    )

# ------------------------------------------------------------
# Distribuição dos intervalos
# ------------------------------------------------------------

fig, ax = plt.subplots(figsize=(10, 5))

for (linha, sensor), grupo in (
    drying.groupby(["line", "generated_by"])
):

    intervalos = grupo["intervalo_min"].dropna()

    intervalos = intervalos[intervalos > 0]

    if intervalos.empty:
        continue

    ax.hist(
        intervalos,
        bins=100,
        alpha=0.5,
        label=f"L{linha} — {sensor}"
    )

ax.set_title(
    "Distribuição dos intervalos entre leituras "
    "dos sensores de umidade"
)

ax.set_xlabel(
    "Intervalo entre leituras (min)"
)

ax.set_ylabel("Frequência")

ax.legend(
    fontsize=8
)

ax.grid(
    True,
    alpha=0.3
)

salvar_figura(
    fig,
    "06_frequencia_sensor.png",
    OUTPUT_DIR
)

plt.close(fig)

# ------------------------------------------------------------
# 6.2 VARIAÇÃO DA UMIDADE ENTRE LEITURAS
# ------------------------------------------------------------

resultados_secagem = []
maiores_variacoes_todas = []
variacoes_todas = []

for (linha, sensor), grupo in (
    drying.groupby(["line", "generated_by"])
):

    grupo = grupo.copy()

    # --------------------------------------------------------
    # Diferença entre leituras consecutivas
    # --------------------------------------------------------

    grupo["datetime_anterior"] = (
        grupo["datetime"].shift(1)
    )

    grupo["umidade_anterior"] = (
        grupo["soil_moisture"].shift(1)
    )

    grupo["delta_moisture"] = (
        grupo["soil_moisture"]
        - grupo["umidade_anterior"]
    )

    grupo["abs_delta_moisture"] = (
        grupo["delta_moisture"].abs()
    )

    grupo["delta_tempo_min"] = (
        grupo["datetime"]
        - grupo["datetime_anterior"]
    ).dt.total_seconds() / 60

    # --------------------------------------------------------
    # Estatísticas das variações
    # --------------------------------------------------------

    print(
        f"\nLinha {linha} — Sensor {sensor} "
        f"— variações de umidade:"
    )

    print(
        grupo["abs_delta_moisture"]
        .describe(
            percentiles=[
                0.50,
                0.75,
                0.90,
                0.95,
                0.99,
                0.999
            ]
        )
        .to_string()
    )

    # --------------------------------------------------------
    # Frequência de grandes variações
    # --------------------------------------------------------

    limiares = [
        1,
        2,
        5,
        10,
        15,
        20,
        30
    ]

    delta_abs = (
        grupo["delta_moisture"]
        .abs()
        .dropna()
    )

    print(
        f"\nLinha {linha} — Sensor {sensor}"
    )

    print("-" * 60)

    for limiar in limiares:

        quantidade = (
            delta_abs > limiar
        ).sum()

        percentual = (
            100 * quantidade / len(delta_abs)
            if len(delta_abs) > 0
            else 0
        )

        print(
            f"|Δ umidade| > {limiar:2}: "
            f"{quantidade:6} "
            f"({percentual:6.2f}%)"
        )

    # --------------------------------------------------------
    # Maiores variações
    # --------------------------------------------------------

    maiores = (
        grupo
        .dropna(subset=["delta_moisture"])
        .sort_values(
            "abs_delta_moisture",
            ascending=False
        )
        .head(20)
        .copy()
    )

    maiores["line"] = linha
    maiores["generated_by"] = sensor

    if not maiores.empty:

        maiores_variacoes_todas.append(
            maiores[
                [
                    "line",
                    "generated_by",
                    "datetime_anterior",
                    "datetime",
                    "umidade_anterior",
                    "soil_moisture",
                    "delta_tempo_min",
                    "delta_moisture",
                    "abs_delta_moisture"
                ]
            ]
        )

    # --------------------------------------------------------
    # 6.3 FILTRO DOS INTERVALOS TEMPORAIS
    # --------------------------------------------------------

    intervalo_minimo = 1
    intervalo_maximo = 30

    grupo["intervalo_valido"] = (
        (grupo["delta_tempo_min"] > intervalo_minimo)
        & (grupo["delta_tempo_min"] <= intervalo_maximo)
    )

    print(
        f"\nLinha {linha} — Sensor {sensor}: "
        f"{grupo['intervalo_valido'].sum()} "
        f"intervalos válidos de {len(grupo)}"
    )

    # --------------------------------------------------------
    # Taxa de variação da umidade
    # --------------------------------------------------------

    grupo["delta_tempo_h"] = (
        grupo["delta_tempo_min"] / 60
    )

    grupo.loc[
        ~grupo["intervalo_valido"],
        "delta_tempo_h"
    ] = np.nan

    grupo["taxa_umidade_por_hora"] = (
        grupo["delta_moisture"]
        / grupo["delta_tempo_h"]
    )

    # --------------------------------------------------------
    # Apenas intervalos válidos
    # --------------------------------------------------------

    validos = grupo[
        grupo["intervalo_valido"]
    ].copy()

    # --------------------------------------------------------
    # Variações negativas de umidade
    # --------------------------------------------------------

    secagem = validos[
        validos["taxa_umidade_por_hora"] < 0
    ].copy()

    # --------------------------------------------------------
    # Armazena todas as variações válidas
    # --------------------------------------------------------

    if not validos.empty:

        variacoes_todas.append(
            validos[
                [
                    "line",
                    "generated_by",
                    "datetime_anterior",
                    "datetime",
                    "umidade_anterior",
                    "soil_moisture",
                    "delta_tempo_min",
                    "delta_moisture",
                    "taxa_umidade_por_hora"
                ]
            ]
        )

    # --------------------------------------------------------
    # Resultados
    # --------------------------------------------------------

    resultados_secagem.append({

        "line":
            linha,

        "generated_by":
            sensor,

        "intervalo_mediano_min":
            validos["delta_tempo_min"].median(),

        "intervalos_validos":
            len(validos),

        "intervalos_invalidos":
            (~grupo["intervalo_valido"]).sum(),

        "media_delta_umidade":
            validos["delta_moisture"].mean(),

        "mediana_taxa_variacao_por_hora":
            secagem[
                "taxa_umidade_por_hora"
            ].median(),

        "p01_taxa_variacao_por_hora":
            secagem[
                "taxa_umidade_por_hora"
            ].quantile(0.01),

        "p05_taxa_variacao_por_hora":
            secagem[
                "taxa_umidade_por_hora"
            ].quantile(0.05),

        "p25_taxa_variacao_por_hora":
            secagem[
                "taxa_umidade_por_hora"
            ].quantile(0.25),

        "p75_taxa_variacao_por_hora":
            secagem[
                "taxa_umidade_por_hora"
            ].quantile(0.75),

        "p95_taxa_variacao_por_hora":
            secagem[
                "taxa_umidade_por_hora"
            ].quantile(0.95),

        "p99_taxa_variacao_por_hora":
            secagem[
                "taxa_umidade_por_hora"
            ].quantile(0.99),

        "min_taxa_variacao_por_hora":
            secagem[
                "taxa_umidade_por_hora"
            ].min(),

        "eventos_reducao_umidade":
            len(secagem)
    })

# ------------------------------------------------------------
# SALVAR MAIORES VARIAÇÕES
# ------------------------------------------------------------

if maiores_variacoes_todas:

    maiores_variacoes_df = pd.concat(
        maiores_variacoes_todas,
        ignore_index=True
    )

    maiores_variacoes_df.to_csv(
        OUTPUT_DIR /
        "06_maiores_variacoes_umidade.csv",
        index=False
    )

# ------------------------------------------------------------
# SALVAR TODAS AS VARIAÇÕES VÁLIDAS
# ------------------------------------------------------------

if variacoes_todas:

    variacoes_df = pd.concat(
        variacoes_todas,
        ignore_index=True
    )

    variacoes_df.to_csv(
        OUTPUT_DIR /
        "06_variacoes_umidade.csv",
        index=False
    )

# ------------------------------------------------------------
# SALVAR RESULTADOS DA TAXA
# ------------------------------------------------------------

secagem_df = pd.DataFrame(
    resultados_secagem
)

print(
    "\nResumo da taxa de variação da umidade:"
)

print(
    secagem_df.to_string(index=False)
)

secagem_df.to_csv(
    OUTPUT_DIR /
    "06_taxa_secagem_solo.csv",
    index=False
)

# Média da taxa de secagem por sensor
taxas = (
    secagem_df
    .groupby(["line", "generated_by"])["mediana_taxa_variacao_por_hora"]
    .mean()
    .reset_index()
)

# Ordena primeiro pela linha e depois pelo sensor
taxas = taxas.sort_values(["line", "generated_by"])

# Posições das barras
x = np.arange(len(taxas))

# Uma cor para cada linha
cores_linhas = {
    1: "tab:blue",
    2: "tab:orange",
    3: "tab:green",
    4: "tab:red",
    5: "tab:purple"
}

cores = taxas["line"].map(cores_linhas)

# Gráfico
plt.figure(figsize=(12, 6))

plt.bar(
    x,
    taxas["mediana_taxa_variacao_por_hora"],
    color=cores
)

# Eixo X
plt.xticks(
    x,
    taxas["generated_by"],
    rotation=45,
    ha="right"
)

plt.xlabel("Sensor (generated_by)")
plt.ylabel("Taxa média de variação da umidade (%/h)")
plt.title("Taxa média de secagem por sensor")

# Linha horizontal em zero
plt.axhline(
    0,
    linewidth=1
)

# Legenda das linhas
handles = [
    plt.Rectangle((0, 0), 1, 1, color=cor)
    for cor in cores_linhas.values()
]

labels = [
    f"Linha {linha}"
    for linha in cores_linhas
]

plt.legend(
    handles,
    labels,
    title="Linha"
)

plt.tight_layout()

plt.savefig(
    OUTPUT_DIR /
    "06_taxa_secagem_por_sensor.png",
    dpi=300,
    bbox_inches="tight"
)

plt.show()

pausar_seguir()

# ============================================================
# 7. IDENTIFICAÇÃO DE EVENTOS DE IRRIGAÇÃO
# ============================================================

import _7_eventos_de_irrigacao as secao07

print_titulo("7. EVENTOS DE IRRIGAÇÃO")

coluna_valvula, coluna_volume = secao07.identificacao(integrada)

# ------------------------------------------------------------
# Verificação
# ------------------------------------------------------------

if coluna_valvula is None:
    print(
        "\nAviso: nenhuma coluna de estado da válvula "
        "foi encontrada."
    )

else:

    irrigacao = integrada.copy()

    # --------------------------------------------------------
    # Preparação
    # --------------------------------------------------------

    irrigacao["valve_state_numeric"] = pd.to_numeric(
        irrigacao[coluna_valvula],
        errors="coerce"
    )

    irrigacao["irrigando"] = (
        irrigacao["valve_state_numeric"] > 0
    )

    # --------------------------------------------------------
    # Identificação da leitura original da válvula
    # --------------------------------------------------------

    coluna_ts_valvula = (
        "valve_ts_generation"
        if "valve_ts_generation" in irrigacao.columns
        else None
    )

    coluna_id_valvula = (
        "valve_generated_by"
        if "valve_generated_by" in irrigacao.columns
        else None
    )

    # --------------------------------------------------------
    # Remoção das duplicações causadas pela integração
    # --------------------------------------------------------

    colunas_deduplicacao = ["line"]

    if coluna_ts_valvula is not None:

        colunas_deduplicacao.append(
            coluna_ts_valvula
        )

    else:

        colunas_deduplicacao.append(
            "datetime"
        )

    if coluna_id_valvula is not None:

        colunas_deduplicacao.append(
            coluna_id_valvula
        )

    irrigacao = (
        irrigacao
        .sort_values(
            ["line", "datetime"]
        )
        .drop_duplicates(
            subset=colunas_deduplicacao,
            keep="first"
        )
        .reset_index(drop=True)
    )

    # --------------------------------------------------------
    # Ordenação temporal
    # --------------------------------------------------------

    irrigacao = irrigacao.sort_values(
        ["line", "datetime"]
    ).reset_index(drop=True)

    # --------------------------------------------------------
    # Identificação do início dos eventos
    # --------------------------------------------------------

    irrigacao["inicio_evento"] = (
        irrigacao
        .groupby("line")["irrigando"]
        .transform(
            lambda s:
            s & ~s.shift(fill_value=False)
        )
    )

    eventos = irrigacao[
        irrigacao["inicio_evento"]
    ].copy()

    print(
        f"\nPossíveis eventos de irrigação: "
        f"{len(eventos)}"
    )

    # --------------------------------------------------------
    # Informações relevantes dos eventos
    # --------------------------------------------------------

    colunas_eventos = [
        "line",
        "datetime",
        "valve_state_numeric"
    ]

    if coluna_id_valvula is not None:

        colunas_eventos.append(
            coluna_id_valvula
        )

    if coluna_ts_valvula is not None:

        colunas_eventos.append(
            coluna_ts_valvula
        )

    if coluna_volume is not None:

        colunas_eventos.append(
            coluna_volume
        )

    eventos = eventos[
        [
            coluna
            for coluna in colunas_eventos
            if coluna in eventos.columns
        ]
    ]

    print("\nEventos identificados:")

    print(
        eventos.to_string(index=False)
    )

    eventos.to_csv(
        OUTPUT_DIR / "07_eventos_irrigacao.csv",
        index=False
    )

    # --------------------------------------------------------
    # Resumo por linha
    # --------------------------------------------------------

    eventos_por_linha = (
        eventos
        .groupby("line")
        .size()
        .rename("eventos_irrigacao")
        .reset_index()
    )

    print("\nEventos por linha:")

    print(
        eventos_por_linha.to_string(index=False)
    )

    eventos_por_linha.to_csv(
        OUTPUT_DIR /
        "07_eventos_irrigacao_por_linha.csv",
        index=False
    )

    # --------------------------------------------------------
    # Gráfico da válvula
    # --------------------------------------------------------

    fig, ax = plt.subplots(
        figsize=(12, 5)
    )

    for linha, grupo in (
        irrigacao.groupby("line")
    ):

        ax.step(
            grupo["datetime"],
            grupo["valve_state_numeric"],
            where="post",
            label=f"Linha {linha}",
            alpha=0.7
        )

    ax.set_title(
        "Ativação das válvulas de irrigação"
    )

    ax.set_xlabel("Tempo")
    ax.set_ylabel("Estado da válvula")

    ax.legend()

    ax.grid(
        True,
        alpha=0.3
    )

    salvar_figura(
        fig,
        "07_valvula_irrigacao.png",
        OUTPUT_DIR
    )

    plt.close(fig)

pausar_seguir()

# ============================================================
# 8. RELAÇÃO ENTRE IRRIGAÇÃO E RESPOSTA DO SOLO
# ============================================================

print_titulo("8. RESPOSTA DO SOLO À IRRIGAÇÃO")

if coluna_valvula is None:

    print(
        "\nAviso: coluna de estado da válvula não encontrada."
    )

else:

    resposta = integrada.copy()

    # --------------------------------------------------------
    # 8.1 Preparação
    # --------------------------------------------------------

    resposta["valve_state_numeric"] = pd.to_numeric(
        resposta[coluna_valvula],
        errors="coerce"
    )

    resposta["soil_moisture"] = pd.to_numeric(
        resposta["soil_humidity"],
        errors="coerce"
    )

    resposta["irrigando"] = (
        resposta["valve_state_numeric"] > 0
    )

    resposta = resposta.dropna(
        subset=[
            "datetime",
            "soil_moisture"
        ]
    )

    resposta = resposta.sort_values(
        ["line", "generated_by", "datetime"]
    ).reset_index(drop=True)

    # --------------------------------------------------------
    # 8.2 Variação da umidade
    # --------------------------------------------------------

    resposta["delta_moisture"] = (
        resposta
        .groupby(
            ["line", "generated_by"]
        )["soil_moisture"]
        .diff()
    )

    resposta["delta_tempo_min"] = (
        resposta
        .groupby(
            ["line", "generated_by"]
        )["datetime"]
        .diff()
        .dt.total_seconds()
        / 60
    )

    resposta["taxa_mudanca_umidade"] = (
        resposta["delta_moisture"]
        / resposta["delta_tempo_min"]
    )

    # --------------------------------------------------------
    # 8.3 Comparação durante / fora da irrigação
    #
    # ATENÇÃO:
    # esta análise é exploratória. As observações da válvula
    # aparecem duplicadas entre os sensores de uma mesma linha.
    # --------------------------------------------------------

    comparacao = (
        resposta
        .groupby("irrigando")["delta_moisture"]
        .agg(
            [
                "count",
                "mean",
                "median",
                "std",
                "min",
                "max"
            ]
        )
    )

    print(
        "\nVariação da umidade durante e fora "
        "da irrigação:"
    )

    print(
        comparacao.to_string()
    )

    comparacao.to_csv(
        OUTPUT_DIR /
        "08_resposta_irrigacao.csv"
    )

    # --------------------------------------------------------
    # 8.4 Resposta por linha e sensor
    # --------------------------------------------------------

    comparacao_sensor = (
        resposta
        .groupby(
            [
                "line",
                "generated_by",
                "irrigando"
            ]
        )["delta_moisture"]
        .agg(
            [
                "count",
                "mean",
                "median",
                "std",
                "min",
                "max"
            ]
        )
    )

    print(
        "\nVariação da umidade por linha, sensor "
        "e estado da irrigação:"
    )

    print(
        comparacao_sensor.to_string()
    )

    comparacao_sensor.to_csv(
        OUTPUT_DIR /
        "08_resposta_irrigacao_por_sensor.csv"
    )

    # ========================================================
    # 8.5 CONSTRUÇÃO DOS EVENTOS DE IRRIGAÇÃO
    # ========================================================
    #
    # Aqui NÃO usamos generated_by do sensor de solo.
    #
    # A válvula pertence à linha. Portanto, primeiro construímos
    # uma série única de eventos de irrigação por linha.
    #
    # Depois relacionamos cada evento aos dois sensores da linha.
    # ========================================================

    eventos_valvula = resposta[
        [
            "line",
            "datetime",
            "irrigando"
        ]
    ].drop_duplicates(
        subset=[
            "line",
            "datetime",
            "irrigando"
        ]
    )

    eventos_valvula = eventos_valvula.sort_values(
        ["line", "datetime"]
    ).reset_index(drop=True)

    eventos_valvula["inicio_irrigacao"] = (
        eventos_valvula
        .groupby("line")["irrigando"]
        .transform(
            lambda s:
            s & ~s.shift(fill_value=False)
        )
    )

    inicios = eventos_valvula[
        eventos_valvula["inicio_irrigacao"]
    ].copy()

    # ID único para cada evento físico de irrigação
    inicios["evento_irrigacao"] = range(
        1,
        len(inicios) + 1
    )

    print(
        f"\nEventos de irrigação identificados: "
        f"{len(inicios)}"
    )

    inicios.to_csv(
        OUTPUT_DIR /
        "08_eventos_irrigacao_unicos.csv",
        index=False
    )

    # ========================================================
    # 8.6 DURAÇÃO DOS EVENTOS
    # ========================================================

    eventos = []

    for linha, grupo in eventos_valvula.groupby("line"):

        grupo = grupo.sort_values(
            "datetime"
        ).reset_index(drop=True)

        indices_inicio = grupo.index[
            grupo["inicio_irrigacao"]
        ]

        for indice_inicio in indices_inicio:

            inicio = grupo.loc[
                indice_inicio,
                "datetime"
            ]

            depois = grupo[
                (grupo.index > indice_inicio)
                & (~grupo["irrigando"])
            ]

            if depois.empty:
                continue

            indice_fim = depois.index[0]

            fim = grupo.loc[
                indice_fim,
                "datetime"
            ]

            duracao = (
                fim - inicio
            ).total_seconds() / 60

            evento = inicios[
                (inicios["line"] == linha)
                & (
                    inicios["datetime"] == inicio
                )
            ]

            if evento.empty:
                continue

            evento_id = evento.iloc[0][
                "evento_irrigacao"
            ]

            eventos.append({
                "evento_irrigacao": int(evento_id),
                "line": linha,
                "inicio_irrigacao": inicio,
                "fim_irrigacao": fim,
                "duracao_min": duracao
            })

    eventos_df = pd.DataFrame(eventos)

    if not eventos_df.empty:

        print(
            "\nResumo da duração dos eventos:"
        )

        print(
            eventos_df[
                "duracao_min"
            ].describe().to_string()
        )

        eventos_df.to_csv(
            OUTPUT_DIR /
            "08_duracao_eventos_irrigacao.csv",
            index=False
        )

    # ========================================================
    # 8.7 RESPOSTA DOS SENSORES APÓS CADA EVENTO
    # ========================================================
    #
    # Para cada evento e para cada sensor da respectiva linha,
    # procuramos a leitura mais próxima de:
    #
    # +10, +20, +30, +60 e +120 minutos.
    #
    # Não exigimos exatamente esses horários: aceitamos a
    # leitura mais próxima dentro de uma tolerância.
    # ========================================================

    HORIZONTES = [
        10,
        20,
        30,
        60,
        120
    ]

    TOLERANCIA_RESPOSTA = 5

    respostas = []

    for _, evento in eventos_df.iterrows():

        linha = evento["line"]

        inicio = evento[
            "inicio_irrigacao"
        ]

        grupo_sensores = resposta[
            resposta["line"] == linha
        ]

        for sensor, grupo in grupo_sensores.groupby(
            "generated_by"
        ):

            grupo = grupo.sort_values(
                "datetime"
            ).reset_index(drop=True)

            # Leitura imediatamente anterior ao evento
            antes = grupo[
                grupo["datetime"] <= inicio
            ]

            if antes.empty:
                continue

            leitura_inicio = antes.iloc[-1]

            umidade_inicio = leitura_inicio[
                "soil_moisture"
            ]

            for horizonte in HORIZONTES:

                alvo = (
                    inicio
                    + pd.Timedelta(
                        minutes=horizonte
                    )
                )

                diferencas = (
                    grupo["datetime"] - alvo
                ).abs()

                if diferencas.empty:
                    continue

                indice = diferencas.idxmin()

                diferenca_min = (
                    diferencas.loc[indice]
                    .total_seconds()
                    / 60
                )

                if (
                    diferenca_min
                    > TOLERANCIA_RESPOSTA
                ):
                    continue

                leitura = grupo.loc[indice]

                umidade_depois = leitura[
                    "soil_moisture"
                ]

                respostas.append({
                    "evento_irrigacao":
                        evento["evento_irrigacao"],

                    "line":
                        linha,

                    "generated_by":
                        sensor,

                    "inicio_irrigacao":
                        inicio,

                    "fim_irrigacao":
                        evento["fim_irrigacao"],

                    "duracao_irrigacao_min":
                        evento["duracao_min"],

                    "horizonte_min":
                        horizonte,

                    "tempo_leitura_min":
                        (
                            leitura["datetime"]
                            - inicio
                        ).total_seconds()
                        / 60,

                    "umidade_inicio":
                        umidade_inicio,

                    "umidade_posterior":
                        umidade_depois,

                    "delta_umidade":
                        (
                            umidade_depois
                            - umidade_inicio
                        )
                })

    resposta_eventos_df = pd.DataFrame(
        respostas
    )

    # --------------------------------------------------------
    # 8.8 Resumo da resposta aos eventos
    # --------------------------------------------------------

    if not resposta_eventos_df.empty:

        print(
            "\nResposta da umidade após os eventos "
            "de irrigação:"
        )

        resumo_resposta = (
            resposta_eventos_df
            .groupby("horizonte_min")
            ["delta_umidade"]
            .agg(
                [
                    "count",
                    "mean",
                    "median",
                    "std",
                    "min",
                    "max"
                ]
            )
        )

        print(
            resumo_resposta.to_string()
        )

        resumo_resposta.to_csv(
            OUTPUT_DIR /
            "08_resumo_resposta_irrigacao.csv"
        )

        resposta_eventos_df.to_csv(
            OUTPUT_DIR /
            "08_resposta_apos_irrigacao.csv",
            index=False
        )

        # ----------------------------------------------------
        # Resposta por linha e sensor
        # ----------------------------------------------------

        resumo_sensor = (
            resposta_eventos_df
            .groupby(
                [
                    "line",
                    "generated_by",
                    "horizonte_min"
                ]
            )["delta_umidade"]
            .agg(
                [
                    "count",
                    "mean",
                    "median",
                    "std"
                ]
            )
        )

        resumo_sensor.to_csv(
            OUTPUT_DIR /
            "08_resposta_apos_irrigacao_por_sensor.csv"
        )

# ============================================================
# 8.8 RESPOSTA DO SOLO APÓS O TÉRMINO DA IRRIGAÇÃO
# ============================================================
#
# Complementa a análise anterior.
#
# Em vez de medir a resposta a partir do INÍCIO do evento,
# aqui usamos o FIM da irrigação como referência.
#
# Para cada evento e sensor da respectiva linha, calculamos:
#
#   - umidade no início
#   - umidade no fim da irrigação
#   - variação durante a irrigação
#   - variação após o término em:
#       +10, +20, +30, +60 e +120 min
#
# Isso permite separar:
#
#   resposta DURANTE a aplicação de água
#
# de:
#
#   comportamento do solo APÓS a aplicação de água.
# ============================================================

if not eventos_df.empty:

    HORIZONTES_POS_FIM = [
        10,
        20,
        30,
        60,
        120
    ]

    TOLERANCIA_POS_FIM = 5

    respostas_pos_fim = []

    for _, evento in eventos_df.iterrows():

        linha = evento["line"]

        inicio = evento[
            "inicio_irrigacao"
        ]

        fim = evento[
            "fim_irrigacao"
        ]

        grupo_sensores = resposta[
            resposta["line"] == linha
        ]

        for sensor, grupo in grupo_sensores.groupby(
            "generated_by"
        ):

            grupo = grupo.sort_values(
                "datetime"
            ).reset_index(drop=True)

            # ------------------------------------------------
            # Leitura imediatamente anterior ao início
            # ------------------------------------------------

            antes = grupo[
                grupo["datetime"] <= inicio
            ]

            # ------------------------------------------------
            # Leitura mais próxima do fim da irrigação
            # ------------------------------------------------

            durante = grupo[
                grupo["datetime"] <= fim
            ]

            if (
                antes.empty
                or durante.empty
            ):
                continue

            leitura_antes = antes.iloc[-1]
            leitura_fim = durante.iloc[-1]

            umidade_antes = (
                leitura_antes["soil_moisture"]
            )

            umidade_fim = (
                leitura_fim["soil_moisture"]
            )

            # Variação acumulada durante a irrigação
            delta_durante = (
                umidade_fim
                - umidade_antes
            )

            # ------------------------------------------------
            # Leituras após o término
            # ------------------------------------------------

            for horizonte in HORIZONTES_POS_FIM:

                alvo = (
                    fim
                    + pd.Timedelta(
                        minutes=horizonte
                    )
                )

                diferencas = (
                    grupo["datetime"] - alvo
                ).abs()

                if diferencas.empty:
                    continue

                indice = diferencas.idxmin()

                diferenca_min = (
                    diferencas.loc[indice]
                    .total_seconds()
                    / 60
                )

                if (
                    diferenca_min
                    > TOLERANCIA_POS_FIM
                ):
                    continue

                leitura_posterior = (
                    grupo.loc[indice]
                )

                umidade_posterior = (
                    leitura_posterior[
                        "soil_moisture"
                    ]
                )

                delta_pos_fim = (
                    umidade_posterior
                    - umidade_fim
                )

                delta_total = (
                    umidade_posterior
                    - umidade_antes
                )

                respostas_pos_fim.append({

                    "evento_irrigacao":
                        evento[
                            "evento_irrigacao"
                        ],

                    "line":
                        linha,

                    "generated_by":
                        sensor,

                    "inicio_irrigacao":
                        inicio,

                    "fim_irrigacao":
                        fim,

                    "duracao_irrigacao_min":
                        evento[
                            "duracao_min"
                        ],

                    "umidade_antes":
                        umidade_antes,

                    "umidade_fim":
                        umidade_fim,

                    "delta_durante":
                        delta_durante,

                    "horizonte_pos_fim_min":
                        horizonte,

                    "tempo_leitura_pos_fim_min":
                        (
                            leitura_posterior[
                                "datetime"
                            ] - fim
                        ).total_seconds()
                        / 60,

                    "umidade_posterior":
                        umidade_posterior,

                    "delta_pos_fim":
                        delta_pos_fim,

                    "delta_total":
                        delta_total
                })

    resposta_pos_fim_df = pd.DataFrame(
        respostas_pos_fim
    )

    # --------------------------------------------------------
    # Resumo geral
    # --------------------------------------------------------

    if not resposta_pos_fim_df.empty:

        resumo_pos_fim = (
            resposta_pos_fim_df
            .groupby(
                "horizonte_pos_fim_min"
            )[
                "delta_pos_fim"
            ]
            .agg(
                [
                    "count",
                    "mean",
                    "median",
                    "std",
                    "min",
                    "max"
                ]
            )
        )

        print(
            "\nResposta da umidade após o "
            "término da irrigação:"
        )

        print(
            resumo_pos_fim.to_string()
        )

        resumo_pos_fim.to_csv(
            OUTPUT_DIR /
            "08_resumo_resposta_pos_fim.csv"
        )

        resposta_pos_fim_df.to_csv(
            OUTPUT_DIR /
            "08_resposta_pos_fim.csv",
            index=False
        )

        # ----------------------------------------------------
        # Resumo por linha e sensor
        # ----------------------------------------------------

        resumo_pos_fim_sensor = (
            resposta_pos_fim_df
            .groupby(
                [
                    "line",
                    "generated_by",
                    "horizonte_pos_fim_min"
                ]
            )[
                "delta_pos_fim"
            ]
            .agg(
                [
                    "count",
                    "mean",
                    "median",
                    "std",
                    "min",
                    "max"
                ]
            )
        )

        resumo_pos_fim_sensor.to_csv(
            OUTPUT_DIR /
            "08_resposta_pos_fim_por_sensor.csv"
        )

        # ----------------------------------------------------
        # Resumo da variação durante a irrigação
        # ----------------------------------------------------

        resumo_durante = (
            resposta_pos_fim_df
            .groupby(
                [
                    "line",
                    "generated_by"
                ]
            )[
                "delta_durante"
            ]
            .agg(
                [
                    "count",
                    "mean",
                    "median",
                    "std",
                    "min",
                    "max"
                ]
            )
        )

        print(
            "\nVariação da umidade durante "
            "a irrigação, por sensor:"
        )

        print(
            resumo_durante.to_string()
        )

        resumo_durante.to_csv(
            OUTPUT_DIR /
            "08_variacao_durante_irrigacao_por_sensor.csv"
        )

        # ----------------------------------------------------
        # Gráfico da resposta após o término
        # ----------------------------------------------------

        fig, ax = plt.subplots(
            figsize=(10, 5)
        )

        dados_boxplot = []

        rotulos_boxplot = []

        for horizonte in HORIZONTES_POS_FIM:

            dados = (
                resposta_pos_fim_df.loc[
                    resposta_pos_fim_df[
                        "horizonte_pos_fim_min"
                    ] == horizonte,
                    "delta_pos_fim"
                ]
                .dropna()
            )

            if not dados.empty:

                dados_boxplot.append(
                    dados
                )

                rotulos_boxplot.append(
                    f"+{horizonte} min"
                )

        if dados_boxplot:

            ax.boxplot(
                dados_boxplot,
                tick_labels=rotulos_boxplot
            )

            ax.axhline(
                0,
                linestyle="--",
                linewidth=1
            )

            ax.set_title(
                "Resposta da umidade do solo "
                "após o término da irrigação"
            )

            ax.set_xlabel(
                "Tempo após término da irrigação"
            )

            ax.set_ylabel(
                "Δ umidade do solo"
            )

            ax.grid(
                True,
                alpha=0.3
            )

            salvar_figura(
                fig,
                "08_resposta_pos_fim_irrigacao.png",
                OUTPUT_DIR
            )

        plt.close(fig)

# ============================================================
# 8.10 GRÁFICO: DURANTE X FORA DA IRRIGAÇÃO
# ============================================================

fig, ax = plt.subplots(
    figsize=(10, 5)
)

if coluna_valvula is not None:

    dados_sem_irrigacao = (
        resposta.loc[
            ~resposta["irrigando"],
            "delta_moisture"
        ]
        .dropna()
    )

    dados_irrigando = (
        resposta.loc[
            resposta["irrigando"],
            "delta_moisture"
        ]
        .dropna()
    )

    ax.boxplot(
        [
            dados_sem_irrigacao,
            dados_irrigando
        ],
        tick_labels=[
            "Sem irrigação",
            "Irrigando"
        ]
    )

    ax.set_title(
        "Variação da umidade do solo "
        "durante e fora da irrigação"
    )

    ax.set_ylabel(
        "Δ umidade do solo"
    )

    ax.grid(
        True,
        alpha=0.3
    )

    salvar_figura(
        fig,
        "08_resposta_umidade_irrigacao.png",
        OUTPUT_DIR
    )

plt.close(fig)

pausar_seguir()

# ============================================================
# 9. PADRÃO DIURNO DA UMIDADE
# ============================================================

print_titulo("9. PADRÃO DIURNO DA UMIDADE")

diario = soil_analysis.copy()

# ------------------------------------------------------------
# Preparação
# ------------------------------------------------------------

diario["hora"] = (
    diario["datetime"]
    .dt.hour
)

# ------------------------------------------------------------
# Estatísticas gerais por hora
# ------------------------------------------------------------

padrao_diario = (
    diario
    .groupby("hora")[
        "soil_moisture"
    ]
    .agg(
        [
            "count",
            "mean",
            "median",
            "std",
            "min",
            "max"
        ]
    )
)

print(
    "\nUmidade por hora do dia:"
)

print(
    padrao_diario.to_string()
)

padrao_diario.to_csv(
    OUTPUT_DIR /
    "09_padrao_diurno_umidade.csv"
)

# ------------------------------------------------------------
# Estatísticas por linha e sensor
# ------------------------------------------------------------

if (
    "line" in diario.columns
    and "generated_by" in diario.columns
):

    padrao_diario_sensor = (
        diario
        .groupby(
            [
                "line",
                "generated_by",
                "hora"
            ]
        )["soil_moisture"]
        .agg(
            [
                "count",
                "mean",
                "median",
                "std",
                "min",
                "max"
            ]
        )
    )

    print(
        "\nPadrão diurno por linha e sensor:"
    )

    print(
        padrao_diario_sensor.to_string()
    )

    padrao_diario_sensor.to_csv(
        OUTPUT_DIR /
        "09_padrao_diurno_umidade_por_sensor.csv"
    )

# ------------------------------------------------------------
# Gráfico geral
# ------------------------------------------------------------

fig, ax = plt.subplots(
    figsize=(10, 5)
)

ax.plot(
    padrao_diario.index,
    padrao_diario["mean"],
    marker="o"
)

ax.set_title(
    "Variação média da umidade "
    "ao longo do dia"
)

ax.set_xlabel(
    "Hora do dia"
)

ax.set_ylabel(
    "Umidade média do solo"
)

ax.set_xticks(
    range(0, 24)
)

ax.grid(
    True,
    alpha=0.3
)

salvar_figura(
    fig,
    "09_padrao_diurno_umidade.png",
    OUTPUT_DIR
)

plt.close(fig)

# ------------------------------------------------------------
# Gráficos por sensor
# ------------------------------------------------------------

if (
    "line" in diario.columns
    and "generated_by" in diario.columns
):

    for (linha, sensor), grupo in (
        diario.groupby(
            ["line", "generated_by"]
        )
    ):

        horario_sensor = (
            grupo
            .groupby("hora")["soil_moisture"]
            .mean()
        )

        fig, ax = plt.subplots(
            figsize=(10, 5)
        )

        ax.plot(
            horario_sensor.index,
            horario_sensor.values,
            marker="o"
        )

        ax.set_title(
            f"Padrão diurno da umidade — "
            f"Linha {linha} — Sensor {sensor}"
        )

        ax.set_xlabel(
            "Hora do dia"
        )

        ax.set_ylabel(
            "Umidade média do solo"
        )

        ax.set_xticks(
            range(0, 24)
        )

        ax.grid(
            True,
            alpha=0.3
        )

        salvar_figura(
            fig,
            f"09_padrao_diurno_linha_{linha}_sensor_{sensor}.png",
            OUTPUT_DIR
        )

        plt.close(fig)

pausar_seguir()

# ============================================================
# 10. INFLUÊNCIA DAS VARIÁVEIS AMBIENTAIS
# ============================================================

print_titulo("10. INFLUÊNCIA AMBIENTAL")

coluna_temp_ambiente = encontrar_coluna(
    integrada,
    [
        "air_temperature",
        "env_temperature",
        "temperature"
    ]
)

coluna_umidade_ambiente = encontrar_coluna(
    integrada,
    [
        "air_humidity",
        "env_humidity",
        "humidity"
    ]
)

print(
    f"Temperatura ambiente: "
    f"{coluna_temp_ambiente}"
)

print(
    f"Umidade ambiente: "
    f"{coluna_umidade_ambiente}"
)

if (
    "soil_humidity" in integrada.columns
    and "line" in integrada.columns
    and "generated_by" in integrada.columns
):

    ambiental = integrada.copy()

    ambiental["soil_moisture"] = pd.to_numeric(
        ambiental["soil_humidity"],
        errors="coerce"
    )

    ambiental = (
        ambiental
        .dropna(subset=["datetime", "soil_moisture"])
        .sort_values(
            ["line", "generated_by", "datetime"]
        )
        .reset_index(drop=True)
    )

    # --------------------------------------------------------
    # Variação da umidade do solo
    # --------------------------------------------------------

    ambiental["delta_moisture"] = (
        ambiental
        .groupby(
            ["line", "generated_by"]
        )["soil_moisture"]
        .diff()
    )

    # --------------------------------------------------------
    # Temperatura ambiente
    # --------------------------------------------------------

    if coluna_temp_ambiente is not None:

        ambiental["ambient_temperature"] = pd.to_numeric(
            ambiental[coluna_temp_ambiente],
            errors="coerce"
        )

        corr_temp = (
            ambiental[
                [
                    "ambient_temperature",
                    "delta_moisture"
                ]
            ]
            .corr()
        )

        print(
            "\nCorrelação entre temperatura ambiente "
            "e variação da umidade do solo:"
        )

        print(
            corr_temp.to_string()
        )

    # --------------------------------------------------------
    # Umidade ambiente
    # --------------------------------------------------------

    if coluna_umidade_ambiente is not None:

        ambiental["ambient_humidity"] = pd.to_numeric(
            ambiental[coluna_umidade_ambiente],
            errors="coerce"
        )

        corr_humidity = (
            ambiental[
                [
                    "ambient_humidity",
                    "delta_moisture"
                ]
            ]
            .corr()
        )

        print(
            "\nCorrelação entre umidade ambiente "
            "e variação da umidade do solo:"
        )

        print(
            corr_humidity.to_string()
        )

    # --------------------------------------------------------
    # Correlação por sensor
    # --------------------------------------------------------

    correlacoes_sensor = []

    for (linha, sensor), grupo in ambiental.groupby(
        ["line", "generated_by"]
    ):

        registro = {
            "line": linha,
            "generated_by": sensor
        }

        if coluna_temp_ambiente is not None:

            dados_temp = grupo[
                [
                    "ambient_temperature",
                    "delta_moisture"
                ]
            ].dropna()

            registro["corr_temperatura"] = (
                dados_temp["ambient_temperature"]
                .corr(dados_temp["delta_moisture"])
            )

        if coluna_umidade_ambiente is not None:

            dados_humidity = grupo[
                [
                    "ambient_humidity",
                    "delta_moisture"
                ]
            ].dropna()

            registro["corr_umidade_ambiente"] = (
                dados_humidity["ambient_humidity"]
                .corr(dados_humidity["delta_moisture"])
            )

        correlacoes_sensor.append(registro)

    correlacoes_sensor_df = pd.DataFrame(
        correlacoes_sensor
    )

    print(
        "\nCorrelações por sensor:"
    )

    print(
        correlacoes_sensor_df.to_string(index=False)
    )

    # --------------------------------------------------------
    # Salvamento
    # --------------------------------------------------------

    correlacoes_sensor_df.to_csv(
        OUTPUT_DIR / "10_correlacoes_ambientais_por_sensor.csv",
        index=False
    )

    # --------------------------------------------------------
    # Gráficos de dispersão
    # --------------------------------------------------------

    if coluna_temp_ambiente is not None:

        dados_plot = ambiental[
            [
                "ambient_temperature",
                "delta_moisture"
            ]
        ].dropna()

        if not dados_plot.empty:

            fig = plt.figure(figsize=(8, 5))

            plt.scatter(
                dados_plot["ambient_temperature"],
                dados_plot["delta_moisture"],
                alpha=0.3
            )

            plt.xlabel(
                "Temperatura ambiente (°C)"
            )

            plt.ylabel(
                "Variação da umidade do solo"
            )

            plt.title(
                "Temperatura ambiente × "
                "Variação da umidade do solo"
            )

            plt.grid(True)

            salvar_figura(
                fig,
                "10_temperatura_vs_delta_umidade.png",
                OUTPUT_DIR
            )

            plt.close(fig)

    if coluna_umidade_ambiente is not None:

        dados_plot = ambiental[
            [
                "ambient_humidity",
                "delta_moisture"
            ]
        ].dropna()

        if not dados_plot.empty:

            fig = plt.figure(figsize=(8, 5))

            plt.scatter(
                dados_plot["ambient_humidity"],
                dados_plot["delta_moisture"],
                alpha=0.3
            )

            plt.xlabel(
                "Umidade ambiente (%)"
            )

            plt.ylabel(
                "Variação da umidade do solo"
            )

            plt.title(
                "Umidade ambiente × "
                "Variação da umidade do solo"
            )

            plt.grid(True)

            salvar_figura(
                fig,
                "10_umidade_ambiente_vs_delta_umidade.png",
                OUTPUT_DIR
            )

            plt.close(fig)

else:

    print(
        "\nDados de solo insuficientes para "
        "análise ambiental."
    )

pausar_seguir()

# ============================================================
# 11. CORRELAÇÕES DAS VARIÁVEIS CANDIDATAS
# ============================================================

print_titulo("11. CORRELAÇÕES DAS VARIÁVEIS CANDIDATAS")

# ------------------------------------------------------------
# Variáveis candidatas
# ------------------------------------------------------------

candidatas = [
    coluna
    for coluna in [
        "soil_humidity",
        "soil_temperature",
        "air_temperature",
        "air_humidity",
        "air_pressure",
        "air_co2",
        "valve_valve_state",
        "water_current_volume"
    ]
    if coluna in integrada.columns
]

print("\nVariáveis encontradas:")

for coluna in candidatas:
    print(f"  - {coluna}")

# ------------------------------------------------------------
# Conversão para numérico
# ------------------------------------------------------------

if candidatas:

    dados_correlacao = (
        integrada[candidatas]
        .apply(
            pd.to_numeric,
            errors="coerce"
        )
    )

    # Remover colunas completamente vazias
    dados_correlacao = dados_correlacao.dropna(
        axis=1,
        how="all"
    )

    if not dados_correlacao.empty:

        # ----------------------------------------------------
        # Matriz de correlação
        # ----------------------------------------------------

        correlacao = dados_correlacao.corr()

        print(
            "\nMatriz de correlação:"
        )

        print(
            correlacao.to_string()
        )

        correlacao.to_csv(
            OUTPUT_DIR / "11_correlacoes.csv"
        )

        # ----------------------------------------------------
        # Correlação com a umidade do solo
        # ----------------------------------------------------

        if "soil_humidity" in correlacao.columns:

            correlacao_umidade = (
                correlacao["soil_humidity"]
                .drop(
                    "soil_humidity"
                )
                .sort_values(
                    key=abs,
                    ascending=False
                )
            )

            print(
                "\nCorrelação das variáveis "
                "com a umidade do solo:"
            )

            print(
                correlacao_umidade.to_string()
            )

            correlacao_umidade.to_csv(
                OUTPUT_DIR
                / "11_correlacoes_com_umidade_solo.csv",
                header=["correlacao"]
            )

        # ----------------------------------------------------
        # Gráfico da matriz
        # ----------------------------------------------------

        fig = plt.figure(
            figsize=(
                max(8, len(correlacao.columns) * 1.2),
                max(6, len(correlacao.columns) * 1.0)
            )
        )

        plt.imshow(
            correlacao,
            interpolation="nearest",
            aspect="auto"
        )

        plt.colorbar(
            label="Correlação de Pearson"
        )

        plt.xticks(
            range(len(correlacao.columns)),
            correlacao.columns,
            rotation=45,
            ha="right"
        )

        plt.yticks(
            range(len(correlacao.index)),
            correlacao.index
        )

        plt.title(
            "Matriz de correlação "
            "das variáveis candidatas"
        )

        plt.tight_layout()

        salvar_figura(
            fig,
            "11_matriz_correlacoes.png",
            OUTPUT_DIR
        )

        plt.close()

    else:

        print(
            "\nNenhuma variável possui dados "
            "numéricos válidos."
        )

else:

    print(
        "\nNenhuma variável candidata "
        "foi encontrada."
    )

pausar_seguir()

# ============================================================
# 12. COMPARAÇÃO ENTRE LINHAS
# ============================================================

print_titulo("12. COMPARAÇÃO ENTRE LINHAS")

if (
    "line" in soil_analysis.columns
    and "soil_moisture" in soil_analysis.columns
):

    # --------------------------------------------------------
    # Estatísticas por linha
    # --------------------------------------------------------

    por_linha = (
        soil_analysis
        .groupby("line")["soil_moisture"]
        .agg(
            [
                "count",
                "mean",
                "median",
                "std",
                "min",
                "max"
            ]
        )
        .sort_index()
    )

    print(
        por_linha.to_string()
    )

    por_linha.to_csv(
        OUTPUT_DIR / "12_comparacao_linhas.csv"
    )

    # --------------------------------------------------------
    # Número de sensores por linha
    # --------------------------------------------------------

    sensores_por_linha = (
        soil_analysis
        .groupby("line")["generated_by"]
        .nunique()
        .rename("sensores")
    )

    sensores_por_linha.to_csv(
        OUTPUT_DIR / "12_sensores_por_linha.csv"
    )

    print(
        "\nNúmero de sensores por linha:"
    )

    print(
        sensores_por_linha.to_string()
    )

    # --------------------------------------------------------
    # Boxplot
    # --------------------------------------------------------

    dados_boxplot = [
        soil_analysis.loc[
            soil_analysis["line"] == linha,
            "soil_moisture"
        ].dropna()
        for linha in LINHAS
    ]

    fig, ax = plt.subplots(
        figsize=(9, 5)
    )

    ax.boxplot(
        dados_boxplot,
        tick_labels=[
            f"Linha {linha}"
            for linha in LINHAS
        ]
    )

    ax.set_title(
        "Distribuição da umidade do solo "
        "por linha de cultivo"
    )

    ax.set_xlabel("Linha")
    ax.set_ylabel("Umidade do solo (%)")

    ax.grid(
        True,
        alpha=0.3
    )

    salvar_figura(
        fig,
        "12_umidade_por_linha.png",
        OUTPUT_DIR
    )

    plt.close(fig)

else:

    print(
        "\nDados insuficientes para "
        "comparação entre linhas."
    )


# ============================================================

# 13. SÍNTESE PARA O MODELO

# ============================================================

print_titulo("13. SÍNTESE PARA O DESENVOLVIMENTO DO MODELO")

print(
"""
O EDA02 foi estruturado para responder às seguintes perguntas:

1. Como a umidade do solo evolui ao longo do tempo?

2. Qual é a velocidade aproximada de secagem do solo?

3. A secagem apresenta comportamento diferente
   entre as linhas de cultivo?

4. Quando a válvula é acionada, existe alteração
   mensurável na umidade do solo?

5. Existe relação entre volume de água aplicado
   e resposta do solo?

6. Temperatura e umidade ambiente ajudam a explicar
   a variação da umidade do solo?

7. Existem padrões diurnos de secagem?

8. Quais variáveis apresentam potencial para serem
   utilizadas no modelo computacional?

A partir dessas análises, uma hipótese de modelagem
particularmente relevante é prever a condição futura
do solo a partir do seu estado atual, condições ambientais
e histórico recente de irrigação.

Possíveis variáveis de entrada:

* umidade atual do solo;
* temperatura do solo;
* temperatura ambiente;
* umidade ambiente;
* estado da válvula;
* volume de água aplicado;
* horário;
* histórico recente da umidade.

Possíveis variáveis-alvo:

* umidade futura do solo;
* variação futura da umidade (ΔH);
* necessidade de irrigação.

A decisão final sobre o alvo deve ser tomada após observar
os resultados desta análise exploratória.
"""
)

# ============================================================

# FINAL

# ============================================================

print_titulo("EDA02 CONCLUÍDO")

print(
f"""
Os resultados foram salvos em:

{OUTPUT_DIR.resolve()}

Principais arquivos:

03_serie_temporal_integrada.csv
04_qualidade_dados_relevantes.csv
06_taxa_secagem_solo.csv
07_eventos_irrigacao.csv
08_resposta_irrigacao.csv
09_padrao_diurno_umidade.csv
11_correlacoes.csv
12_comparacao_linhas.csv

Além disso, os gráficos gerados foram salvos
na mesma pasta.
"""
)