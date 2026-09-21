import pandas as pd
from config import OUTPUT_DIR

def verificacao_temporal(dados):

    temporal_resumo = []

    for nome, df in dados.items():

        if "datetime" not in df.columns:
            print(f"{nome}: sem coluna datetime.")
            continue

        # ==========================================================
        # DEFINIÇÃO DA UNIDADE TEMPORAL
        # ==========================================================

        if "generated_by" in df.columns and "line" in df.columns:
            chaves = ["line", "generated_by"]

        elif "generated_by" in df.columns:
            chaves = ["generated_by"]

        else:
            chaves = []

        # ==========================================================
        # CRIAÇÃO DOS GRUPOS
        # ==========================================================

        if chaves:
            grupos = df.groupby(chaves, dropna=False)
        else:
            grupos = [("geral", df)]

        # ==========================================================
        # ANÁLISE TEMPORAL
        # ==========================================================

        for identificador, dados_grupo in grupos:

            # ------------------------------------------------------
            # Normaliza o identificador do grupo
            # ------------------------------------------------------

            if not isinstance(identificador, tuple):
                identificador = (identificador,)

            info_grupo = dict(zip(chaves, identificador))

            datas = dados_grupo["datetime"].dropna().sort_values()

            if datas.empty:
                continue

            # ------------------------------------------------------
            # Diferenças entre registros consecutivos
            # ------------------------------------------------------

            diferencas = (
                datas
                .diff()
                .dt.total_seconds()
                .dropna()
            )

            # ------------------------------------------------------
            # Informações básicas
            # ------------------------------------------------------

            inicio = datas.min()
            fim = datas.max()
            n_registros = len(datas)

            mediana = None
            media = None
            maior_intervalo = None
            n_gaps = 0

            print("\n" + "-" * 70)
            print(nome)

            if info_grupo:
                grupo_texto = " | ".join(
                    f"{chave}={valor}"
                    for chave, valor in info_grupo.items()
                )
                print(grupo_texto)

            print("-" * 70)

            print(f"Primeiro registro: {inicio}")
            print(f"Último registro:   {fim}")
            print(f"Nº de registros:   {n_registros}")

            # ------------------------------------------------------
            # Estatísticas dos intervalos
            # ------------------------------------------------------

            if not diferencas.empty:

                mediana = diferencas.median()
                media = diferencas.mean()
                maior_intervalo = diferencas.max()

                print(
                    f"Intervalo mediano: "
                    f"{mediana:.2f} s"
                )

                print(
                    f"Intervalo médio:   "
                    f"{media:.2f} s"
                )

                print(
                    f"Maior intervalo:   "
                    f"{maior_intervalo:.2f} s"
                )

                # --------------------------------------------------
                # Detecção de possíveis lacunas
                # --------------------------------------------------

                if mediana > 0:

                    limite_gap = mediana * 10

                    gaps = diferencas[
                        diferencas > limite_gap
                    ]

                    n_gaps = len(gaps)

                    print(
                        f"Possíveis lacunas (>10x mediana): "
                        f"{n_gaps}"
                    )

            # ------------------------------------------------------
            # Armazena resultado
            # ------------------------------------------------------

            temporal_resumo.append({
                "arquivo": nome,
                **info_grupo,
                "inicio": inicio,
                "fim": fim,
                "n_registros": n_registros,
                "intervalo_mediano_s": mediana,
                "intervalo_medio_s": media,
                "maior_intervalo_s": maior_intervalo,
                "possiveis_gaps": n_gaps
            })

    # ==============================================================
    # CONSOLIDAÇÃO E SALVAMENTO
    # ==============================================================

    temporal_df = pd.DataFrame(temporal_resumo)

    temporal_df.to_csv(
        OUTPUT_DIR / "02_resumo_temporal.csv",
        index=False
    )

    print("\n" + "=" * 70)
    print("Resumo temporal salvo em:")
    print(OUTPUT_DIR / "02_resumo_temporal.csv")
    print("=" * 70)
