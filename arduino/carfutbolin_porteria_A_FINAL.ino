/*
 * RAX CARFUTBOLÍN — Portería A
 * Arduino Nano V3 + TSOP38438 + LED IR 940nm
 * Protocolo serial: READY:A → GOAL:A a 9600 baud
 *
 * Configuración Arduino IDE:
 *   Placa: Arduino Nano
 *   Processor: ATmega328P (Old Bootloader)
 *   Port: COM4
 *
 * Frecuencia IR corregida: 38kHz exactos
 * Timer2: 16MHz / prescaler8 / (51+1) = 38.46 kHz
 */

const byte EMISOR_IR = 3;   // D3 → 1kΩ → Base 2N2222 → LED IR
const byte SENSOR_IR = 7;   // D7 ← OUT TSOP38438

bool hazAnterior = true;
bool listo = true;
unsigned long ultimoGol = 0;
const unsigned long BLOQUEO_GOL = 700;  // ms sin repetir el mismo gol

void configurar38kHz() {
  pinMode(EMISOR_IR, OUTPUT);
  // Timer2 genera ~38kHz en pin D3 (OC2B)
  TCCR2A = _BV(COM2B1) | _BV(WGM20) | _BV(WGM21);
  TCCR2B = _BV(WGM22) | _BV(CS21);
  OCR2A = 51;   // 16MHz / (8 * (51+1)) = 38.46 kHz
  OCR2B = 26;   // ~50% duty cycle
}

void setup() {
  Serial.begin(9600);
  pinMode(SENSOR_IR, INPUT);
  configurar38kHz();
  delay(400);

  // TSOP: LOW = está recibiendo el haz IR
  hazAnterior = (digitalRead(SENSOR_IR) == LOW);

  Serial.println("READY:A");
}

void loop() {
  bool haz = (digitalRead(SENSOR_IR) == LOW);
  unsigned long ahora = millis();

  // El balón cortó el haz IR → GOL!
  if (hazAnterior && !haz && listo && (ahora - ultimoGol > BLOQUEO_GOL)) {
    ultimoGol = ahora;
    listo = false;
    Serial.println("GOAL:A");
  }

  // Se rearma cuando el balón sale del haz
  if (haz) {
    listo = true;
  }

  hazAnterior = haz;
  delay(5);
}
