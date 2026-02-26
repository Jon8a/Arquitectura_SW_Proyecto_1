import time
import random
import getpass
import threading
import msvcrt
import sqlite3
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional
import uuid


# --- BASE DE DATOS ---

DB_PATH = "planta.db"

def init_db():
    con = sqlite3.connect(DB_PATH)
    cur = con.cursor()
    cur.executescript("""
        CREATE TABLE IF NOT EXISTS maquinas (
            id          TEXT PRIMARY KEY,
            nombre      TEXT NOT NULL,
            modelo      TEXT NOT NULL,
            ubicacion   TEXT NOT NULL,
            en_servicio INTEGER DEFAULT 1
        );

        CREATE TABLE IF NOT EXISTS usuarios (
            id            TEXT PRIMARY KEY,
            nombre        TEXT NOT NULL,
            apellido      TEXT NOT NULL,
            email         TEXT NOT NULL,
            nivel_acceso  TEXT NOT NULL,
            turno         TEXT NOT NULL,
            activo        INTEGER DEFAULT 1,
            fecha_registro TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS fallos (
            id               TEXT PRIMARY KEY,
            maquina_id       TEXT NOT NULL,
            usuario_id       TEXT NOT NULL,
            codigo           TEXT NOT NULL,
            descripcion      TEXT NOT NULL,
            severidad        TEXT NOT NULL,
            estado           TEXT NOT NULL,
            timestamp        TEXT NOT NULL,
            notas            TEXT DEFAULT '',
            FOREIGN KEY (maquina_id) REFERENCES maquinas(id),
            FOREIGN KEY (usuario_id) REFERENCES usuarios(id)
        );
    """)
    con.commit()
    con.close()

def guardar_maquina(maquina):
    con = sqlite3.connect(DB_PATH)
    cur = con.cursor()
    cur.execute("""
        INSERT OR REPLACE INTO maquinas (id, nombre, modelo, ubicacion, en_servicio)
        VALUES (?, ?, ?, ?, ?)
    """, (maquina.id, maquina.nombre, maquina.modelo, maquina.ubicacion, int(maquina.en_servicio)))
    con.commit()
    con.close()

def guardar_usuario(usuario):
    con = sqlite3.connect(DB_PATH)
    cur = con.cursor()
    cur.execute("""
        INSERT OR REPLACE INTO usuarios (id, nombre, apellido, email, nivel_acceso, turno, activo, fecha_registro)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        usuario.id, usuario.nombre, usuario.apellido, usuario.email,
        usuario.nivel_acceso.value, usuario.turno, int(usuario.activo),
        usuario.fecha_registro.strftime("%Y-%m-%d %H:%M:%S")
    ))
    con.commit()
    con.close()

def guardar_fallo(fallo, maquina_id):
    con = sqlite3.connect(DB_PATH)
    cur = con.cursor()
    cur.execute("""
        INSERT OR REPLACE INTO fallos
            (id, maquina_id, usuario_id, codigo, descripcion, severidad, estado, timestamp, notas)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        fallo.id, maquina_id, fallo.operario_id,
        fallo.codigo, fallo.descripcion, fallo.severidad.value,
        fallo.estado.value, fallo.timestamp.strftime("%Y-%m-%d %H:%M:%S"),
        fallo.notas
    ))
    con.commit()
    con.close()

def consulta_historial(maquina_id):
    """
    Consulta SQL con JOIN entre las tres tablas.
    Devuelve todos los fallos de la máquina con datos del operario.
    """
    con = sqlite3.connect(DB_PATH)
    cur = con.cursor()
    cur.execute("""
        SELECT
            f.timestamp,
            f.codigo,
            f.severidad,
            f.estado,
            u.nombre || ' ' || u.apellido  AS operario,
            u.nivel_acceso,
            m.nombre                        AS maquina,
            m.ubicacion,
            f.descripcion,
            f.notas
        FROM   fallos   f
        JOIN   usuarios u ON f.usuario_id  = u.id
        JOIN   maquinas m ON f.maquina_id  = m.id
        WHERE  f.maquina_id = ?
        ORDER  BY f.timestamp ASC
    """, (maquina_id,))
    filas = cur.fetchall()
    con.close()
    return filas

def consulta_resumen_por_operario(maquina_id):
    con = sqlite3.connect(DB_PATH)
    cur = con.cursor()
    cur.execute("""
        SELECT
            u.nombre || ' ' || u.apellido  AS operario,
            COUNT(*)                        AS total,
            SUM(f.severidad = 'critico')    AS criticos,
            SUM(f.severidad = 'moderado')   AS moderados,
            SUM(f.severidad = 'leve')       AS leves
        FROM  fallos   f
        JOIN  usuarios u ON f.usuario_id = u.id
        WHERE f.maquina_id = ?
        GROUP BY f.usuario_id
        ORDER BY total DESC
    """, (maquina_id,))
    filas = cur.fetchall()
    con.close()
    return filas


# --- ENUMS ---

class NivelAcceso(Enum):
    OPERARIO      = "operario"
    SUPERVISOR    = "supervisor"
    ADMINISTRADOR = "administrador"

class SeveridadFallo(Enum):
    LEVE     = "leve"
    MODERADO = "moderado"
    CRITICO  = "critico"

class EstadoFallo(Enum):
    ACTIVO      = "activo"
    EN_REVISION = "en_revision"
    RESUELTO    = "resuelto"


# --- MODELOS ---

@dataclass
class Usuario:
    nombre: str
    apellido: str
    email: str
    nivel_acceso: NivelAcceso
    password: str
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    turno: str = "mañana"
    activo: bool = True
    fecha_registro: datetime = field(default_factory=datetime.now)

@dataclass
class Fallo:
    codigo: str
    descripcion: str
    severidad: SeveridadFallo
    operario_id: str
    operario_nombre: str
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    estado: EstadoFallo = EstadoFallo.ACTIVO
    timestamp: datetime = field(default_factory=datetime.now)
    notas: str = ""

@dataclass
class Maquina:
    nombre: str
    modelo: str
    ubicacion: str
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    operarios: list[Usuario] = field(default_factory=list)
    fallos: list[Fallo] = field(default_factory=list)
    en_servicio: bool = True

    def registrar_operario(self, usuario: Usuario):
        self.operarios.append(usuario)

    def registrar_fallo(self, fallo: Fallo):
        self.fallos.append(fallo)

    def buscar_usuario(self, nombre: str, password: str) -> Optional[Usuario]:
        for u in self.operarios:
            if u.nombre.lower() == nombre.lower() and u.password == password and u.activo:
                return u
        return None


# --- POOL DE FALLOS ---

FALLOS_POSIBLES = [
    ("ERR-001", "Sobrecalentamiento en motor principal",       SeveridadFallo.CRITICO),
    ("ERR-002", "Vibración anómala en eje secundario",         SeveridadFallo.MODERADO),
    ("ERR-003", "Sensor de presión fuera de rango",            SeveridadFallo.LEVE),
    ("ERR-004", "Fallo en sistema de lubricación",             SeveridadFallo.CRITICO),
    ("ERR-005", "Tensión de alimentación inestable",           SeveridadFallo.MODERADO),
    ("ERR-006", "Encoder de posición sin señal",               SeveridadFallo.MODERADO),
    ("ERR-007", "Temperatura ambiente fuera de límites",       SeveridadFallo.LEVE),
    ("ERR-008", "Puerta de seguridad abierta durante ciclo",   SeveridadFallo.CRITICO),
    ("ERR-009", "Desgaste excesivo en correa de transmisión",  SeveridadFallo.LEVE),
    ("ERR-010", "Fallo de comunicación con PLC",               SeveridadFallo.MODERADO),
]

SEVERIDAD_COLOR = {
    SeveridadFallo.LEVE:     "\033[93m",
    SeveridadFallo.MODERADO: "\033[33m",
    SeveridadFallo.CRITICO:  "\033[91m",
}
RESET  = "\033[0m"
VERDE  = "\033[92m"
CYAN   = "\033[96m"
BLANCO = "\033[97m"
GRIS   = "\033[90m"


# --- CONTROL DEL HILO ---

escuchar_activo   = threading.Event()
cambio_solicitado = threading.Event()
ver_fallos        = threading.Event()

def hilo_escuchador():
    while True:
        if not escuchar_activo.is_set():
            time.sleep(0.1)
            continue
        if msvcrt.kbhit():
            ch = msvcrt.getwch()
            if ch in ('\r', '\n'):
                cambio_solicitado.set()
            elif ch.lower() == 'v':
                ver_fallos.set()
        time.sleep(0.05)


# --- LOGIN ---

def login(maquina: Maquina, cambio_turno: bool = False) -> Optional[Usuario]:
    escuchar_activo.clear()
    time.sleep(0.2)

    titulo = "CAMBIO DE TURNO" if cambio_turno else f"SISTEMA DE CONTROL — {maquina.nombre}"
    print(f"\n{CYAN}{'═'*55}{RESET}")
    print(f"{BLANCO}   {titulo}{RESET}")
    print(f"{CYAN}{'═'*55}{RESET}")

    resultado = None
    intentos = 3
    while intentos > 0:
        print(f"\n  Introduce tus credenciales ({intentos} intento(s) restante(s))")
        nombre   = input(f"  {BLANCO}Usuario  :{RESET} ").strip()
        password = getpass.getpass(f"  {BLANCO}Contraseña:{RESET} ")

        usuario = maquina.buscar_usuario(nombre, password)
        if usuario:
            print(f"\n  {VERDE}✔ Acceso concedido. Bienvenido/a, {usuario.nombre} {usuario.apellido}{RESET}")
            print(f"  Nivel: {usuario.nivel_acceso.value.upper()} | Turno: {usuario.turno}")
            resultado = usuario
            break
        else:
            intentos -= 1
            print(f"  \033[91m✘ Credenciales incorrectas.{RESET}")

    if resultado is None and not cambio_turno:
        print(f"\n  \033[91mDemasiados intentos fallidos. Saliendo...\033[0m\n")
        exit(1)

    while msvcrt.kbhit():
        msvcrt.getwch()
    cambio_solicitado.clear()
    ver_fallos.clear()
    escuchar_activo.set()

    return resultado


# --- VISUALIZAR HISTORIAL DESDE BD ---

def mostrar_historial(maquina: Maquina):
    escuchar_activo.clear()
    time.sleep(0.1)

    print(f"\n{CYAN}{'═'*65}{RESET}")
    print(f"{BLANCO}   HISTORIAL DE FALLOS — {maquina.nombre} (desde BD){RESET}")
    print(f"{CYAN}{'═'*65}{RESET}")

    filas = consulta_historial(maquina.id)

    if not filas:
        print(f"\n  {GRIS}No hay fallos registrados en la base de datos.{RESET}")
    else:
        # Cabecera tabla
        print(f"\n  {GRIS}{'#':<4} {'HORA':<10} {'CÓDIGO':<10} {'SEVERIDAD':<10} {'ESTADO':<13} {'OPERARIO':<22} DESCRIPCIÓN{RESET}")
        print(f"  {'─'*100}")

        for i, fila in enumerate(filas, 1):
            ts, codigo, severidad, estado, operario, nivel, maq, ubic, descripcion, notas = fila
            hora  = ts[11:19]   # extraer HH:MM:SS del timestamp
            sev   = SeveridadFallo(severidad)
            color = SEVERIDAD_COLOR[sev]

            print(
                f"  {GRIS}{i:<4}{RESET}"
                f" {GRIS}{hora:<10}{RESET}"
                f" {color}{codigo:<10}{RESET}"
                f" {color}{severidad.upper():<10}{RESET}"
                f" {GRIS}{estado:<13}{RESET}"
                f" {BLANCO}{operario:<22}{RESET}"
                f" {descripcion}"
            )
            if notas:
                print(f"  {' '*47}{GRIS}↳ {notas}{RESET}")

        # Resumen por operario desde BD
        print(f"\n  {CYAN}Resumen por operario:{RESET}")
        resumen = consulta_resumen_por_operario(maquina.id)
        for operario, total, criticos, moderados, leves in resumen:
            print(
                f"  · {BLANCO}{operario:<22}{RESET}"
                f" Total: {total}  |  "
                f"{SEVERIDAD_COLOR[SeveridadFallo.CRITICO]}Críticos: {criticos}{RESET}  "
                f"{SEVERIDAD_COLOR[SeveridadFallo.MODERADO]}Moderados: {moderados}{RESET}  "
                f"{SEVERIDAD_COLOR[SeveridadFallo.LEVE]}Leves: {leves}{RESET}"
            )

    print(f"\n{CYAN}{'═'*65}{RESET}")
    print(f"  {GRIS}Pulsa cualquier tecla para volver...{RESET}")
    msvcrt.getwch()

    while msvcrt.kbhit():
        msvcrt.getwch()
    ver_fallos.clear()
    cambio_solicitado.clear()
    escuchar_activo.set()


# --- DEMO PRINCIPAL ---

def demo_fallos(maquina: Maquina, usuario_inicial: Usuario, intervalo: int = 10):
    usuario_activo = usuario_inicial
    contador = 1

    hilo = threading.Thread(target=hilo_escuchador, daemon=True)
    hilo.start()
    escuchar_activo.set()

    print(f"\n{CYAN}{'─'*55}{RESET}")
    print(f"{BLANCO}  DEMO EN CURSO — fallos cada {intervalo}s{RESET}")
    print(f"  Pulsa  Enter  → cambiar de operario")
    print(f"  Pulsa  V      → ver historial (BD)")
    print(f"  Pulsa  Ctrl+C → detener demo")
    print(f"{CYAN}{'─'*55}{RESET}")

    try:
        while True:
            for _ in range(intervalo * 5):
                time.sleep(0.2)
                if cambio_solicitado.is_set() or ver_fallos.is_set():
                    break

            if ver_fallos.is_set():
                mostrar_historial(maquina)
                print(f"\n{CYAN}{'─'*55}{RESET}")
                print(f"  Pulsa  Enter  → cambiar de operario")
                print(f"  Pulsa  V      → ver historial (BD)")
                print(f"  Pulsa  Ctrl+C → detener demo")
                print(f"{CYAN}{'─'*55}{RESET}")
                continue

            if cambio_solicitado.is_set():
                cambio_solicitado.clear()
                print(f"\n  {CYAN}[CAMBIO DE TURNO SOLICITADO]{RESET}")
                print(f"  Operario saliente: {usuario_activo.nombre} {usuario_activo.apellido}")

                nuevo = login(maquina, cambio_turno=True)
                if nuevo:
                    usuario_activo = nuevo
                    print(f"\n  {VERDE}✔ Operario activo: {usuario_activo.nombre} {usuario_activo.apellido}{RESET}")
                else:
                    print(f"  {CYAN}→ Se mantiene: {usuario_activo.nombre} {usuario_activo.apellido}{RESET}")

                print(f"\n{CYAN}{'─'*55}{RESET}")
                print(f"  Pulsa  Enter  → cambiar de operario")
                print(f"  Pulsa  V      → ver historial (BD)")
                print(f"  Pulsa  Ctrl+C → detener demo")
                print(f"{CYAN}{'─'*55}{RESET}")
                continue

            # Generar fallo y guardar en BD
            codigo, descripcion, severidad = random.choice(FALLOS_POSIBLES)
            fallo = Fallo(
                codigo=codigo,
                descripcion=descripcion,
                severidad=severidad,
                operario_id=usuario_activo.id,
                operario_nombre=f"{usuario_activo.nombre} {usuario_activo.apellido}"
            )
            maquina.registrar_fallo(fallo)
            guardar_fallo(fallo, maquina.id)      # ← persiste en SQLite

            color = SEVERIDAD_COLOR[severidad]
            ts    = fallo.timestamp.strftime("%H:%M:%S")

            print(f"\n  {CYAN}[{ts}] FALLO #{contador}{RESET}")
            print(f"  {'─'*45}")
            print(f"  Máquina    : {maquina.nombre} ({maquina.modelo})")
            print(f"  Operario   : {usuario_activo.nombre} {usuario_activo.apellido}  [{usuario_activo.nivel_acceso.value}]")
            print(f"  Código     : {color}{fallo.codigo}{RESET}")
            print(f"  Descripción: {color}{fallo.descripcion}{RESET}")
            print(f"  Severidad  : {color}{fallo.severidad.value.upper()}{RESET}")
            print(f"  {GRIS}[Guardado en BD]{RESET}")

            contador += 1

    except KeyboardInterrupt:
        escuchar_activo.clear()
        print(f"\n{CYAN}{'─'*55}{RESET}")
        print(f"\n  {VERDE}Demo detenida. Datos guardados en {DB_PATH}{RESET}")
        mostrar_historial(maquina)


# --- ARRANQUE ---

if __name__ == "__main__":

    init_db()   # crea las tablas si no existen

    maquina = Maquina(
        nombre="Prensa Hidráulica #3",
        modelo="PH-2000X",
        ubicacion="Nave B - Línea 4"
    )

    # Registrar operarios y persistirlos en BD
    operarios = [
        Usuario("Carlos", "Martínez", "carlos@planta.com", NivelAcceso.OPERARIO,      "1234",  turno="mañana"),
        Usuario("Lucia",  "Fernández","lucia@planta.com",  NivelAcceso.SUPERVISOR,    "abcd",  turno="tarde"),
        Usuario("Marcos", "Gil",      "marcos@planta.com", NivelAcceso.OPERARIO,      "pass1", turno="noche"),
        Usuario("Admin",  "Sistema",  "admin@planta.com",  NivelAcceso.ADMINISTRADOR, "admin", turno="mañana"),
    ]
    for op in operarios:
        maquina.registrar_operario(op)
        guardar_usuario(op)

    guardar_maquina(maquina)

    usuario_activo = login(maquina)
    demo_fallos(maquina, usuario_activo, intervalo=10)
    