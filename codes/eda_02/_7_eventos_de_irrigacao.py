from utils import encontrar_coluna

def identificacao(integrada):
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

    return coluna_valvula, coluna_volume