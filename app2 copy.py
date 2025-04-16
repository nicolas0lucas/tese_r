from flask import Flask, render_template, request, jsonify, redirect, url_for, send_file
from calculos_emissoes import (
    calcular_emissoes_combustao_estacionaria,
    calcular_emissoes_combustao_movel,
    calcular_emissoes_residuos_solidos,
    calcular_emissoes_energia_eletrica,
    calcular_emissoes_supressao_vegetal,
    calcular_emissoes_transporte_rodoviario,
    calcular_emissoes_transporte_hidroviario,
    calcular_emissoes_fugitivas
)
import pandas as pd
from datetime import datetime
import os

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['ALLOWED_EXTENSIONS'] = {'xlsx', 'csv'}

# Dados temporários (substituir por banco de dados real)
empreendimentos = []
historico_emissoes = []

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/salvar-empreendimento", methods=["POST"])
def salvar_empreendimento():
    empreendimento = {
        'id': len(empreendimentos) + 1,
        'nome': request.form.get('nome_empreendimento'),
        'local': request.form.get('local'),
        'bioma': request.form.get('bioma'),
        'vida_util': int(request.form.get('vida_util')),
        'fator_capacidade': float(request.form.get('fator_capacidade')),
        'inicio_operacao': request.form.get('inicio_geracao'),
        'termino_previsto': request.form.get('termino_previsto'),
        'metodologia': request.form.get('metodologia'),
        'data_criacao': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }
    empreendimentos.append(empreendimento)
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
            combustivel = request.form["combustivel"]
            consumo = float(request.form["consumo"])
            resultado = calcular_emissoes_combustao_estacionaria(combustivel, consumo)
            
        elif tipo == "Combustão Móvel":
            combustivel = request.form["combustivel"]
            distancia = float(request.form["distancia"])
            eficiencia = float(request.form["eficiencia"])
            resultado = calcular_emissoes_combustao_movel(combustivel, distancia, eficiencia)
            
        elif tipo == "Resíduos Sólidos":
            peso_residuos = float(request.form["peso_residuos"])
            resultado = calcular_emissoes_residuos_solidos(peso_residuos)
            
        elif tipo == "Energia Elétrica":
            consumo = float(request.form["consumo"])
            fator_emissao = float(request.form.get("fator_emissao", 0.1))
            resultado = calcular_emissoes_energia_eletrica(consumo, fator_emissao)
            
        elif tipo == "Supressão Vegetal":
            volume_madeira = float(request.form["volume_madeira"])
            densidade = float(request.form["densidade"])
            teor_carbono = float(request.form["teor_carbono"])
            resultado = calcular_emissoes_supressao_vegetal(volume_madeira, densidade, teor_carbono)
            
        elif tipo == "Transporte Rodoviário":
            distancia = float(request.form["distancia"])
            carga = float(request.form["carga"])
            tipo_transporte = request.form.get("tipo_transporte", "rodoviario")
            resultado = calcular_emissoes_transporte_rodoviario(distancia, carga)
            
        elif tipo == "Transporte Hidroviário":
            distancia = float(request.form["distancia"])
            carga = float(request.form["carga"])
            resultado = calcular_emissoes_transporte_hidroviario(distancia, carga)
            
        elif tipo == "Emissões Fugitivas":
            gas = request.form["gas"]
            quantidade = float(request.form["quantidade"])
            tipo_emissao = request.form["tipo_emissao"]
            resultado = calcular_emissoes_fugitivas(gas, quantidade, tipo_emissao)

        # Salvar no histórico
        if resultado:
            registro = {
                'id': len(historico_emissoes) + 1,
                'tipo': tipo,
                'id_fonte': id_fonte,
                'data': datetime.now().strftime("%Y-%m-%d"),
                'resultado': resultado,
                'detalhes': request.form.to_dict()
            }
            historico_emissoes.append(registro)

    except (ValueError, KeyError) as e:
        return jsonify({"error": str(e)}), 400

    return jsonify(resultado)

@app.route("/resumo")
def resumo():
    # Agrupar resultados por categoria
    resumo = {}
    for registro in historico_emissoes:
        if registro['tipo'] not in resumo:
            resumo[registro['tipo']] = registro['resultado']
        else:
            for gas in registro['resultado']:
                if gas in resumo[registro['tipo']]:
                    resumo[registro['tipo']][gas] += registro['resultado'][gas]
    
    return render_template("resumo.html", resumo=resumo)

@app.route("/api/historico")
def api_historico():
    # Formatar dados para o frontend
    dados = []
    for registro in historico_emissoes:
        dados.append({
            'id': registro['id'],
            'empreendimento': empreendimentos[-1]['nome'] if empreendimentos else "N/A",
            'data': registro['data'],
            'co2': registro['resultado'].get('CO2', 0),
            'ch4': registro['resultado'].get('CH4', 0),
            'n2o': registro['resultado'].get('N2O', 0),
            'total': registro['resultado'].get('Total', 0),
            'tipo': registro['tipo']
        })
    return jsonify(dados)

@app.route("/api/historico/<int:id>")
def api_historico_item(id):
    registro = next((r for r in historico_emissoes if r['id'] == id), None)
    if registro:
        return jsonify({
            'empreendimento': empreendimentos[-1]['nome'] if empreendimentos else "N/A",
            'data': registro['data'],
            'co2': registro['resultado'].get('CO2', 0),
            'ch4': registro['resultado'].get('CH4', 0),
            'n2o': registro['resultado'].get('N2O', 0),
            'total': registro['resultado'].get('Total', 0),
            'detalhes': registro['detalhes']
        })
    return jsonify({"error": "Registro não encontrado"}), 404

@app.route("/exportar-excel")
def exportar_excel():
    # Criar DataFrame com todos os dados
    dados = []
    for registro in historico_emissoes:
        dados.append({
            'Tipo': registro['tipo'],
            'Fonte': registro['id_fonte'],
            'Data': registro['data'],
            'CO2 (t)': registro['resultado'].get('CO2', 0),
            'CH4 (tCO2e)': registro['resultado'].get('CH4', 0),
            'N2O (tCO2e)': registro['resultado'].get('N2O', 0),
            'Total (tCO2e)': registro['resultado'].get('Total', 0)
        })
    
    df = pd.DataFrame(dados)
    df.to_excel("temp_export.xlsx", index=False)
    
    return send_file("temp_export.xlsx", as_attachment=True, download_name="historico_emissoes.xlsx")

@app.route("/importar", methods=["POST"])
def importar_dados():
    if 'file' not in request.files:
        return redirect(request.url)
    
    file = request.files['file']
    if file.filename == '':
        return redirect(request.url)
    
    if file and allowed_file(file.filename):
        filename = os.path.join(app.config['UPLOAD_FOLDER'], file.filename)
        file.save(filename)
        
        # Processar arquivo (implementar lógica específica)
        return jsonify({"message": "Arquivo importado com sucesso"})
    
    return jsonify({"error": "Tipo de arquivo não permitido"}), 400

if __name__ == "__main__":
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    app.run(debug=True)