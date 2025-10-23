import yfinance as yf
import pandas as pd
import time
from datetime import datetime
import requests
import warnings

# Suprimir warnings de SSL
warnings.filterwarnings('ignore', message='Unverified HTTPS request')

class RobustDataLoader:
    def __init__(self):
        self.ativos_monitorados = {
            'FII': ['MXRF11.SA', 'HGLG11.SA', 'KNRI11.SA', 'VISC11.SA', 'RBRP11.SA', 'SDIL11.SA'],
            'ETF': ['BOVA11.SA', 'DIVO11.SA', 'SMAL11.SA', 'IVVB11.SA'],
            'ACAO': ['VALE3.SA', 'PETR4.SA', 'BBAS3.SA', 'ITUB4.SA', 'TAEE11.SA']
        }
        
        # Dados de fallback para nomes de empresas
        self.nomes_fallback = {
            'VALE3.SA': 'Vale SA',
            'PETR4.SA': 'Petrobras',
            'BBAS3.SA': 'Banco do Brasil',
            'ITUB4.SA': 'Itaú Unibanco',
            'TAEE11.SA': 'Taesa',
            'MXRF11.SA': 'Maxi Renda FII',
            'HGLG11.SA': 'CSHG Logística',
            'KNRI11.SA': 'Kinea Renda Imobiliária',
            'VISC11.SA': 'Vinci Shopping Centers',
            'RBRP11.SA': 'RBR Properties',
            'SDIL11.SA': 'SDI Dividendos',
            'BOVA11.SA': 'ETF Ibovespa',
            'DIVO11.SA': 'ETF Dividendos',
            'SMAL11.SA': 'ETF Small Caps',
            'IVVB11.SA': 'ETF S&P 500'
        }
    
    def get_ativos_info(self):
        """Busca informações com fallback robusto"""
        ativos = []
        
        for tipo, lista_ativos in self.ativos_monitorados.items():
            for simbolo in lista_ativos:
                try:
                    print(f"📡 Buscando {simbolo}...")
                    
                    # Configurar session sem verificação SSL
                    session = requests.Session()
                    session.verify = False
                    
                    # Tentar com yfinance primeiro
                    dados = self._get_yfinance_data(simbolo, session)
                    
                    if dados is None:
                        # Fallback para API alternativa
                        dados = self._get_fallback_data(simbolo)
                    
                    if dados:
                        ativos.append(dados)
                        print(f"✅ {simbolo} - R$ {dados['preco_atual']:.2f}")
                    else:
                        print(f"❌ Falha ao buscar {simbolo}")
                    
                    time.sleep(1.5)  # Delay maior para evitar bloqueio
                    
                except Exception as e:
                    print(f"❌ Erro crítico em {simbolo}: {e}")
                    continue
        
        return ativos
    
    def _get_yfinance_data(self, simbolo, session):
        """Tenta obter dados via yfinance"""
        try:
            # Configurar timeout e retry
            yf.set_session(session)
            ticker = yf.Ticker(simbolo)
            
            # Obter histórico com tratamento de erro
            hist = ticker.history(period="2d", timeout=20)
            
            if hist.empty or len(hist) < 1:
                return None
            
            preco_atual = hist['Close'].iloc[-1]
            preco_anterior = hist['Open'].iloc[-1] if len(hist) > 1 else hist['Close'].iloc[0]
            variacao = ((preco_atual - preco_anterior) / preco_anterior) * 100
            
            # Tentar obter info, mas não crítico se falhar
            try:
                info = ticker.info
                nome = info.get('longName', self.nomes_fallback.get(simbolo, simbolo))
                setor = info.get('sector', 'N/A')
            except:
                nome = self.nomes_fallback.get(simbolo, simbolo)
                setor = 'N/A'
            
            # Calcular dividend yield
            dividend_yield = self._safe_dividend_calc(ticker, preco_atual)
            ultimo_dividendo = self._safe_last_dividend(ticker)
            
            return {
                'simbolo': simbolo.replace('.SA', ''),
                'nome': nome,
                'tipo': next((k for k, v in self.ativos_monitorados.items() if simbolo in v), 'OUTRO'),
                'preco_atual': round(preco_atual, 2),
                'dividend_yield': round(dividend_yield, 2),
                'ultimo_dividendo': round(ultimo_dividendo, 2),
                'frequencia_pagamento': self._get_frequencia_pagamento(simbolo),
                'setor': setor,
                'variacao_dia': round(variacao, 2),
                'atualizado_em': datetime.now()
            }
            
        except Exception as e:
            print(f"   yfinance falhou para {simbolo}: {e}")
            return None
    
    def _get_fallback_data(self, simbolo):
        """Fallback quando yfinance falha"""
        try:
            # Dados mock para demonstração - na prática você pode integrar com outra API
            preco_mock = self._get_mock_price(simbolo)
            
            return {
                'simbolo': simbolo.replace('.SA', ''),
                'nome': self.nomes_fallback.get(simbolo, simbolo),
                'tipo': next((k for k, v in self.ativos_monitorados.items() if simbolo in v), 'OUTRO'),
                'preco_atual': preco_mock,
                'dividend_yield': 6.5,  # Mock
                'ultimo_dividendo': 0.50,  # Mock
                'frequencia_pagamento': self._get_frequencia_pagamento(simbolo),
                'setor': 'N/A',
                'variacao_dia': 0.0,
                'atualizado_em': datetime.now()
            }
        except:
            return None
    
    def _safe_dividend_calc(self, ticker, current_price):
        """Calcula dividend yield com tratamento de erro"""
        try:
            dividends = ticker.dividends
            if len(dividends) > 0 and current_price > 0:
                avg_dividend = dividends.tail(4).mean()
                return (avg_dividend * 12 / current_price) * 100
        except:
            pass
        return 0.0
    
    def _safe_last_dividend(self, ticker):
        """Obtém último dividendo com tratamento de erro"""
        try:
            dividends = ticker.dividends
            if len(dividends) > 0:
                return dividends.iloc[-1]
        except:
            pass
        return 0.0
    
    def _get_frequencia_pagamento(self, simbolo):
        """Determina frequência baseada no tipo"""
        if '11' in simbolo:  # FII ou ETF
            return 'Mensal' if 'FII' in simbolo else 'Trimestral'
        else:  # Ação
            return 'Trimestral/Semestral'
    
    def _get_mock_price(self, simbolo):
        """Preços mock para demonstração (remova em produção)"""
        mock_prices = {
            'VALE3.SA': 68.90, 'PETR4.SA': 37.50, 'BBAS3.SA': 57.80,
            'ITUB4.SA': 33.45, 'TAEE11.SA': 41.20, 'MXRF11.SA': 10.25,
            'HGLG11.SA': 158.30, 'KNRI11.SA': 134.50, 'VISC11.SA': 94.80,
            'RBRP11.SA': 86.90, 'SDIL11.SA': 106.75, 'BOVA11.SA': 115.40,
            'DIVO11.SA': 98.60, 'SMAL11.SA': 52.30, 'IVVB11.SA': 245.80
        }
        return mock_prices.get(simbolo, 10.0)