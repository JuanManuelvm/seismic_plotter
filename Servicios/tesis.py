# gui_tesis.py
# -*- coding: utf-8 -*-

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import threading
import openpyxl
import requests
import urllib3
import numpy as np
import warnings
from obspy import UTCDateTime, read_inventory, read
from obspy.io.mseed.headers import InternalMSEEDWarning
import matplotlib.pyplot as plt


# =====================================================
# Función principal de análisis (se puede usar sin GUI)
# =====================================================
def analizar_evento(ws, row):
    warnings.filterwarnings("ignore", category=InternalMSEEDWarning)
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

    values = [ws.cell(row=row, column=i).value for i in range(1, ws.max_column + 1)]

    # 1. Descargar traza MiniSEED
    url = values[0]
    local_filename = values[1]
    response = requests.get(url, verify=False)
    with open(local_filename, 'wb') as f:
        f.write(response.content)

    # 2. Ventana de análisis
    inicio = UTCDateTime(values[2])
    fin = inicio + values[3]

    # 3. Leer traza y remover respuesta
    trace = read(local_filename, starttime=inicio, endtime=fin)
    url_inv = values[4]
    inv_file = values[5]

    response = requests.get(url_inv, verify=False)
    with open(inv_file, 'wb') as f:
        f.write(response.content)

    inv = read_inventory(inv_file)
    trace.attach_response(inv)
    trace.remove_response(output="VEL")
    trace.detrend('linear')
    trace.detrend('demean')

    # Selección de datos
    tr = trace[0]
    data = tr.data
    dt = tr.stats.delta

    # Filtro
    sampling_rate = tr.stats.sampling_rate
    nyquist = 0.5 * sampling_rate
    freqmax = min(45.0, nyquist - 0.5)
    trace.filter("bandpass", freqmin=0.1, freqmax=freqmax, corners=4, zerophase=True)

    # =============================
    # Análisis de desplazamiento, velocidad y aceleración
    # =============================
    tr = trace[0]
    data = tr.data
    times = np.linspace(0, (tr.stats.npts - 1) * dt, tr.stats.npts)

    velocity = data * 1e3  # mm/s
    tr_disp = tr.copy().integrate(method="cumtrapz")
    displacement = tr_disp.data * 1e3  # mm
    acceleration = np.gradient(data, dt) * 1e3  # mm/s²

    def get_extremes(y):
        idx_max = np.argmax(y)
        idx_min = np.argmin(y)
        return (idx_max, y[idx_max]), (idx_min, y[idx_min])

    (disp_max_t, disp_max), (disp_min_t, disp_min) = get_extremes(displacement)
    (vel_max_t, vel_max), (vel_min_t, vel_min) = get_extremes(velocity)
    (acc_max_t, acc_max), (acc_min_t, acc_min) = get_extremes(acceleration)

    vpp_disp = disp_max - disp_min
    vpp_vel = vel_max - vel_min
    vpp_acc = acc_max - acc_min

    zero_crossings = np.where(np.diff(np.sign(data)))[0]
    zero_crossing_times = times[zero_crossings]
    frequency_zero_crossings = len(zero_crossings) / (tr.stats.npts / tr.stats.sampling_rate)
    
    def annotate_extreme(ax, time, value, label, color, offset_x=10, offset_y=10):
        ax.annotate(
            label,
            xy=(time, value),
            xytext=(offset_x, offset_y),
            textcoords='offset points',
            arrowprops=dict(
                arrowstyle="->",
                color=color,
                lw=1.5,
                connectionstyle="arc3,rad=0.3"
            ),
            bbox=dict(boxstyle='round,pad=0.5', fc='white', alpha=0.8),
            fontsize=9,
            color=color
        )

    # =============================
    # Gráficas
    # =============================
    plt.style.use('seaborn-v0_8-notebook')
    colors = {'disp': '#4e79a7', 'vel': '#e15759', 'acc': '#59a14f', 'freq': '#ff7f0e'}

    fig1, axes = plt.subplots(4, 1, figsize=(14, 14), sharex=True)

    # Subplot 1: Desplazamiento
    axes[0].plot(times, displacement, color=colors['disp'], lw=1.5)
    annotate_extreme(axes[0], times[vel_max_t], vel_max, f'Max: {vel_max:.2f} mm/s', 'red', 20, 20)
    annotate_extreme(axes[0], times[vel_min_t], vel_min, f'Min: {vel_min:.2f} mm/s', 'blue', 20, -30)
    axes[0].set_ylabel(f'Desplazamiento\nVpp: {vpp_disp:.3f} mm')

    # Subplot 2: Velocidad
    axes[1].plot(times, velocity, color=colors['vel'])
    axes[1].set_ylabel(f'Velocidad\nVpp: {vpp_vel:.3f} mm/s')

    # Subplot 3: Aceleración
    axes[2].plot(times, acceleration, color=colors['acc'])
    axes[2].set_ylabel(f'Aceleración\nVpp: {vpp_acc:.3f} mm/s²')

    # Subplot 4: Cruce por cero
    axes[3].plot(times, data, color=colors['freq'])
    axes[3].scatter(zero_crossing_times, np.zeros_like(zero_crossing_times), color='red', s=50)
    axes[3].set_ylabel(f'Cruces por cero\nFZC: {frequency_zero_crossings:.3f} Hz')
    axes[3].set_xlabel('Tiempo (s)')

    fig1.suptitle(f'ANÁLISIS DE SEÑALES - {tr.id}\n{inicio} - {fin}', fontsize=14)
    plt.tight_layout()
    plt.show()


# =====================================================
# Clase GUI
# =====================================================
class App:
    def __init__(self, root):
        self.root = root
        self.root.title("Análisis Sísmico - Tesis")
        self.root.geometry("600x400")

        # Botón para seleccionar Excel
        self.btn_excel = ttk.Button(root, text="Seleccionar archivo Excel", command=self.cargar_excel)
        self.btn_excel.pack(pady=10)

        # ComboBox para elegir fila
        self.label = ttk.Label(root, text="Seleccione un sismo:")
        self.label.pack(pady=5)
        self.combo = ttk.Combobox(root, state="readonly", width=60)
        self.combo.pack(pady=5)

        # Botón de ejecutar
        self.btn_run = ttk.Button(root, text="Ejecutar análisis", command=self.run_analysis)
        self.btn_run.pack(pady=15)

        # Status
        self.status = ttk.Label(root, text="Esperando acción...", foreground="blue")
        self.status.pack(pady=5)

        self.ws = None

    def cargar_excel(self):
        file_path = filedialog.askopenfilename(filetypes=[("Excel files", "*.xlsx")])
        if not file_path:
            return
        try:
            wb = openpyxl.load_workbook(file_path)
            self.ws = wb.active
            opciones = [f"{i}. {self.ws.cell(row=i, column=2).value}" for i in range(2, self.ws.max_row + 1)]
            self.combo["values"] = opciones
            self.status.config(text=f"Archivo cargado: {file_path}")
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo cargar el Excel:\n{e}")

    def run_analysis(self):
        if not self.ws:
            messagebox.showwarning("Atención", "Primero carga un archivo Excel.")
            return
        if not self.combo.get():
            messagebox.showwarning("Atención", "Seleccione un sismo.")
            return

        idx = int(self.combo.get().split(".")[0])
        self.status.config(text="Ejecutando análisis...")

        # Hilo para no congelar la GUI
        threading.Thread(target=self.ejecutar_principal, args=(idx,)).start()

    def ejecutar_principal(self, idx):
        try:
            analizar_evento(self.ws, idx)
            self.status.config(text="✅ Análisis completado")
        except Exception as e:
            messagebox.showerror("Error en análisis", str(e))
            self.status.config(text="❌ Error durante el análisis")


# =====================================================
# Función para lanzar la GUI (para ser llamada externamente)
# =====================================================
def principal():
    root = tk.Tk()
    app = App(root)
    root.mainloop()


# Si se ejecuta directamente: abre la GUI
if __name__ == "__main__":
    run_gui()
