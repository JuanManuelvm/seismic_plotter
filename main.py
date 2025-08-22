import tkinter as tk
from tkinter import ttk, scrolledtext
from obspy.clients.seedlink.easyseedlink import EasySeedLinkClient
from obspy import UTCDateTime
import threading
import subprocess
from datetime import datetime, timedelta
import urllib3

# Importar el graficador
from seismic_plotter import SeismicPlotter
from LecturaSeedlink import seleccionar_host

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# ============================================================
# Función de selección de host inicial
# ============================================================
def tipo_monitoreo():
    def confirmar():
        root.destroy()
        seleccionar_host()

    root = tk.Tk()
    root.title("Modos")
    root.geometry("350x150")
    root.resizable(False, False)

    ttk.Label(root, text="Ingrese el modo de graficar la información:").pack(pady=10)
    ttk.Button(root, text="Tiempo real", command=confirmar).pack(pady=10)
    ttk.Button(root, text="Analisis", command=confirmar).pack(pady=10)
    root.mainloop()

if __name__ == "__main__":
    tipo_monitoreo()
