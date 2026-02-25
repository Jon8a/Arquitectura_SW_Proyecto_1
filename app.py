from flask import Flask, render_template, redirect, url_for, request, flash, session, jsonify
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import random

app = Flask(__name__)
app.config['SECRET_KEY'] = 'clave-secreta'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'

db = SQLAlchemy(app)


# MODELOS

class Usuario(db.Model):
    id              = db.Column(db.Integer, primary_key=True)
    nombre_usuario  = db.Column(db.String(50), unique=True, nullable=False)
    contraseña      = db.Column(db.String(50), nullable=False)
    nombre_completo = db.Column(db.String(100))
    rol             = db.Column(db.String(20), default='operario')
    activo          = db.Column(db.Boolean, default=True)
    registros       = db.relationship('RegistroActividad', backref='usuario', lazy=True)


class Maquina(db.Model):
    """Máquina de troqueado de la empresa."""
    id          = db.Column(db.Integer, primary_key=True)
    nombre      = db.Column(db.String(100), unique=True, nullable=False)
    descripcion = db.Column(db.String(200))
    activa      = db.Column(db.Boolean, default=True)
    registros   = db.relationship('RegistroActividad', backref='maquina', lazy=True)


class RegistroActividad(db.Model):
    """
    Registro de cada acción que un usuario realiza sobre una máquina.
    Almacena: quién (usuario_id), en qué (maquina_id), qué hizo (actividad) y cuándo (fecha).
    """
    id          = db.Column(db.Integer, primary_key=True)
    usuario_id  = db.Column(db.Integer, db.ForeignKey('usuario.id'), nullable=False)
    maquina_id  = db.Column(db.Integer, db.ForeignKey('maquina.id'), nullable=False)
    actividad   = db.Column(db.String(300), nullable=False)
    fecha       = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)


# RUTAS DE AUTENTICACIÓN
@app.route('/')
def index():
    if 'usuario_id' in session:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        nombre_usuario = request.form.get('nombre_usuario')
        password       = request.form.get('password')
        usuario = Usuario.query.filter_by(nombre_usuario=nombre_usuario, contraseña=password).first()
        if usuario:
            session['usuario_id']      = usuario.id
            session['nombre_usuario']  = usuario.nombre_usuario
            session['nombre_completo'] = usuario.nombre_completo
            session['rol']             = usuario.rol
            flash('Login exitoso!', 'success')
            return redirect(url_for('dashboard'))
        else:
            flash('Usuario o contraseña incorrectos', 'danger')
    return render_template('login.html')


@app.route('/logout')
def logout():
    session.clear()
    flash('Has cerrado sesión', 'info')
    return redirect(url_for('login'))


# DASHBOARD

@app.route('/dashboard')
def dashboard():
    if 'usuario_id' not in session:
        return redirect(url_for('login'))

    usuarios = []
    if session.get('rol') == 'jefe_operarios':
        usuarios = Usuario.query.all()

    maquinas = Maquina.query.filter_by(activa=True).all()

    return render_template('dashboard.html', usuarios=usuarios, maquinas=maquinas)


# GESTIÓN DE USUARIOS (solo jefe_operarios)

@app.route('/registrar', methods=['POST'])
def registrar():
    if 'usuario_id' not in session or session.get('rol') != 'jefe_operarios':
        flash('No tienes permisos para realizar esta acción', 'danger')
        return redirect(url_for('login'))

    nombre_usuario  = request.form.get('nombre_usuario')
    password        = request.form.get('password')
    nombre_completo = request.form.get('nombre_completo')
    rol             = request.form.get('rol', 'operario')

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


@app.route('/eliminar/<int:usuario_id>', methods=['POST'])
def eliminar_usuario(usuario_id):
    if 'usuario_id' not in session or session.get('rol') != 'jefe_operarios':
        flash('No tienes permisos para realizar esta acción', 'danger')
        return redirect(url_for('login'))

    if usuario_id == session.get('usuario_id'):
        flash('No puedes eliminar tu propia cuenta', 'danger')
        return redirect(url_for('dashboard'))

    usuario = Usuario.query.get(usuario_id)
    if usuario:
        db.session.delete(usuario)
        db.session.commit()
        flash(f'Usuario "{usuario.nombre_usuario}" eliminado', 'info')

    return redirect(url_for('dashboard'))


 
# REGISTRO DE ACTIVIDADES

@app.route('/registrar_actividad', methods=['POST'])
def registrar_actividad():
    """Crea un nuevo registro de actividad para el usuario en sesión."""
    if 'usuario_id' not in session:
        flash('Debes iniciar sesión para registrar actividades.', 'danger')
        return redirect(url_for('login'))

    maquina_id = request.form.get('maquina_id', type=int)
    actividad  = request.form.get('actividad', '').strip()

    if not maquina_id or not actividad:
        flash('Debes seleccionar una máquina y describir la actividad.', 'danger')
        return redirect(url_for('dashboard'))

    maquina = Maquina.query.get(maquina_id)
    if not maquina or not maquina.activa:
        flash('La máquina seleccionada no existe o está inactiva.', 'danger')
        return redirect(url_for('dashboard'))

    nuevo_registro = RegistroActividad(
        usuario_id=session['usuario_id'],
        maquina_id=maquina_id,
        actividad=actividad
    )
    db.session.add(nuevo_registro)
    db.session.commit()

    flash(
        f'Actividad "{actividad}" registrada en {maquina.nombre}.',
        'success'
    )
    return redirect(url_for('dashboard'))


@app.route('/mis_registros')
def mis_registros():
    """Devuelve en JSON los últimos 50 registros del usuario en sesión."""
    if 'usuario_id' not in session:
        return jsonify({'error': 'No autorizado'}), 401

    registros = (
        RegistroActividad.query
        .filter_by(usuario_id=session['usuario_id'])
        .order_by(RegistroActividad.fecha.desc())
        .limit(50)
        .all()
    )

    return jsonify([
        {
            'id':        r.id,
            'maquina':   r.maquina.nombre,
            'actividad': r.actividad,
            'fecha':     r.fecha.strftime('%d/%m/%Y %H:%M')
        }
        for r in registros
    ])


@app.route('/todos_los_registros')
def todos_los_registros():
    """Solo accesible por jefe_operarios. Devuelve los últimos 200 registros globales."""
    if 'usuario_id' not in session or session.get('rol') != 'jefe_operarios':
        return jsonify({'error': 'No autorizado'}), 403

    registros = (
        RegistroActividad.query
        .order_by(RegistroActividad.fecha.desc())
        .limit(200)
        .all()
    )

    return jsonify([
        {
            'id':        r.id,
            'usuario':   r.usuario.nombre_completo,
            'maquina':   r.maquina.nombre,
            'actividad': r.actividad,
            'fecha':     r.fecha.strftime('%d/%m/%Y %H:%M')
        }
        for r in registros
    ])


 
# API SENSORES
 

@app.route('/api/sensores')
def api_sensores():
    if 'usuario_id' not in session:
        return jsonify({'error': 'No autorizado'}), 401

    temperatura = round(random.uniform(20.0, 95.0), 1)
    presion     = round(random.uniform(30.0, 150.0), 1)

    if temperatura > 85.0 or presion > 130.0:
        estado = 'CRITICO'
    elif temperatura > 70.0 or presion > 100.0:
        estado = 'ADVERTENCIA'
    else:
        estado = 'NORMAL'

    return jsonify({'temperatura': temperatura, 'presion': presion, 'estado': estado})


 
# DATOS INICIALES
 

def seed_usuarios():
    if Usuario.query.count() == 0:
        usuarios = [
            Usuario(nombre_usuario='jefe',      contraseña='jefe', nombre_completo='Carlos Jefe',   rol='jefe_operarios'),
            Usuario(nombre_usuario='operario1', contraseña='123',  nombre_completo='Juan Perez',    rol='operario'),
            Usuario(nombre_usuario='operario2', contraseña='123',  nombre_completo='Maria Garcia',  rol='operario'),
        ]
        db.session.add_all(usuarios)
        db.session.commit()
        print("[OK] Usuarios creados: jefe/jefe, operario1/123, operario2/123")
    else:
        print("[INFO] Usuarios ya existentes en la base de datos.")


def seed_maquinas():
    if Maquina.query.count() == 0:
        maquinas = [
            Maquina(nombre='Troqueladora T-01', descripcion='Línea 1 — planta baja'),
            Maquina(nombre='Troqueladora T-02', descripcion='Línea 2 — planta baja'),
            Maquina(nombre='Troqueladora T-03', descripcion='Línea 1 — planta alta'),
        ]
        db.session.add_all(maquinas)
        db.session.commit()
        print("[OK] Máquinas de ejemplo creadas.")
    else:
        print("[INFO] Máquinas ya existentes en la base de datos.")


if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        seed_usuarios()
        seed_maquinas()
    app.run(debug=True, port=5000)
