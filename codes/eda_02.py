from pathlib import Path

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

# ============================================================

# CONFIGURAÇÃO

# ============================================================

BASE_DIR = Path(__file__).resolve().parent.parent

print(f"BASE_DIR: {BASE_DIR}")

DATA_DIR = (
BASE_DIR
/ "data"
/ "IoT Dataset from an Evolving Tomato Cultivation Te"
/ "IoT Dataset from an Evolving Tomato Cultivation Te"
)

OUTPUT_DIR = BASE_DIR / "outputs" / "eda02"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# ============================================================

# CONFIGURAÇÕES DA ANÁLISE

# ============================================================

# Ano principal da análise.

# 2025 possui a cadeia mais completa de dados.

ANO = 2025

# Linhas de cultivo presentes nos arquivos.

LINHAS = [1, 2, 3, 4, 5]

# Tolerância utilizada no alinhamento temporal.

# Dois registros com diferença menor ou igual a este valor

# serão considerados temporalmente correspondentes.

TOLERANCIA_ALINHAMENTO = "5min"

# ============================================================

# FUNÇÕES AUXILIARES

# ============================================================

def carregar_csv(nome):
    """
    Carrega um CSV do dataset e converte ts_generation
    para datetime.

    Esta conversão já foi investigada no EDA01. Aqui ela é
    utilizada apenas para possibilitar a construção da série
    temporal integrada.
    """

    caminho = DATA_DIR / nome

    if not caminho.exists():
        raise FileNotFoundError(f"Arquivo não encontrado: {caminho}")

    df = pd.read_csv(caminho)

    # Remove possíveis colunas de índice geradas pelo pandas.
    unnamed_columns = [
        col for col in df.columns
        if str(col).startswith("Unnamed")
    ]

    if unnamed_columns:
        df = df.drop(columns=unnamed_columns)

    # Conversão temporal.
    if "ts_generation" in df.columns:

        ts = pd.to_numeric(
            df["ts_generation"],
            errors="coerce"
        )

        df["datetime"] = pd.to_datetime(
            ts,
            unit="ms",
            errors="coerce"
        )

    return df

def salvar_figura(fig, nome):
    """
    Salva uma figura na pasta de saída.
    """


    caminho = OUTPUT_DIR / nome

    fig.savefig(
        caminho,
        dpi=150,
        bbox_inches="tight"
    )

    plt.close(fig)

    print(f"Figura salva: {caminho}")

def encontrar_coluna(df, candidatos):
    """
    Procura uma coluna utilizando uma lista de possíveis nomes.

    Retorna None caso nenhuma seja encontrada.
    """

    for candidato in candidatos:

        if candidato in df.columns:
            return candidato

    return None

def mostrar_colunas(df, nome):
    """
    Mostra as colunas disponíveis de um DataFrame.
    """


    print("\n" + "-" * 70)
    print(f"COLUNAS — {nome}")
    print("-" * 70)

    for coluna in df.columns:
        print(f"  - {coluna}")


# ============================================================

# 1. CARREGAMENTO DOS DADOS PRINCIPAIS

# ============================================================

print("\n" + "=" * 70)
print("1. CARREGAMENTO DOS DADOS")
print("=" * 70)

arquivos = {
"environmental": f"{ANO}/environmental{ANO}.csv",
"soil": f"{ANO}/soil{ANO}.csv",
"valve": f"{ANO}/valve_controller{ANO}.csv",
"water_meter": f"{ANO}/water_meter{ANO}.csv",
}

dados = {}

for nome, arquivo in arquivos.items():
    
    try:

        df = carregar_csv(arquivo)

        dados[nome] = df

        print(
            f"{nome:20s} -> "
            f"{len(df):8d} registros | "
            f"{len(df.columns):2d} colunas"
        )

        mostrar_colunas(df, nome)

    except FileNotFoundError as erro:

        print(f"\nAVISO: {erro}")


# ============================================================

# 2. VERIFICAÇÃO TEMPORAL

# ============================================================

print("\n" + "=" * 70)
print("2. VERIFICAÇÃO DA SÉRIE TEMPORAL")
print("=" * 70)

temporal_resumo = []

for nome, df in dados.items():


    if "datetime" not in df.columns:
        print(f"{nome}: sem coluna datetime.")
        continue

    datas = df["datetime"].dropna()

    if datas.empty:
        continue

    # Diferença entre registros consecutivos.
    diferencas = (
        datas
        .sort_values()
        .diff()
        .dt.total_seconds()
    )

    diferencas_validas = diferencas.dropna()

    print("\n" + "-" * 70)
    print(nome)
    print("-" * 70)

    print(f"Primeiro registro: {datas.min()}")
    print(f"Último registro:   {datas.max()}")

    if not diferencas_validas.empty:

        print(
            f"Intervalo mediano: "
            f"{diferencas_validas.median():.2f} s"
        )

        print(
            f"Intervalo médio:   "
            f"{diferencas_validas.mean():.2f} s"
        )

        print(
            f"Maior intervalo:   "
            f"{diferencas_validas.max():.2f} s"
        )

        # Considera como possível lacuna qualquer intervalo
        # superior a 10 vezes o intervalo mediano.
        mediana = diferencas_validas.median()

        if mediana > 0:

            limite_gap = mediana * 10

            gaps = diferencas_validas[
                diferencas_validas > limite_gap
            ]

            print(
                f"Possíveis lacunas (>10x mediana): "
                f"{len(gaps)}"
            )

    temporal_resumo.append({
        "arquivo": nome,
        "inicio": datas.min(),
        "fim": datas.max(),
        "intervalo_mediano_s": mediana,
        "intervalo_medio_s": diferencas_validas.mean(),
        "maior_intervalo_s": diferencas_validas.max(),
        "possiveis_gaps": len(gaps)
    })


    temporal_df = pd.DataFrame(temporal_resumo)

    temporal_df.to_csv(
    OUTPUT_DIR / "02_resumo_temporal.csv",
    index=False
    )

# ============================================================
# 3. CONSTRUÇÃO DA SÉRIE TEMPORAL INTEGRADA
# ============================================================

print("\n" + "=" * 70)
print("3. CONSTRUÇÃO DA SÉRIE TEMPORAL INTEGRADA")
print("=" * 70)

"""
A série integrada será construída utilizando o solo como
base temporal.

Para os sensores associados a uma linha específica:
    soil + valve + water_meter

o alinhamento será feito por:

    linha + datetime

Para o ambiente, como não existe identificação de linha,
o alinhamento será feito somente por:

    datetime

Não utilizamos a posição das linhas dos DataFrames, pois
cada sensor possui sua própria frequência de aquisição.
"""

# ------------------------------------------------------------
# Verificação
# ------------------------------------------------------------

if "soil" not in dados:
    raise RuntimeError(
        "O arquivo de solo é necessário para construir "
        "a série temporal integrada."
    )

# ------------------------------------------------------------
# SOLO — BASE DA INTEGRAÇÃO
# ------------------------------------------------------------

soil = dados["soil"].copy()

if "datetime" not in soil.columns:
    raise RuntimeError(
        "O arquivo de solo não possui datetime."
    )

# Identificação das colunas
coluna_linha_soil = encontrar_coluna(
    soil,
    ["line", "Line", "LINE"]
)

coluna_humidade = encontrar_coluna(
    soil,
    [
        "humidity",
        "soil_humidity",
        "soil_moisture",
        "moisture"
    ]
)

coluna_temperatura_solo = encontrar_coluna(
    soil,
    [
        "temperature",
        "soil_temperature"
    ]
)

print("\nColunas identificadas no solo:")
print(f"  Linha:              {coluna_linha_soil}")
print(f"  Umidade do solo:    {coluna_humidade}")
print(f"  Temperatura solo:   {coluna_temperatura_solo}")

if coluna_linha_soil is None:
    raise RuntimeError(
        "Não foi possível identificar a coluna de linha do solo."
    )

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
    .sort_values(["line", "datetime"])
    .reset_index(drop=True)
)

# ------------------------------------------------------------
# FUNÇÃO PARA INTEGRAR DADOS DE UM SENSOR POR LINHA
# ------------------------------------------------------------

def integrar_por_linha(base, outro, prefixo):

    if outro is None:
        return base

    if "datetime" not in outro.columns:
        print(
            f"\nAviso: dataset '{prefixo}' não possui datetime. "
            "Ignorado."
        )
        return base

    outro = outro.copy()

    # Detecta a coluna de linha
    coluna_linha = encontrar_coluna(
        outro,
        ["line", "Line", "LINE"]
    )

    if coluna_linha is None:
        print(
            f"\nAviso: dataset '{prefixo}' não possui "
            "identificação de linha. "
            "Integração por linha não realizada."
        )
        return base

    # Padroniza o nome da linha
    if coluna_linha != "line":
        outro = outro.rename(
            columns={coluna_linha: "line"}
        )

    outro = (
        outro
        .dropna(subset=["datetime"])
        .sort_values(["line", "datetime"])
        .reset_index(drop=True)
    )

    resultados = []

    # --------------------------------------------------------
    # Integração separada para cada linha
    # --------------------------------------------------------

    for linha in LINHAS:

        base_linha = base[
            base["line"] == linha
        ].copy()

        outro_linha = outro[
            outro["line"] == linha
        ].copy()

        if base_linha.empty:
            continue

        if outro_linha.empty:
            print(
                f"  Linha {linha}: sem dados em '{prefixo}'."
            )
            resultados.append(base_linha)
            continue

        # ----------------------------------------------------
        # Remover colunas que não devem entrar novamente
        # ----------------------------------------------------

        colunas_remover = [
            "line",
            "ts_generation",
            "generated_by"
        ]

        outro_linha = outro_linha.drop(
            columns=[
                col
                for col in colunas_remover
                if col in outro_linha.columns
            ]
        )

        # ----------------------------------------------------
        # Renomear variáveis do sensor
        # ----------------------------------------------------

        outras_colunas = [
            col
            for col in outro_linha.columns
            if col != "datetime"
        ]

        outro_linha = outro_linha.rename(
            columns={
                col: f"{prefixo}_{col}"
                for col in outras_colunas
            }
        )

        # ----------------------------------------------------
        # Merge temporal
        # ----------------------------------------------------

        unido = pd.merge_asof(
            base_linha.sort_values("datetime"),
            outro_linha.sort_values("datetime"),
            on="datetime",
            direction="nearest",
            tolerance=pd.Timedelta(
                TOLERANCIA_ALINHAMENTO
            )
        )

        resultados.append(unido)

    if not resultados:
        return base

    return (
        pd.concat(
            resultados,
            ignore_index=True
        )
        .sort_values(["line", "datetime"])
        .reset_index(drop=True)
    )


# ------------------------------------------------------------
# 3.1 INTEGRAR VÁLVULA
# ------------------------------------------------------------

if "valve" in dados:

    print("\nIntegrando válvula...")

    integrada = integrar_por_linha(
        soil,
        dados["valve"],
        "valve"
    )

    print(
        f"  Registros após integração: "
        f"{len(integrada)}"
    )

else:

    integrada = soil.copy()

    print("\nDataset de válvula não encontrado.")


# ------------------------------------------------------------
# 3.2 INTEGRAR HIDRÔMETRO
# ------------------------------------------------------------

if "water_meter" in dados:

    print("\nIntegrando hidrômetro...")

    integrada = integrar_por_linha(
        integrada,
        dados["water_meter"],
        "water"
    )

    print(
        f"  Registros após integração: "
        f"{len(integrada)}"
    )

else:

    print("\nDataset de hidrômetro não encontrado.")


# ------------------------------------------------------------
# 3.3 INTEGRAR DADOS AMBIENTAIS
# ------------------------------------------------------------

if "environmental" in dados:

    print("\nIntegrando dados ambientais...")

    environmental = dados["environmental"].copy()

    if "datetime" in environmental.columns:

        environmental = (
            environmental
            .dropna(subset=["datetime"])
            .sort_values("datetime")
            .reset_index(drop=True)
        )

        # ----------------------------------------------------
        # Renomear variáveis ambientais
        # ----------------------------------------------------

        environmental = environmental.rename(
            columns={
                "temperature": "air_temperature",
                "humidity": "air_humidity",
                "pressure": "air_pressure",
                "co2": "air_co2"
            }
        )

        # Manter somente variáveis úteis
        colunas_ambientais = [
            "datetime",
            "air_temperature",
            "air_humidity",
            "air_pressure",
            "air_co2"
        ]

        colunas_ambientais = [
            col
            for col in colunas_ambientais
            if col in environmental.columns
        ]

        environmental = environmental[
            colunas_ambientais
        ]

        # ----------------------------------------------------
        # Merge somente por tempo
        # ----------------------------------------------------

        integrada = pd.merge_asof(
            integrada.sort_values("datetime"),
            environmental,
            on="datetime",
            direction="nearest",
            tolerance=pd.Timedelta(
                TOLERANCIA_ALINHAMENTO
            )
        )

        # Restaurar ordenação por linha + tempo
        integrada = (
            integrada
            .sort_values(["line", "datetime"])
            .reset_index(drop=True)
        )

        print(
            f"  Registros após integração: "
            f"{len(integrada)}"
        )

    else:

        print(
            "  Aviso: environmental não possui datetime."
        )

else:

    print(
        "\nDataset ambiental não encontrado."
    )


# ------------------------------------------------------------
# 3.4 RESULTADO FINAL
# ------------------------------------------------------------

print("\n" + "-" * 70)
print("SÉRIE TEMPORAL INTEGRADA")
print("-" * 70)

print(
    f"Total de registros: {len(integrada)}"
)

print("\nColunas finais:")

for coluna in integrada.columns:
    print(f"  - {coluna}")


# ------------------------------------------------------------
# 3.5 VERIFICAÇÃO POR LINHA
# ------------------------------------------------------------

print("\nRegistros por linha:")

if "line" in integrada.columns:

    print(
        integrada["line"]
        .value_counts()
        .sort_index()
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

print(
    integrada
    .head(10)
    .to_string(index=False)
)


# ------------------------------------------------------------
# 3.7 SALVAR
# ------------------------------------------------------------

arquivo_saida = (
    OUTPUT_DIR /
    "03_serie_temporal_integrada.csv"
)

integrada.to_csv(
    arquivo_saida,
    index=False
)

print(
    f"\nArquivo salvo em:\n"
    f"{arquivo_saida.resolve()}"
)

# ============================================================
# 4. QUALIDADE DOS DADOS RELEVANTES AO PROBLEMA
# ============================================================

print("\n" + "=" * 70)
print("4. QUALIDADE DOS DADOS RELEVANTES")
print("=" * 70)

qualidade = []

colunas_interesse = []

for coluna in integrada.columns:
    nome = coluna.lower()

    if any(
        termo in nome
        for termo in [
            "humidity",
            "moisture",
            "temperature",
            "pressure",
            "valve",
            "volume",
            "water"
        ]
    ):
        colunas_interesse.append(coluna)

# Avalia cada coluna UMA única vez
for coluna in colunas_interesse:

    serie = pd.to_numeric(
        integrada[coluna],
        errors="coerce"
    )

    qualidade.append({
        "coluna": coluna,
        "registros": len(serie),
        "validos": serie.notna().sum(),
        "ausentes": serie.isna().sum(),
        "percentual_ausente":
            100 * serie.isna().mean(),
        "zeros":
            (serie == 0).sum(),
        "percentual_zero":
            100 * (serie == 0).mean()
    })

qualidade_df = pd.DataFrame(qualidade)

print(qualidade_df.to_string(index=False))

qualidade_df.to_csv(
    OUTPUT_DIR / "04_qualidade_dados_relevantes.csv",
    index=False
)

# ============================================================
# 5. ANÁLISE DA UMIDADE DO SOLO
# ============================================================

print("\n" + "=" * 70)
print("5. DINÂMICA DA UMIDADE DO SOLO")
print("=" * 70)

# ------------------------------------------------------------
# Preparação
# ------------------------------------------------------------

soil_analysis = soil.copy()

if "soil_humidity" not in soil_analysis.columns:
    raise RuntimeError(
        "A coluna 'soil_humidity' não foi encontrada "
        "no dataset de solo."
    )

soil_analysis["soil_moisture"] = pd.to_numeric(
    soil_analysis["soil_humidity"],
    errors="coerce"
)

soil_analysis = soil_analysis.dropna(
    subset=["datetime", "soil_moisture"]
)

# ------------------------------------------------------------
# Estatísticas
# ------------------------------------------------------------

print("\nEstatísticas da umidade do solo:")

print(
    soil_analysis["soil_moisture"]
    .describe()
    .to_string()
)

# ------------------------------------------------------------
# Estatísticas por linha
# ------------------------------------------------------------

if "line" in soil_analysis.columns:

    print("\nEstatísticas por linha:")

    estatisticas_linha = (
        soil_analysis
        .groupby("line")["soil_moisture"]
        .describe()
    )

    print(
        estatisticas_linha.to_string()
    )

    estatisticas_linha.to_csv(
        OUTPUT_DIR /
        "05_estatisticas_umidade_por_linha.csv"
    )

# ------------------------------------------------------------
# Gráfico geral
# ------------------------------------------------------------

fig, ax = plt.subplots(figsize=(12, 5))

if "line" in soil_analysis.columns:

    for linha, grupo in soil_analysis.groupby("line"):

        ax.plot(
            grupo["datetime"],
            grupo["soil_moisture"],
            label=f"Linha {linha}",
            alpha=0.7
        )

    ax.legend()

else:

    ax.plot(
        soil_analysis["datetime"],
        soil_analysis["soil_moisture"]
    )

ax.set_title(
    "Evolução temporal da umidade do solo"
)

ax.set_xlabel("Tempo")
ax.set_ylabel("Umidade do solo")

ax.grid(
    True,
    alpha=0.3
)

salvar_figura(
    fig,
    "05_umidade_solo_temporal.png"
)

plt.close(fig)


# ============================================================
# 6. DINÂMICA TEMPORAL DA UMIDADE DO SOLO
# ============================================================

print("\n" + "=" * 70)
print("6. DINÂMICA TEMPORAL DA UMIDADE DO SOLO")
print("=" * 70)

drying = soil_analysis.copy()

drying = drying.sort_values(
    ["line", "datetime"]
).reset_index(drop=True)


# ------------------------------------------------------------
# 6.1 FREQUÊNCIA DE AMOSTRAGEM DO SENSOR
# ------------------------------------------------------------

print("\n" + "-" * 70)
print("FREQUÊNCIA DE AMOSTRAGEM DO SENSOR DE UMIDADE")
print("-" * 70)

drying["intervalo_min"] = (
    drying
    .groupby("line")["datetime"]
    .diff()
    .dt.total_seconds()
    / 60
)

frequencia_sensor = (
    drying
    .groupby("line")["intervalo_min"]
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

print("\nIntervalo mediano por linha:")

for linha in LINHAS:
    valores = drying.loc[
        drying["line"] == linha,
        "intervalo_min"
    ].dropna()

    if valores.empty:
        continue

    print(
        f"  Linha {linha}: "
        f"{valores.median():.3f} min"
    )


# ------------------------------------------------------------
# DISTRIBUIÇÃO DOS INTERVALOS
# ------------------------------------------------------------

fig, ax = plt.subplots(figsize=(10, 5))

for linha, grupo in drying.groupby("line"):

    intervalos = grupo["intervalo_min"].dropna()

    intervalos = intervalos[
        intervalos > 0
    ]

    ax.hist(
        intervalos,
        bins=100,
        alpha=0.5,
        label=f"Linha {linha}"
    )

ax.set_title(
    "Distribuição dos intervalos entre leituras "
    "do sensor de umidade"
)

ax.set_xlabel(
    "Intervalo entre leituras (min)"
)

ax.set_ylabel("Frequência")

ax.legend()
ax.grid(True, alpha=0.3)

salvar_figura(
    fig,
    "06_frequencia_sensor.png"
)


# ------------------------------------------------------------
# 6.2 VARIAÇÃO DA UMIDADE ENTRE LEITURAS
# ------------------------------------------------------------

resultados_secagem = []

maiores_variacoes_todas = []

for linha, grupo in drying.groupby("line"):

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
        f"\nLinha {linha} — variações de umidade:"
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

    limiares = [1, 2, 5, 10, 15, 20, 30]

    delta_abs = (
        grupo["delta_moisture"]
        .abs()
        .dropna()
    )

    print(f"\nLinha {linha}")
    print("-" * 60)

    for limiar in limiares:

        quantidade = (
            delta_abs > limiar
        ).sum()

        percentual = (
            100 * quantidade / len(delta_abs)
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

    maiores_variacoes_todas.append(
        maiores[
            [
                "line",
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
        f"\nLinha {linha}: "
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


    # Apenas reduções da umidade
    secagem = validos[
        validos["taxa_umidade_por_hora"] < 0
    ].copy()


    # --------------------------------------------------------
    # Resultados
    # --------------------------------------------------------

    resultados_secagem.append({

        "linha":
            linha,

        "intervalo_mediano_min":
            validos["delta_tempo_min"].median(),

        "intervalos_validos":
            grupo["intervalo_valido"].sum(),

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

maiores_variacoes_df = pd.concat(
    maiores_variacoes_todas,
    ignore_index=True
)

maiores_variacoes_df.to_csv(
    OUTPUT_DIR / "06_maiores_variacoes_umidade.csv",
    index=False
)


# ------------------------------------------------------------
# SALVAR RESULTADOS DA TAXA
# ------------------------------------------------------------

secagem_df = pd.DataFrame(
    resultados_secagem
)

print("\nResumo da taxa de variação da umidade:")
print(
    secagem_df.to_string(index=False)
)

secagem_df.to_csv(
    OUTPUT_DIR / "06_taxa_secagem_solo.csv",
    index=False
)

# ============================================================

# 7. IDENTIFICAÇÃO DE EVENTOS DE IRRIGAÇÃO

# ============================================================

print("\n" + "=" * 70)
print("7. EVENTOS DE IRRIGAÇÃO")
print("=" * 70)

coluna_valvula = encontrar_coluna(
integrada,
[
"valve_valve_state",
"valve_state",
"valve_valveState",
"valve_state_value"
]
)

coluna_volume = encontrar_coluna(
integrada,
[
"water_current_volume",
"current_volume",
"water_volume",
"volume"
]
)

print(f"Coluna da válvula: {coluna_valvula}")
print(f"Coluna de volume:  {coluna_volume}")

if coluna_valvula is not None:
    irrigacao = integrada.copy()

    irrigacao["valve_state_numeric"] = pd.to_numeric(
        irrigacao[coluna_valvula],
        errors="coerce"
    )

    irrigacao["irrigando"] = (
        irrigacao["valve_state_numeric"] > 0
    )

    irrigacao = irrigacao.sort_values(
        ["line", "datetime"]
    ).reset_index(drop=True)

    irrigacao["inicio_evento"] = (
        irrigacao
        .groupby("line")["irrigando"]
        .transform(
            lambda s: s & ~s.shift(fill_value=False)
        )
    )

    eventos = irrigacao[
        irrigacao["inicio_evento"]
    ].copy()

    print(
        f"Possíveis eventos de irrigação: "
        f"{len(eventos)}"
    )

    eventos.to_csv(
        OUTPUT_DIR / "07_eventos_irrigacao.csv",
        index=False
    )

# --------------------------------------------------------
# Gráfico de válvula
# --------------------------------------------------------

fig, ax = plt.subplots(figsize=(12, 4))

ax.step(
    irrigacao["datetime"],
    irrigacao["valve_state_numeric"],
    where="post"
)

ax.set_title(
    "Ativação da válvula de irrigação"
)

ax.set_xlabel("Tempo")
ax.set_ylabel("Estado da válvula")

ax.grid(True, alpha=0.3)

salvar_figura(
    fig,
    "07_valvula_irrigacao.png"
)

# ============================================================

# 8. RELAÇÃO ENTRE IRRIGAÇÃO E RESPOSTA DO SOLO

# ============================================================

print("\n" + "=" * 70)
print("8. RESPOSTA DO SOLO À IRRIGAÇÃO")
print("=" * 70)

if (
coluna_valvula is not None
and coluna_humidade is not None
):
    resposta = integrada.copy()

    resposta["valve_state_numeric"] = pd.to_numeric(
        resposta[coluna_valvula],
        errors="coerce"
    )

    resposta["soil_moisture"] = pd.to_numeric(
        resposta[
            "soil_humidity"
        ],
        errors="coerce"
    )

    resposta["irrigando"] = (
        resposta["valve_state_numeric"] > 0
    )

    resposta = resposta.sort_values(
    ["line", "datetime"]
    ).reset_index(drop=True)

    # --------------------------------------------------------
    # Variação da umidade
    # --------------------------------------------------------

    resposta["delta_moisture"] = (
        resposta
        .groupby("line")["soil_moisture"]
        .diff()
    )

    resposta["delta_tempo_min"] = (
        resposta
        .groupby("line")["datetime"]
        .diff()
        .dt.total_seconds()
        / 60
    )

    resposta["taxa_mudanca_umidade"] = (
        resposta["delta_moisture"]
        / resposta["delta_tempo_min"]
    )

    # --------------------------------------------------------
    # Comparação irrigando x não irrigando
    # --------------------------------------------------------

    comparacao = (
        resposta
        .groupby("irrigando")[
            "delta_moisture"
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
        "\nVariação da umidade durante os estados "
        "de irrigação:"
    )

    print(comparacao.to_string())

    comparacao.to_csv(
        OUTPUT_DIR / "08_resposta_irrigacao.csv"
    )

# --------------------------------------------------------
# Gráfico
# --------------------------------------------------------

fig, ax = plt.subplots(figsize=(10, 5))

ax.boxplot(
    [
        resposta.loc[
            ~resposta["irrigando"],
            "delta_moisture"
        ].dropna(),

        resposta.loc[
            resposta["irrigando"],
            "delta_moisture"
        ].dropna()
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

ax.grid(True, alpha=0.3)

salvar_figura(
    fig,
    "08_resposta_umidade_irrigacao.png"
)


# ============================================================

# 9. PADRÃO DIURNO

# ============================================================

print("\n" + "=" * 70)
print("9. PADRÃO DIURNO DA UMIDADE")
print("=" * 70)

if coluna_humidade is not None:
    diario = soil_analysis.copy()

    diario["hora"] = (
        diario["datetime"]
        .dt.hour
    )

    padrao_diario = (
        diario
        .groupby("hora")[
            "soil_moisture"
        ]
        .agg(
            [
                "mean",
                "median",
                "std",
                "min",
                "max"
            ]
        )
    )

    print(
        "\nUmidade média por hora do dia:"
    )

    print(
        padrao_diario.to_string()
    )

    padrao_diario.to_csv(
        OUTPUT_DIR / "09_padrao_diurno_umidade.csv"
    )

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

    ax.set_xlabel("Hora do dia")
    ax.set_ylabel("Umidade média do solo")

    ax.set_xticks(range(0, 24))

    ax.grid(True, alpha=0.3)

    salvar_figura(
        fig,
        "09_padrao_diurno_umidade.png"
    )


# ============================================================

# 10. INFLUÊNCIA DAS VARIÁVEIS AMBIENTAIS

# ============================================================

print("\n" + "=" * 70)
print("10. INFLUÊNCIA AMBIENTAL")
print("=" * 70)

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

if coluna_humidade is not None:
    ambiental = integrada.copy()

    ambiental["soil_moisture"] = pd.to_numeric(
        ambiental["soil_humidity"],
        errors="coerce"
    )

    ambiental = ambiental.sort_values(
        ["line", "datetime"]
    ).reset_index(drop=True)

    ambiental["delta_moisture"] = (
        ambiental
        .groupby("line")["soil_moisture"]
        .diff()
    )

    if coluna_temp_ambiente is not None:

        ambiental["ambient_temperature"] = pd.to_numeric(
            ambiental[coluna_temp_ambiente],
            errors="coerce"
        )

        corr_temp = ambiental[
            [
                "ambient_temperature",
                "delta_moisture"
            ]
        ].corr()

        print(
            "\nCorrelação entre temperatura "
            "e variação da umidade:"
        )

        print(corr_temp.to_string())

    if coluna_umidade_ambiente is not None:

        ambiental["ambient_humidity"] = pd.to_numeric(
            ambiental[coluna_umidade_ambiente],
            errors="coerce"
        )

        corr_humidity = ambiental[
            [
                "ambient_humidity",
                "delta_moisture"
            ]
        ].corr()

        print(
            "\nCorrelação entre umidade ambiente "
            "e variação da umidade do solo:"
        )

        print(
            corr_humidity.to_string()
        )


# ============================================================

# 11. CORRELAÇÕES DAS VARIÁVEIS CANDIDATAS

# ============================================================

print("\n" + "=" * 70)
print("11. CORRELAÇÕES DAS VARIÁVEIS CANDIDATAS")
print("=" * 70)

candidatas = []

for coluna in integrada.columns:

    nome = coluna.lower()

    if any(
        termo in nome
        for termo in [
            "soil",
            "humidity",
            "moisture",
            "temperature",
            "pressure",
            "volume",
            "valve"
        ]
    ):
        serie = pd.to_numeric(
            integrada[coluna],
            errors="coerce"
        )

        if serie.notna().sum() > 10:
            candidatas.append(coluna)

if candidatas:

    correlacao = (
        integrada[candidatas]
        .apply(
            pd.to_numeric,
            errors="coerce"
        )
        .corr()
    )

    print(correlacao.to_string())

    correlacao.to_csv(
        OUTPUT_DIR / "11_correlacoes.csv"
    )

# ============================================================

# 12. COMPARAÇÃO ENTRE LINHAS

# ============================================================

print("\n" + "=" * 70)
print("12. COMPARAÇÃO ENTRE LINHAS")
print("=" * 70)

if (
coluna_linha_soil is not None
and coluna_humidade is not None
):


    por_linha = (
        soil_analysis
        .groupby("line")[
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
        por_linha.to_string()
    )

    por_linha.to_csv(
        OUTPUT_DIR / "12_comparacao_linhas.csv"
    )

    fig, ax = plt.subplots(
        figsize=(9, 5)
    )

    ax.boxplot(
        [
            soil_analysis.loc[
                soil_analysis[
                    coluna_linha_soil
                ] == linha,
                "soil_moisture"
            ].dropna()
            for linha in LINHAS
        ],
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
    ax.set_ylabel("Umidade do solo")

    ax.grid(True, alpha=0.3)

    salvar_figura(
        fig,
        "12_umidade_por_linha.png"
    )


# ============================================================

# 13. SÍNTESE PARA O MODELO

# ============================================================

print("\n" + "=" * 70)
print("13. SÍNTESE PARA O DESENVOLVIMENTO DO MODELO")
print("=" * 70)

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

print("\n" + "=" * 70)
print("EDA02 CONCLUÍDO")
print("=" * 70)

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
