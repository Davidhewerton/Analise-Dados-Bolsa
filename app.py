import dash
from dash import html, dcc, dash_table, Input, Output, State, callback_context
import dash_bootstrap_components as dbc
import yfinance as yf
import pandas as pd
import sqlite3
from datetime import datetime
import time
import plotly.express as px
import plotly.graph_objects as go

# ========== CONFIGURAÇÃO DA APLICAÇÃO ==========
app = dash.Dash(
    __name__,
    external_stylesheets=[dbc.themes.DARKLY],
    meta_tags=[{"name": "viewport", "content": "width=device-width, initial-scale=1"}]
)

app.title = "Dashboard Bolsa - Dividendos"

# ========== CLASSES DE DADOS ==========
class DataLoader:
    def __init__(self):
        self.ativos_monitorados = {
            'FII': ['MXRF11.SA', 'HGLG11.SA', 'KNRI11.SA', 'VISC11.SA', 'RBRP11.SA', 'SDIL11.SA'],
            'ETF': ['BOVA11.SA', 'DIVO11.SA', 'SMAL11.SA', 'IVVB11.SA'],
            'ACAO': ['VALE3.SA', 'PETR4.SA', 'BBAS3.SA', 'ITUB4.SA', 'TAEE11.SA', 'WEGE3.SA']
        }
    
    def get_ativos_info(self):
        """Busca informações atualizadas dos ativos"""
        ativos = []
        
        for tipo, lista_ativos in self.ativos_monitorados.items():
            for simbolo in lista_ativos:
                try:
                    ticker = yf.Ticker(simbolo)
                    info = ticker.info
                    hist = ticker.history(period="1d")
                    
                    if not hist.empty:
                        preco_atual = hist['Close'].iloc[-1]
                        preco_anterior = hist['Open'].iloc[-1] if len(hist) > 1 else preco_atual
                        variacao = ((preco_atual - preco_anterior) / preco_anterior) * 100
                        
                        dividend_yield = self._estimate_dividend_yield(ticker, preco_atual)
                        ultimo_dividendo = self._get_ultimo_dividendo(ticker)
                        
                        ativo = {
                            'simbolo': simbolo.replace('.SA', ''),
                            'nome': info.get('longName', simbolo),
                            'tipo': tipo,
                            'preco_atual': preco_atual,
                            'dividend_yield': dividend_yield,
                            'ultimo_dividendo': ultimo_dividendo,
                            'frequencia_pagamento': self._get_frequencia_pagamento(tipo),
                            'setor': info.get('sector', 'N/A'),
                            'variacao_dia': variacao,
                            'atualizado_em': datetime.now()
                        }
                        ativos.append(ativo)
                    
                    time.sleep(0.5)
                    
                except Exception as e:
                    print(f"Erro ao buscar dados para {simbolo}: {e}")
                    continue
        
        return ativos
    
    def _estimate_dividend_yield(self, ticker, current_price):
        """Estima o dividend yield"""
        try:
            dividends = ticker.dividends
            if len(dividends) > 0 and current_price > 0:
                avg_dividend = dividends.tail(4).mean()
                return (avg_dividend * 12 / current_price) * 100
        except:
            pass
        return 0.0
    
    def _get_ultimo_dividendo(self, ticker):
        """Obtém o último dividendo pago"""
        try:
            dividends = ticker.dividends
            if len(dividends) > 0:
                return dividends.iloc[-1]
        except:
            pass
        return 0.0
    
    def _get_frequencia_pagamento(self, tipo):
        """Retorna a frequência de pagamento"""
        frequencias = {
            'FII': 'Mensal',
            'ETF': 'Trimestral',
            'ACAO': 'Trimestral/Semestral'
        }
        return frequencias.get(tipo, 'N/A')

class Database:
    def __init__(self, db_path='bolsa_data.db'):
        self.db_path = db_path
        self._init_db()
    
    def _init_db(self):
        """Inicializa o banco de dados"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS ativos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                simbolo TEXT UNIQUE,
                nome TEXT,
                tipo TEXT,
                preco_atual REAL,
                dividend_yield REAL,
                ultimo_dividendo REAL,
                frequencia_pagamento TEXT,
                setor TEXT,
                variacao_dia REAL,
                atualizado_em TIMESTAMP
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def salvar_ativos(self, ativos):
        """Salva lista de ativos no banco"""
        conn = sqlite3.connect(self.db_path)
        
        for ativo in ativos:
            conn.execute('''
                INSERT OR REPLACE INTO ativos 
                (simbolo, nome, tipo, preco_atual, dividend_yield, ultimo_dividendo, 
                 frequencia_pagamento, setor, variacao_dia, atualizado_em)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                ativo['simbolo'], ativo['nome'], ativo['tipo'], ativo['preco_atual'],
                ativo['dividend_yield'], ativo['ultimo_dividendo'], ativo['frequencia_pagamento'],
                ativo['setor'], ativo['variacao_dia'], ativo['atualizado_em']
            ))
        
        conn.commit()
        conn.close()
    
    def carregar_ativos(self):
        """Carrega ativos do banco"""
        conn = sqlite3.connect(self.db_path)
        df = pd.read_sql('SELECT * FROM ativos ORDER BY dividend_yield DESC', conn)
        conn.close()
        return df

# ========== LAYOUT DA APLICAÇÃO ==========
def create_layout():
    return dbc.Container([
        # Header
        dbc.Row([
            dbc.Col([
                html.H1("📈 Dashboard Bolsa - Monitor de Dividendos", 
                       className="text-center mb-4",
                       style={'color': '#00ff00'}),
                html.P("Acompanhe seus investimentos em tempo real", 
                      className="text-center text-muted mb-4")
            ])
        ]),
        
        # Filtros
        dbc.Row([
            dbc.Col([
                dbc.Card([
                    dbc.CardBody([
                        html.H5("Filtros", className="card-title"),
                        dcc.Dropdown(
                            id='filtro-tipo',
                            options=[
                                {'label': 'Todos', 'value': 'ALL'},
                                {'label': 'FIIs', 'value': 'FII'},
                                {'label': 'ETFs', 'value': 'ETF'},
                                {'label': 'Ações', 'value': 'ACAO'}
                            ],
                            value='ALL',
                            className="mb-2"
                        ),
                        html.Button("🔄 Atualizar Dados", 
                                  id="btn-atualizar", 
                                  className="btn btn-success mt-2")
                    ])
                ], className="mb-4")
            ], width=12)
        ]),
        
        # Métricas Gerais
        dbc.Row([
            dbc.Col([
                dbc.Card([
                    dbc.CardBody([
                        html.H4("💰 DY Médio", className="card-title"),
                        html.H2(id="dy-medio", className="text-success")
                    ])
                ])
            ], width=3),
            dbc.Col([
                dbc.Card([
                    dbc.CardBody([
                        html.H4("📊 Total Ativos", className="card-title"),
                        html.H2(id="total-ativos", className="text-info")
                    ])
                ])
            ], width=3),
            dbc.Col([
                dbc.Card([
                    dbc.CardBody([
                        html.H4("🎯 FIIs Mensais", className="card-title"),
                        html.H2(id="total-fiis", className="text-warning")
                    ])
                ])
            ], width=3),
            dbc.Col([
                dbc.Card([
                    dbc.CardBody([
                        html.H4("📈 Melhor DY", className="card-title"),
                        html.H2(id="melhor-dy", className="text-danger")
                    ])
                ])
            ], width=3),
        ], className="mb-4"),
        
        # Tabela de Ativos
        dbc.Row([
            dbc.Col([
                dbc.Card([
                    dbc.CardBody([
                        html.H5("📋 Ativos Monitorados", className="card-title"),
                        html.Div(id="tabela-ativos")
                    ])
                ])
            ], width=12)
        ], className="mb-4"),
        
        # Gráficos
        dbc.Row([
            dbc.Col([
                dbc.Card([
                    dbc.CardBody([
                        html.H5("📊 Dividend Yield por Tipo", className="card-title"),
                        dcc.Graph(id="grafico-dy-tipo")
                    ])
                ])
            ], width=6),
            dbc.Col([
                dbc.Card([
                    dbc.CardBody([
                        html.H5("🎯 Distribuição por Tipo", className="card-title"),
                        dcc.Graph(id="grafico-distribuicao")
                    ])
                ])
            ], width=6)
        ]),
        
        # Atualização automática
        dcc.Interval(
            id='interval-component',
            interval=5*60*1000,  # 5 minutos
            n_intervals=0
        ),
        
        # Store para dados
        dcc.Store(id='dados-ativos')
        
    ], fluid=True)

# ========== CALLBACKS ==========
data_loader = DataLoader()
database = Database()

@app.callback(
    Output('dados-ativos', 'data'),
    [Input('interval-component', 'n_intervals'),
     Input('btn-atualizar', 'n_clicks')]
)
def atualizar_dados(n_intervals, n_clicks):
    """Atualiza dados dos ativos"""
    ativos = data_loader.get_ativos_info()
    database.salvar_ativos(ativos)
    
    df = database.carregar_ativos()
    return df.to_dict('records')

@app.callback(
    [Output('tabela-ativos', 'children'),
     Output('dy-medio', 'children'),
     Output('total-ativos', 'children'),
     Output('total-fiis', 'children'),
     Output('melhor-dy', 'children'),
     Output('grafico-dy-tipo', 'figure'),
     Output('grafico-distribuicao', 'figure')],
    [Input('dados-ativos', 'data'),
     Input('filtro-tipo', 'value')]
)
def atualizar_dashboard(dados, filtro_tipo):
    if not dados:
        return criar_tabela_vazia(), "0%", "0", "0", "0%", criar_grafico_vazio(), criar_grafico_vazio()
    
    df = pd.DataFrame(dados)
    
    # Aplicar filtros
    if filtro_tipo != 'ALL':
        df = df[df['tipo'] == filtro_tipo]
    
    # Calcular métricas
    dy_medio = f"{df['dividend_yield'].mean():.2f}%" if not df.empty else "0%"
    total_ativos = str(len(df))
    total_fiis = str(len(df[df['tipo'] == 'FII']))
    melhor_dy = f"{df['dividend_yield'].max():.2f}%" if not df.empty else "0%"
    
    # Criar tabela
    tabela = criar_tabela_ativos(df)
    
    # Criar gráficos
    fig_dy_tipo = criar_grafico_dy_tipo(df)
    fig_distribuicao = criar_grafico_distribuicao(df)
    
    return tabela, dy_medio, total_ativos, total_fiis, melhor_dy, fig_dy_tipo, fig_distribuicao

def criar_tabela_vazia():
    return html.Div("Nenhum dado disponível. Clique em 'Atualizar Dados'.")

def criar_tabela_ativos(df):
    if df.empty:
        return criar_tabela_vazia()
    
    # Formatar colunas
    df_display = df.copy()
    df_display['preco_atual'] = df_display['preco_atual'].apply(lambda x: f"R$ {x:.2f}")
    df_display['dividend_yield'] = df_display['dividend_yield'].apply(lambda x: f"{x:.2f}%")
    df_display['ultimo_dividendo'] = df_display['ultimo_dividendo'].apply(lambda x: f"R$ {x:.2f}" if x > 0 else "N/A")
    df_display['variacao_dia'] = df_display['variacao_dia'].apply(lambda x: f"{x:+.2f}%")
    
    return dash_table.DataTable(
        columns=[{"name": col, "id": col} for col in [
            'simbolo', 'nome', 'tipo', 'preco_atual', 'dividend_yield', 
            'ultimo_dividendo', 'frequencia_pagamento', 'variacao_dia'
        ]],
        data=df_display.to_dict('records'),
        style_cell={
            'textAlign': 'left',
            'padding': '10px',
            'fontSize': '14px'
        },
        style_header={
            'backgroundColor': 'rgb(30, 30, 30)',
            'color': 'white',
            'fontWeight': 'bold',
            'fontSize': '16px'
        },
        style_data={
            'backgroundColor': 'rgb(50, 50, 50)',
            'color': 'white'
        },
        style_data_conditional=[
            {
                'if': {'column_id': 'variacao_dia', 'filter_query': '{variacao_dia} contains "-"'},
                'color': 'red',
                'fontWeight': 'bold'
            },
            {
                'if': {'column_id': 'variacao_dia', 'filter_query': '{variacao_dia} contains "+"'},
                'color': 'green',
                'fontWeight': 'bold'
            },
            {
                'if': {'column_id': 'dividend_yield'},
                'color': '#00ff00',
                'fontWeight': 'bold'
            }
        ],
        page_size=15
    )

def criar_grafico_vazio():
    fig = go.Figure()
    fig.update_layout(
        template="plotly_dark",
        title="Aguardando dados...",
        xaxis_title="",
        yaxis_title=""
    )
    return fig

def criar_grafico_dy_tipo(df):
    if df.empty:
        return criar_grafico_vazio()
    
    fig = px.box(df, x='tipo', y='dividend_yield', 
                 title="Distribuição do Dividend Yield por Tipo",
                 color='tipo')
    fig.update_layout(template="plotly_dark")
    return fig

def criar_grafico_distribuicao(df):
    if df.empty:
        return criar_grafico_vazio()
    
    contagem = df['tipo'].value_counts()
    fig = px.pie(values=contagem.values, names=contagem.index,
                 title="Distribuição de Ativos por Tipo")
    fig.update_layout(template="plotly_dark")
    return fig

# ========== EXECUÇÃO ==========
app.layout = create_layout()

if __name__ == "__main__":
    print("🚀 Iniciando Dashboard Bolsa...")
    print("📊 Acesse: http://localhost:8050")
    app.run_server(debug=True, host='0.0.0.0', port=8050)