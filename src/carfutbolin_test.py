"""
RAX Carfutbolín — Test de lectura serial
Auto-detecta los Arduinos conectados y muestra mensajes en vivo
Uso: python carfutbolin_test.py
"""

import serial
import serial.tools.list_ports
import time

BAUD = 9600

# Auto-detectar puertos USB
puertos = [p.device for p in serial.tools.list_ports.comports()
           if "USB" in p.description or "CH340" in p.description or "serie" in p.description]

if not puertos:
    print("❌ No se encontraron Arduinos conectados por USB")
    print("   Conectá los Arduinos y volvé a intentar")
    exit(1)

print(f"🔍 Puertos detectados: {', '.join(puertos)}")
print("-" * 40)

for port in puertos:
    try:
        ser = serial.Serial(port, BAUD, timeout=2)
        time.sleep(0.5)
        ser.reset_input_buffer()
        print(f"✅ {port} conectado — esperando datos (presioná Ctrl+C para salir)...")
        print()

        while True:
            if ser.in_waiting:
                linea = ser.readline().decode('utf-8', errors='ignore').strip()
                if linea:
                    print(f"📩 {port}: {linea}")
                    if "GOAL" in linea:
                        print(f"⚽⚽⚽ ¡GOL en {port}! ⚽⚽⚽")
            time.sleep(0.01)

    except serial.SerialException as e:
        print(f"❌ Error en {port}: {e}")
    except KeyboardInterrupt:
        print(f"\n👋 {port} cerrado")
    finally:
        if 'ser' in locals() and ser.is_open:
            ser.close()
