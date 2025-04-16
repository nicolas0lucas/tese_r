# Fatores de Emissão e Configurações Globais
FATORES_EMISSAO = {
    # Combustíveis (kg CO2e por unidade)
    "Gasolina": {"CO2": 2.31, "CH4": 0.0001, "N2O": 0.00002, "unidade": "litro"},
    "Diesel": {"CO2": 2.68, "CH4": 0.00003, "N2O": 0.00003, "unidade": "litro"},
    "Etanol": {"CO2": 1.51, "CH4": 0.0001, "N2O": 0.00002, "unidade": "litro"},
    "Biodiesel": {"CO2": 0.4957, "CH4": 0.0007, "N2O": 0.000004, "unidade": "litro"},
    "Gás Natural": {"CO2": 2.02, "CH4": 0.0001, "N2O": 0.00002, "unidade": "m³"},
    "GNV": {"CO2": 1.85, "CH4": 0.0001, "N2O": 0.00002, "unidade": "m³"},
    "Acetileno": {"CO2": 2.40, "CH4": 0.00015, "N2O": 0.00003, "unidade": "kg"},
}

# Fatores de transporte (kg CO2e por tonelada-km)
FATORES_TRANSPORTE = {
    "Rodoviário": {"CO2": 0.12, "CH4": 0.000015, "N2O": 0.000006},
    "Hidroviário": {"CO2": 0.0166, "CH4": 0.0002, "N2O": 0.000076},
}

# Potencial de Aquecimento Global (GWP) - IPCC AR6
GWP = {
    "CO2": 1,
    "CH4": 27.9,  # Novo valor do IPCC AR6
    "N2O": 273,    # Novo valor do IPCC AR6
    "SF6": 25200
}

# Fatores de conversão
FATORES_CONVERSAO = {
    "SIN": 0.1,            # tCO2/MWh (Sistema Interligado Nacional)
    "CO2_para_C": 3.6667,  # Conversão de CO2 para Carbono
    "kg_para_t": 0.001     # Conversão de kg para toneladas
}

# Fatores para emissões fugitivas
FATORES_FUGITIVOS = {
    "vazamento": 1.0,
    "evaporacao": 0.8,
    "descarga": 1.2
}

def calcular_emissoes_combustao_estacionaria(combustivel, consumo):
    """
    Calcula emissões para combustão estacionária
    Args:
        combustivel: Tipo de combustível (deve existir em FATORES_EMISSAO)
        consumo: Quantidade consumida (na unidade do combustível)
    Returns:
        Dicionário com emissões de CO2, CH4, N2O e Total em tCO2e
    """
    if combustivel not in FATORES_EMISSAO:
        raise ValueError(f"Combustível '{combustivel}' não encontrado.")
    
    fe = FATORES_EMISSAO[combustivel]
    kg_para_t = FATORES_CONVERSAO["kg_para_t"]
    
    # Cálculo das emissões em toneladas
    emissao_CO2 = consumo * fe["CO2"] * kg_para_t
    emissao_CH4 = consumo * fe["CH4"] * kg_para_t * GWP["CH4"]
    emissao_N2O = consumo * fe["N2O"] * kg_para_t * GWP["N2O"]
    
    return {
        "CO2": round(emissao_CO2, 4),
        "CH4": round(emissao_CH4, 4),
        "N2O": round(emissao_N2O, 4),
        "Total": round(emissao_CO2 + emissao_CH4 + emissao_N2O, 4),
        "Unidade": "tCO2e",
        "Combustivel": combustivel,
        "Consumo": consumo,
        "UnidadeConsumo": fe["unidade"]
    }

def calcular_emissoes_combustao_movel(combustivel, distancia, eficiencia):
    """
    Calcula emissões para combustão móvel
    Args:
        combustivel: Tipo de combustível
        distancia: Distância percorrida (km)
        eficiencia: Eficiência do veículo (km/unidade de combustível)
    Returns:
        Dicionário com emissões em tCO2e
    """
    if eficiencia <= 0:
        raise ValueError("A eficiência deve ser maior que zero.")
    
    # Calcula o consumo com base na distância e eficiência
    consumo = distancia / eficiencia
    resultado = calcular_emissoes_combustao_estacionaria(combustivel, consumo)
    
    # Adiciona informações específicas de transporte
    resultado.update({
        "Distancia": round(distancia, 2),
        "Eficiencia": round(eficiencia, 2),
        "Tipo": "Combustão Móvel"
    })
    
    return resultado

def calcular_emissoes_energia_eletrica(consumo, fator_emissao=0.1):
    """
    Calcula emissões para energia elétrica
    Args:
        consumo: Consumo em MWh
        fator_emissao: Fator de emissão (tCO2/MWh)
    Returns:
        Dicionário com emissões em tCO2
    """
    if consumo < 0:
        raise ValueError("O consumo não pode ser negativo.")
    
    if fator_emissao < 0:
        raise ValueError("O fator de emissão não pode ser negativo.")
    
    emissao = consumo * fator_emissao
    
    return {
        "CO2": round(emissao, 4),
        "Total": round(emissao, 4),
        "Unidade": "tCO2",
        "Consumo": round(consumo, 2),
        "FatorEmissao": round(fator_emissao, 4),
        "Tipo": "Energia Elétrica"
    }

def calcular_emissoes_transporte_rodoviario(distancia, carga):
    """
    Calcula emissões para transporte rodoviário de cargas
    Args:
        distancia: Distância percorrida (km)
        carga: Carga transportada (toneladas)
    Returns:
        Dicionário com emissões em tCO2e
    """
    return calcular_emissoes_transporte("Rodoviário", distancia, carga)

def calcular_emissoes_transporte_hidroviario(distancia, carga):
    """
    Calcula emissões para transporte hidroviário de cargas
    Args:
        distancia: Distância percorrida (km)
        carga: Carga transportada (toneladas)
    Returns:
        Dicionário com emissões em tCO2e
    """
    return calcular_emissoes_transporte("Hidroviário", distancia, carga)

def calcular_emissoes_transporte(tipo, distancia, carga):
    """
    Função genérica para cálculo de emissões em transportes
    """
    if tipo not in FATORES_TRANSPORTE:
        raise ValueError(f"Tipo de transporte '{tipo}' não suportado.")
    
    if distancia <= 0 or carga <= 0:
        raise ValueError("Distância e carga devem ser maiores que zero.")
    
    ft = FATORES_TRANSPORTE[tipo]
    kg_para_t = FATORES_CONVERSAO["kg_para_t"]
    
    # Cálculo das emissões em toneladas
    emissao_CO2 = distancia * carga * ft["CO2"] * kg_para_t
    emissao_CH4 = distancia * carga * ft["CH4"] * kg_para_t * GWP["CH4"]
    emissao_N2O = distancia * carga * ft["N2O"] * kg_para_t * GWP["N2O"]
    
    return {
        "CO2": round(emissao_CO2, 4),
        "CH4": round(emissao_CH4, 4),
        "N2O": round(emissao_N2O, 4),
        "Total": round(emissao_CO2 + emissao_CH4 + emissao_N2O, 4),
        "Unidade": "tCO2e",
        "Distancia": round(distancia, 2),
        "Carga": round(carga, 2),
        "TipoTransporte": tipo
    }

def calcular_emissoes_fugitivas(gas, quantidade, tipo_emissao="vazamento"):
    """
    Calcula emissões fugitivas
    Args:
        gas: Tipo de gás (CO2, CH4, N2O ou SF6)
        quantidade: Quantidade emitida (kg)
        tipo_emissao: Tipo de emissão (vazamento, evaporacao, descarga)
    Returns:
        Dicionário com emissões em tCO2e
    """
    gas = gas.upper()
    if gas not in GWP:
        raise ValueError(f"Gás '{gas}' não suportado.")
    
    if tipo_emissao not in FATORES_FUGITIVOS:
        raise ValueError(f"Tipo de emissão '{tipo_emissao}' não suportado.")
    
    if quantidade < 0:
        raise ValueError("A quantidade não pode ser negativa.")
    
    kg_para_t = FATORES_CONVERSAO["kg_para_t"]
    fator_emissao = FATORES_FUGITIVOS[tipo_emissao]
    
    emissao = quantidade * kg_para_t * fator_emissao
    total_co2e = emissao * GWP[gas]
    
    return {
        gas: round(emissao, 4),
        "Total": round(total_co2e, 4),
        "Unidade": "tCO2e",
        "TipoEmissao": tipo_emissao,
        "Quantidade": round(quantidade, 2)
    }

def calcular_emissoes_supressao_vegetal(volume_madeira, densidade, teor_carbono=50):
    """
    Calcula emissões por supressão vegetal
    Args:
        volume_madeira: Volume em m³
        densidade: Densidade da madeira em kg/m³
        teor_carbono: Teor de carbono na matéria seca (%)
    Returns:
        Dicionário com emissões em tCO2
    """
    if volume_madeira <= 0 or densidade <= 0:
        raise ValueError("Volume e densidade devem ser maiores que zero.")
    
    if not 0 <= teor_carbono <= 100:
        raise ValueError("Teor de carbono deve estar entre 0 e 100%.")
    
    carbono_estoque = volume_madeira * densidade * (teor_carbono/100)
    emissao = carbono_estoque * FATORES_CONVERSAO["CO2_para_C"] * FATORES_CONVERSAO["kg_para_t"]
    
    return {
        "CO2": round(emissao, 4),
        "Total": round(emissao, 4),
        "Unidade": "tCO2",
        "VolumeMadeira": round(volume_madeira, 2),
        "Densidade": round(densidade, 2),
        "TeorCarbono": round(teor_carbono, 1)
    }