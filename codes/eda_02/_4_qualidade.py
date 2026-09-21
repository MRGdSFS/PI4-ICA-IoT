import pandas as pd

def teste_qualidade(integrada):

    qualidade = []

    # --------------------------------------------------------
    # 1. Identificação das colunas relevantes
    # --------------------------------------------------------

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

    # --------------------------------------------------------
    # 2. Qualidade geral das variáveis
    # --------------------------------------------------------

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
            "zeros": (serie == 0).sum(),
            "percentual_zero":
                100 * (serie == 0).mean()
        })

    qualidade_df = pd.DataFrame(qualidade)

    # --------------------------------------------------------
    # 3. Qualidade dos sensores de solo
    # --------------------------------------------------------

    qualidade_solo = []

    colunas_solo = [
        coluna
        for coluna in [
            "soil_humidity",
            "soil_temperature"
        ]
        if coluna in integrada.columns
    ]

    if (
        colunas_solo
        and "line" in integrada.columns
        and "generated_by" in integrada.columns
    ):

        agrupamento = integrada.groupby(
            ["line", "generated_by"],
            dropna=False
        )

        for (linha, sensor), grupo in agrupamento:

            for coluna in colunas_solo:

                serie = pd.to_numeric(
                    grupo[coluna],
                    errors="coerce"
                )

                qualidade_solo.append({
                    "line": linha,
                    "generated_by": sensor,
                    "coluna": coluna,
                    "registros": len(serie),
                    "validos": serie.notna().sum(),
                    "ausentes": serie.isna().sum(),
                    "percentual_ausente":
                        100 * serie.isna().mean(),
                    "zeros": (serie == 0).sum(),
                    "percentual_zero":
                        100 * (serie == 0).mean()
                })

    qualidade_solo_df = pd.DataFrame(qualidade_solo)

    return qualidade_df, qualidade_solo_df 