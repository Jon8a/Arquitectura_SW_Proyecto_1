from flask import Flask, render_template, redirect, url_for, request, flash, session, jsonify
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import random

app = Flask(__name__)
app.config['SECRET_KEY'] = 'clave-secreta'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'

db = SQLAlchemy(app)


# ================================================================
# MODELOS
# ================================================================

class Usuario(db.Model):
    id              = db.Column(db.Integer, primary_key=True)
    nombre_usuario  = db.Column(db.String(50), unique=True, nullable=False)
    contraseña      = db.Column(db.String(50), nullable=False)
    nombre_completo = db.Column(db.String(100))
    rol             = db.Column(db.String(20), default='operario')
    activo          = db.Column(db.Boolean, default=True)
    registros       = db.relationship('RegistroActividad', backref='usuario', lazy=True)
    incidencias     = db.relationship('Incidencia', backref='usuario', lazy=True)


class Maquina(db.Model):
    """Máquina de troqueado de la empresa."""
    id          = db.Column(db.Integer, primary_key=True)
    nombre      = db.Column(db.String(100), unique=True, nullable=False)
    descripcion = db.Column(db.String(200))
    activa      = db.Column(db.Boolean, default=True)
    registros   = db.relationship('RegistroActividad', backref='maquina', lazy=True)
    incidencias = db.relationship('Incidencia', backref='maquina', lazy=True)


class RegistroActividad(db.Model):
    """Actividad rutinaria de un operario en una máquina."""
    id          = db.Column(db.Integer, primary_key=True)
    usuario_id  = db.Column(db.Integer, db.ForeignKey('usuario.id'), nullable=False)
    maquina_id  = db.Column(db.Integer, db.ForeignKey('maquina.id'), nullable=False)
    actividad   = db.Column(db.String(300), nullable=False)
    fecha       = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)


class Incidencia(db.Model):
    """
    Ciclo de vida completo de un problema detectado en una máquina.

    Estados posibles:
        abierta      → recién creada, pendiente de atención
        en_progreso  → alguien está trabajando en ella
        resuelta     → solucionada; se rellena fecha_resolucion

    Severidades:
        leve / moderada / critica
    """
    id                = db.Column(db.Integer, primary_key=True)
    usuario_id        = db.Column(db.Integer, db.ForeignKey('usuario.id'), nullable=False)
    maquina_id        = db.Column(db.Integer, db.ForeignKey('maquina.id'), nullable=False)
    titulo            = db.Column(db.String(150), nullable=False)
    descripcion       = db.Column(db.String(500), nullable=False)
    severidad         = db.Column(db.String(20), nullable=False, default='leve')   # leve / moderada / critica
    estado            = db.Column(db.String(20), nullable=False, default='abierta') # abierta / en_progreso / resuelta
    fecha_apertura    = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    fecha_resolucion  = db.Column(db.DateTime, nullable=True)   # se rellena al resolver
    notas_resolucion  = db.Column(db.String(500), nullable=True)

    @property
    def minutos_resolucion(self):
        """Minutos que tardó en resolverse. None si aún no está resuelta."""
        if self.fecha_resolucion and self.fecha_apertura:
            delta = self.fecha_resolucion - self.fecha_apertura
            return round(delta.total_seconds() / 60, 1)
        return None

    @property
    def tiempo_resolucion_texto(self):
        """Devuelve el tiempo de resolución en formato legible (ej: '2h 30min')."""
        mins = self.minutos_resolucion
        if mins is None:
            return '—'
        if mins < 60:
            return f'{int(mins)} min'
        horas = int(mins // 60)
        resto = int(mins % 60)
        return f'{horas}h {resto}min' if resto else f'{horas}h'


# ================================================================
# AUTENTICACIÓN
# ================================================================

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


# ================================================================
# DASHBOARD
# ================================================================

@app.route('/dashboard')
def dashboard():
    if 'usuario_id' not in session:
        return redirect(url_for('login'))

    usuarios = []
    if session.get('rol') == 'jefe_operarios':
        usuarios = Usuario.query.all()

    maquinas = Maquina.query.filter_by(activa=True).all()

    return render_template('dashboard.html', usuarios=usuarios, maquinas=maquinas)


# ================================================================
# GESTIÓN DE USUARIOS  (solo jefe_operarios)
# ================================================================

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

    db.session.add(Usuario(
        nombre_usuario=nombre_usuario,
        contraseña=password,
        nombre_completo=nombre_completo,
        rol=rol
    ))
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


# ================================================================
# REGISTRO DE ACTIVIDADES
# ================================================================

@app.route('/registrar_actividad', methods=['POST'])
def registrar_actividad():
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

    db.session.add(RegistroActividad(
        usuario_id=session['usuario_id'],
        maquina_id=maquina_id,
        actividad=actividad
    ))
    db.session.commit()
    flash(f'Actividad "{actividad}" registrada en {maquina.nombre}.', 'success')
    return redirect(url_for('dashboard'))


@app.route('/mis_registros')
def mis_registros():
    if 'usuario_id' not in session:
        return jsonify({'error': 'No autorizado'}), 401

    registros = (
        RegistroActividad.query
        .filter_by(usuario_id=session['usuario_id'])
        .order_by(RegistroActividad.fecha.desc())
        .limit(50).all()
    )
    return jsonify([
        {'id': r.id, 'maquina': r.maquina.nombre, 'actividad': r.actividad,
         'fecha': r.fecha.strftime('%d/%m/%Y %H:%M')}
        for r in registros
    ])


@app.route('/todos_los_registros')
def todos_los_registros():
    if 'usuario_id' not in session or session.get('rol') != 'jefe_operarios':
        return jsonify({'error': 'No autorizado'}), 403

    registros = (
        RegistroActividad.query
        .order_by(RegistroActividad.fecha.desc())
        .limit(200).all()
    )
    return jsonify([
        {'id': r.id, 'usuario': r.usuario.nombre_completo, 'maquina': r.maquina.nombre,
         'actividad': r.actividad, 'fecha': r.fecha.strftime('%d/%m/%Y %H:%M')}
        for r in registros
    ])


# ================================================================
# INCIDENCIAS
# ================================================================

@app.route('/abrir_incidencia', methods=['POST'])
def abrir_incidencia():
    """El operario abre una nueva incidencia."""
    if 'usuario_id' not in session:
        flash('Debes iniciar sesión.', 'danger')
        return redirect(url_for('login'))

    maquina_id  = request.form.get('maquina_id', type=int)
    titulo      = request.form.get('titulo', '').strip()
    descripcion = request.form.get('descripcion', '').strip()
    severidad   = request.form.get('severidad', 'leve')

    if not maquina_id or not titulo or not descripcion:
        flash('Rellena todos los campos de la incidencia.', 'danger')
        return redirect(url_for('dashboard'))

    if severidad not in ('leve', 'moderada', 'critica'):
        severidad = 'leve'

    maquina = Maquina.query.get(maquina_id)
    if not maquina:
        flash('Máquina no encontrada.', 'danger')
        return redirect(url_for('dashboard'))

    # ── Comprobar duplicado ──────────────────────────────────────────
    duplicada = Incidencia.query.filter(
        Incidencia.maquina_id == maquina_id,
        Incidencia.titulo.ilike(titulo),
        Incidencia.estado.in_(['abierta', 'en_progreso'])
    ).first()

    if duplicada:
        flash(f'Ya existe una incidencia activa con ese título en esa máquina (#{duplicada.id}).', 'danger')
        return redirect(url_for('dashboard'))
    # ────────────────────────────────────────────────────────────────

    db.session.add(Incidencia(
        usuario_id=session['usuario_id'],
        maquina_id=maquina_id,
        titulo=titulo,
        descripcion=descripcion,
        severidad=severidad
    ))
    db.session.commit()
    flash(f'Incidencia "{titulo}" abierta correctamente.', 'success')
    return redirect(url_for('dashboard'))


@app.route('/actualizar_incidencia/<int:inc_id>', methods=['POST'])
def actualizar_incidencia(inc_id):
    """El jefe cambia el estado de una incidencia (en_progreso o resuelta)."""
    if 'usuario_id' not in session or session.get('rol') != 'jefe_operarios':
        flash('No tienes permisos.', 'danger')
        return redirect(url_for('login'))

    inc    = Incidencia.query.get_or_404(inc_id)
    estado = request.form.get('estado')
    notas  = request.form.get('notas_resolucion', '').strip()

    if estado not in ('en_progreso', 'resuelta'):
        flash('Estado no válido.', 'danger')
        return redirect(url_for('dashboard'))

    inc.estado = estado
    if estado == 'resuelta':
        inc.fecha_resolucion = datetime.utcnow()
        inc.notas_resolucion = notas or None

    db.session.commit()
    flash(f'Incidencia #{inc_id} marcada como {estado.replace("_", " ")}.', 'success')
    return redirect(url_for('dashboard'))


@app.route('/mis_incidencias')
def mis_incidencias():
    """JSON con las incidencias abiertas por el operario en sesión."""
    if 'usuario_id' not in session:
        return jsonify({'error': 'No autorizado'}), 401

    incs = (
        Incidencia.query
        .filter_by(usuario_id=session['usuario_id'])
        .order_by(Incidencia.fecha_apertura.desc())
        .limit(50).all()
    )
    return jsonify([_inc_to_dict(i) for i in incs])


@app.route('/todas_las_incidencias')
def todas_las_incidencias():
    """JSON con todas las incidencias (solo jefe)."""
    if 'usuario_id' not in session or session.get('rol') != 'jefe_operarios':
        return jsonify({'error': 'No autorizado'}), 403

    incs = (
        Incidencia.query
        .order_by(Incidencia.fecha_apertura.desc())
        .limit(300).all()
    )
    return jsonify([_inc_to_dict(i) for i in incs])


@app.route('/metricas')
def metricas():
    """
    Devuelve en JSON las métricas de incidencias para el jefe:
      - total, abiertas, en_progreso, resueltas
      - media_resolucion_minutos  (solo incidencias resueltas)
      - por_maquina               (total por máquina)
      - por_operario              (total por operario)
      - por_severidad             (total por severidad)
      - resueltas_ultimos_7_dias  (últimas 7 × 24h)
    """
    if 'usuario_id' not in session or session.get('rol') != 'jefe_operarios':
        return jsonify({'error': 'No autorizado'}), 403

    todas = Incidencia.query.all()

    resueltas = [i for i in todas if i.estado == 'resuelta']
    tiempos   = [i.minutos_resolucion for i in resueltas if i.minutos_resolucion is not None]
    media     = round(sum(tiempos) / len(tiempos), 1) if tiempos else None

    # Agrupaciones
    por_maquina   = {}
    por_operario  = {}
    por_severidad = {'leve': 0, 'moderada': 0, 'critica': 0}

    for i in todas:
        nombre_maq = i.maquina.nombre
        nombre_op  = i.usuario.nombre_completo
        por_maquina[nombre_maq]  = por_maquina.get(nombre_maq, 0) + 1
        por_operario[nombre_op]  = por_operario.get(nombre_op, 0) + 1
        por_severidad[i.severidad] = por_severidad.get(i.severidad, 0) + 1

    # Resueltas en los últimos 7 días
    from datetime import timedelta
    hace_7_dias = datetime.utcnow() - timedelta(days=7)
    rec_7 = sum(
        1 for i in resueltas
        if i.fecha_resolucion and i.fecha_resolucion >= hace_7_dias
    )

    return jsonify({
        'total':                    len(todas),
        'abiertas':                 sum(1 for i in todas if i.estado == 'abierta'),
        'en_progreso':              sum(1 for i in todas if i.estado == 'en_progreso'),
        'resueltas':                len(resueltas),
        'media_resolucion_minutos': media,
        'por_maquina':              por_maquina,
        'por_operario':             por_operario,
        'por_severidad':            por_severidad,
        'resueltas_ultimos_7_dias': rec_7,
    })


def _inc_to_dict(i: Incidencia) -> dict:
    return {
        'id':               i.id,
        'titulo':           i.titulo,
        'descripcion':      i.descripcion,
        'severidad':        i.severidad,
        'estado':           i.estado,
        'maquina':          i.maquina.nombre,
        'operario':         i.usuario.nombre_completo,
        'fecha_apertura':   i.fecha_apertura.strftime('%d/%m/%Y %H:%M'),
        'fecha_resolucion': i.fecha_resolucion.strftime('%d/%m/%Y %H:%M') if i.fecha_resolucion else None,
        'tiempo_resolucion':i.tiempo_resolucion_texto,
        'notas_resolucion': i.notas_resolucion,
    }


# ================================================================
# API SENSORES
# ================================================================

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


# ================================================================
# DATOS INICIALES
# ================================================================

def seed_usuarios():
    if Usuario.query.count() == 0:
        db.session.add_all([
            Usuario(nombre_usuario='jefe',      contraseña='jefe', nombre_completo='Carlos Jefe',  rol='jefe_operarios'),
            Usuario(nombre_usuario='operario1', contraseña='123',  nombre_completo='Juan Perez',   rol='operario'),
            Usuario(nombre_usuario='operario2', contraseña='123',  nombre_completo='Maria Garcia', rol='operario'),
        ])
        db.session.commit()
        print("[OK] Usuarios creados: jefe/jefe, operario1/123, operario2/123")
    else:
        print("[INFO] Usuarios ya existentes.")


def seed_maquinas():
    if Maquina.query.count() == 0:
        db.session.add_all([
            Maquina(nombre='Troqueladora T-01', descripcion='Línea 1 — planta baja'),
            Maquina(nombre='Troqueladora T-02', descripcion='Línea 2 — planta baja'),
            Maquina(nombre='Troqueladora T-03', descripcion='Línea 1 — planta alta'),
        ])
        db.session.commit()
        print("[OK] Máquinas de ejemplo creadas.")
    else:
        print("[INFO] Máquinas ya existentes.")


if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        seed_usuarios()
        seed_maquinas()
    app.run(debug=True, port=5000)
