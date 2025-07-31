from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from werkzeug.utils import secure_filename
import os
import sqlite3
from datetime import datetime

UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'pdf'}

if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

app = Flask(__name__)
CORS(app)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def get_db_connection():
    conn = sqlite3.connect('contabilidad.db')
    conn.row_factory = sqlite3.Row
    return conn

@app.before_first_request
def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS ingresos (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        fecha TEXT,
                        monto REAL,
                        descripcion TEXT)''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS gastos (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        fecha TEXT,
                        monto REAL,
                        descripcion TEXT,
                        archivo TEXT)''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS mantenimientos (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        tipo TEXT,
                        fecha TEXT,
                        kilometraje INTEGER,
                        descripcion TEXT,
                        componente TEXT,
                        proximo_kilometraje INTEGER,
                        proxima_fecha TEXT,
                        costo REAL,
                        archivo TEXT)''')
    conn.commit()
    conn.close()

@app.route('/api/ingresos', methods=['POST'])
def registrar_ingreso():
    data = request.json
    conn = get_db_connection()
    conn.execute('INSERT INTO ingresos (fecha, monto, descripcion) VALUES (?, ?, ?)',
                 (data['fecha'], data['monto'], data['descripcion']))
    conn.commit()
    conn.close()
    return jsonify({'message': 'Ingreso registrado'})

@app.route('/api/gastos', methods=['POST'])
def registrar_gasto():
    monto = request.form['monto']
    fecha = request.form['fecha']
    descripcion = request.form['descripcion']
    archivo = request.files['archivo']

    if archivo and allowed_file(archivo.filename):
        filename = secure_filename(f"{datetime.now().timestamp()}_{archivo.filename}")
        archivo.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))

        conn = get_db_connection()
        conn.execute('INSERT INTO gastos (fecha, monto, descripcion, archivo) VALUES (?, ?, ?, ?)',
                     (fecha, monto, descripcion, filename))
        conn.commit()
        conn.close()
        return jsonify({'message': 'Gasto registrado'})
    return jsonify({'error': 'Archivo no válido'}), 400

@app.route('/api/mantenimientos', methods=['POST'])
def registrar_mantenimiento():
    data = request.form
    archivo = request.files.get('archivo')
    filename = None

    if archivo and allowed_file(archivo.filename):
        filename = secure_filename(f"{datetime.now().timestamp()}_{archivo.filename}")
        archivo.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))

    conn = get_db_connection()
    conn.execute('''INSERT INTO mantenimientos 
        (tipo, fecha, kilometraje, descripcion, componente, proximo_kilometraje, proxima_fecha, costo, archivo)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)''',
        (
            data['tipo'],
            data['fecha'],
            int(data['kilometraje']),
            data['descripcion'],
            data['componente'],
            int(data['proximo_kilometraje']) if data['proximo_kilometraje'] else None,
            data['proxima_fecha'],
            float(data['costo']),
            filename
        )
    )
    conn.commit()
    conn.close()
    return jsonify({'message': 'Mantenimiento registrado'})

@app.route('/api/mantenimientos', methods=['GET'])
def listar_mantenimientos():
    conn = get_db_connection()
    mantenimientos = conn.execute('SELECT * FROM mantenimientos ORDER BY fecha DESC').fetchall()
    conn.close()
    return jsonify([dict(row) for row in mantenimientos])

@app.route('/uploads/<filename>')
def get_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

@app.route('/api/resumen')
def resumen():
    conn = get_db_connection()
    ingresos = conn.execute('SELECT * FROM ingresos').fetchall()
    gastos = conn.execute('SELECT * FROM gastos').fetchall()
    conn.close()

    total_ingresos = sum(row['monto'] for row in ingresos)
    total_gastos = sum(row['monto'] for row in gastos)

    return jsonify({
        'total_ingresos': total_ingresos,
        'total_gastos': total_gastos,
        'balance': total_ingresos - total_gastos,
        'gastos': [dict(g) for g in gastos]
    })

if __name__ == '__main__':
    app.run(debug=True)
