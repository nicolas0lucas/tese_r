from flask import Flask, render_template, request, jsonify, redirect, url_for, send_file
from calculos_emissoes import (
    calcular_emissoes_combustao_estacionaria,
    calcular_emissoes_combustao_movel,
    calcular_emissoes_energia_eletrica,
    calcular_emissoes_transporte_rodoviario,
    calcular_emissoes_transporte_hidroviario,
    calcular_emissoes_fugitivas
)
from collections import defaultdict
import pandas as pd
from datetime import datetime
import os
import json

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['ALLOWED_EXTENSIONS'] = {'xlsx', 'csv'}

# Dados temporários em memória (substituir por banco de dados em produção)
dados_sessao = {
    'empreendimento': None,
    'emissoes': [],
    'detalhes_gas': defaultdict(lambda: {'CO2': 0, 'CH4': 0, 'N2O': 0, 'Total': 0})
}

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/salvar-empreendimento", methods=["POST"])
def salvar_empreendimento():
    dados_sessao['empreendimento'] = {
        'nome': request.form.get('nome_empreendimento'),
        'local': request.form.get('local'),
        'bioma': request.form.get('bioma'),
        'vida_util': request.form.get('vida_util'),
        'fator_capacidade': request.form.get('fator_capacidade'),
        'inicio_operacao': request.form.get('inicio_geracao'),
        'termino_previsto': request.form.get('termino_previsto'),
        'metodologia': request.form.get('metodologia'),
        'data_criacao': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }
    return redirect(url_for('combustao'))

@app.route("/combustao")
def combustao():
    return render_template("combustao.html")

@app.route("/energia-transporte")
def energia_transporte():
    return render_template("energia_transporte.html")

@app.route("/fugitivas-solo")
def fugitivas_solo():
    return render_template("fugitivas_solo.html")

@app.route("/calcular", methods=["POST"])
def calcular():
    tipo = request.form["tipo"]
    resultado = None
    id_fonte = request.form.get("id_fonte", "")

    try:
        if tipo == "Combustão Estacionária":
            resultado = calcular_emissoes_combustao_estacionaria(
                request.form["combustivel"],
                float(request.form["consumo"])
            )
            
        elif tipo == "Combustão Móvel":
            resultado = calcular_emissoes_combustao_movel(
                request.form["combustivel"],
                float(request.form["distancia"]),
                float(request.form["eficiencia"])
            )
            
        elif tipo == "Energia Elétrica":
            resultado = calcular_emissoes_energia_eletrica(
                float(request.form["consumo"]),
                float(request.form.get("fator_emissao", 0.1))
            )
            
        elif tipo == "Transporte Rodoviário":
            resultado = calcular_emissoes_transporte_rodoviario(
                float(request.form["distancia"]),
                float(request.form["carga"])
            )
            
        elif tipo == "Transporte Hidroviário":
            resultado = calcular_emissoes_transporte_hidroviario(
                float(request.form["distancia"]),
                float(request.form["carga"])
            )
            
        elif tipo == "Emissões Fugitivas":
            resultado = calcular_emissoes_fugitivas(
                request.form["gas"],
                float(request.form["quantidade"]),
                request.form["tipo_emissao"]
            )

        # Atualiza os dados na sessão
        if resultado:
            registro = {
                'id': len(dados_sessao['emissoes']) + 1,
                'tipo': tipo,
                'id_fonte': id_fonte,
                'resultado': resultado,
                'detalhes': request.form.to_dict()
            }
            dados_sessao['emissoes'].append(registro)
            
            # Acumula valores por tipo de gás
            for gas in ['CO2', 'CH4', 'N2O']:
                if gas in resultado:
                    dados_sessao['detalhes_gas'][tipo][gas] += resultado[gas]
                    dados_sessao['detalhes_gas'][tipo]['Total'] += resultado[gas]

    except (ValueError, KeyError) as e:
        return jsonify({"error": str(e)}), 400

    return jsonify({"success": True, "resultado": resultado})

@app.route("/resumo")
def resumo():
    if not dados_sessao['empreendimento']:
        return redirect(url_for('index'))
    
    # Prepara dados para os gráficos
    categorias = list(dados_sessao['detalhes_gas'].keys())
    dados_grafico = {
        'CO2': [],
        'CH4': [],
        'N2O': [],
        'Total': []
    }
    
    for categoria in categorias:
        for gas in dados_grafico.keys():
            dados_grafico[gas].append(dados_sessao['detalhes_gas'][categoria].get(gas, 0))
    
    # Prepara tabela detalhada
    tabela_detalhes = []
    for categoria, gases in dados_sessao['detalhes_gas'].items():
        linha = {'Categoria': categoria}
        linha.update(gases)
        tabela_detalhes.append(linha)
    
    # Calcula totais gerais
    totais_gerais = {
        'CO2': sum(item['CO2'] for item in tabela_detalhes),
        'CH4': sum(item['CH4'] for item in tabela_detalhes),
        'N2O': sum(item['N2O'] for item in tabela_detalhes),
        'Total': sum(item['Total'] for item in tabela_detalhes)
    }
    
    return render_template(
        "resumo.html",
        empreendimento=dados_sessao['empreendimento'],
        categorias=json.dumps(categorias),
        dados_grafico=json.dumps(dados_grafico),
        tabela_detalhes=tabela_detalhes,
        totais_gerais=totais_gerais
    )

@app.route("/api/resumo")
def api_resumo():
    if not dados_sessao['empreendimento']:
        return jsonify({"error": "Nenhum empreendimento cadastrado"}), 400
    
    categorias = list(dados_sessao['detalhes_gas'].keys())
    tabela_detalhes = []
    
    for categoria, gases in dados_sessao['detalhes_gas'].items():
        linha = {'Categoria': categoria}
        linha.update(gases)
        tabela_detalhes.append(linha)
    
    totais_gerais = {
        'CO2': sum(item['CO2'] for item in tabela_detalhes),
        'CH4': sum(item['CH4'] for item in tabela_detalhes),
        'N2O': sum(item['N2O'] for item in tabela_detalhes),
        'Total': sum(item['Total'] for item in tabela_detalhes)
    }
    
    return jsonify({
        "success": True,
        "empreendimento": dados_sessao['empreendimento'],
        "categorias": categorias,
        "tabela_detalhes": tabela_detalhes,
        "totais_gerais": totais_gerais
    })

@app.route("/api/resumo/excel")
def exportar_resumo_excel():
    # Criar DataFrame com os dados resumidos
    dados = []
    for categoria, gases in dados_sessao['detalhes_gas'].items():
        dados.append({
            'Categoria': categoria,
            'CO2 (t)': gases['CO2'],
            'CH4 (tCO2e)': gases['CH4'],
            'N2O (tCO2e)': gases['N2O'],
            'Total (tCO2e)': gases['Total']
        })
    
    # Adicionar totais gerais
    totais = {
        'CO2 (t)': sum(item['CO2 (t)'] for item in dados),
        'CH4 (tCO2e)': sum(item['CH4 (tCO2e)'] for item in dados),
        'N2O (tCO2e)': sum(item['N2O (tCO2e)'] for item in dados),
        'Total (tCO2e)': sum(item['Total (tCO2e)'] for item in dados)
    }
    dados.append({
        'Categoria': 'TOTAL GERAL',
        **totais
    })
    
    df = pd.DataFrame(dados)
    df.to_excel("temp_resumo.xlsx", index=False)
    
    return send_file(
        "temp_resumo.xlsx",
        as_attachment=True,
        download_name="resumo_emissoes.xlsx"
    )

@app.route("/api/historico")
def api_historico():
    historico = []
    for registro in dados_sessao['emissoes']:
        historico.append({
            'id': registro['id'],
            'tipo': registro['tipo'],
            'id_fonte': registro['id_fonte'],
            'data': datetime.now().strftime("%Y-%m-%d"),
            'co2': registro['resultado'].get('CO2', 0),
            'ch4': registro['resultado'].get('CH4', 0),
            'n2o': registro['resultado'].get('N2O', 0),
            'total': registro['resultado'].get('Total', 0),
            'empreendimento': dados_sessao['empreendimento']['nome'] if dados_sessao['empreendimento'] else "N/A"
        })
    return jsonify(historico)

@app.route("/api/historico", methods=["POST"])
def salvar_historico():
    if not dados_sessao['empreendimento']:
        return jsonify({"error": "Nenhum empreendimento cadastrado"}), 400
    
    registro = {
        'id': len(dados_sessao['emissoes']) + 1,
        'empreendimento': dados_sessao['empreendimento'],
        'emissoes': dados_sessao['emissoes'],
        'detalhes_gas': dados_sessao['detalhes_gas'],
        'data': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }
    
    # Aqui você deveria salvar no banco de dados real
    # Por enquanto, apenas simulamos o salvamento
    return jsonify({
        "success": True,
        "message": "Dados salvos no histórico",
        "id": registro['id']
    })

@app.route("/limpar-dados", methods=["POST"])
def limpar_dados():
    # Reinicia os dados para nova simulação
    dados_sessao['empreendimento'] = None
    dados_sessao['emissoes'] = []
    dados_sessao['detalhes_gas'].clear()
    return jsonify({"status": "Dados limpos com sucesso"})

@app.route("/importar", methods=["POST"])
def importar_dados():
    if 'file' not in request.files:
        return jsonify({"error": "Nenhum arquivo enviado"}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({"error": "Nenhum arquivo selecionado"}), 400
    
    if file and allowed_file(file.filename):
        try:
            # Simulação de importação - implemente conforme sua necessidade
            filename = os.path.join(app.config['UPLOAD_FOLDER'], file.filename)
            file.save(filename)
            
            # Processar arquivo (implementar lógica específica)
            return jsonify({
                "success": True,
                "message": "Arquivo importado com sucesso",
                "dados": "Implemente o processamento do arquivo aqui"
            })
        except Exception as e:
            return jsonify({"error": str(e)}), 500
    
    return jsonify({"error": "Tipo de arquivo não permitido"}), 400

if __name__ == "__main__":
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    app.run(debug=True)