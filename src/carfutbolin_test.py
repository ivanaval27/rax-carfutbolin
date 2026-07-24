"""
RAX Carfutbolín — Test de lectura serial
Auto-detecta los Arduinos y muestra ambos en vivo simultáneamente
Uso: python carfutbolin_test.py
"""

import serial
import serial.tools.list_ports
import time
import threading

BAUD = 115200

puertos = [p.device for p in serial.tools.list_ports.comports()
           if "USB" in p.description or "CH340" in p.description or "serie" in p.description]

if not puertos:
    print("❌ No se encontraron Arduinos conectados por USB")
    exit(1)

print(f"🔍 Puertos detectados: {', '.join(puertos)}")
print("-" * 40)

def leer_puerto(port):
    try:
        ser = serial.Serial(port, BAUD, timeout=2)
        time.sleep(0.8)
        ser.reset_input_buffer()
        print(f"✅ {port} conectado — esperando goles...")
        print()

        while True:
            if ser.in_waiting:
                linea = ser.readline().decode('utf-8', errors='ignore').strip()
                if linea:
                    print(f"📩 {port}: {linea}")
                    if "GOAL" in linea:
                        print(f"⚽⚽⚽ ¡GOL en {port}! ⚽⚽⚽")
            time.sleep(0.002)
    except serial.SerialException as e:
        print(f"❌ Error en {port}: {e}")
    except:
        pass

threads = []
for port in puertos:
    t = threading.Thread(target=leer_puerto, args=(port,), daemon=True)
    t.start()
    threads.append(t)

print("⏳ Presioná Ctrl+C para salir\n")

try:
    while True:
        time.sleep(0.5)
except KeyboardInterrupt:
    print("\n👋 Prueba terminada")
