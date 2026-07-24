/*
 * RAX CARFUTBOLÍN — Portería A
 * Arduino Nano V3 + TSOP38438 + LED IR 940nm
 * v2.1 - Anti-falso gol al iniciar + cooldown 10s
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

void configurar38kHz() {
  pinMode(EMISOR_IR, OUTPUT);
  TCCR2A = _BV(COM2B1) | _BV(WGM20) | _BV(WGM21);
  TCCR2B = _BV(WGM22) | _BV(CS21);
  OCR2A = 51;
  OCR2B = 26;
}

void setup() {
  Serial.begin(9600);
  pinMode(SENSOR_IR, INPUT);
  configurar38kHz();
  delay(400);
  hazAnterior = (digitalRead(SENSOR_IR) == LOW);
  arranque = millis();
  Serial.println("READY:A");
}

void loop() {
  bool haz = (digitalRead(SENSOR_IR) == LOW);
  unsigned long ahora = millis();

  // NO detectar goles durante los primeros 3 segundos (estabilizacion)
  if (ahora - arranque < ESTABILIZACION) {
    hazAnterior = haz;
    delay(5);
    return;
  }

  // El balon corto el haz
  if (hazAnterior && !haz && (ahora > cooldownHasta)) {
    cooldownHasta = ahora + COOLDOWN_GOL;
    esperandoRearme = true;
    inicioHazEstable = 0;
    Serial.println("GOAL:A");
  }

  // Esperar haz estable para rearmar
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

  hazAnterior = haz;
  delay(5);
}
