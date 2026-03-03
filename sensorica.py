import tkinter as tk
from tkinter import ttk, messagebox
import random
import datetime

class MonitorMaquinas:
    def __init__(self, root):
        self.root = root
        self.root.title("Monitor de Estado de Maquina")
        self.root.geometry("450x250")
        self.root.configure(padx=20, pady=20)

        # Variables de estado
        self.temp_var = tk.StringVar()
        self.presion_var = tk.StringVar()
        self.estado_var = tk.StringVar()
        
        # Sistema de incidencias (Memoria temporal)
        self.incidencias = []
        self.id_incidencia = 1
        self.estado_anterior = "NORMAL"

        # Interfaz Principal
        tk.Label(root, text="Temperatura:", font=("Arial", 12, "bold")).grid(row=0, column=0, sticky="w", pady=5)
        self.lbl_temp = tk.Label(root, textvariable=self.temp_var, font=("Arial", 12))
        self.lbl_temp.grid(row=0, column=1, sticky="w", pady=5)

        tk.Label(root, text="Presion del Sistema:", font=("Arial", 12, "bold")).grid(row=1, column=0, sticky="w", pady=5)
        self.lbl_presion = tk.Label(root, textvariable=self.presion_var, font=("Arial", 12))
        self.lbl_presion.grid(row=1, column=1, sticky="w", pady=5)

        tk.Label(root, text="Estado General:", font=("Arial", 12, "bold")).grid(row=2, column=0, sticky="w", pady=5)
        self.lbl_estado = tk.Label(root, textvariable=self.estado_var, font=("Arial", 12, "bold"))
        self.lbl_estado.grid(row=2, column=1, sticky="w", pady=5)

        # Botones de roles
        tk.Button(root, text="Ver Incidencias (Operario)", command=self.vista_operario, bg="lightblue").grid(row=3, column=0, pady=20, sticky="w")
        tk.Button(root, text="Gestionar Incidencias (Jefe)", command=self.vista_jefe, bg="lightcoral").grid(row=3, column=1, pady=20, sticky="e")

        self.actualizar_datos()

    def actualizar_datos(self):
        temperatura = round(random.uniform(20.0, 95.0), 1)
        presion = round(random.uniform(30.0, 150.0), 1)
        
        self.temp_var.set(f"{temperatura} C")
        self.presion_var.set(f"{presion} PSI")

        if temperatura > 85.0 or presion > 130.0:
            estado = "CRITICO"
            color = "red"
            # Solo crea incidencia si acaba de entrar en estado critico para evitar generar alertas repetidas cada 5 segundos
            if self.estado_anterior != "CRITICO":
                self.crear_incidencia(f"Temp: {temperatura}C, Presion: {presion}PSI")
        elif temperatura > 70.0 or presion > 100.0:
            estado = "ADVERTENCIA"
            color = "orange"
        else:
            estado = "NORMAL"
            color = "green"

        self.estado_anterior = estado
        self.estado_var.set(estado)
        self.lbl_estado.configure(fg=color)

        self.root.after(5000, self.actualizar_datos)

    def crear_incidencia(self, detalles):
        hora_actual = datetime.datetime.now().strftime("%H:%M:%S")
        nueva_incidencia = {
            "id": self.id_incidencia,
            "hora": hora_actual,
            "detalles": detalles,
            "estado": "Abierta"
        }
        self.incidencias.append(nueva_incidencia)
        self.id_incidencia += 1

    def crear_tabla_incidencias(self, ventana):
        columnas = ("id", "hora", "detalles", "estado")
        tabla = ttk.Treeview(ventana, columns=columnas, show="headings", height=8)
        
        tabla.heading("id", text="ID")
        tabla.heading("hora", text="Hora")
        tabla.heading("detalles", text="Detalles")
        tabla.heading("estado", text="Estado")
        
        tabla.column("id", width=30, anchor="center")
        tabla.column("hora", width=80, anchor="center")
        tabla.column("detalles", width=200, anchor="w")
        tabla.column("estado", width=80, anchor="center")
        
        tabla.pack(padx=10, pady=10, fill="both", expand=True)
        return tabla

    def poblar_tabla(self, tabla):
        # Limpiar datos antiguos de la tabla antes de recargar
        for item in tabla.get_children():
            tabla.delete(item)
        # Insertar los datos actuales
        for inc in self.incidencias:
            tabla.insert("", "end", values=(inc["id"], inc["hora"], inc["detalles"], inc["estado"]))

    def vista_operario(self):
        ventana_op = tk.Toplevel(self.root)
        ventana_op.title("Panel de Operario - Solo Lectura")
        ventana_op.geometry("450x250")
        
        tk.Label(ventana_op, text="Incidencias Registradas", font=("Arial", 12, "bold")).pack(pady=5)
        tabla = self.crear_tabla_incidencias(ventana_op)
        self.poblar_tabla(tabla)
        
        # Boton para refrescar los datos manualmente
        tk.Button(ventana_op, text="Actualizar Vista", command=lambda: self.poblar_tabla(tabla)).pack(pady=5)

    def vista_jefe(self):
        ventana_jefe = tk.Toplevel(self.root)
        ventana_jefe.title("Panel de Jefe - Gestion")
        ventana_jefe.geometry("450x300")
        
        tk.Label(ventana_jefe, text="Gestion de Incidencias", font=("Arial", 12, "bold")).pack(pady=5)
        tabla = self.crear_tabla_incidencias(ventana_jefe)
        self.poblar_tabla(tabla)
        
        def cerrar_incidencia():
            seleccionado = tabla.selection()
            if not seleccionado:
                messagebox.showwarning("Aviso", "Seleccione una incidencia de la lista para cerrar.", parent=ventana_jefe)
                return
            
            # Obtener el ID de la fila seleccionada
            item = tabla.item(seleccionado)
            id_seleccionado = item['values'][0]
            
            # Buscar la incidencia en la lista y cambiar su estado
            for inc in self.incidencias:
                if inc["id"] == id_seleccionado:
                    if inc["estado"] == "Cerrada":
                        messagebox.showinfo("Info", "Esta incidencia ya esta cerrada.", parent=ventana_jefe)
                        return
                    inc["estado"] = "Cerrada"
                    break
            
            # Refrescar la tabla
            self.poblar_tabla(tabla)
            messagebox.showinfo("Exito", f"Incidencia {id_seleccionado} cerrada correctamente.", parent=ventana_jefe)

        frame_botones = tk.Frame(ventana_jefe)
        frame_botones.pack(pady=5)
        
        tk.Button(frame_botones, text="Cerrar Incidencia", command=cerrar_incidencia, bg="lightgreen").pack(side="left", padx=10)
        tk.Button(frame_botones, text="Actualizar Vista", command=lambda: self.poblar_tabla(tabla)).pack(side="right", padx=10)

if __name__ == "__main__":
    ventana_principal = tk.Tk()
    aplicacion = MonitorMaquinas(ventana_principal)
    ventana_principal.mainloop()