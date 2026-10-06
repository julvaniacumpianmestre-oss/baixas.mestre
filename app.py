import os, sqlite3, json
from datetime import datetime
from flask import Flask, render_template, request, jsonify

app = Flask(__name__)
DB_PATH = os.environ.get('DB_PATH', os.path.join(os.path.dirname(__file__), 'baixas.db'))

def conn():
    os.makedirs(os.path.dirname(DB_PATH) or '.', exist_ok=True)
    c=sqlite3.connect(DB_PATH); c.row_factory=sqlite3.Row; return c

def init_db():
    with conn() as c:
        c.executescript('''
        CREATE TABLE IF NOT EXISTS atualizacoes(
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          criado_em TEXT NOT NULL,
          descricao TEXT,
          total_clientes INTEGER NOT NULL DEFAULT 0,
          total_valor REAL NOT NULL DEFAULT 0,
          total_credito REAL NOT NULL DEFAULT 0
        );
        CREATE TABLE IF NOT EXISTS resultados(
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          atualizacao_id INTEGER NOT NULL,
          codigo TEXT NOT NULL,
          valor REAL NOT NULL DEFAULT 0,
          credito REAL NOT NULL DEFAULT 0,
          saldo REAL NOT NULL DEFAULT 0,
          base TEXT,
          FOREIGN KEY(atualizacao_id) REFERENCES atualizacoes(id) ON DELETE CASCADE
        );
        CREATE INDEX IF NOT EXISTS idx_resultados_atualizacao ON resultados(atualizacao_id);
        CREATE INDEX IF NOT EXISTS idx_resultados_codigo ON resultados(codigo);
        ''')
init_db()

@app.get('/')
def index(): return render_template('index.html')

@app.post('/api/atualizacoes')
def salvar():
    data=request.get_json(force=True) or {}; itens=data.get('itens') or []
    if not isinstance(itens,list): return jsonify(ok=False,erro='Dados inválidos'),400
    agora=datetime.now().astimezone().isoformat(timespec='seconds')
    total_valor=sum(float(x.get('valor') or 0) for x in itens)
    total_credito=sum(float(x.get('credito') or 0) for x in itens)
    with conn() as c:
        cur=c.execute('INSERT INTO atualizacoes(criado_em,descricao,total_clientes,total_valor,total_credito) VALUES(?,?,?,?,?)',
                      (agora, data.get('descricao','Atualização diária'), len(itens), total_valor, total_credito))
        aid=cur.lastrowid
        c.executemany('INSERT INTO resultados(atualizacao_id,codigo,valor,credito,saldo,base) VALUES(?,?,?,?,?,?)',
          [(aid,str(x.get('codigo','')),float(x.get('valor') or 0),float(x.get('credito') or 0),float(x.get('saldo') or 0),str(x.get('base',''))) for x in itens])
    return jsonify(ok=True,id=aid,criado_em=agora)

@app.get('/api/atualizacoes')
def listar():
    with conn() as c: rows=c.execute('SELECT * FROM atualizacoes ORDER BY id DESC LIMIT 100').fetchall()
    return jsonify([dict(r) for r in rows])

@app.get('/api/atualizacoes/<int:aid>')
def detalhe(aid):
    with conn() as c:
        a=c.execute('SELECT * FROM atualizacoes WHERE id=?',(aid,)).fetchone()
        if not a:return jsonify(erro='Atualização não encontrada'),404
        itens=c.execute('SELECT codigo,valor,credito,saldo,base FROM resultados WHERE atualizacao_id=? ORDER BY base,saldo,codigo',(aid,)).fetchall()
    return jsonify(atualizacao=dict(a),itens=[dict(r) for r in itens])

@app.get('/api/atual')
def atual():
    with conn() as c:
        a=c.execute('SELECT * FROM atualizacoes ORDER BY id DESC LIMIT 1').fetchone()
        if not a:return jsonify(atualizacao=None,itens=[])
        itens=c.execute('SELECT codigo,valor,credito,saldo,base FROM resultados WHERE atualizacao_id=? ORDER BY base,saldo,codigo',(a['id'],)).fetchall()
    return jsonify(atualizacao=dict(a),itens=[dict(r) for r in itens])

if __name__=='__main__': app.run(host='0.0.0.0',port=int(os.environ.get('PORT','5000')),debug=True)
