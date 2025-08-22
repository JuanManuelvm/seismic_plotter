import tkinter as tk
from tkinter import ttk, scrolledtext
import numpy as np
import urllib3

# Importar el graficador
from tesis import principal
from LecturaSeedlink import seleccionar_host

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# ============================================================
# Función de selección de nicial
# ============================================================
def tipo_monitoreo():
    def tiempoReal():
        root.destroy()
        seleccionar_host()
        tipo_monitoreo()

    def analisis():
        root.destroy()
        principal()
        tipo_monitoreo()

    root = tk.Tk()
    root.title("Modos")
    root.geometry("350x150")
    root.resizable(False, False)

    ttk.Label(root, text="Ingrese el modo de graficar la información:").pack(pady=10)
    ttk.Button(root, text="Tiempo real", command=tiempoReal).pack(pady=10)
    ttk.Button(root, text="Analisis", command=analisis).pack(pady=10)
    root.mainloop()

if __name__ == "__main__":
    tipo_monitoreo()
