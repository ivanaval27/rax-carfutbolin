/*
 * RAX CARFUTBOLÍN — Portería B v2.5
 * Arduino Nano V3 + TSOP38438 + LED IR 940nm
 * v2.5 - Detección por flanco (edge detection), loop a máxima velocidad
 *        Sin ISR, sin delays, sin debounce complejo.
 *        Confiable y rápido — como v2.0 pero sin delay(5).
 */

const byte EMISOR_IR = 3;
const byte SENSOR_IR = 7;

bool hazAnterior;
unsigned long cooldownHasta = 0;
unsigned long arranque = 0;

const unsigned long COOLDOWN_GOL   = 10000;
const unsigned long TIEMPO_REARME  = 500;
const unsigned long ESTABILIZACION = 3000;

unsigned long inicioHazEstable = 0;
bool esperandoRearme = false;

void configurar38kHz() {
  pinMode(EMISOR_IR, OUTPUT);
  TCCR2A = _BV(COM2B1) | _BV(WGM20) | _BV(WGM21);
  TCCR2B = _BV(WGM22) | _BV(CS21);
  OCR2A = 51;
  OCR2B = 26;
}

void setup() {
  Serial.begin(115200);
  pinMode(SENSOR_IR, INPUT);
  configurar38kHz();
  delay(400);
  hazAnterior = (digitalRead(SENSOR_IR) == LOW);
  arranque = millis();
  Serial.println("READY:B");
}

void loop() {
  unsigned long ahora = millis();

  if (ahora - arranque < ESTABILIZACION) {
    hazAnterior = (digitalRead(SENSOR_IR) == LOW);
    return;
  }

  bool haz = (digitalRead(SENSOR_IR) == LOW);  // LOW = haz OK, HIGH = roto

  // --- Detección de gol por flanco: haz pasó de OK → ROTO ---
  if (hazAnterior && !haz && (ahora > cooldownHasta)) {
    cooldownHasta = ahora + COOLDOWN_GOL;
    esperandoRearme = true;
    inicioHazEstable = 0;
    Serial.println("GOAL:B");
  }

  hazAnterior = haz;

  // --- Rearme: esperar 500ms de haz continuo ---
  if (esperandoRearme) {
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
}
