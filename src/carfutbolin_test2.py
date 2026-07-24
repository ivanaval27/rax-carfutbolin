"""
RAX Carfutbolin - Test lectura serial
"""
import serial, time, sys

PORT = "COM3"

try:
    ser = serial.Serial(PORT, 9600, timeout=3)
    time.sleep(2)
    print("Conectado a", PORT)
    print("Esperando datos...")
    print("-" * 40)

    while True:
        if ser.in_waiting:
            linea = ser.readline().decode().strip()
            print("[RECIBIDO]", linea)
            if "GOAL" in linea:
                print("[GOLAZO!]")
        time.sleep(0.01)

except serial.SerialException as e:
    print("ERROR:", e)
    print()
    print("Posibles causas:")
    print("  1. Arduino IDE Monitor Serial abierto? Cerrarlo")
    print("  2. Otro COM? Ejecutar: mode")
except Exception as e:
    print("ERROR:", e)
finally:
    try:
        ser.close()
    except:
        pass
