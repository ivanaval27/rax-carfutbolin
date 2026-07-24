"""
RAX Carfutbolín — Test de lectura serial
Lee puerto COM3 (Portería A) y muestra los mensajes en vivo
Uso: python carfutbolin_test.py
"""

import serial
import time

PORT = "COM3"  # Cambiar si es otro COM
BAUD = 9600

try:
    ser = serial.Serial(PORT, BAUD, timeout=3)
    time.sleep(2)  # Esperar reset del Nano

    print(f"✅ Conectado a {PORT} a {BAUD} baud")
    print("Esperando datos... (Ctrl+C para salir)")
    print("-" * 40)

    while True:
        if ser.in_waiting:
            linea = ser.readline().decode().strip()
            print(f"📩 {linea}")

            if "GOAL" in linea:
                print("⚽⚽⚽ ¡GOLAZO! ⚽⚽⚽")

        time.sleep(0.01)

except serial.SerialException as e:
    print(f"❌ Error conectando a {PORT}: {e}")
    print("\nVerificar:")
    print("  1. El Nano está conectado por USB")
    print(f"  2. El puerto correcto es {PORT}")
    print("  3. Driver CH340 instalado (si es clon chino)")
except KeyboardInterrupt:
    print("\n👋 Prueba terminada")
finally:
    if 'ser' in locals() and ser.is_open:
        ser.close()
        print("Puerto cerrado")
