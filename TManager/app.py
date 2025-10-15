# app.py - VERSÃO COMPLETA E CORRIGIDA
import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
import os
import requests
from datetime import datetime, timedelta
import io

# Configuração
st.set_page_config(page_title="T-Manager", page_icon="🚌", layout="wide")

# CSS
st.markdown("""
<style>
.main-header {font-size: 3rem; color: #2E86AB; font-weight: bold; text-align: center; margin-bottom: 2rem;}
.data-table {margin: 1rem 0;}
.footer {position: fixed; left: 0; bottom: 0; width: 100%; background-color: #2E86AB; color: white; text-align: center; padding: 10px;}
.consumo-card {background: #f8f9fa; padding: 1rem; border-radius: 10px; border-left: 4px solid #28a745; margin: 0.5rem 0;}
.anp-header {background: linear-gradient(135deg, #2E86AB, #A23B72); color: white; padding: 1rem; border-radius: 10px; margin-bottom: 1rem;}
.success-box {background: #d4edda; color: #155724; padding: 1rem; border-radius: 5px; margin: 1rem 0;}
.warning-box {background: #fff3cd; color: #856404; padding: 1rem; border-radius: 5px; margin: 1rem 0;}
</style>
""", unsafe_allow_html=True)

# ========== SISTEMA DE ARMAZENAMENTO ==========
class DatabaseManager:
    def __init__(self):
        self.data_dir = "data"
        self._criar_diretorio()
    
    def _criar_diretorio(self):
        if not os.path.exists(self.data_dir):
            os.makedirs(self.data_dir)
    
    def salvar_veiculo(self, dados_veiculo):
        arquivo = f"{self.data_dir}/veiculos.csv"
        novo_veiculo = pd.DataFrame([dados_veiculo])
        
        if os.path.exists(arquivo):
            df_existente = pd.read_csv(arquivo)
            if dados_veiculo['placa'] in df_existente['placa'].values:
                return False, "Placa já cadastrada"
            df_final = pd.concat([df_existente, novo_veiculo], ignore_index=True)
        else:
            df_final = novo_veiculo
        
        df_final.to_csv(arquivo, index=False)
        return True, "Veículo salvo com sucesso"
    
    def carregar_veiculos(self):
        arquivo = f"{self.data_dir}/veiculos.csv"
        if os.path.exists(arquivo):
            return pd.read_csv(arquivo)
        else:
            return pd.DataFrame()
    
    def salvar_precos_anp(self, df_precos):
        arquivo = f"{self.data_dir}/precos_anp.csv"
        df_precos['data_importacao'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        if os.path.exists(arquivo):
            df_existente = pd.read_csv(arquivo)
            df_final = pd.concat([df_existente, df_precos], ignore_index=True)
        else:
            df_final = df_precos
        
        df_final.to_csv(arquivo, index=False)
        return True
    
    def carregar_precos_anp(self):
        arquivo = f"{self.data_dir}/precos_anp.csv"
        if os.path.exists(arquivo):
            return pd.read_csv(arquivo)
        else:
            return pd.DataFrame()

# ========== MÓDULO ANP MANAGER ==========
class ANPManager:
    def __init__(self, db_manager):
        self.db_manager = db_manager
    
    def processar_planilha_anp(self, uploaded_file):
        try:
            if uploaded_file.name.endswith('.csv'):
                df = self._ler_csv(uploaded_file)
            elif uploaded_file.name.endswith('.xlsx'):
                df = pd.read_excel(uploaded_file)
            else:
                return False, "Formato não suportado. Use CSV ou XLSX."
            
            if df.empty:
                return False, "Arquivo vazio ou não pôde ser lido."
            
            st.write("🔍 **Pré-visualização dos dados brutos:**")
            st.write(f"Colunas encontradas: {list(df.columns)}")
            st.dataframe(df.head(3))
            
            df_limpo = self._limpar_dados_anp(df)
            
            if df_limpo.empty:
                return False, "Nenhum dado válido encontrado. Verifique o formato."
            
            self.db_manager.salvar_precos_anp(df_limpo)
            return True, f"✅ {len(df_limpo)} registros importados com sucesso!"
            
        except Exception as e:
            return False, f"❌ Erro ao processar arquivo: {str(e)}"
    
    def _ler_csv(self, uploaded_file):
        tentativas = [
            {'encoding': 'utf-8', 'sep': ';'},
            {'encoding': 'latin-1', 'sep': ';'},
            {'encoding': 'utf-8', 'sep': ','},
            {'encoding': 'latin-1', 'sep': ','},
        ]
        
        for tentativa in tentativas:
            try:
                uploaded_file.seek(0)
                df = pd.read_csv(uploaded_file, **tentativa)
                if not df.empty:
                    return df
            except:
                continue
        
        try:
            uploaded_file.seek(0)
            df = pd.read_csv(uploaded_file, engine='python')
            return df
        except:
            return pd.DataFrame()
    
    def _detectar_colunas_anp(self, df):
        """Detecta automaticamente as colunas relevantes da ANP"""
        colunas_detectadas = {}
        
        # Mapeamento expandido incluindo seus nomes de colunas
        mapeamento_colunas = {
            'produto': [
                'Produto', 'produto', 'COMBUSTÍVEL', 'combustivel', 'PRODUTO', 
                'PRODUTO', 'Combustível', 'Tipo', 'tipo', 'PRODUTO'
            ],
            'estado': [
                'Estado', 'estado', 'UF', 'uf', 'Estado - Sigla', 'SIGLA', 
                'sigla', 'ESTADO', 'Estado'
            ],
            'municipio': [
                'Município', 'municipio', 'MUNICÍPIO', 'Cidade', 'cidade', 
                'CIDADE', 'Localidade', 'MUNICÍPIO'
            ],
            'preco': [
                'Valor de Venda', 'preco', 'Preço', 'PREÇO', 'Valor', 'valor', 
                'Preco', 'Preço de Venda', 'PRECO', 'Venda', 'venda', 
                'Preço Revenda', 'PREÇO MÁXIMO REVENDA', 'Preço Máximo Revenda',
                'PREÇO MÁXIMO', 'Preço Máximo'
            ],
            'bairro': ['Bairro', 'bairro', 'BAIRRO', 'Bairro Revendedor'],
            'endereco': [
                'Endereço', 'endereco', 'ENDEREÇO', 'Nome da Rua', 'Rua', 'rua', 
                'Logradouro', 'logradouro', 'Local', 'local'
            ]
        }
        
        # Mostrar colunas disponíveis para debug
        st.write("🔍 **Colunas disponíveis no arquivo:**", list(df.columns))
        
        # Detectar colunas (case insensitive e com correspondência parcial)
        df_colunas = [str(col).strip().upper() for col in df.columns]
        
        for coluna_padrao, possiveis_nomes in mapeamento_colunas.items():
            for nome in possiveis_nomes:
                nome_limpo = str(nome).strip().upper()
                
                # Busca exata
                for i, coluna_df in enumerate(df_colunas):
                    if nome_limpo == coluna_df:
                        colunas_detectadas[coluna_padrao] = df.columns[i]  # Usar nome original
                        break
                
                # Se não encontrou exato, busca parcial
                if coluna_padrao not in colunas_detectadas:
                    for i, coluna_df in enumerate(df_colunas):
                        if nome_limpo in coluna_df or coluna_df in nome_limpo:
                            colunas_detectadas[coluna_padrao] = df.columns[i]
                            break
                
                if coluna_padrao in colunas_detectadas:
                    break
        
        # Debug: mostrar o que foi detectado
        st.write("🎯 **Mapeamento detectado:**", colunas_detectadas)
        
        return colunas_detectadas
    
    def _limpar_dados_anp(self, df):
        """Limpa e padroniza os dados da ANP"""
        # Detectar colunas automaticamente
        colunas_detectadas = self._detectar_colunas_anp(df)
        
        st.write("🎯 **Colunas detectadas:**", colunas_detectadas)
        
        if not colunas_detectadas:
            st.error("""
            ❌ **Não foi possível detectar colunas válidas!**
            
            **Suas colunas atuais:** {}
            
            **Solução:**
            1. Verifique se as colunas têm os nomes corretos
            2. Ou renomeie para: Produto, Estado, Município, Valor de Venda
            """.format(list(df.columns)))
            return pd.DataFrame()
        
        # Renomear colunas
        df_renomeado = df.rename(columns=colunas_detectadas)
        
        # Garantir colunas essenciais
        for coluna in ['produto', 'estado', 'municipio', 'preco']:
            if coluna not in df_renomeado.columns:
                df_renomeado[coluna] = None
        
        # Mostrar prévia dos dados renomeados
        st.write("📋 **Dados após renomeação:**")
        st.dataframe(df_renomeado.head(3))
        
        # Converter preços para numérico
        if 'preco' in df_renomeado.columns:
            st.write("💰 **Convertendo preços...**")
            df_renomeado['preco'] = (
                df_renomeado['preco']
                .astype(str)
                .str.replace('R$', '', regex=False)
                .str.replace('$', '', regex=False)
                .str.replace(',', '.')
                .str.strip()
            )
            df_renomeado['preco'] = pd.to_numeric(df_renomeado['preco'], errors='coerce')
            
            # Mostrar estatísticas de conversão
            st.write(f"✅ Preços convertidos: {df_renomeado['preco'].notna().sum()} de {len(df_renomeado)}")
            df_renomeado = df_renomeado.dropna(subset=['preco'])
        
        # Filtrar combustíveis - expandindo a lista
        combustiveis_principais = [
            'GASOLINA', 'GASOLINA COMUM', 'ETANOL', 'ÓLEO DIESEL', 'DIESEL', 
            'GASOLINA ADITIVADA', 'DIESEL S10', 'DIESEL S500', 'GNV',
            'ETANOL HIDRATADO', 'GASOLINA C', 'GASOLINA A'
        ]
        
        if 'produto' in df_renomeado.columns:
            st.write("🔍 **Filtrando combustíveis...**")
            mask = df_renomeado['produto'].astype(str).str.upper().isin(combustiveis_principais)
            df_filtrado = df_renomeado[mask]
            st.write(f"✅ Combustíveis filtrados: {len(df_filtrado)} de {len(df_renomeado)}")
        else:
            df_filtrado = df_renomeado
        
        # Limpar textos
        if 'estado' in df_filtrado.columns:
            df_filtrado['estado'] = df_filtrado['estado'].astype(str).str.upper().str.strip()
        
        if 'municipio' in df_filtrado.columns:
            df_filtrado['municipio'] = df_filtrado['municipio'].astype(str).str.title().str.strip()
        
        # Timestamp
        df_filtrado['data_importacao'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        st.success(f"📊 **Processamento concluído:** {len(df_filtrado)} registros válidos")
        
        # Mostrar amostra dos dados finais
        st.write("🎉 **Dados finais processados:**")
        st.dataframe(df_filtrado.head())
        
        return df_filtrado
    
    def obter_estatisticas_precos(self):
        df_precos = self.db_manager.carregar_precos_anp()
        
        if df_precos.empty:
            return None
        
        estatisticas = {
            'total_registros': len(df_precos),
            'ultima_importacao': df_precos['data_importacao'].max() if 'data_importacao' in df_precos.columns else 'N/A',
            'combustiveis': df_precos['produto'].value_counts().to_dict(),
            'preco_medio_por_combustivel': df_precos.groupby('produto')['preco'].mean().round(2).to_dict(),
            'estados_cobertos': df_precos['estado'].nunique() if 'estado' in df_precos.columns else 0,
        }
        
        return estatisticas

# ========== DATA LOADER ==========
class DataLoader:
    def __init__(self):
        self.db_manager = DatabaseManager()
        self.veiculos_df = self.db_manager.carregar_veiculos()
        self.anp_manager = ANPManager(self.db_manager)

# ========== MÓDULO DASHBOARD ==========
class Dashboard:
    def __init__(self, data_loader=None):
        self.data_loader = data_loader
    
    def mostrar(self):
        st.markdown('<h1 class="main-header">📊 Dashboard</h1>', unsafe_allow_html=True)
        
        veiculos_count = len(self.data_loader.veiculos_df) if not self.data_loader.veiculos_df.empty else 0
        stats_anp = self.data_loader.anp_manager.obter_estatisticas_precos()
        
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Veículos Cadastrados", veiculos_count)
        col2.metric("Preços ANP", f"{stats_anp['total_registros'] if stats_anp else 0}")
        col3.metric("Custo Total", "R$ 15.000")
        col4.metric("Estados", f"{stats_anp['estados_cobertos'] if stats_anp else 0}")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("📊 Distribuição por Combustível")
            if not self.data_loader.veiculos_df.empty:
                combustivel_count = self.data_loader.veiculos_df['combustivel'].value_counts()
                fig = px.pie(values=combustivel_count.values, names=combustivel_count.index)
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("Cadastre veículos para ver dados")
        
        with col2:
            st.subheader("⛽ Preços por Combustível (ANP)")
            if stats_anp and stats_anp['preco_medio_por_combustivel']:
                precos_df = pd.DataFrame({
                    'Combustível': stats_anp['preco_medio_por_combustivel'].keys(),
                    'Preço Médio (R$)': stats_anp['preco_medio_por_combustivel'].values()
                })
                fig = px.bar(precos_df, x='Combustível', y='Preço Médio (R$)')
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("Importe dados da ANP")

# ========== MÓDULO FUEL ANALYSIS ==========
class FuelAnalysis:
    def __init__(self, data_loader=None):
        self.data_loader = data_loader
    
    def mostrar(self):
        st.markdown('<h1 class="main-header">⛽ Análise de Combustível</h1>', unsafe_allow_html=True)
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("📈 Evolução de Preços")
            df_precos = self.data_loader.db_manager.carregar_precos_anp()
            
            if not df_precos.empty:
                precos_por_combustivel = df_precos.groupby('produto')['preco'].mean().reset_index()
                fig = px.bar(precos_por_combustivel, x='produto', y='preco')
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("Importe dados da ANP para ver preços")
        
        with col2:
            st.subheader("🧮 Calculadora de Viagem")
            with st.form("calculadora_viagem"):
                distancia = st.number_input("Distância (km)", min_value=1, value=300)
                consumo = st.number_input("Consumo (km/l)", min_value=1.0, value=10.0)
                preco = st.number_input("Preço (R$/litro)", min_value=0.1, value=5.80)
                
                if st.form_submit_button("Calcular Custo"):
                    custo_total = (distancia / consumo) * preco
                    st.success(f"**Custo total: R$ {custo_total:.2f}**")

# ========== MÓDULO ANP PRICES ==========
class ANPPrices:
    def __init__(self, data_loader=None):
        self.data_loader = data_loader
    
    def mostrar(self):
        st.markdown('<h1 class="main-header">⛽ Dados ANP</h1>', unsafe_allow_html=True)
        
        tab1, tab2 = st.tabs(["📤 Importar Dados", "📊 Visualizar Preços"])
        
        with tab1:
            self._mostrar_importacao()
        
        with tab2:
            self._mostrar_precos()
    
    def _mostrar_importacao(self):
        st.subheader("📤 Upload da Planilha ANP")
        
        st.info("""
        **Formato esperado:**
        - Colunas: Produto, Estado, Município, Valor de Venda
        - Exemplo: GASOLINA COMUM, SP, SÃO PAULO, 5.85
        """)
        
        uploaded_file = st.file_uploader("Escolha o arquivo", type=['csv', 'xlsx'])
        
        if uploaded_file is not None:
            if st.button("Processar Arquivo"):
                with st.spinner("Processando..."):
                    sucesso, mensagem = self.data_loader.anp_manager.processar_planilha_anp(uploaded_file)
                    if sucesso:
                        st.success(mensagem)
                    else:
                        st.error(mensagem)
    
    def _mostrar_precos(self):
        st.subheader("📋 Dados de Preços")
        
        df_precos = self.data_loader.db_manager.carregar_precos_anp()
        
        if not df_precos.empty:
            st.dataframe(df_precos, use_container_width=True)
        else:
            st.info("Nenhum dado disponível")

# ========== MÓDULO ROUTE OPTIMIZER ==========
class RouteOptimizer:
    def __init__(self, data_loader=None):
        self.data_loader = data_loader
    
    def mostrar(self):
        st.markdown('<h1 class="main-header">🗺️ Otimização de Rotas</h1>', unsafe_allow_html=True)
        
        st.subheader("📍 Configurar Rota")
        col1, col2 = st.columns(2)
        
        with col1:
            origem = st.text_input("Origem", "São Paulo")
            destino = st.text_input("Destino", "Rio de Janeiro")
            distancia = st.number_input("Distância (km)", min_value=1, value=450)
        
        with col2:
            consumo = st.number_input("Consumo (km/l)", min_value=1.0, value=8.0)
            preco_combustivel = st.number_input("Preço (R$/litro)", min_value=0.1, value=4.20)
            pedagios = st.number_input("Pedágios (R$)", min_value=0, value=120)
        
        if st.button("Calcular Custo"):
            litros_necessarios = distancia / consumo
            custo_combustivel = litros_necessarios * preco_combustivel
            custo_total = custo_combustivel + pedagios
            
            st.success(f"**Custo total da viagem: R$ {custo_total:.2f}**")

# ========== MÓDULO COST CONTROL ==========
class CostControl:
    def __init__(self, data_loader=None):
        self.data_loader = data_loader
    
    def mostrar(self):
        st.markdown('<h1 class="main-header">💰 Controle de Custos</h1>', unsafe_allow_html=True)
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("📊 Custos Mensais")
            meses = ['Jan', 'Fev', 'Mar', 'Abr', 'Mai', 'Jun']
            combustivel = [12000, 13500, 14200, 12800, 15600, 14900]
            manutencao = [2000, 1500, 3000, 1800, 2200, 1900]
            
            fig = go.Figure()
            fig.add_trace(go.Bar(name='Combustível', x=meses, y=combustivel))
            fig.add_trace(go.Bar(name='Manutenção', x=meses, y=manutencao))
            fig.update_layout(barmode='stack')
            st.plotly_chart(fig, use_container_width=True)
        
        with col2:
            st.subheader("📈 Métricas")
            st.metric("Custo Total", "R$ 89.500,00")
            st.metric("Custo Médio Mensal", "R$ 14.916,67")

# ========== MÓDULO DATA MANAGER ==========
class DataManager:
    def __init__(self, data_loader=None):
        self.data_loader = data_loader
        self.db_manager = DatabaseManager()
    
    def mostrar(self):
        st.markdown('<h1 class="main-header">📊 Adicionar Dados</h1>', unsafe_allow_html=True)
        
        tab1, tab2 = st.tabs(["🚛 Veículos", "⛽ Postos"])
        
        with tab1:
            self._form_veiculo()
        
        with tab2:
            self._form_posto()
    
    def _form_veiculo(self):
        st.subheader("Adicionar Veículo")
        
        with st.form("veiculo_form"):
            col1, col2 = st.columns(2)
            
            with col1:
                nome = st.text_input("Nome do Veículo")
                placa = st.text_input("Placa").upper()
                marca = st.selectbox("Marca", ["Volkswagen", "Mercedes", "Ford", "Scania", "Volvo"])
            
            with col2:
                modelo = st.text_input("Modelo")
                combustivel = st.selectbox("Combustível", ["Diesel", "Gasolina", "Álcool"])
                consumo = st.number_input("Consumo (km/l)", min_value=0.1, value=8.0)
            
            if st.form_submit_button("Salvar Veículo"):
                if nome and placa and modelo:
                    dados_veiculo = {
                        'placa': placa,
                        'nome': nome,
                        'marca': marca,
                        'modelo': modelo,
                        'combustivel': combustivel,
                        'consumo': consumo,
                        'data_cadastro': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    }
                    
                    sucesso, mensagem = self.db_manager.salvar_veiculo(dados_veiculo)
                    if sucesso:
                        st.success(mensagem)
                        self.data_loader.veiculos_df = self.db_manager.carregar_veiculos()
                    else:
                        st.error(mensagem)
                else:
                    st.error("Preencha todos os campos")
    
    def _form_posto(self):
        st.subheader("Cadastrar Posto")
        
        with st.form("posto_form"):
            col1, col2 = st.columns(2)
            
            with col1:
                nome = st.text_input("Nome do Posto")
                cidade = st.text_input("Cidade")
            
            with col2:
                preco_gasolina = st.number_input("Preço Gasolina", min_value=0.0, value=5.80)
                preco_diesel = st.number_input("Preço Diesel", min_value=0.0, value=4.20)
            
            if st.form_submit_button("Salvar Posto"):
                if nome and cidade:
                    st.success(f"Posto '{nome}' salvo com sucesso!")
                else:
                    st.warning("Preencha todos os campos")

# ========== APP PRINCIPAL ==========
class TManager:
    def __init__(self):
        self.version = "2.0"
        self.data_loader = DataLoader()
        self.dashboard = Dashboard(self.data_loader)
        self.fuel_analysis = FuelAnalysis(self.data_loader)
        self.anp_prices = ANPPrices(self.data_loader)
        self.route_optimizer = RouteOptimizer(self.data_loader)
        self.cost_control = CostControl(self.data_loader)
        self.data_manager = DataManager(self.data_loader)
    
    def sidebar(self):
        st.sidebar.markdown("# 🚌 T-Manager")
        st.sidebar.markdown("**Sistema de Gestão de Frotas**")
        st.sidebar.markdown("---")
        page = st.sidebar.selectbox(
            "Navegação",
            [
                "📊 Dashboard", 
                "⛽ Dados ANP",
                "⛽ Análise Combustível", 
                "🗺️ Otimizar Rotas", 
                "💰 Controle de Custos",
                "📊 Adicionar Dados"
            ]
        )
        st.sidebar.markdown("---")
        st.sidebar.markdown(f"**Versão:** {self.version}")
        st.sidebar.markdown("Desenvolvido por Fthec")
        return page
    
    def footer(self):
        st.markdown("---")
        st.markdown(
            """
            <div style='text-align: center; color: #666; padding: 20px;'>
                📞 <strong>Suporte:</strong> 55 11 98217-0425 
                🌐 <strong>Site:</strong> <a href='https://home-page-76ks.onrender.com/' target='_blank'>desenvolvedor responsável pelo projeto</a> || 
                📧 <strong>Email:</strong> fernandoalexthec@gmail.com
            </div>
            """,
            unsafe_allow_html=True
        )
    
    def run(self):
        page = self.sidebar()
        
        if page == "📊 Dashboard":
            self.dashboard.mostrar()
        elif page == "⛽ Dados ANP":
            self.anp_prices.mostrar()
        elif page == "⛽ Análise Combustível":
            self.fuel_analysis.mostrar()
        elif page == "🗺️ Otimizar Rotas":
            self.route_optimizer.mostrar()
        elif page == "💰 Controle de Custos":
            self.cost_control.mostrar()
        elif page == "📊 Adicionar Dados":
            self.data_manager.mostrar()
        
        self.footer()

# ========== EXECUTAR ==========
if __name__ == "__main__":
    app = TManager()
    app.run()