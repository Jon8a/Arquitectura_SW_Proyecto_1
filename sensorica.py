import tkinter as tk
import random

class MonitorMaquinas:
    def __init__(self, root):
        self.root = root
        self.root.title("Monitor de Estado de Maquina")
        self.root.geometry("350x200")
        self.root.configure(padx=20, pady=20)

        self.temp_var = tk.StringVar()
        self.presion_var = tk.StringVar()
        self.estado_var = tk.StringVar()

        tk.Label(root, text="Temperatura:", font=("Arial", 12, "bold")).grid(row=0, column=0, sticky="w", pady=5)
        self.lbl_temp = tk.Label(root, textvariable=self.temp_var, font=("Arial", 12))
        self.lbl_temp.grid(row=0, column=1, sticky="w", pady=5)

        tk.Label(root, text="Presion del Sistema:", font=("Arial", 12, "bold")).grid(row=1, column=0, sticky="w", pady=5)
        self.lbl_presion = tk.Label(root, textvariable=self.presion_var, font=("Arial", 12))
        self.lbl_presion.grid(row=1, column=1, sticky="w", pady=5)

        tk.Label(root, text="Estado General:", font=("Arial", 12, "bold")).grid(row=2, column=0, sticky="w", pady=5)
        self.lbl_estado = tk.Label(root, textvariable=self.estado_var, font=("Arial", 12, "bold"))
        self.lbl_estado.grid(row=2, column=1, sticky="w", pady=5)

        self.actualizar_datos()

    def actualizar_datos(self):
        temperatura = round(random.uniform(20.0, 95.0), 1)
        presion = round(random.uniform(30.0, 150.0), 1)
        
        self.temp_var.set(f"{temperatura} C")
        self.presion_var.set(f"{presion} PSI")

        if temperatura > 85.0 or presion > 130.0:
            estado = "CRITICO"
            color = "red"
        elif temperatura > 70.0 or presion > 100.0:
            estado = "ADVERTENCIA"
            color = "orange"
        else:
            estado = "NORMAL"
            color = "green"

        self.estado_var.set(estado)
        self.lbl_estado.configure(fg=color)

        self.root.after(5000, self.actualizar_datos)

if __name__ == "__main__":
    ventana_principal = tk.Tk()
    aplicacion = MonitorMaquinas(ventana_principal)
    ventana_principal.mainloop()