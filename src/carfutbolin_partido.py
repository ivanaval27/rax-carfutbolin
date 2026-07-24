"""
RAX Carfutbolín — Sistema de Partido
v2.0 — Selección de puertos COM, equipos Negro vs Rojo
Compilar: pyinstaller --onefile --windowed --name "RAX Carfutbolin" carfutbolin_partido.py
"""

import tkinter as tk
from tkinter import font, ttk, messagebox
import serial
import serial.tools.list_ports
import threading
import time
import sys
import os
import winsound
import json
import logging
import ctypes

# ============================================================
# CONFIGURACIÓN
# ============================================================
# Ruta a carpeta sounds/ junto al .exe
if getattr(sys, 'frozen', False):
    DIR_APP = os.path.dirname(sys.executable)
else:
    DIR_APP = os.path.dirname(os.path.abspath(__file__))
DIR_SOUNDS = os.path.join(DIR_APP, "sounds")
DIR_DATA = os.path.join(os.environ.get('LOCALAPPDATA', DIR_APP), "RAX Carfutbolin")
os.makedirs(DIR_DATA, exist_ok=True)
SETTINGS_FILE = os.path.join(DIR_DATA, "settings.json")

# ============================================================
# FUNCIONES DE PERSISTENCIA
# ============================================================
def cargar_settings():
    """Cargar configuración desde settings.json junto al .exe"""
    if os.path.exists(SETTINGS_FILE):
        try:
            with open(SETTINGS_FILE, 'r') as f:
                return json.load(f)
        except Exception as e:
            logging.warning(f"No se pudo cargar settings.json: {e}")
    return {}

def guardar_settings(puerto_negro="", puerto_rojo="", tiempo_juego=4, tiempo_descanso=4):
    """Guardar configuración a settings.json junto al .exe"""
    data = {
        "puerto_negro": puerto_negro,
        "puerto_rojo": puerto_rojo,
        "tiempo_juego": tiempo_juego,
        "tiempo_descanso": tiempo_descanso
    }
    try:
        with open(SETTINGS_FILE, 'w') as f:
            json.dump(data, f, indent=2)
        logging.info(f"Configuración guardada: {data}")
        return True
    except Exception as e:
        logging.error(f"Error al guardar settings.json: {e}")
        return False

# Logging setup
log_path = os.path.join(DIR_DATA, 'carfutbolin.log')
logging.basicConfig(
    filename=log_path,
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logging.info("=== RAX Carfutbolin iniciado ===")

MINUTOS_PARTIDO = 4
MINUTOS_DESCANSO = 4

# Colores RAX Brand Book
COLOR_NEGRO = "#1a1a1a"
COLOR_ROJO = "#da0000"
COLOR_BG = "#050505"
COLOR_BG2 = "#0a0a0a"
COLOR_GLASS = "#141414"
COLOR_SILVER = "#a0a0a0"
COLOR_ORO = "#DB9651"
COLOR_ROJO_OSCURO = "#1f0808"  # Fondo para columna ROJO en historial
# ============================================================
# ESTADOS DEL PARTIDO
# ============================================================
IDLE, PRIMER_TIEMPO, DESCANSO, SEGUNDO_TIEMPO, FINALIZADO = range(5)
ESTADOS = {
    IDLE: "LISTO",
    PRIMER_TIEMPO: "1ER TIEMPO",
    DESCANSO: "DESCANSO",
    SEGUNDO_TIEMPO: "2DO TIEMPO",
    FINALIZADO: "FINALIZADO"
}

# ============================================================
# LECTOR DE PUERTOS SERIAL
# ============================================================
class LectorSerial(threading.Thread):
    def __init__(self, puerto, baud, callback_gol, callback_error, nombre):
        super().__init__(daemon=True)
        self.puerto = puerto
        self.baud = baud
        self.callback = callback_gol
        self.callback_error = callback_error
        self.nombre = nombre
        self.running = True
        self.ser = None
        self.conectado = False
        self.ready = False  # B2: solo contar goles después de READY

    def run(self):
        try:
            self.ser = serial.Serial(self.puerto, self.baud, timeout=0.5)
            time.sleep(2.5)
            self.conectado = True
            logging.info(f"[{self.nombre}] Puerto {self.puerto} conectado")

            # B2: Esperar mensaje READY del Arduino
            timeout_ready = time.time() + 10  # 10s de timeout
            while self.running and not self.ready:
                if self.ser and self.ser.in_waiting:
                    linea = self.ser.readline().decode().strip()
                    if "READY" in linea:
                        self.ready = True
                        logging.info(f"[{self.nombre}] READY recibido — sistema listo")
                if time.time() > timeout_ready:
                    logging.warning(f"[{self.nombre}] Timeout esperando READY — se continua igual")
                    self.ready = True  # permitir goles de todas formas
                    break
                time.sleep(0.1)

            # Bucle principal de detección de goles
            while self.running:
                if self.ser and self.ser.in_waiting:
                    linea = self.ser.readline().decode().strip()
                    if "GOAL" in linea and self.ready:  # B2: ignorar si no ready
                        logging.info(f"[{self.nombre}] GOAL detectado")
                        self.callback(self.nombre)
                time.sleep(0.02)
        except Exception as e:
            logging.error(f"[{self.nombre}] Error de conexion serial: {e}")
            # B1: notificar al hilo principal via callback
            if self.callback_error:
                self.callback_error(self.nombre, str(e))
        finally:
            self.conectado = False
            self.ready = False
            if self.ser and self.ser.is_open:
                try:
                    self.ser.close()
                except:
                    pass

    def detener(self):
        self.running = False
        if self.ser and self.ser.is_open:
            try:
                self.ser.close()
            except:
                pass


# ============================================================
# VENTANA DE CONFIGURACIÓN
# ============================================================
class VentanaConfig:
    def __init__(self):
        self.ventana = tk.Tk()
        self.ventana.title("RAX Carfutbolín — Configuración")
        self.ventana.configure(bg=COLOR_BG)
        self.ventana.geometry("520x580")
        self.ventana.minsize(520, 580)
        try:
            self.ventana.iconbitmap(default=os.path.join(
                os.path.dirname(os.path.abspath(__file__)), "rax_carfutbolin.ico"))
        except:
            pass

        self.puerto_negro = tk.StringVar()
        self.puerto_rojo = tk.StringVar()
        self.tiempo_juego = tk.IntVar(value=4)
        self.tiempo_descanso = tk.IntVar(value=4)

        self._crear_ui()
        self._detectar_puertos()
        self._cargar_settings_ui()

        self.ventana.bind("<Return>", lambda e: self._iniciar())

    def _detectar_puertos(self):
        puertos = list(serial.tools.list_ports.comports())
        ch340 = [p.device for p in puertos if "CH340" in p.description or "USB-SERIAL" in p.description or "serie USB" in p.description or "USB" in p.description]
        # Excluir COM1 que es el puerto interno
        ch340 = [p for p in ch340 if p.upper() not in ("COM1",)]
        if not ch340:
            ch340 = [p.device for p in puertos if p.device.upper() not in ("COM1",)]

        if len(ch340) >= 1:
            self.puerto_negro.set(ch340[0])
        if len(ch340) >= 2:
            self.puerto_rojo.set(ch340[1])

        # Actualizar combos
        menu = self.combo_negro["menu"]
        menu.delete(0, "end")
        for p in ch340:
            menu.add_command(label=p, command=lambda v=p: self.puerto_negro.set(v))

        menu = self.combo_rojo["menu"]
        menu.delete(0, "end")
        for p in ch340:
            menu.add_command(label=p, command=lambda v=p: self.puerto_rojo.set(v))

    def _refrescar(self):
        self._detectar_puertos()

    def _cargar_settings_ui(self):
        """Cargar settings.json y aplicar valores guardados en la UI"""
        cfg = cargar_settings()
        if not cfg:
            return
        if cfg.get("puerto_negro"):
            self.puerto_negro.set(cfg["puerto_negro"])
        if cfg.get("puerto_rojo"):
            self.puerto_rojo.set(cfg["puerto_rojo"])
        if cfg.get("tiempo_juego"):
            self.tiempo_juego.set(int(cfg["tiempo_juego"]))
        if cfg.get("tiempo_descanso"):
            self.tiempo_descanso.set(int(cfg["tiempo_descanso"]))
        logging.info(f"Configuración cargada desde settings.json")

    def _guardar_config(self):
        """Guardar configuración actual a settings.json"""
        ok = guardar_settings(
            puerto_negro=self.puerto_negro.get(),
            puerto_rojo=self.puerto_rojo.get(),
            tiempo_juego=self.tiempo_juego.get(),
            tiempo_descanso=self.tiempo_descanso.get()
        )
        if ok:
            messagebox.showinfo("Configuración", "✅ Configuración guardada correctamente")
        else:
            messagebox.showerror("Error", "❌ No se pudo guardar la configuración")

    def _crear_ui(self):
        # Logo / Título
        tk.Label(self.ventana, text="⚽ RAX CARFUTBOLÍN ⚽",
                 font=("Segoe UI", 22, "bold"), fg=COLOR_ROJO,
                 bg=COLOR_BG).pack(pady=(30, 5))
        tk.Label(self.ventana, text="Configuración de Puertos",
                 font=("Segoe UI", 11), fg=COLOR_SILVER,
                 bg=COLOR_BG).pack(pady=(0, 20))

        # Frame selector
        frame = tk.Frame(self.ventana, bg=COLOR_BG2, bd=0,
                         highlightbackground="#da0000", highlightthickness=1)
        frame.pack(padx=40, pady=10, fill="x")

        # Equipo NEGRO
        eq_negro = tk.Frame(frame, bg=COLOR_BG2)
        eq_negro.pack(fill="x", pady=15, padx=20)

        tk.Canvas(eq_negro, width=24, height=24, bg=COLOR_NEGRO,
                  highlightthickness=0, bd=0,
                  relief="ridge").pack(side="left", padx=(0, 10))

        tk.Label(eq_negro, text="EQUIPO NEGRO",
                 font=("Segoe UI", 14, "bold"), fg="white",
                 bg=COLOR_BG2).pack(side="left")

        self.combo_negro = tk.OptionMenu(eq_negro, self.puerto_negro, "")
        self.combo_negro.config(font=("Consolas", 11), bg=COLOR_NEGRO,
                                fg="white", activebackground="#333",
                                activeforeground="white", bd=0, width=12,
                                indicatoron=False, highlightthickness=0)
        self.combo_negro.pack(side="right")

        tk.Label(eq_negro, text="COM:",
                 font=("Segoe UI", 10), fg=COLOR_SILVER,
                 bg=COLOR_BG2).pack(side="right", padx=(0, 5))

        # Separador
        tk.Frame(frame, bg="#333", height=1).pack(fill="x", padx=20)

        # Equipo ROJO
        eq_rojo = tk.Frame(frame, bg=COLOR_BG2)
        eq_rojo.pack(fill="x", pady=15, padx=20)

        tk.Canvas(eq_rojo, width=24, height=24, bg=COLOR_ROJO,
                  highlightthickness=0, bd=0).pack(side="left", padx=(0, 10))

        tk.Label(eq_rojo, text="EQUIPO ROJO",
                 font=("Segoe UI", 14, "bold"), fg=COLOR_ROJO,
                 bg=COLOR_BG2).pack(side="left")

        self.combo_rojo = tk.OptionMenu(eq_rojo, self.puerto_rojo, "")
        self.combo_rojo.config(font=("Consolas", 11), bg=COLOR_NEGRO,
                               fg="white", activebackground="#333",
                               activeforeground="white", bd=0, width=12,
                               indicatoron=False, highlightthickness=0)
        self.combo_rojo.pack(side="right")

        tk.Label(eq_rojo, text="COM:",
                 font=("Segoe UI", 10), fg=COLOR_SILVER,
                 bg=COLOR_BG2).pack(side="right", padx=(0, 5))

        # Info
        info = tk.Frame(self.ventana, bg=COLOR_BG)
        info.pack(pady=5)
        tk.Label(info, text="💡 Conectá los Arduinos por USB antes de iniciar",
                 font=("Segoe UI", 9), fg="#666", bg=COLOR_BG).pack()
        tk.Label(info, text="📌 Ambos Nanos deben tener el firmware cargado (GOAL:A / GOAL:B)",
                 font=("Segoe UI", 9), fg="#666", bg=COLOR_BG).pack()

        # TIEMPOS
        tiempo_frame = tk.Frame(self.ventana, bg=COLOR_BG2, bd=0,
                                highlightbackground="#da0000", highlightthickness=1)
        tiempo_frame.pack(padx=40, pady=5, fill="x")

        tk.Label(tiempo_frame, text="⚙ TIEMPOS DEL PARTIDO",
                 font=("Segoe UI", 11, "bold"), fg=COLOR_ORO,
                 bg=COLOR_BG2).pack(pady=(8, 2))

        row_juego = tk.Frame(tiempo_frame, bg=COLOR_BG2)
        row_juego.pack(fill="x", pady=5, padx=20)
        tk.Label(row_juego, text="⏱ Tiempo por tiempo (min):",
                 font=("Segoe UI", 11), fg="white", bg=COLOR_BG2).pack(side="left")
        tk.Spinbox(row_juego, from_=1, to=30, textvariable=self.tiempo_juego,
                   font=("Consolas", 12, "bold"), width=4, justify="center",
                   bg=COLOR_NEGRO, fg="white", bd=0, buttonbackground="#333",
                   relief="flat", highlightthickness=0).pack(side="right")

        row_desc = tk.Frame(tiempo_frame, bg=COLOR_BG2)
        row_desc.pack(fill="x", pady=(0, 8), padx=20)
        tk.Label(row_desc, text="☕ Tiempo de descanso (min):",
                 font=("Segoe UI", 11), fg="white", bg=COLOR_BG2).pack(side="left")
        tk.Spinbox(row_desc, from_=1, to=15, textvariable=self.tiempo_descanso,
                   font=("Consolas", 12, "bold"), width=4, justify="center",
                   bg=COLOR_NEGRO, fg="white", bd=0, buttonbackground="#333",
                   relief="flat", highlightthickness=0).pack(side="right")

        # Botones
        btn_frame = tk.Frame(self.ventana, bg=COLOR_BG)
        btn_frame.pack(pady=20)

        tk.Button(btn_frame, text="🔄 REFRESCAR PUERTOS", bg="#333", fg="#ccc",
                  font=("Segoe UI", 10), bd=0, padx=15, pady=6,
                  activebackground="#555", cursor="hand2",
                  command=self._refrescar).pack(side="left", padx=5)

        tk.Button(btn_frame, text="💾 GUARDAR CONFIG", bg="#2a6e2a", fg="white",
                  font=("Segoe UI", 10, "bold"), bd=0, padx=15, pady=8,
                  activebackground="#3d9e3d", cursor="hand2",
                  command=self._guardar_config).pack(side="left", padx=5)

        tk.Button(btn_frame, text="⚽ INICIAR PARTIDO", bg=COLOR_ROJO, fg="white",
                  font=("Segoe UI", 12, "bold"), bd=0, padx=20, pady=8,
                  activebackground="#ff1a1a", cursor="hand2",
                  command=self._iniciar).pack(side="left", padx=5)

    def _iniciar(self):
        p1 = self.puerto_negro.get()
        p2 = self.puerto_rojo.get()

        if not p1 and not p2:
            messagebox.showerror("Error", "Conectá al menos un Arduino")
            return

        self.ventana.destroy()
        app = AppPartido(
            puerto_negro=p1,
            puerto_rojo=p2,
            minutos_partido=self.tiempo_juego.get(),
            minutos_descanso=self.tiempo_descanso.get()
        )
        app.ejecutar()

    def ejecutar(self):
        self.ventana.mainloop()


# ============================================================
# APLICACIÓN PRINCIPAL
# ============================================================
class AppPartido:
    def __init__(self, puerto_negro="", puerto_rojo="", minutos_partido=4, minutos_descanso=4):
        self.puerto_negro = puerto_negro
        self.puerto_rojo = puerto_rojo
        self.MINUTOS_PARTIDO = minutos_partido
        self.MINUTOS_DESCANSO = minutos_descanso

        self.ventana = tk.Tk()
        self.ventana.title("RAX Carfutbolín")
        self.ventana.configure(bg=COLOR_BG)
        self.fullscreen = False
        self._saved_geometry = None
        # Iniciar en ventana NORMAL (no maximizada, no fullscreen)
        # para que el usuario pueda arrastrar entre monitores
        self.ventana.state('normal')
        self._center_window(1024, 768)
        self.ventana.bind("<Escape>", lambda e: self._salir_fullscreen())
        self.ventana.bind("<F11>", lambda e: self._entrar_fullscreen())
        self.ventana.bind("<space>", lambda e: self._toggle_partido())
        try:
            self.ventana.iconbitmap(default=os.path.join(
                os.path.dirname(os.path.abspath(__file__)), "rax_carfutbolin.ico"))
        except:
            pass

        # Estado del partido
        self.estado = IDLE
        self.tiempo_restante = self.MINUTOS_PARTIDO * 60
        self.goles_negro = 0
        self.goles_rojo = 0
        self.historial = []
        self.timer_corriendo = False
        self.timer_id = None
        self.half = "1T"
        self.equipo_negro = "NEGRO"
        self.equipo_rojo = "ROJO"
        self.ventana_celebrar = None
        # N2: Cooldown en Python como defensa en profundidad
        self.ultimo_gol_time = 0
        self.COOLDOWN_GOL_PYTHON = 10  # segundos

        # Fuentes
        self.fnt_titulo = font.Font(family="Segoe UI", size=28, weight="bold")
        self.fnt_tiempo = font.Font(family="Segoe UI", size=72, weight="bold")
        self.fnt_score = font.Font(family="Segoe UI", size=84, weight="bold")
        self.fnt_team = font.Font(family="Segoe UI", size=26, weight="bold")
        self.fnt_hist = font.Font(family="Consolas", size=14)
        self.fnt_btn = font.Font(family="Segoe UI", size=13, weight="bold")
        self.fnt_estado = font.Font(family="Segoe UI", size=16)
        self.fnt_gol = font.Font(family="Segoe UI", size=36, weight="bold")

        # Cargar logo RAX para la UI — priorizar PNG sobre ICO
        self.img_logo = None
        rutas_logo = [
            os.path.join(DIR_APP, "resources", "logo.png"),
            os.path.join(DIR_APP, "logo.png"),
            os.path.join(DIR_APP, "rax_carfutbolin.ico"),
        ]
        for logo_path in rutas_logo:
            if os.path.exists(logo_path):
                try:
                    from PIL import Image, ImageTk
                    pil_img = Image.open(logo_path).resize((80, 80), Image.LANCZOS)
                    self.img_logo = ImageTk.PhotoImage(pil_img)
                    logging.info(f"Logo RAX cargado desde: {logo_path}")
                except Exception as e:
                    logging.warning(f"No se pudo cargar logo desde {logo_path}: {e}")
                    continue
                break

        self._crear_ui()
        self._conectar_arduinos()

    def _conectar_arduinos(self):
        if self.puerto_negro:
            try:
                self.lector_negro = LectorSerial(
                    self.puerto_negro, 9600, self._gol_detectado,
                    self._error_serial, "NEGRO")
                self.lector_negro.start()
                self.lbl_com_negro.config(
                    text=f"{self.equipo_negro}: {self.puerto_negro} ✅", fg="white")
                logging.info(f"Lector NEGRO iniciado en {self.puerto_negro}")
            except Exception as e:
                self.lbl_com_negro.config(
                    text=f"{self.equipo_negro}: {self.puerto_negro} ❌", fg=COLOR_ROJO)
                logging.error(f"Error al conectar NEGRO en {self.puerto_negro}: {e}")

        if self.puerto_rojo:
            try:
                self.lector_rojo = LectorSerial(
                    self.puerto_rojo, 9600, self._gol_detectado,
                    self._error_serial, "ROJO")
                self.lector_rojo.start()
                self.lbl_com_rojo.config(
                    text=f"{self.equipo_rojo}: {self.puerto_rojo} ✅", fg=COLOR_ROJO)
                logging.info(f"Lector ROJO iniciado en {self.puerto_rojo}")
            except Exception as e:
                self.lbl_com_rojo.config(
                    text=f"{self.equipo_rojo}: {self.puerto_rojo} ❌", fg=COLOR_ROJO)
                logging.error(f"Error al conectar ROJO en {self.puerto_rojo}: {e}")

    def _error_serial(self, equipo, mensaje):
        """B1: Callback de error desde el hilo LectorSerial — muestra messagebox y log"""
        logging.error(f"[{equipo}] Error serial en segundo plano: {mensaje}")
        try:
            self.ventana.after(0, lambda: messagebox.showerror(
                "Error de Conexión",
                f"Se perdió la conexión con el Arduino {equipo}.\n\n{mensaje}\n\n"
                "Verificá el cable USB y reiniciá el sistema."))
        except:
            pass

    def _crear_ui(self):
        # Contenedor principal HORIZONTAL
        main = tk.Frame(self.ventana, bg=COLOR_BG)
        main.pack(fill="both", expand=True, padx=30, pady=15)

        # === LADO IZQUIERDO: Partido ===
        left = tk.Frame(main, bg=COLOR_BG)
        left.pack(side="left", fill="both", expand=True)

        # HEADER con logo RAX (alineado arriba-izquierda)
        header = tk.Frame(left, bg=COLOR_BG)
        header.pack(fill="x", anchor="nw")
        
        # Fila superior: logo + título
        top_row = tk.Frame(header, bg=COLOR_BG)
        top_row.pack(fill="x", anchor="w")
        if self.img_logo:
            tk.Label(top_row, image=self.img_logo,
                     bg=COLOR_BG).pack(side="left", padx=(0, 10))
        tk.Label(top_row, text="RAX CARFUTBOLÍN",
                 font=self.fnt_titulo, fg=COLOR_ROJO, bg=COLOR_BG,
                 anchor="w").pack(side="left")
        
        # Botón pantalla completa
        self.btn_fullscreen = tk.Label(top_row, text="⛶",
                                       font=("Segoe UI", 14, "bold"),
                                       fg="#666", bg=COLOR_BG, cursor="hand2")
        self.btn_fullscreen.pack(side="right", padx=5)
        self.btn_fullscreen.bind("<Button-1>", lambda e: self._entrar_fullscreen() if not self.fullscreen else self._salir_fullscreen())
        
        tk.Frame(header, bg=COLOR_ROJO, height=2).pack(fill="x", pady=2)

        info_estado = tk.Frame(header, bg=COLOR_BG)
        info_estado.pack()
        self.lbl_estado = tk.Label(info_estado, text=ESTADOS[self.estado],
                                   font=self.fnt_estado, fg=COLOR_ORO, bg=COLOR_BG)
        self.lbl_estado.pack(side="left", padx=5)
        self.lbl_half = tk.Label(info_estado, text="1ER TIEMPO",
                                 font=self.fnt_estado, fg="#888", bg=COLOR_BG)
        self.lbl_half.pack(side="left", padx=5)

        # TIMER
        timer_frame = tk.Frame(left, bg=COLOR_BG)
        timer_frame.pack(pady=5)
        self.lbl_tiempo = tk.Label(timer_frame, text=f"{self.MINUTOS_PARTIDO}:00",
                                   font=self.fnt_tiempo, fg="white", bg=COLOR_BG)
        self.lbl_tiempo.pack()

        # Gol notification
        self.lbl_gol = tk.Label(left, text="", font=self.fnt_gol,
                                fg=COLOR_ORO, bg=COLOR_BG)
        self.lbl_gol.pack(pady=3)

        # SCOREBOARD
        score_frame = tk.Frame(left, bg="#0d0d0d", highlightbackground="#da0000",
                               highlightthickness=2, bd=0)
        score_frame.pack(pady=8, ipadx=25, ipady=10)

        score_row = tk.Frame(score_frame, bg=COLOR_BG2)
        score_row.pack()

        # NEGRO
        eq_negro = tk.Frame(score_row, bg=COLOR_BG2, width=200)
        eq_negro.pack(side="left", padx=15)
        self.lbl_eq_negro = tk.Label(eq_negro, text="⚪ NEGRO",
                                     font=self.fnt_team, fg="white", bg=COLOR_BG2)
        self.lbl_eq_negro.pack()
        self.lbl_score_negro = tk.Label(eq_negro, text="0",
                                        font=self.fnt_score, fg="white", bg=COLOR_BG2)
        self.lbl_score_negro.pack()

        # VS
        vs_frame = tk.Frame(score_row, bg=COLOR_BG2)
        vs_frame.pack(side="left", padx=8)
        tk.Label(vs_frame, text="VS", font=("Segoe UI", 18, "bold"),
                 fg=COLOR_ORO, bg=COLOR_BG2).pack()

        # ROJO
        eq_rojo = tk.Frame(score_row, bg=COLOR_BG2, width=200)
        eq_rojo.pack(side="left", padx=15)
        self.lbl_eq_rojo = tk.Label(eq_rojo, text="🔴 ROJO",
                                    font=self.fnt_team, fg=COLOR_ROJO, bg=COLOR_BG2)
        self.lbl_eq_rojo.pack()
        self.lbl_score_rojo = tk.Label(eq_rojo, text="0",
                                       font=self.fnt_score, fg=COLOR_ROJO, bg=COLOR_BG2)
        self.lbl_score_rojo.pack()

        tk.Frame(left, bg="#da0000", height=1).pack(fill="x", pady=5)

        # CONTROLES
        btn_frame = tk.Frame(left, bg=COLOR_BG)
        btn_frame.pack(pady=6)
        self.btn_iniciar = tk.Button(btn_frame, text="⏯ INICIAR PARTIDO",
                                     font=self.fnt_btn, bg=COLOR_ROJO, fg="white",
                                     activebackground="#ff1a1a", bd=0, padx=15,
                                     pady=6, cursor="hand2", command=self._iniciar_partido)
        self.btn_iniciar.pack(side="left", padx=3)
        self.btn_descanso = tk.Button(btn_frame, text="☐ DESCANSO",
                                      font=self.fnt_btn, bg="#333", fg="#ccc",
                                      activebackground="#888", bd=0, padx=12,
                                      pady=6, cursor="hand2", state="disabled",
                                      command=self._iniciar_descanso)
        self.btn_descanso.pack(side="left", padx=3)
        self.btn_segundo = tk.Button(btn_frame, text="⚽ 2DO TIEMPO",
                                     font=self.fnt_btn, bg=COLOR_ROJO, fg="white",
                                     activebackground="#ff1a1a", bd=0, padx=12,
                                     pady=6, cursor="hand2", state="disabled",
                                     command=self._iniciar_segundo_tiempo)
        self.btn_segundo.pack(side="left", padx=3)
        tk.Button(btn_frame, text="🔄 RESET", font=self.fnt_btn, bg="#333",
                  fg="#ccc", activebackground="#555", bd=0, padx=10,
                  pady=6, cursor="hand2", command=self._reset).pack(side="left", padx=3)
        tk.Button(btn_frame, text="⏻ SALIR", font=self.fnt_btn,
                  bg="#0d0000", fg=COLOR_ROJO, activebackground="#1a0000",
                  bd=0, padx=12, pady=6, cursor="hand2",
                  command=self._salir).pack(side="left", padx=5)

        # STATUS
        status = tk.Frame(left, bg=COLOR_BG)
        status.pack(side="bottom", fill="x", pady=2)
        tk.Label(status, text="[Espacio] Iniciar", font=("Consolas", 9),
                 fg="#666", bg=COLOR_BG).pack(side="left")
        self.lbl_com_negro = tk.Label(status, text="⚪ Negro: ...",
                                      font=("Consolas", 9), fg=COLOR_SILVER, bg=COLOR_BG)
        self.lbl_com_negro.pack(side="right", padx=8)
        self.lbl_com_rojo = tk.Label(status, text="🔴 Rojo: ...",
                                     font=("Consolas", 9), fg=COLOR_SILVER, bg=COLOR_BG)
        self.lbl_com_rojo.pack(side="right", padx=8)

        # Footer
        tk.Label(left, text="© 2026 RAX Experience · Todos los derechos reservados · Powered by Iván Nava",
                 font=("Segoe UI", 8), fg="#555", bg=COLOR_BG).pack(side="bottom", pady=2)

        # === LADO DERECHO: Historial ===
        right = tk.Frame(main, bg=COLOR_BG2, highlightbackground="#da0000",
                         highlightthickness=1, width=380)
        right.pack(side="right", fill="y", padx=(15, 0))
        right.pack_propagate(False)

        # Título
        tk.Label(right, text="📋 GOLES", font=self.fnt_estado,
                         fg=COLOR_ORO, bg="#0d0d0d").pack(pady=(10, 5))
        tk.Frame(right, bg=COLOR_ROJO, height=1).pack(fill="x", padx=10, pady=2)

        # Columnas de equipos
        cols = tk.Frame(right, bg=COLOR_BG2)
        cols.pack(fill="both", expand=True, padx=5)

        # NEGRO
        col_negro = tk.Frame(cols, bg=COLOR_NEGRO, highlightbackground="#da0000",
                             highlightthickness=1)
        col_negro.pack(side="left", fill="both", expand=True, padx=2)
        col_negro.pack_propagate(False)
        tk.Label(col_negro, text="⚪ NEGRO", font=("Segoe UI", 12, "bold"),
                 fg="white", bg=COLOR_NEGRO).pack(pady=3)

        self.canvas_negro = tk.Canvas(col_negro, bg=COLOR_NEGRO,
                                      highlightthickness=0)
        self.inner_negro = tk.Frame(self.canvas_negro, bg=COLOR_NEGRO)
        self.canvas_negro.pack(fill="both", expand=True)
        self.canvas_negro.create_window((0, 0), window=self.inner_negro, anchor="nw")

        # Separador
        tk.Frame(cols, bg=COLOR_ROJO, width=2).pack(side="left", fill="y", padx=1)

        # ROJO
        col_rojo = tk.Frame(cols, bg=COLOR_ROJO_OSCURO, highlightbackground="#da0000",
                             highlightthickness=1)
        col_rojo.pack(side="left", fill="both", expand=True, padx=2)
        col_rojo.pack_propagate(False)
        tk.Label(col_rojo, text="🔴 ROJO", font=("Segoe UI", 12, "bold"),
                 fg=COLOR_ROJO, bg=COLOR_ROJO_OSCURO).pack(pady=3)

        self.canvas_rojo = tk.Canvas(col_rojo, bg=COLOR_ROJO_OSCURO,
                                     highlightthickness=0)
        self.inner_rojo = tk.Frame(self.canvas_rojo, bg=COLOR_ROJO_OSCURO)
        self.canvas_rojo.pack(fill="both", expand=True)
        self.canvas_rojo.create_window((0, 0), window=self.inner_rojo, anchor="nw")

    # ============================================================
    # LÓGICA DEL PARTIDO
    # ============================================================
    def _gol_detectado(self, equipo):
        if self.estado not in (PRIMER_TIEMPO, SEGUNDO_TIEMPO):
            return

        # N2: Cooldown en Python — defensa en profundidad
        ahora = time.time()
        if ahora - self.ultimo_gol_time < self.COOLDOWN_GOL_PYTHON:
            logging.info(f"[{equipo}] GOAL ignorado por cooldown ({ahora - self.ultimo_gol_time:.1f}s < {self.COOLDOWN_GOL_PYTHON}s)")
            return
        self.ultimo_gol_time = ahora

        minuto_gol = int((self.MINUTOS_PARTIDO * 60 - self.tiempo_restante) / 60)
        segundo_gol = int((self.MINUTOS_PARTIDO * 60 - self.tiempo_restante) % 60)
        half = "1T" if self.estado == PRIMER_TIEMPO else "2T"
        half_label = "1ER TIEMPO" if self.estado == PRIMER_TIEMPO else "2DO TIEMPO"

        # En 2do tiempo los equipos cambian de lado
        if self.estado == PRIMER_TIEMPO:
            if equipo == "NEGRO":
                self.goles_negro += 1
                label = "NEGRO"
                color = "white"
            else:
                self.goles_rojo += 1
                label = "ROJO"
                color = COLOR_ROJO
        else:
            # Cambiaron de lado
            if equipo == "NEGRO":
                self.goles_rojo += 1
                label = "ROJO"
                color = COLOR_ROJO
            else:
                self.goles_negro += 1
                label = "NEGRO"
                color = "white"

        self.historial.append((minuto_gol, segundo_gol, label, half, half_label, color))
        self._actualizar_ui()
        self._animar_gol(label)
        # Sonido y celebración
        sonido = f"gol_{label.lower()}.wav"
        self._reproducir_sonido(sonido)
        self._reproducir_sonido("gol.wav")  # sonido genérico también
        self._celebrar_gol(label, color)
        # B3: Log de gol
        logging.info(f"GOL {label} ({minuto_gol}:{segundo_gol:02d} · {half_label}) — "
                     f"Score: NEGRO {self.goles_negro} / ROJO {self.goles_rojo}")

    def _animar_gol(self, equipo):
        color = "white" if equipo == "NEGRO" else COLOR_ROJO
        m = int((self.MINUTOS_PARTIDO * 60 - self.tiempo_restante) / 60)
        s = int((self.MINUTOS_PARTIDO * 60 - self.tiempo_restante) % 60)
        half = "1ER TIEMPO" if self.estado == PRIMER_TIEMPO else "2DO TIEMPO"
        self.lbl_gol.config(
            text=f"⚽ GOL {equipo}! ({m}:{s:02d} · {half}) ⚽",
            fg=color)
        self.lbl_tiempo.config(fg=COLOR_ORO)
        self.ventana.after(3000, self._limpiar_gol)

    def _limpiar_gol(self):
        self.lbl_gol.config(text="")
        self.lbl_tiempo.config(fg="white")
        self._actualizar_tiempo()
        # Cerrar celebración si existe
        try:
            self.ventana_celebrar.destroy()
        except:
            pass

    def _reproducir_sonido(self, nombre):
        """Reproduce un .wav desde la carpeta sounds/ si existe"""
        ruta = os.path.join(DIR_SOUNDS, nombre)
        if os.path.exists(ruta):
            try:
                winsound.PlaySound(ruta, winsound.SND_ASYNC)
            except:
                pass

    def _celebrar_gol(self, equipo, color):
        """Overlay de celebración tipo flash"""
        try:
            self.ventana_celebrar.destroy()
        except:
            pass
        self.ventana_celebrar = tk.Toplevel(self.ventana)
        self.ventana_celebrar.overrideredirect(True)
        self.ventana_celebrar.attributes("-topmost", True)
        self.ventana_celebrar.configure(bg="black")
        self.ventana_celebrar.attributes("-alpha", 0.85)

        # Tamaño: toda la pantalla
        ancho = self.ventana.winfo_width()
        alto = self.ventana.winfo_height()
        x = self.ventana.winfo_x()
        y = self.ventana.winfo_y()
        if ancho < 100:
            ancho = 1920
            alto = 1080
        self.ventana_celebrar.geometry(f"{ancho}x{alto}+{x}+{y}")

        # Fondo con efecto
        bg_color = "#1a0000" if equipo == "ROJO" else "#111"
        frame = tk.Frame(self.ventana_celebrar, bg=bg_color)
        frame.pack(fill="both", expand=True)

        # Texto grande con sombra
        emoji = "🔴" if equipo == "ROJO" else "⚪"
        txt = f"{emoji} GOL DE {equipo} {emoji}"
        lbl = tk.Label(frame, text=txt,
                       font=("Segoe UI", 48, "bold"),
                       fg=color, bg=bg_color)
        lbl.pack(expand=True)

        # Subtítulo
        m = int((self.MINUTOS_PARTIDO * 60 - self.tiempo_restante) / 60)
        s = int((self.MINUTOS_PARTIDO * 60 - self.tiempo_restante) % 60)
        half = "1ER TIEMPO" if self.estado == PRIMER_TIEMPO else "2DO TIEMPO"
        tk.Label(frame, text=f"{m}:{s:02d} · {half}",
                 font=("Segoe UI", 24), fg="#ccc", bg=bg_color).pack()

        # Destello: animar opacidad
        self._animar_destello(1.0, -0.05)

    def _animar_destello(self, alpha, paso):
        try:
            self.ventana_celebrar.attributes("-alpha", alpha)
            nueva = alpha + paso
            if nueva > 0.85:
                nueva = 0.85
                paso = -0.05
            elif nueva < 0.3:
                nueva = 0.3
                paso = 0.05
            self.ventana_celebrar.after(80, lambda: self._animar_destello(nueva, paso))
        except:
            pass

    def _actualizar_tiempo(self):
        if self.estado == DESCANSO:
            total = self.MINUTOS_DESCANSO * 60
        else:
            total = self.MINUTOS_PARTIDO * 60
        resto = total - (total - self.tiempo_restante)
        m = int(self.tiempo_restante / 60)
        s = int(self.tiempo_restante % 60)
        self.lbl_tiempo.config(text=f"{m}:{s:02d}")

    def _get_monitor_rect(self):
        """Obtener (x, y, w, h) del monitor donde está la ventana.
        Usa win32api para detectar el monitor ACTUAL, no el primario.
        Retorna None si falla."""
        try:
            from ctypes import wintypes

            # Obtener HWND de la ventana tkinter.
            # En algunas versiones de tkinter, winfo_id() ya devuelve
            # el HWND toplevel; en otras, hay que usar GetParent().
            wid = self.ventana.winfo_id()
            hwnd = ctypes.windll.user32.GetParent(wid)
            # Verificar que GetParent devolvió un HWND válido (distinto de 0 y del desktop)
            if not hwnd or hwnd == ctypes.windll.user32.GetDesktopWindow():
                hwnd = wid  # usar winfo_id() directo como fallback

            # Si el HWND sigue sin ser válido, intentar obtener el root
            if not hwnd:
                hwnd = wid

            class MONITORINFOEXW(ctypes.Structure):
                _fields_ = [
                    ("cbSize",   wintypes.DWORD),
                    ("rcMonitor", wintypes.RECT),
                    ("rcWork",    wintypes.RECT),
                    ("dwFlags",   wintypes.DWORD),
                    ("szDevice",  wintypes.WCHAR * 32),
                ]

            mi = MONITORINFOEXW()
            mi.cbSize = ctypes.sizeof(MONITORINFOEXW)

            MONITOR_DEFAULTTONEAREST = 2
            hmonitor = ctypes.windll.user32.MonitorFromWindow(
                hwnd, MONITOR_DEFAULTTONEAREST)

            if ctypes.windll.user32.GetMonitorInfoW(hmonitor, ctypes.byref(mi)):
                r = mi.rcMonitor
                return (r.left, r.top,
                        r.right - r.left, r.bottom - r.top)
        except Exception as e:
            logging.warning(f"No se pudo obtener rect del monitor: {e}")
        return None

    def _center_window(self, w, h):
        """Centrar la ventana en el monitor donde está actualmente.
        Si no se puede detectar el monitor, centrar en la pantalla principal."""
        monitor = self._get_monitor_rect()
        if monitor:
            mx, my, mw, mh = monitor
            x = mx + (mw - w) // 2
            y = my + (mh - h) // 2
        else:
            ws = self.ventana.winfo_screenwidth()
            hs = self.ventana.winfo_screenheight()
            x = (ws - w) // 2
            y = (hs - h) // 2
        self.ventana.geometry(f"{w}x{h}+{x}+{y}")

    def _entrar_fullscreen(self):
        """F11: Fullscreen en el monitor ACTUAL.
        NO usa .attributes('-fullscreen') — usa overrideredirect + win32api.
        CRÍTICO: detectar el monitor ANTES de overrideredirect, porque
        overrideredirect(True) reposiciona la ventana al monitor principal."""
        if self.fullscreen:
            return
        # Guardar geometry actual para restaurar después
        self._saved_geometry = self.ventana.geometry()
        logging.info(f"Guardada geometry previa: {self._saved_geometry}")

        # ⚠️ CRÍTICO: Detectar monitor ANTES de overrideredirect.
        # overrideredirect(True) hace que Windows reposicione la ventana
        # al monitor principal, así que debemos capturar el rect antes.
        monitor = self._get_monitor_rect()
        if monitor:
            mx, my, mw, mh = monitor
            logging.info(f"Fullscreen en monitor: {mx},{my} {mw}x{mh}")
        else:
            logging.warning("No se pudo detectar monitor — fallback a zoomed")

        # 1. Ocultar barra de título
        self.ventana.overrideredirect(True)

        self.fullscreen = True

        # 2. Aplicar geometría del monitor detectado
        if monitor:
            self.ventana.geometry(f"{mw}x{mh}+{mx}+{my}")
        else:
            # Fallback: state('zoomed') que respeta monitor actual en Windows
            logging.info("Fallback a state('zoomed') para fullscreen")
            self.ventana.state('zoomed')

        self.ventana.update_idletasks()
        txt = "🗖"
        try:
            self.btn_fullscreen.config(text=txt)
        except:
            pass
        logging.info(f"Fullscreen: ON")

    def _salir_fullscreen(self):
        """Escape: Salir de fullscreen, volver a ventana normal."""
        if not self.fullscreen:
            return
        self.fullscreen = False

        # 1. Restaurar barra de título
        self.ventana.overrideredirect(False)

        # 2. Volver a estado normal
        self.ventana.state('normal')

        # 3. Restaurar geometry guardada
        if self._saved_geometry:
            try:
                self.ventana.geometry(self._saved_geometry)
                logging.info(f"Geometry restaurada: {self._saved_geometry}")
            except:
                self._center_window(1024, 768)
        else:
            self._center_window(1024, 768)

        self.ventana.update_idletasks()
        txt = "⛶"
        try:
            self.btn_fullscreen.config(text=txt)
        except:
            pass
        logging.info(f"Fullscreen: OFF")

    def _toggle_partido(self):
        if self.estado == IDLE:
            self._iniciar_partido()
        elif self.estado == PRIMER_TIEMPO:
            pass
        elif self.estado == DESCANSO:
            self._iniciar_segundo_tiempo()

    def _iniciar_partido(self):
        if self.estado != IDLE:
            return
        self.estado = PRIMER_TIEMPO
        self.tiempo_restante = self.MINUTOS_PARTIDO * 60
        self.half = "1T"
        self.lbl_half.config(text="1ER TIEMPO")
        self._actualizar_ui()
        self._iniciar_timer()
        self.btn_iniciar.config(state="disabled", text="▶ JUGANDO")
        self.btn_descanso.config(state="normal", bg="#DB9651", fg="white")
        # Sonido inicio
        self._reproducir_sonido("inicio.wav")
        logging.info(f"PARTIDO INICIADO — 1er tiempo ({self.MINUTOS_PARTIDO} min)")

    def _iniciar_descanso(self):
        if self.estado != PRIMER_TIEMPO:
            return
        self._detener_timer()
        self.estado = DESCANSO
        self.tiempo_restante = self.MINUTOS_DESCANSO * 60
        self.lbl_half.config(text="☐ DESCANSO")
        self._actualizar_ui()
        self.btn_descanso.config(state="disabled", bg="#333", fg="#ccc")
        self.btn_segundo.config(state="normal")
        self.btn_iniciar.config(state="normal", text="▶ CONTINUAR")
        logging.info(f"DESCANSO INICIADO ({self.MINUTOS_DESCANSO} min)")

    def _iniciar_segundo_tiempo(self):
        if self.estado != DESCANSO:
            return
        self.estado = SEGUNDO_TIEMPO
        self.tiempo_restante = self.MINUTOS_PARTIDO * 60
        self.half = "2T"
        self.lbl_half.config(text="2DO TIEMPO")

        # B5: NO intercambiar labels. El scoreboard siempre muestra NEGRO a izquierda, ROJO a derecha.
        # La logica de _gol_detectado ya invierte los contadores en 2T automaticamente.

        self._actualizar_ui()
        self._iniciar_timer()
        self.btn_segundo.config(state="disabled")
        self.btn_descanso.config(state="disabled", bg="#333", fg="#ccc")
        self.btn_iniciar.config(state="disabled", text="▶ JUGANDO")
        logging.info(f"SEGUNDO TIEMPO INICIADO ({self.MINUTOS_PARTIDO} min)")

    def _iniciar_timer(self):
        if self.timer_corriendo:
            return
        self.timer_corriendo = True
        self._tick_timer()

    def _detener_timer(self):
        self.timer_corriendo = False
        if self.timer_id:
            self.ventana.after_cancel(self.timer_id)
            self.timer_id = None

    def _tick_timer(self):
        if not self.timer_corriendo:
            return
        self.tiempo_restante -= 1

        if self.tiempo_restante <= 0:
            self.tiempo_restante = 0
            self._tiempo_cumplido()
            return

        m = int(self.tiempo_restante / 60)
        s = int(self.tiempo_restante % 60)
        self.lbl_tiempo.config(text=f"{m}:{s:02d}")

        if self.tiempo_restante <= 30:
            self.lbl_tiempo.config(fg=COLOR_ROJO)
        elif self.tiempo_restante <= 60:
            self.lbl_tiempo.config(fg=COLOR_ORO)
        else:
            self.lbl_tiempo.config(fg="white")

        self.timer_id = self.ventana.after(1000, self._tick_timer)

    def _tiempo_cumplido(self):
        self.timer_corriendo = False
        self.lbl_tiempo.config(text="0:00", fg=COLOR_ROJO)
        logging.info(f"TIEMPO CUMPLIDO — Estado: {ESTADOS.get(self.estado, '?')}")

        if self.estado == PRIMER_TIEMPO:
            # Ir automáticamente a descanso
            self.estado = DESCANSO
            self.tiempo_restante = self.MINUTOS_DESCANSO * 60
            self.lbl_half.config(text="☐ DESCANSO")
            self.btn_descanso.config(state="disabled", bg="#333", fg="#ccc")
            self.btn_segundo.config(state="normal")
            self.lbl_gol.config(text="☕ DESCANSO — 2do tiempo en breve...", fg=COLOR_ORO)
            self._actualizar_ui()
            # Iniciar descanso automático
            self._iniciar_timer()

        elif self.estado == DESCANSO:
            # Descanso terminó → ir al 2do tiempo
            self._iniciar_segundo_tiempo()

        elif self.estado == SEGUNDO_TIEMPO:
            self.estado = FINALIZADO
            self.lbl_half.config(text="🏁 PARTIDO FINALIZADO")
            self._mostrar_resultado()
            self._actualizar_ui()
            logging.info(f"PARTIDO FINALIZADO — Score final: NEGRO {self.goles_negro} / ROJO {self.goles_rojo}")

    def _mostrar_resultado(self):
        if self.goles_negro > self.goles_rojo:
            ganador = "⚪ NEGRO"
        elif self.goles_rojo > self.goles_negro:
            ganador = "🔴 ROJO"
        else:
            ganador = "EMPATE"

        self.lbl_gol.config(text=f"🏆 GANADOR: {ganador} 🏆", fg=COLOR_ORO)
        self._reproducir_sonido("final.wav")

    def _reset(self):
        self._detener_timer()
        self.estado = IDLE
        self.tiempo_restante = self.MINUTOS_PARTIDO * 60
        self.goles_negro = 0
        self.goles_rojo = 0
        self.historial = []
        self.half = "1T"
        self.equipo_negro = "NEGRO"
        self.equipo_rojo = "ROJO"
        # N2: resetear cooldown
        self.ultimo_gol_time = 0

        self.lbl_tiempo.config(text=f"{self.MINUTOS_PARTIDO}:00", fg="white")
        self.lbl_half.config(text="1ER TIEMPO")
        self.lbl_gol.config(text="")
        self.lbl_eq_negro.config(text="⚪ NEGRO")
        self.lbl_eq_rojo.config(text="🔴 ROJO")

        self.btn_iniciar.config(state="normal", text="⏯ INICIAR PARTIDO", bg=COLOR_ROJO)
        self.btn_descanso.config(state="disabled", bg="#333", fg="#ccc")
        self.btn_segundo.config(state="disabled")

        self._actualizar_ui()
        logging.info("PARTIDO RESETEADO")

    def _salir(self):
        """Cerrar la aplicacion"""
        if self.estado in (PRIMER_TIEMPO, SEGUNDO_TIEMPO):
            if not messagebox.askyesno("Salir", "Hay un partido en curso. ¿Salir igual?"):
                return
        self._detener_timer()
        try:
            self.lector_negro.detener()
        except:
            pass
        try:
            self.lector_rojo.detener()
        except:
            pass
        logging.info("APLICACION CERRADA")
        self.ventana.destroy()

    def _actualizar_ui(self):
        self.lbl_estado.config(text=ESTADOS.get(self.estado, "?"))
        self.lbl_score_negro.config(text=str(self.goles_negro))
        self.lbl_score_rojo.config(text=str(self.goles_rojo))

        # Historial en columnas separadas
        for w in self.inner_negro.winfo_children():
            w.destroy()
        for w in self.inner_rojo.winfo_children():
            w.destroy()

        # Separar goles por equipo con numeracion secuencial (B6)
        goles_negro_hist = [x for x in self.historial if x[2] == "NEGRO"]
        goles_rojo_hist  = [x for x in self.historial if x[2] == "ROJO"]
        goles_negro = [(i, m, s, hl) for i, (m, s, lbl, h, hl, c) in enumerate(goles_negro_hist, 1)]
        goles_rojo  = [(i, m, s, hl) for i, (m, s, lbl, h, hl, c) in enumerate(goles_rojo_hist, 1)]

        # Goles NEGRO
        if goles_negro:
            for num, minuto, segundo, half_label in goles_negro:
                row = tk.Frame(self.inner_negro, bg=COLOR_NEGRO)
                row.pack(fill="x", padx=4, pady=2)
                tk.Label(row, text=f"#{num}", font=self.fnt_hist,
                         fg=COLOR_SILVER, bg=COLOR_NEGRO, width=2).pack(side="left")
                tk.Label(row, text=f"{minuto}:{segundo:02d}", font=self.fnt_hist,
                         fg="white", bg=COLOR_NEGRO, width=4).pack(side="left")
                tk.Label(row, text=f"·{half_label}", font=("Consolas", 10),
                         fg="#666", bg=COLOR_NEGRO, width=8).pack(side="left")
        else:
            tk.Label(self.inner_negro, text="—", font=("Segoe UI", 20),
                     fg="#333", bg=COLOR_NEGRO).pack(expand=True)

        # Goles ROJO
        if goles_rojo:
            for num, minuto, segundo, half_label in goles_rojo:
                row = tk.Frame(self.inner_rojo, bg=COLOR_ROJO_OSCURO)
                row.pack(fill="x", padx=4, pady=2)
                tk.Label(row, text=f"#{num}", font=self.fnt_hist,
                         fg=COLOR_ROJO, bg=COLOR_ROJO_OSCURO, width=2).pack(side="left")
                tk.Label(row, text=f"{minuto}:{segundo:02d}", font=self.fnt_hist,
                         fg=COLOR_ROJO, bg=COLOR_ROJO_OSCURO, width=4).pack(side="left")
                tk.Label(row, text=f"·{half_label}", font=("Consolas", 10),
                         fg="#666", bg=COLOR_ROJO_OSCURO, width=8).pack(side="left")
        else:
            tk.Label(self.inner_rojo, text="—", font=("Segoe UI", 20),
                     fg="#555", bg=COLOR_ROJO_OSCURO).pack(expand=True)

        # Forzar scrollregion en ambos canvases
        self.canvas_negro.config(scrollregion=self.canvas_negro.bbox("all"))
        self.canvas_rojo.config(scrollregion=self.canvas_rojo.bbox("all"))

    def ejecutar(self):
        self.ventana.mainloop()


# ============================================================
# ENTRY POINT
# ============================================================
if __name__ == "__main__":
    config = VentanaConfig()
    config.ejecutar()
