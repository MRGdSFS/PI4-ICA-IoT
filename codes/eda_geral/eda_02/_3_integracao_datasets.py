import pandas as pd

from config import LINHAS, TOLERANCIA_ALINHAMENTO

from utils import encontrar_coluna
from utils import integrar_por_linha

def verificacao(dados):
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

    if "generated_by" not in soil.columns:
        raise RuntimeError(
            "O arquivo de solo não possui generated_by."
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
    print("  Sensor:      generated_by")
    print(f"  Umidade do solo:    {coluna_humidade}")
    print(f"  Temperatura solo:   {coluna_temperatura_solo}")

    if coluna_linha_soil is None:
        raise RuntimeError(
            "Não foi possível identificar a coluna de linha do solo."
        )

    if coluna_humidade is None:
        raise RuntimeError(
            "Não foi possível identificar a umidade do solo."
        )

    if coluna_temperatura_solo is None:
        raise RuntimeError(
            "Não foi possível identificar a temperatura do solo."
        )

    return soil, coluna_linha_soil, coluna_humidade, coluna_temperatura_solo

def integrar_valvula(dados, soil):
    print("\nIntegrando válvula...")

    integrada = integrar_por_linha(
        soil,
        dados["valve"],
        "valve",
        LINHAS,
        TOLERANCIA_ALINHAMENTO
    )

    print(
        f"  Registros após integração: "
        f"{len(integrada)}"
    )
    return integrada

def integrar_hidrometro(dados, soil, integrada):

    print("\nIntegrando hidrômetro...")

    integrada = integrar_por_linha(
        integrada,
        dados["water_meter"],
        "water",
        LINHAS,
        TOLERANCIA_ALINHAMENTO
    )

    print(
        f"  Registros após integração: "
        f"{len(integrada)}"
    )
    return integrada

def integrar_ambiental(dados, soil, integrada):
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

        # ----------------------------------------------------
        # Preservar sensores do ambiente
        # ----------------------------------------------------

        environmental = environmental.rename(
            columns={
                "generated_by": "environmental_generated_by",
                "ts_generation": "environmental_ts_generation"
            }
        )

        # ----------------------------------------------------
        # Manter variáveis relevantes
        # ----------------------------------------------------

        colunas_ambientais = [
            "datetime",
            "environmental_generated_by",
            "environmental_ts_generation",
            "air_temperature",
            "air_humidity",
            "air_pressure",
            "air_co2"
        ]

        colunas_ambientais = [
            coluna
            for coluna in colunas_ambientais
            if coluna in environmental.columns
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

        # ----------------------------------------------------
        # Restaurar ordenação
        # ----------------------------------------------------

        integrada = (
            integrada
            .sort_values(
                ["line", "generated_by", "datetime"]
            )
            .reset_index(drop=True)
        )

        print(
            f"  Registros após integração: "
            f"{len(integrada)}"
        )
        return integrada
    else:

        print(
            "  Aviso: environmental não possui datetime."
        )
