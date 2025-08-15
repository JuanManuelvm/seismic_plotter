#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Graficador Sísmico Avanzado - Versión mejorada con descarga automática de inventarios
"""

import numpy as np
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation
from obspy.clients.seedlink.easyseedlink import EasySeedLinkClient
from obspy import Stream, UTCDateTime, read_inventory
import threading
from collections import defaultdict
import os
import urllib3
import requests
from matplotlib.widgets import CheckButtons
import datetime
from scipy.signal import detrend

# Deshabilitar advertencias de SSL
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

class SeismicPlotter:
    def __init__(self, stations, stationxml_paths, seedlink_host="192.168.84.112", 
                 window_seconds=150, refresh_rate_ms=500, data_timeout=30):
        
        self.stations = stations
        self.stationxml_paths = stationxml_paths
        self.seedlink_host = seedlink_host
        self.window_seconds = window_seconds
        self.refresh_rate_ms = refresh_rate_ms
        self.data_timeout = data_timeout
        
        # Configuración de estilo
        self.setup_style()
        
        # Configuración de datos
        self.streams = {f"{net}.{sta}.{loc}.{cha}": Stream() for net, sta, loc, cha in self.stations}
        self.last_data_times = {sta: None for net, sta, loc, cha in self.stations}
        self.connection_status = {sta: False for net, sta, loc, cha in self.stations}
        
        self.current_values = defaultdict(lambda: {
            'vel': 0,
            'desp': 0,
            'acel': 0,
            'last_update': None,
        })
        
        # Cargar inventarios (local o descargando de la web)
        self.inventories = self.load_inventories()
        
        # Configuración de la interfaz gráfica
        self.fig, self.selector_ax, self.graph_ax = self.setup_figure()
        self.plot_elements = {
            'axes': [],
            'lines': [],
            'texts': [],
            'indicators': []
        }
        
        self.setup_checkboxes()
        
        # Cliente SeedLink
        self.client = None
        self.client_thread = None
        self.ani = None

    def setup_style(self):
        plt.style.use('default')
        plt.rcParams.update({
            'font.size': 9,
            'axes.titlesize': 10,
            'axes.labelsize': 9,
            'xtick.labelsize': 8,
            'ytick.labelsize': 8,
            'figure.facecolor': 'white',
            'axes.facecolor': 'white',
            'grid.color': '#dddddd',
            'text.color': '#333333',
            'axes.labelcolor': '#333333',
            'xtick.color': '#333333',
            'ytick.color': '#333333'
        })

    def setup_figure(self):
        fig = plt.figure(figsize=(16, 10), dpi=100)
        fig.canvas.manager.set_window_title("Monitor Sísmico")
        self.title_text = fig.suptitle('', y=0.98, fontsize=12, fontweight='bold')
        selector_ax = plt.axes([0.85, 0.1, 0.13, 0.8])
        selector_ax.set_title('Estaciones Disponibles', pad=10)
        selector_ax.axis('off')
        graph_ax = plt.axes([0.1, 0.1, 0.7, 0.8])
        graph_ax.axis('off')
        return fig, selector_ax, graph_ax

    def setup_checkboxes(self):
        station_labels = [f"{sta} ({cha})" for net, sta, loc, cha in self.stations]
        self.check = CheckButtons(
            ax=self.selector_ax,
            labels=station_labels,
            actives=[True] * len(self.stations))
        self.check.on_clicked(self.update_station_selection)

    def update_station_selection(self, label):
        pass

    def load_inventories(self):
        """Carga archivos StationXML desde local o descargándolos si no existen"""
        base_url = "https://osso.univalle.edu.co/apps/seiscomp/inventory/"
        inventories = {}

        for sta in {s[1] for s in self.stations}:
            path = self.stationxml_paths.get(sta)

            if not path:
                print(f"No se especificó ruta para {sta}")
                continue

            # Si no existe, descargarlo
            if not os.path.exists(path):
                try:
                    print(f"Descargando inventario de {sta} desde la web...")
                    url = f"{base_url}{sta}.xml"
                    response = requests.get(url, verify=False, timeout=10)
                    if response.status_code == 200:
                        os.makedirs(os.path.dirname(path), exist_ok=True)
                        with open(path, "wb") as f:
                            f.write(response.content)
                        print(f"Inventario de {sta} guardado en {path}")
                    else:
                        print(f"No se pudo descargar inventario de {sta}: código {response.status_code}")
                        continue
                except Exception as e:
                    print(f"Error descargando inventario de {sta}: {e}")
                    continue

            # Cargar inventario
            try:
                inventories[sta] = read_inventory(path)
                print(f"Inventario de {sta} cargado correctamente.")
            except Exception as e:
                print(f"Error cargando StationXML para {sta}: {str(e)}")

        return inventories

    def setup_plots(self):
        for ax in self.plot_elements['axes']:
            ax.clear()
            ax.remove()
        self.plot_elements['axes'].clear()
        self.plot_elements['lines'].clear()
        self.plot_elements['texts'].clear()
        self.plot_elements['indicators'].clear()
        self.graph_ax.clear()
        self.graph_ax.axis('off')

        if not self.stations:
            self.graph_ax.text(0.5, 0.5, 'No hay estaciones configuradas', 
                             ha='center', va='center', fontsize=12)
            return
        
        n_stations = len(self.stations)
        gs = self.graph_ax.figure.add_gridspec(
            nrows=n_stations,
            ncols=2,
            width_ratios=[3, 1],
            hspace=0.7
        )
        
        for i, (net, sta, loc, cha) in enumerate(self.stations):
            ax = self.graph_ax.figure.add_subplot(gs[i, 0])
            ax.set_title(f'Estación: {sta} | Componente: {cha}', pad=10)
            ax.set_ylabel('Counts', labelpad=5)
            ax.grid(True, linestyle=':', alpha=0.7)
            line, = ax.plot([], [], color='#1f77b4', linewidth=0.8)
            
            ax_text = self.graph_ax.figure.add_subplot(gs[i, 1])
            ax_text.axis('off')
            indicator = plt.Circle((0.1, 0.9), 0.05, color='red', transform=ax_text.transAxes)
            ax_text.add_patch(indicator)
            
            self.plot_elements['axes'].append(ax)
            self.plot_elements['lines'].append(line)
            self.plot_elements['indicators'].append(indicator)
            
            text = ax_text.text(
                0.05, 0.5, 'Cargando datos...',
                fontfamily='monospace',
                fontsize=9,
                linespacing=1.5,
                va='center',
                ha='left',
                transform=ax_text.transAxes,
                bbox=dict(facecolor='white', alpha=0.8, edgecolor='red', boxstyle='round,pad=0.5')
            )
            self.plot_elements['texts'].append(text)
        
        if self.stations:
            self.plot_elements['axes'][-1].set_xlabel('Tiempo (s)', labelpad=10)

    def start(self):
        if not self.stations:
            print("Error: No hay estaciones configuradas para graficar")
            return
            
        print(f"[{UTCDateTime.now()}] Iniciando graficador sísmico...")
        print(f"Estaciones a graficar: {self.stations}")
        
        self.setup_plots()
        self.client = self.SeismicClient(self.seedlink_host, self)
        
        for net, sta, loc, cha in self.stations:
            print(f"Conectando a: {net}.{sta}.{cha}")
            self.client.select_stream(net, sta, cha)
        
        self.client_thread = threading.Thread(target=self.client.run, daemon=True)
        self.client_thread.start()
        
        self.ani = FuncAnimation(
            self.fig,
            self.update_plot,
            interval=self.refresh_rate_ms,
            blit=False,
            cache_frame_data=False
        )
        
        try:
            plt.tight_layout(rect=[0, 0, 0.85, 1])
            plt.show()
        except KeyboardInterrupt:
            print("\nCerrando graficador...")
            self.stop()

    def stop(self):
        if self.client:
            self.client.stop()
        if self.ani:
            self.ani.event_source.stop()
        plt.close(self.fig)

    def update_plot(self, frame):
        now = datetime.datetime.now()
        fecha_str = now.strftime("%A, %d de %B de %Y")
        hora_str = now.strftime("%H:%M:%S")
        self.title_text.set_text(f'Monitor Sísmico | {hora_str} - {fecha_str}')

        current_time = UTCDateTime.now()
        artists = []
        
        for i, (net, sta, loc, cha) in enumerate(self.stations):
            key = f"{net}.{sta}.{loc}.{cha}"
            if self.last_data_times[sta] and (current_time - self.last_data_times[sta]) > self.data_timeout:
                self.connection_status[sta] = False
            
            status_color = 'green' if self.connection_status[sta] else 'red'
            self.plot_elements['indicators'][i].set_color(status_color)
            artists.append(self.plot_elements['indicators'][i])
            
            if len(self.streams[key]) > 0 and self.connection_status[sta]:
                tr = self.streams[key][0]
                times = np.linspace(0, len(tr.data)/tr.stats.sampling_rate, len(tr.data))
                self.plot_elements['lines'][i].set_data(times, tr.data)
                self.plot_elements['lines'][i].set_color("#c94949")
                data_range = max(1, np.max(np.abs(tr.data)) * 1.2)
                self.plot_elements['axes'][i].set_ylim(-data_range, data_range)
                self.plot_elements['axes'][i].set_xlim(0, times[-1] if len(times) > 0 else 10)
            else:
                self.plot_elements['lines'][i].set_data([0, self.window_seconds], [0, 0])
                self.plot_elements['lines'][i].set_color('red')
                self.plot_elements['axes'][i].set_ylim(-1, 1)
                self.plot_elements['axes'][i].set_xlim(0, self.window_seconds)
            
            artists.append(self.plot_elements['lines'][i])
            
            self.plot_elements['texts'][i].set_text(
                f"ESTACIÓN: {sta} ({cha})\n\n"
                f"DATOS:\n"
                f"Velocidad: {self.current_values[sta]['vel']:.2f} µm/s\n"
                f"Desplazamiento: {self.current_values[sta]['desp']:.2f} µm\n"
                f"Aceleración: {self.current_values[sta]['acel']:.2f} µm/s²\n\n"
                f"Muestras: {len(self.streams[key][0].data):,}\n\n" if len(self.streams[key]) > 0 else "Muestras: 0\n\n"
                f"ESTADO: [{'CONECTADO' if self.connection_status[sta] else 'SIN CONEXIÓN'}]\n"
                f"Últ. dato: {self.current_values[sta]['last_update'].strftime('%H:%M:%S') if self.current_values[sta]['last_update'] else 'Nunca'}"
            )
            self.plot_elements['texts'][i].get_bbox_patch().set_edgecolor(status_color)
            artists.append(self.plot_elements['texts'][i])
        
        return artists

    class SeismicClient(EasySeedLinkClient):
        def __init__(self, host, plotter):
            super().__init__(host)
            self.plotter = plotter
        
        def on_data(self, trace):
            key = f"{trace.stats.network}.{trace.stats.station}.{trace.stats.location}.{trace.stats.channel}"
            station = trace.stats.station
            
            if key in self.plotter.streams:
                try:
                    self.plotter.last_data_times[station] = UTCDateTime.now()
                    self.plotter.connection_status[station] = True
                    trace.detrend('linear')
                    trace.detrend('demean')
                    self.plotter.streams[key].append(trace)
                    self.plotter.streams[key].merge(method=1, fill_value='interpolate')
                    t_now = UTCDateTime.now()
                    self.plotter.streams[key].trim(t_now - self.plotter.window_seconds, t_now, pad=True, fill_value=0)
                    
                    if station in self.plotter.inventories:
                        trace.remove_response(inventory=self.plotter.inventories[station], output="VEL")
                    
                    señal = trace.trim(t_now - self.plotter.window_seconds, t_now, pad=True, fill_value=0)
                    recorte = señal.slice(t_now - 10, t_now)

                    if len(recorte) > 0:
                        vel_trace = recorte.copy()
                        self.plotter.current_values[station]['vel'] = np.abs(vel_trace.data).max() * 1e6
                        desp_trace = vel_trace.copy()
                        desp_trace.integrate()
                        self.plotter.current_values[station]['desp'] = np.abs(desp_trace.data).max() * 1e6
                        acel_trace = vel_trace.copy()
                        acel_trace.differentiate()
                        self.plotter.current_values[station]['acel'] = np.abs(acel_trace.data).max() * 1e6
                        self.plotter.current_values[station]['last_update'] = t_now
                        
                except Exception as e:
                    print(f"Error procesando datos de {station}: {str(e)}")

def main():
    stations_to_plot = [
        ("UX", "UIS09", "00", "EHZ"),
        ("UX", "UIS05", "00", "EHZ"),
        ("UX", "UIS03", "00", "HNZ"),
        ("UX", "UIS01", "00", "HNZ")
    ]
    
    stationxml_paths = {
        "UIS09": "/home/jumavamu/Documentos/PruebasSeiscom/UIS09.xml",
        "UIS05": "/home/jumavamu/Documentos/PruebasSeiscom/UIS05.xml",
        "UIS03": "/home/jumavamu/Documentos/PruebasSeiscom/UIS03.xml",
        "UIS01": "/home/jumavamu/Documentos/PruebasSeiscom/UIS01.xml"   
    }
    
    plotter = SeismicPlotter(
        stations=stations_to_plot,
        stationxml_paths=stationxml_paths,
        seedlink_host="192.168.84.112",
        window_seconds=150,
        refresh_rate_ms=500,
        data_timeout=30
    )
    plotter.start()

if __name__ == "__main__":
    main()
