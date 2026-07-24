"""
RAX Carfutbolin — Monitor de diagnóstico TSOP
Conecta al Arduino, lee los cambios de pin 7 y los muestra en tiempo real.
"""
import serial
import serial.tools.list_ports
import time
import sys

def main():
    # Detectar Arduino (CH340)
    puertos = list(serial.tools.list_ports.comports())
    ch340 = [p.device for p in puertos if p.device.upper() not in ("COM1",)]
    
    if not ch340:
        print("❌ No se detectaron puertos COM.")
        print("   Conectá el Arduino por USB.")
        input("   Presioná Enter para salir...")
        return
    
    print(f"Puertos detectados: {', '.join(ch340)}")
    
    if len(ch340) == 1:
        puerto = ch340[0]
    else:
        print("Elegí el puerto del Arduino con el sketch de diagnóstico:")
        for i, p in enumerate(ch340):
            print(f"  {i+1}. {p}")
        try:
            idx = int(input("Número: ")) - 1
            puerto = ch340[idx]
        except:
            print("Puerto inválido, usando el primero")
            puerto = ch340[0]
    
    print(f"\n🔌 Conectando a {puerto} a 115200 baud...")
    
    try:
        ser = serial.Serial(puerto, 115200, timeout=2)
    except Exception as e:
        print(f"❌ Error al abrir {puerto}: {e}")
        input("Presioná Enter para salir...")
        return
    
    # Esperar a que el Arduino se reinicie (DTR reset)
    time.sleep(3)
    ser.reset_input_buffer()
    
    print("✅ Conectado! (Presioná Ctrl+C para salir)\n")
    print("👉 MOVÉ LA PELOTA RÁPIDO POR EL HAZ y observá los cambios\n")
    
    try:
        inicio = time.time()
        cambios = 0
        while True:
            if ser.in_waiting:
                linea = ser.readline().decode(errors='replace').strip()
                if not linea:
                    continue
                    
                ts = time.time() - inicio
                
                if "ROTO" in linea:
                    cambios += 1
                    print(f"\n🔴 [{ts:6.2f}s] CAMBIO #{cambios} → HAZ ROTO (pelota pasando)")
                elif "OK" in linea:
                    print(f"  🟢 [{ts:6.2f}s]          → HAZ RESTAURADO")
                elif "DIAGNOSTICO" in linea or "Monitoreando" in linea or "Esperando" in linea:
                    print(f"  ℹ️  {linea}")
                elif "Estado inicial" in linea:
                    print(f"  📊 {linea}")
                elif "Formato" in linea:
                    print(f"  📝 {linea}")
                else:
                    print(f"  {linea}")
            else:
                # Sin datos - mostrar heartbeat cada 5s
                time.sleep(0.01)
                
    except KeyboardInterrupt:
        print("\n\nDiagnóstico finalizado.")
        print(f"Total de cambios detectados: {cambios}")
    finally:
        ser.close()
        input("Presioná Enter para salir...")

if __name__ == "__main__":
    main()
