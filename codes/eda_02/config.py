from pathlib import Path

# ============================================================
# CONFIGURAÇÃO
# ============================================================

BASE_DIR = Path(__file__).resolve().parent.parent.parent

NOME_DATASET = "IoT Dataset from an Evolving Tomato Cultivation Te"

# O zip em data/ extrai em data/<NOME_DATASET>/. Se o extrator criou uma pasta extra
# (data/<NOME_DATASET>/<NOME_DATASET>/), usa a interna.
DATA_DIR = BASE_DIR / "data" / NOME_DATASET
if (DATA_DIR / NOME_DATASET).is_dir():
    DATA_DIR = DATA_DIR / NOME_DATASET

OUTPUT_DIR = BASE_DIR / "outputs" / "eda02"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# ============================================================

# CONFIGURAÇÕES DA ANÁLISE

# ============================================================

# Ano principal da análise: 2025 possui a cadeia mais completa de dados.
ANO = 2025

# Linhas de cultivo presentes nos arquivos.
LINHAS = [1, 2, 3, 4, 5]

# Tolerância utilizada no alinhamento temporal.
# Dois registros com diferença menor ou igual a este valor
# serão considerados temporalmente correspondentes.
TOLERANCIA_ALINHAMENTO = "5min"