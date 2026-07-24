/*
 * RAX CARFUTBOLÍN — Portería B
 * Arduino Nano V3 + TSOP38438 + LED IR 940nm
 * Protocolo serial: READY:B → GOAL:B a 9600 baud
 *
 * Configuración Arduino IDE:
 *   Placa: Arduino Nano
 *   Processor: ATmega328P (Old Bootloader)
 *   Port: COM4
 */

const byte EMISOR_IR = 3;   // D3 → 1kΩ → Base 2N2222 → LED IR
const byte SENSOR_IR = 7;   // D7 ← OUT TSOP38438

bool hazAnterior = true;
bool listo = true;
unsigned long ultimoGol = 0;
const unsigned long BLOQUEO_GOL = 700;  // ms sin repetir el mismo gol

void configurar38kHz() {
  pinMode(EMISOR_IR, OUTPUT);
  TCCR2A = _BV(COM2B1) | _BV(WGM20) | _BV(WGM21);
  TCCR2B = _BV(WGM22) | _BV(CS21);
  OCR2A = 209;
  OCR2B = 105;
}

void setup() {
  Serial.begin(9600);
  pinMode(SENSOR_IR, INPUT);
  configurar38kHz();
  delay(400);
  hazAnterior = (digitalRead(SENSOR_IR) == LOW);
  Serial.println("READY:B");
}

void loop() {
  bool haz = (digitalRead(SENSOR_IR) == LOW);
  unsigned long ahora = millis();

  if (hazAnterior && !haz && listo && (ahora - ultimoGol > BLOQUEO_GOL)) {
    ultimoGol = ahora;
    listo = false;
    Serial.println("GOAL:B");
  }

  if (haz) {
    listo = true;
  }

  hazAnterior = haz;
  delay(5);
}
