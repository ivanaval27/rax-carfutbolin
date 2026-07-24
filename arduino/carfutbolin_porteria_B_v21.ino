/*
 * RAX CARFUTBOLÍN — Portería B
 * Arduino Nano V3 + TSOP38438 + LED IR 940nm
 * v2.2 - Optimizado para pelotas rápidas: Pin Change Interrupt + loop sin delays
 */

const byte EMISOR_IR = 3;
const byte SENSOR_IR = 7;

bool hazAnterior = true;
unsigned long cooldownHasta = 0;
unsigned long arranque = 0;

const unsigned long COOLDOWN_GOL = 10000;  // 10 segundos entre goles
const unsigned long TIEMPO_REARME = 500;   // 500ms de haz continuo para rearmar
const unsigned long ESTABILIZACION = 3000; // 3 segundos al inicio sin detectar goles

unsigned long inicioHazEstable = 0;
bool esperandoRearme = false;

// --- Interrupción por cambio de pin (PCINT) en pin 7 ---
// Pin 7 = PD7 = PCINT23, grupo PCIE2
volatile bool hazRoto = false;

ISR(PCINT2_vect) {
  // PD7 HIGH = haz roto (TSOP38438 suelta la línea cuando no ve carrier)
  if (PIND & (1 << PD7)) {
    hazRoto = true;
  }
}

void configurar38kHz() {
  pinMode(EMISOR_IR, OUTPUT);
  TCCR2A = _BV(COM2B1) | _BV(WGM20) | _BV(WGM21);
  TCCR2B = _BV(WGM22) | _BV(CS21);
  OCR2A = 51;   // 16MHz / (8 * 52) = 38.46 kHz
  OCR2B = 26;   // ~50% duty cycle
}

void configurarInterrupcion() {
  PCICR  |= (1 << PCIE2);    // Habilitar grupo PCINT[23:16]
  PCMSK2 |= (1 << PCINT23);  // Habilitar PCINT23 (pin 7 / PD7)
}

void setup() {
  Serial.begin(115200);  // Alta velocidad para detección rápida
  pinMode(SENSOR_IR, INPUT);
  configurar38kHz();
  configurarInterrupcion();
  delay(400);
  hazAnterior = (digitalRead(SENSOR_IR) == LOW);
  arranque = millis();
  Serial.println("READY:B");
}

void loop() {
  unsigned long ahora = millis();

  // NO detectar goles durante los primeros 3 segundos
  if (ahora - arranque < ESTABILIZACION) {
    hazRoto = false;       // ignorar eventos durante estabilización
    hazAnterior = (digitalRead(SENSOR_IR) == LOW);
    return;                // sin delay — el loop vuela
  }

  // --- Detección de gol vía interrupción ---
  if (hazRoto && (ahora > cooldownHasta)) {
    hazRoto = false;
    cooldownHasta = ahora + COOLDOWN_GOL;
    esperandoRearme = true;
    inicioHazEstable = 0;
    Serial.println("GOAL:B");
  }

  // --- Esperar haz estable para rearmar ---
  if (esperandoRearme) {
    bool haz = (digitalRead(SENSOR_IR) == LOW);
    if (haz) {
      if (inicioHazEstable == 0) {
        inicioHazEstable = ahora;
      } else if (ahora - inicioHazEstable >= TIEMPO_REARME) {
        esperandoRearme = false;
        inicioHazEstable = 0;
      }
    } else {
      inicioHazEstable = 0;
    }
  }

  // Sin delay — el loop corre a máxima velocidad (microsegundos por iteración)
}
