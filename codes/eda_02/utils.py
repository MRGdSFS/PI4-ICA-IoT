import os
import pandas as pd
import matplotlib.pyplot as plt

def carregar_csv(nome, DATA_DIR):
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

def salvar_figura(fig, nome, OUTPUT_DIR):
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

def integrar_por_linha(base,outro,prefixo,LINHAS,TOLERANCIA_ALINHAMENTO):
    if outro is None:
        return base

    if "datetime" not in outro.columns:
        print(
            f"\nAviso: dataset '{prefixo}' não possui datetime. "
            "Ignorado."
        )
        return base

    outro = outro.copy()

    # --------------------------------------------------------
    # Identificar coluna de linha
    # --------------------------------------------------------

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

    if coluna_linha != "line":
        outro = outro.rename(
            columns={coluna_linha: "line"}
        )

    # --------------------------------------------------------
    # Preparação temporal
    # --------------------------------------------------------

    outro = (
        outro
        .dropna(subset=["datetime"])
        .sort_values(["line", "datetime"])
        .reset_index(drop=True)
    )

    resultados = []

    # --------------------------------------------------------
    # Integração separada por linha
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
        # Evitar duplicação da coluna line
        # ----------------------------------------------------

        outro_linha = outro_linha.drop(
            columns=[
                "line"
            ]
        )

        # ----------------------------------------------------
        # Preservar identificadores do dataset integrado
        # ----------------------------------------------------

        colunas_identificacao = {
            "generated_by": f"{prefixo}_generated_by",
            "ts_generation": f"{prefixo}_ts_generation"
        }

        outro_linha = outro_linha.rename(
            columns={
                coluna: novo_nome
                for coluna, novo_nome
                in colunas_identificacao.items()
                if coluna in outro_linha.columns
            }
        )

        # ----------------------------------------------------
        # Renomear demais variáveis
        # ----------------------------------------------------

        colunas_excluir_prefixo = {
            "datetime",
            f"{prefixo}_generated_by",
            f"{prefixo}_ts_generation"
        }

        outras_colunas = [
            coluna
            for coluna in outro_linha.columns
            if coluna not in colunas_excluir_prefixo
        ]

        outro_linha = outro_linha.rename(
            columns={
                coluna: f"{prefixo}_{coluna}"
                for coluna in outras_colunas
            }
        )

        # ----------------------------------------------------
        # Ordenação temporal
        # ----------------------------------------------------

        base_linha = (
            base_linha
            .sort_values("datetime")
            .reset_index(drop=True)
        )

        outro_linha = (
            outro_linha
            .sort_values("datetime")
            .reset_index(drop=True)
        )

        # ----------------------------------------------------
        # Alinhamento temporal
        # ----------------------------------------------------

        unido = pd.merge_asof(
            base_linha,
            outro_linha,
            on="datetime",
            direction="nearest",
            tolerance=pd.Timedelta(
                TOLERANCIA_ALINHAMENTO
            )
        )

        resultados.append(unido)

    # --------------------------------------------------------
    # Consolidar resultados
    # --------------------------------------------------------

    if not resultados:
        return base

    return (
        pd.concat(
            resultados,
            ignore_index=True
        )
        .sort_values(
            ["line", "generated_by", "datetime"]
        )
        .reset_index(drop=True)
    )

def print_titulo(titulo, n=70, double=True):
    if(double):
        print("\n" + "=" * n)
        print(titulo)
        print("=" * n)
    else:
        print("\n" + "-" * n)
        print(titulo)
        print("-" * n)

def pausar_seguir():
    resposta = input(
        "\nPosso seguir para a próxima seção? [Enter = sim / n = parar] "
    ).strip().lower()

    if resposta == "n":
        print("\nExecução interrompida pelo usuário.")
        raise SystemExit

    os.system("cls")