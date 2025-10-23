import sqlite3
import pandas as pd
from typing import List
from .models import Ativo

class Database:
    def __init__(self, db_path='bolsa_data.db'):
        self.db_path = db_path
        self._init_db()
    
    def _init_db(self):
        """Inicializa o banco de dados"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Tabela de ativos
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
        
        # Tabela de histórico de preços
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS historico_precos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                simbolo TEXT,
                data TIMESTAMP,
                preco REAL,
                volume INTEGER,
                FOREIGN KEY (simbolo) REFERENCES ativos (simbolo)
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def salvar_ativos(self, ativos: List[Ativo]):
        """Salva lista de ativos no banco"""
        conn = sqlite3.connect(self.db_path)
        
        for ativo in ativos:
            conn.execute('''
                INSERT OR REPLACE INTO ativos 
                (simbolo, nome, tipo, preco_atual, dividend_yield, ultimo_dividendo, 
                 frequencia_pagamento, setor, variacao_dia, atualizado_em)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                ativo.simbolo, ativo.nome, ativo.tipo, ativo.preco_atual,
                ativo.dividend_yield, ativo.ultimo_dividendo, ativo.frequencia_pagamento,
                ativo.setor, ativo.variacao_dia, ativo.atualizado_em
            ))
        
        conn.commit()
        conn.close()
    
    def carregar_ativos(self) -> pd.DataFrame:
        """Carrega ativos do banco"""
        conn = sqlite3.connect(self.db_path)
        df = pd.read_sql('SELECT * FROM ativos ORDER BY dividend_yield DESC', conn)
        conn.close()
        return df