from config import ANO
from config import DATA_DIR

def carregar_dados(carregar_csv, mostrar_colunas):
    
    arquivos = {
    "environmental": f"{ANO}/environmental{ANO}.csv",
    "soil": f"{ANO}/soil{ANO}.csv",
    "valve": f"{ANO}/valve_controller{ANO}.csv",
    "water_meter": f"{ANO}/water_meter{ANO}.csv",
    }

    dados = {}

    for nome, arquivo in arquivos.items():
        
        try:

            df = carregar_csv(arquivo, DATA_DIR)

            dados[nome] = df

            print(
                "\n=================================================\n\n"
                f"{nome:20s} -> "
                f"{len(df):8d} registros | "
                f"{len(df.columns):2d} colunas"
            )

            mostrar_colunas(df, nome)

        except FileNotFoundError as erro:

            print(f"\nAVISO: {erro}")

    if "soil" in dados and "generated_by" in dados["soil"].columns:
        print("\nSensores por linha:")
        print(
            dados["soil"]
            .groupby("line")["generated_by"]
            .nunique()
            .to_string()
        )

    return dados
