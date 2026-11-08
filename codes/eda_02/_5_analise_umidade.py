from config import OUTPUT_DIR
from utils import salvar_figura

import pandas as pd
import matplotlib.pyplot as plt

fig, ax = plt.subplots(figsize=(12,5))

def preparacao(soil):
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

    soil_analysis = soil_analysis.sort_values(
        ["line", "generated_by", "datetime"]
    )
    
    return soil_analysis

def estatisticas_gerais(soil_analysis):
    estatisticas_gerais = (soil_analysis["soil_moisture"].describe())
    print(estatisticas_gerais.to_string())
    estatisticas_gerais.to_frame(name="soil_moisture").to_csv(OUTPUT_DIR / "05_estatisticas_umidade_geral.csv")

def estatisticas_por_linha(soil_analysis):
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

def estatisticas_por_sensor(soil_analysis):
    print("\nEstatísticas por sensor:")

    estatisticas_sensor = (
        soil_analysis
        .groupby(
            ["line", "generated_by"]
        )["soil_moisture"]
        .describe()
    )

    print(
        estatisticas_sensor.to_string()
    )

    estatisticas_sensor.to_csv(
        OUTPUT_DIR /
        "05_estatisticas_umidade_por_sensor.csv"
    )

def graf_por_linha(soil_analysis):
    if "line" in soil_analysis.columns:

        for linha, grupo in soil_analysis.groupby("line"):

            ax.plot(
                grupo["datetime"],
                grupo["soil_moisture"],
                label=f"Linha {linha}",
                alpha=0.7
            )

    else:

        ax.plot(
            soil_analysis["datetime"],
            soil_analysis["soil_moisture"]
        )

    ax.set_title(
        "Evolução temporal da umidade do solo por linha"
    )

    ax.set_xlabel("Tempo")
    ax.set_ylabel("Umidade do solo")

    ax.legend()
    ax.grid(
        True,
        alpha=0.3
    )

    salvar_figura(
        fig,
        "05_umidade_solo_temporal_por_linha.png",
        OUTPUT_DIR
    )

    plt.close(fig)

def graf_por_sensor(soil_analysis):
    if (
        "line" in soil_analysis.columns
        and "generated_by" in soil_analysis.columns
    ):

        for (linha, sensor), grupo in soil_analysis.groupby(
            ["line", "generated_by"]
        ):

            fig, ax = plt.subplots(
                figsize=(12, 5)
            )

            ax.plot(
                grupo["datetime"],
                grupo["soil_moisture"],
                alpha=0.7
            )

            ax.set_title(
                f"Umidade do solo — Linha {linha} — "
                f"Sensor {sensor}"
            )

            ax.set_xlabel("Tempo")
            ax.set_ylabel("Umidade do solo")

            ax.grid(
                True,
                alpha=0.3
            )

            salvar_figura(
                fig,
                f"05_umidade_solo_linha_{linha}_sensor_{sensor}.png",
                OUTPUT_DIR
            )

            plt.close(fig)
