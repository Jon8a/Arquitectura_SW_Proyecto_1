from flask import Flask, render_template, redirect, url_for, request, flash, session, jsonify
from flask_sqlalchemy import SQLAlchemy
import random

app = Flask(__name__)
app.config['SECRET_KEY'] = 'clave-secreta'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'

db = SQLAlchemy(app)

# Modelo de Usuario
class Usuario(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nombre_usuario = db.Column(db.String(50), unique=True, nullable=False)
    contraseña = db.Column(db.String(50), nullable=False)
    nombre_completo = db.Column(db.String(100))
    rol = db.Column(db.String(20), default='operario')
    activo = db.Column(db.Boolean, default=True)

# Ruta principal - redirige a login
@app.route('/')
def index():
    if 'usuario_id' in session:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))

# Login
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        nombre_usuario = request.form.get('nombre_usuario')
        password = request.form.get('password')
        
        usuario = Usuario.query.filter_by(nombre_usuario=nombre_usuario, contraseña=password).first()
        
        if usuario:
            session['usuario_id'] = usuario.id
            session['nombre_usuario'] = usuario.nombre_usuario
            session['nombre_completo'] = usuario.nombre_completo
            session['rol'] = usuario.rol
            flash('Login exitoso!', 'success')
            return redirect(url_for('dashboard'))
        else:
            flash('Usuario o contraseña incorrectos', 'danger')
    
    return render_template('login.html')

# Dashboard (requiere login)
@app.route('/dashboard')
def dashboard():
    if 'usuario_id' not in session:
        return redirect(url_for('login'))
    
    usuarios = []
    if session.get('rol') == 'jefe_operarios':
        usuarios = Usuario.query.all()
    
    return render_template('dashboard.html', usuarios=usuarios)

# Registrar nuevo usuario (solo jefe de operarios)
@app.route('/registrar', methods=['POST'])
def registrar():
    if 'usuario_id' not in session or session.get('rol') != 'jefe_operarios':
        flash('No tienes permisos para realizar esta acción', 'danger')
        return redirect(url_for('login'))
    
    nombre_usuario = request.form.get('nombre_usuario')
    password = request.form.get('password')
    nombre_completo = request.form.get('nombre_completo')
    rol = request.form.get('rol', 'operario')
    
    # Verificar si el usuario ya existe
    if Usuario.query.filter_by(nombre_usuario=nombre_usuario).first():
        flash('El nombre de usuario ya existe', 'danger')
        return redirect(url_for('dashboard'))
    
    nuevo_usuario = Usuario(
        nombre_usuario=nombre_usuario,
        contraseña=password,
        nombre_completo=nombre_completo,
        rol=rol
    )
    db.session.add(nuevo_usuario)
    db.session.commit()
    flash(f'Usuario "{nombre_usuario}" creado exitosamente', 'success')
    return redirect(url_for('dashboard'))

# Eliminar usuario (solo jefe de operarios)
@app.route('/eliminar/<int:usuario_id>', methods=['POST'])
def eliminar_usuario(usuario_id):
    if 'usuario_id' not in session or session.get('rol') != 'jefe_operarios':
        flash('No tienes permisos para realizar esta acción', 'danger')
        return redirect(url_for('login'))
    
    # No permitir auto-eliminación
    if usuario_id == session.get('usuario_id'):
        flash('No puedes eliminar tu propia cuenta', 'danger')
        return redirect(url_for('dashboard'))
    
    usuario = Usuario.query.get(usuario_id)
    if usuario:
        db.session.delete(usuario)
        db.session.commit()
        flash(f'Usuario "{usuario.nombre_usuario}" eliminado', 'info')
    
    return redirect(url_for('dashboard'))

# API de datos de sensores (replica la lógica de sensorica.py)
@app.route('/api/sensores')
def api_sensores():
    if 'usuario_id' not in session:
        return jsonify({'error': 'No autorizado'}), 401
    
    temperatura = round(random.uniform(20.0, 95.0), 1)
    presion = round(random.uniform(30.0, 150.0), 1)
    
    if temperatura > 85.0 or presion > 130.0:
        estado = 'CRITICO'
    elif temperatura > 70.0 or presion > 100.0:
        estado = 'ADVERTENCIA'
    else:
        estado = 'NORMAL'
    
    return jsonify({
        'temperatura': temperatura,
        'presion': presion,
        'estado': estado
    })

# Logout
@app.route('/logout')
def logout():
    session.clear()
    flash('Has cerrado sesión', 'info')
    return redirect(url_for('login'))

# Función para crear usuarios iniciales
def seed_usuarios():
    if Usuario.query.count() == 0:
        usuarios = [
            Usuario(nombre_usuario='jefe', contraseña='jefe', nombre_completo='Carlos Jefe', rol='jefe_operarios'),
            Usuario(nombre_usuario='operario1', contraseña='123', nombre_completo='Juan Perez', rol='operario'),
            Usuario(nombre_usuario='operario2', contraseña='123', nombre_completo='Maria Garcia', rol='operario'),
        ]
        db.session.add_all(usuarios)
        db.session.commit()
        print("[OK] Usuarios creados: jefe/jefe, operario1/123, operario2/123")
    else:
        print("[INFO] Base de datos ya contiene usuarios")

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        seed_usuarios()
    app.run(debug=True, port=5000)
