# Sistema de Identificación de Operarios - TM-13

Sistema de login y monitorización para operarios de máquinas. Parte del Sprint 1 de Tablero TM.

## 🚀 Instalación

1. **Instalar dependencias:**
```bash
pip install -r requirements.txt
```

2. **Ejecutar la aplicación:**
```bash
python app.py
```
> Los usuarios de prueba se crean automáticamente al arrancar el programa.

3. **Acceder al sistema:**
- Ve a: http://localhost:5000

## 👤 Usuarios de Prueba

| Usuario    | Contraseña | Rol                |
|------------|------------|--------------------|
| jefe       | jefe       | Jefe de Operarios  |
| operario1  | 123        | Operario           |
| operario2  | 123        | Operario           |

## 🔑 Roles

| Rol                | Permisos                                                    |
|--------------------|-------------------------------------------------------------|
| **Operario**       | Registra y consulta sus incidencias, ve sensórica           |
| **Jefe de Operarios** | Supervisa todo, ve métricas, registra y elimina usuarios |

## 📁 Estructura del Proyecto

```
Arquitectura_SW_Proyecto_1/
│
├── app.py                  # Aplicación principal Flask + API sensores
├── sensorica.py            # Monitor de sensores (Tkinter standalone)
├── requirements.txt        # Dependencias Python
├── README.md               # Este archivo
├── instance/
│   └── database.db         # Base de datos SQLite (se crea automáticamente)
└── templates/
    ├── login.html           # Página de login (glassmorphism dark theme)
    └── dashboard.html       # Panel de control con vistas por rol
```

## 📡 Sensórica en Tiempo Real

El dashboard muestra datos de sensores que se actualizan cada 5 segundos:

- 🌡️ **Temperatura** (20–95 °C)
- ⚙️ **Presión del Sistema** (30–150 PSI)
- 📊 **Estado General** — NORMAL / ADVERTENCIA / CRITICO

Endpoint API: `GET /api/sensores` (requiere sesión activa, devuelve JSON).

## 🔗 Integración con TM-14

Para obtener el usuario autenticado en otras partes del código:

```python
from flask import session

usuario_id = session.get('usuario_id')
nombre_usuario = session.get('nombre_usuario')
nombre_completo = session.get('nombre_completo')
rol = session.get('rol')  # 'operario' o 'jefe_operarios'
```

## 🛠️ Funcionalidades

- ✅ Login con usuario y contraseña
- ✅ Sesión persistente con rol
- ✅ Logout
- ✅ Dashboards diferenciados por rol
- ✅ Registro y eliminación de usuarios (solo Jefe de Operarios)
- ✅ Monitorización de sensores en tiempo real
- ✅ Interfaz moderna con glassmorphism y animaciones
- ✅ Base de datos SQLite con seed automático al arrancar

## 📝 Notas

- Las contraseñas se almacenan en texto plano (solo para demo)
- La base de datos es SQLite local (`instance/database.db`)
- Puerto por defecto: 5000
