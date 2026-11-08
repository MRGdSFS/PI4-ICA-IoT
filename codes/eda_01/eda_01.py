from pathlib import Path
import pandas as pd

# ============================================================
# CONFIGURAÇÃO
# ============================================================

# Pasta-raiz onde você extraiu o dataset
# Rodar da raiz do repositório. O zip em data/ extrai em data/<nome>/; se o extrator
# criou uma pasta extra (data/<nome>/<nome>/), usa a interna.
DATASET_DIR = Path("data/IoT Dataset from an Evolving Tomato Cultivation Te")
if (DATASET_DIR / DATASET_DIR.name).is_dir():
    DATASET_DIR = DATASET_DIR / DATASET_DIR.name

# Pasta onde os resultados da análise serão salvos
OUTPUT_DIR = Path("outputs/eda01")
OUTPUT_DIR.mkdir(exist_ok=True)

# ============================================================
# 1. LOCALIZAR TODOS OS CSVs
# ============================================================

csv_files = sorted(DATASET_DIR.rglob("*.csv"))

print("\n" + "=" * 70)
print("1. ARQUIVOS CSV ENCONTRADOS")
print("=" * 70)

print(f"Total de CSVs: {len(csv_files)}\n")

for i, csv_file in enumerate(csv_files, start=1):
    print(f"[{i}] {csv_file.relative_to(DATASET_DIR)}")


# ============================================================
# 2. INFORMAÇÕES GERAIS DE CADA CSV
# ============================================================

print("\n" + "=" * 70)
print("2. ESTRUTURA DOS CSVs")
print("=" * 70)

resumo = []

for csv_file in csv_files:

    try:
        df = pd.read_csv(csv_file)
        
        unnamed_columns = [col for col in df.columns if col.startswith("Unnamed")]
        df = df.drop(columns=unnamed_columns)
        
        rel_path = csv_file.relative_to(DATASET_DIR)

        print("\n" + "-" * 70)
        print(f"ARQUIVO: {rel_path}")
        print("-" * 70)

        print(f"Linhas: {len(df)}")
        print(f"Colunas: {len(df.columns)}")

        print("\nColunas:")
        for col in df.columns:
            print(f"  - {col}")

        print("\nTipos:")
        print(df.dtypes.to_string())

        print("\nPrimeiras 3 linhas:")
        print(df.head(3).to_string(index=False))

        print("\nÚltimas 3 linhas:")
        print(df.tail(3).to_string(index=False))

        # Informações para o resumo
        resumo.append({
            "arquivo": str(rel_path),
            "linhas": len(df),
            "colunas": len(df.columns),
            "tamanho_MB": csv_file.stat().st_size / (1024 ** 2)
        })

    except Exception as e:
        print(f"\nERRO ao ler {csv_file}: {e}")


# ============================================================
# 3. RESUMO DOS ARQUIVOS
# ============================================================

resumo_df = pd.DataFrame(resumo)

resumo_df.to_csv(
    OUTPUT_DIR / "resumo_arquivos.csv",
    index=False
)

print("\n" + "=" * 70)
print("3. RESUMO DOS ARQUIVOS")
print("=" * 70)

print(resumo_df.to_string(index=False))


# ============================================================
# 4. ESTATÍSTICAS DESCRITIVAS
# ============================================================

print("\n" + "=" * 70)
print("4. ESTATÍSTICAS DESCRITIVAS")
print("=" * 70)

for csv_file in csv_files:

    try:
        df = pd.read_csv(csv_file)
        
        unnamed_columns = [col for col in df.columns if col.startswith("Unnamed")]
        df = df.drop(columns=unnamed_columns)

        rel_path = csv_file.relative_to(DATASET_DIR)

        # Apenas variáveis numéricas
        numeric_df = df.select_dtypes(include="number")

        if numeric_df.empty:
            continue

        print("\n" + "-" * 70)
        print(f"ARQUIVO: {rel_path}")
        print("-" * 70)

        stats = numeric_df.describe().T

        print(stats.to_string())

        # Salvar
        safe_name = "_".join(rel_path.parts)
        safe_name = safe_name.replace(".csv", "_estatisticas.csv")

        stats.to_csv(
            OUTPUT_DIR / safe_name
        )

    except Exception as e:
        print(f"Erro: {e}")


# ============================================================
# 5. VALORES AUSENTES
# ============================================================

print("\n" + "=" * 70)
print("5. VALORES AUSENTES")
print("=" * 70)

missing_summary = []

for csv_file in csv_files:

    try:
        df = pd.read_csv(csv_file)
        
        unnamed_columns = [col for col in df.columns if col.startswith("Unnamed")]
        df = df.drop(columns=unnamed_columns)

        rel_path = csv_file.relative_to(DATASET_DIR)

        missing = df.isna().sum()

        print("\n" + "-" * 70)
        print(f"ARQUIVO: {rel_path}")
        print("-" * 70)

        if missing.sum() == 0:
            print("Nenhum valor ausente.")
        else:
            print(
                missing[missing > 0]
                .sort_values(ascending=False)
                .to_string()
            )

        for column, count in missing.items():
            if count > 0:
                missing_summary.append({
                    "arquivo": str(rel_path),
                    "coluna": column,
                    "valores_ausentes": count,
                    "percentual": 100 * count / len(df)
                })

    except Exception as e:
        print(f"Erro: {e}")

missing_df = pd.DataFrame(missing_summary)

missing_df.to_csv(
    OUTPUT_DIR / "valores_ausentes.csv",
    index=False
)


# ============================================================
# 6. POSSÍVEIS COLUNAS TEMPORAIS
# ============================================================

print("\n" + "=" * 70)
print("6. COLUNAS TEMPORAIS")
print("=" * 70)

temporal_candidates = [
    "timestamp",
    "time",
    "date",
    "datetime",
    "Date",
    "Time",
    "Timestamp",
    "Datetime",
    "ts_generation"
]

temporal_info = []

for csv_file in csv_files:
    try:
        df = pd.read_csv(csv_file)
        
        unnamed_columns = [col for col in df.columns if col.startswith("Unnamed")]
        df = df.drop(columns=unnamed_columns)

        rel_path = csv_file.relative_to(DATASET_DIR)

        for column in df.columns:

            # Primeiro verifica pelo nome
            if column in temporal_candidates:

                print(f"\nArquivo: {rel_path}")
                print(f"Coluna temporal candidata: {column}")

                # Tenta converter para valores numéricos
                numeric = pd.to_numeric(df[column], errors="coerce")

                # Remove valores inválidos
                valid_numeric = numeric.dropna()

                if len(valid_numeric) == 0:
                    print("Não foi possível interpretar a coluna como timestamp.")
                    continue

                # Detecta automaticamente a unidade do timestamp
                magnitude = valid_numeric.abs().median()

                if magnitude >= 1e11:
                    unit = "ms"
                elif magnitude >= 1e9:
                    unit = "s"
                elif magnitude >= 1e6:
                    unit = "us"
                else:
                    unit = None

                if unit is not None:

                    parsed = pd.to_datetime(
                        df[column],
                        unit=unit,
                        errors="coerce"
                    )

                    valid = parsed.dropna()

                    print(f"Unidade detectada: {unit}")
                    print(f"Primeiro registro: {valid.min()}")
                    print(f"Último registro:   {valid.max()}")

                    temporal_info.append({
                        "arquivo": str(rel_path),
                        "coluna": column,
                        "unidade": unit,
                        "primeiro_registro": valid.min(),
                        "ultimo_registro": valid.max(),
                        "registros_validos": len(valid)
                    })

                else:

                    # Caso não seja Unix timestamp,
                    # tenta interpretar diretamente como data/hora
                    parsed = pd.to_datetime(
                        df[column],
                        errors="coerce"
                    )

                    valid = parsed.dropna()

                    if len(valid) > 0:

                        print("Formato interpretado diretamente como data/hora.")
                        print(f"Primeiro registro: {valid.min()}")
                        print(f"Último registro:   {valid.max()}")

                        temporal_info.append({
                            "arquivo": str(rel_path),
                            "coluna": column,
                            "unidade": "datetime",
                            "primeiro_registro": valid.min(),
                            "ultimo_registro": valid.max(),
                            "registros_validos": len(valid)
                        })

    except Exception as e:
        print(f"Erro: {e}")


temporal_df = pd.DataFrame(temporal_info)

temporal_df.to_csv(
    OUTPUT_DIR / "informacoes_temporais.csv",
    index=False
)

# ============================================================
# 7. VALORES ÚNICOS DAS COLUNAS CATEGÓRICAS
# ============================================================

print("\n" + "=" * 70)
print("7. VARIÁVEIS CATEGÓRICAS / IDENTIFICADORES")
print("=" * 70)

categorical_info = []

for csv_file in csv_files:

    try:
        df = pd.read_csv(csv_file)
        
        unnamed_columns = [col for col in df.columns if col.startswith("Unnamed")]
        df = df.drop(columns=unnamed_columns)

        rel_path = csv_file.relative_to(DATASET_DIR)

        for column in df.columns:

            # Considera objetos/string como possíveis categóricas
            if df[column].dtype == "object":

                unique_values = df[column].dropna().unique()

                print("\n" + "-" * 70)
                print(f"Arquivo: {rel_path}")
                print(f"Coluna: {column}")
                print(f"Quantidade de valores únicos: {len(unique_values)}")

                # Não despejar milhares de valores no terminal
                if len(unique_values) <= 30:
                    print("Valores:")
                    print(unique_values)
                else:
                    print("Primeiros 20 valores:")
                    print(unique_values[:20])

                categorical_info.append({
                    "arquivo": str(rel_path),
                    "coluna": column,
                    "valores_unicos": len(unique_values),
                    "exemplos": " | ".join(
                        str(x) for x in unique_values[:10]
                    )
                })

    except Exception as e:
        print(f"Erro: {e}")


categorical_df = pd.DataFrame(categorical_info)

categorical_df.to_csv(
    OUTPUT_DIR / "variaveis_categoricas.csv",
    index=False
)


# ============================================================
# FINAL
# ============================================================

print("\n" + "=" * 70)
print("ETAPA 1 CONCLUÍDA")
print("=" * 70)

print(f"""
Os resultados foram salvos na pasta:

{OUTPUT_DIR.resolve()}

Arquivos principais:

- resumo_arquivos.csv
- valores_ausentes.csv
- informacoes_temporais.csv
- variaveis_categoricas.csv
- *_estatisticas.csv
""")