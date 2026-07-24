# 🏎️ RAX CARFUTBOLÍN — MANUAL DEL SISTEMA
> **Versión:** v2.0+ | **Fecha:** 23/07/2026
> **Departamento:** Carfutbolín RAX
> **Revisor:** Alan

---

## 📋 1. ARQUITECTURA DEL SISTEMA

```
┌─────────────────────────────────────────────────┐
│                 RAX SOCIAL (Windows)             │
│              10.0.10.197 · SSH :5022             │
│                                                   │
│   ┌─────────────────────────────────────────┐   │
│   │        RAX Carfutbolin.exe              │   │
│   │   (PyInstaller · Tkinter · pyserial)    │   │
│   └──────────┬──────────────────────────────┘   │
│              │ USB                              │
│        ┌─────┴─────┐  ┌─────┴─────┐            │
│        │ Arduino A  │  │ Arduino B  │            │
│        │ (NEGRO)    │  │ (ROJO)     │            │
│        │ COM6       │  │ COM5       │            │
│        │ TSOP38438  │  │ TSOP38438  │            │
│        │ LED IR     │  │ LED IR     │            │
│        │ 38kHz      │  │ 38kHz      │            │
│        └────────────┘  └────────────┘            │
└─────────────────────────────────────────────────┘
```

---

## 🎮 2. COMPONENTES

### 2.1 Aplicación Principal (`carfutbolin_partido.py`)
- **Lenguaje:** Python 3.11
- **GUI:** Tkinter (fullscreen)
- **Puertos serial:** pyserial
- **Compilación:** PyInstaller → `RAX Carfutbolin.exe`

### 2.2 Firmware Arduino (`carfutbolin_v21.ino`)
- **Placa:** Arduino Nano (ATmega328P)
- **Driver:** CH340 (Old Bootloader)
- **Frecuencia LED IR:** 38kHz (Timer2, OCR2A=51)
- **Protocolo:** Serial 9600 baud
- **Mensajes:** `READY:A` / `READY:B` / `GOAL:A` / `GOAL:B`

### 2.3 Electrónica por Portería
| Componente | Pin | Señal |
|-----------|-----|-------|
| LED IR 940nm | D3 (OC2B) | 38kHz PWM |
| Transistor 2N2222 | D3 → Base | Driver LED |
| TSOP38438 | D7 (INPUT) | Señal IR recibida |
| Resistencia LED | 100Ω | Ánodo → 5V |
| Resistencia base | 1kΩ | D3 → Base 2N2222 |

---

## ⚙️ 3. CONFIGURACIÓN ACTUAL

| Parámetro | Valor por defecto | Rango |
|-----------|-------------------|-------|
| ⏱ Tiempo por tiempo | 4 min | 1-30 min |
| ☕ Tiempo descanso | 4 min | 1-15 min |
| 🔄 Total partido | 8 min (2×4) | - |
| 🔌 Baud rate | 9600 | fijo |
| 📡 Frecuencia IR | 38.46 kHz | fijo |
| ⏱ Cooldown gol | 10 seg | fijo |
| 🛡 Estabilización | 3 seg | fijo |

---

## 🎨 4. BRAND BOOK RAX APLICADO

| Elemento | Código | Color |
|----------|--------|-------|
| Fondo principal | `#050505` | Negro profundo |
| Fondo secundario | `#0a0a0a` | Negro claro |
| Panel glass | `#0d0d0d` | Negro vidrio |
| 🔴 Rojo RAX | `#da0000` | Rojo principal |
| 🟡 Oro RAX | `#DB9651` | Dorado acento |
| ⚪ Plata | `#a0a0a0` | Secundario |
| Borde panel | `#da0000` · 2px | Borde glass |

---

## 📂 5. ESTRUCTURA DE ARCHIVOS

```
RAX Carfutbolin.exe          → App compilada
carfutbolin_partido.py       → Código fuente
carfutbolin_v21.ino          → Firmware Arduino (Portería A)
carfutbolin_porteria_B_v21.ino → Firmware Arduino (Portería B)
sounds/
  ├── inicio.wav             → Sonido inicio partido
  ├── gol.wav                → Sonido gol genérico
  ├── gol_negro.wav          → Sonido gol NEGRO
  ├── gol_rojo.wav           → Sonido gol ROJO
  └── final.wav              → Sonido final partido
```

---

## 🔄 6. FLUJO DEL PARTIDO

```
INICIAR ──→ ⏱ 1er Tiempo (4:00) ──→ 0:00
                                        │
                                   [Automático]
                                        │
                                        ↓
                                   ☕ DESCANSO (x min)
                                        │
                                   [Automático]
                                        │
                                        ↓
                                   ⏱ 2do Tiempo (4:00) ──→ 0:00
                                                              │
                                                         [Automático]
                                                              │
                                                              ↓
                                                         🏁 FINALIZADO
                                                         🏆 GANADOR
```

---

## ✅ 7. CHECKLIST DE REVISIÓN (Para Alan)

### Código Fuente
- [ ] Revisar `carfutbolin_partido.py` completo
- [ ] Verificar lógica de detección de goles
- [ ] Verificar flujo automático (1T → Descanso → 2T)
- [ ] Verificar cooldown de goles (10s)
- [ ] Verificar cambio de lados en 2do tiempo
- [ ] Verificar manejo de errores (puertos, sonidos)
- [ ] Verificar estilo RAX Brand Book

### Firmware Arduino
- [ ] Revisar `carfutbolin_v21.ino`
- [ ] Verificar frecuencia 38kHz (OCR2A=51)
- [ ] Verificar cooldown 10s
- [ ] Verificar estabilización 3s al inicio
- [ ] Verificar anti-falso gol
- [ ] Probar en ambos Arduinos (A y B)

### Electrónica
- [ ] Verificar cableado LED IR + TSOP38438
- [ ] Verificar resistencia 100Ω y 1kΩ
- [ ] Verificar transistor 2N2222
- [ ] Probar distancia de detección

### App Windows
- [ ] Probar detección de COM ports
- [ ] Probar inicio de partido
- [ ] Probar goles en ambas porterías
- [ ] Probar descanso automático
- [ ] Probar sonidos (si hay archivos)
- [ ] Probar celebración visual
- [ ] Probar reset y salir

---

## 🚀 8. INSTRUCCIONES DE COMPILACIÓN

```powershell
# En RAX SOCIAL:
pyinstaller --clean --onefile --windowed `
  --icon C:\rax_logo.ico `
  --name "RAX Carfutbolin" `
  --distpath C:\dist `
  C:\carfutbolin.py
```

---

## 📌 9. NOTAS TÉCNICAS

- **Puertos COM dinámicos:** Cambian según el puerto USB. La app detecta automáticamente.
- **Sonidos opcionales:** Si la carpeta `sounds/` no existe, la app funciona igual.
- **Fullscreen:** Escape para salir, F11 para volver.
- **Arduino Old Bootloader:** Es crítico seleccionar "ATmega328P (Old Bootloader)" en Arduino IDE.
- **El LED IR calienta:** Usar resistencia limitadora de corriente.

---

*Documento generado por Hermes Agent · RAX Experience*
