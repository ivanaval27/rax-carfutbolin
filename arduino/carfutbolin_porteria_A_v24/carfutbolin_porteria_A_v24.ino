/*
 * RAX CARFUTBOLÍN — Portería A v2.4.2
 * Arduino Nano V3 + TSOP38438 + LED IR 940nm
 * 
 * v2.4.2 - Carrier continuo (como v23) + detección debounced con
 *           timestamps para filtrar falsos positivos por ruido.
 *           Se elimina el pulso de carrier que causaba falsos disparos.
 * 
 * Placa: Arduino Nano | Processor: ATmega328P (Old Bootloader)
 */

const byte EMISOR_IR = 3;   // D3 → 1kΩ → Base 2N2222 → LED IR 940nm
const byte SENSOR_IR = 7;   // D7 ← OUT TSOP38438

const unsigned long COOLDOWN_GOL = 10000;
const unsigned long TIEMPO_REARME = 500;
const unsigned long ESTABILIZACION = 3000;

// Timestamps de bordes del TSOP (ISR-safe)
volatile unsigned long ultimoRising = 0;
volatile unsigned long ultimoFalling = 0;
const unsigned long DEBOUNCE_US = 1000;  // 1ms antirrebote

unsigned long arranque = 0;
unsigned long cooldownHasta = 0;
unsigned long inicioHazEstable = 0;
bool esperandoRearme = false;

// ============================================================
// ISR: Pin Change Interrupt en pin 7 (PD7 = PCINT23)
// ============================================================
ISR(PCINT2_vect) {
  if (PIND & (1 << PD7)) {
    // Rising: TSOP HIGH = haz roto
    ultimoRising = micros();
  } else {
    // Falling: TSOP LOW = haz OK
    ultimoFalling = micros();
  }
}

void configurar38kHz() {
  pinMode(EMISOR_IR, OUTPUT);
  TCCR2A = _BV(COM2B1) | _BV(WGM20) | _BV(WGM21);
  TCCR2B = _BV(WGM22) | _BV(CS21);
  OCR2A = 51;   // 38.46 kHz
  OCR2B = 26;   // ~50% duty
}

void configurarInterrupcion() {
  PCICR  |= (1 << PCIE2);
  PCMSK2 |= (1 << PCINT23);
}

void setup() {
  Serial.begin(115200);
  pinMode(SENSOR_IR, INPUT);
  configurar38kHz();        // Carrier continuo (SIN pulsos)
  configurarInterrupcion();
  delay(400);

  if (digitalRead(SENSOR_IR) == HIGH) {
    ultimoRising = micros();
  } else {
    ultimoFalling = micros();
  }

  arranque = millis();
  Serial.println("READY:A");
}

// ============================================================
// beamRoto(): true si el TSOP salió HIGH por > DEBOUNCE_US
// ============================================================
bool beamRoto() {
  noInterrupts();
  unsigned long r = ultimoRising;
  unsigned long f = ultimoFalling;
  interrupts();

  if (r > f) {
    return (micros() - r >= DEBOUNCE_US);
  }
  return false;
}

// ============================================================
// LOOP PRINCIPAL
// ============================================================
void loop() {
  unsigned long ahoraMs = millis();

  // Estabilización inicial
  if (ahoraMs - arranque < ESTABILIZACION) {
    return;
  }

  // Detección de gol
  if (beamRoto() && (ahoraMs > cooldownHasta)) {
    cooldownHasta = ahoraMs + COOLDOWN_GOL;
    esperandoRearme = true;
    inicioHazEstable = 0;
    Serial.println("GOAL:A");
    return;
  }

  // Rearme
  if (esperandoRearme) {
    if (!beamRoto()) {
      if (inicioHazEstable == 0) {
        inicioHazEstable = ahoraMs;
      } else if (ahoraMs - inicioHazEstable >= TIEMPO_REARME) {
        esperandoRearme = false;
        inicioHazEstable = 0;
      }
    } else {
      inicioHazEstable = 0;
    }
  }
}
