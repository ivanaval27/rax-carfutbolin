/*
 * RAX CARFUTBOLÍN — Portería A
 * Arduino Nano V3 + TSOP38438 + LED IR 940nm
 * v2.0 - Cooldown antirebote: 3 segundos por gol
 *
 * Protocolo: READY:A → GOAL:A a 9600 baud
 * Placa: Arduino Nano | Processor: ATmega328P (Old Bootloader)
 */

const byte EMISOR_IR = 3;
const byte SENSOR_IR = 7;

bool hazAnterior = true;
unsigned long ultimoGol = 0;
unsigned long cooldownHasta = 0;

const unsigned long COOLDOWN_GOL = 10000;  // 10 segundos (sacar balon y ponerlo en centro)
const unsigned long TIEMPO_REARME = 500;   // 500ms de haz continuo para rearmar
unsigned long inicioHazEstable = 0;
bool esperandoRearme = false;

void configurar38kHz() {
  pinMode(EMISOR_IR, OUTPUT);
  TCCR2A = _BV(COM2B1) | _BV(WGM20) | _BV(WGM21);
  TCCR2B = _BV(WGM22) | _BV(CS21);
  OCR2A = 51;   // 16MHz / (8 * 52) = 38.46 kHz
  OCR2B = 26;   // ~50% duty cycle
}

void setup() {
  Serial.begin(9600);
  pinMode(SENSOR_IR, INPUT);
  configurar38kHz();
  delay(400);
  hazAnterior = (digitalRead(SENSOR_IR) == LOW);
  Serial.println("READY:A");
}

void loop() {
  bool haz = (digitalRead(SENSOR_IR) == LOW);
  unsigned long ahora = millis();

  // El balon corto el haz
  if (hazAnterior && !haz && (ahora > cooldownHasta)) {
    // GOL!
    ultimoGol = ahora;
    cooldownHasta = ahora + COOLDOWN_GOL;
    esperandoRearme = true;
    inicioHazEstable = 0;

    Serial.println("GOAL:A");
  }

  // Despues de un gol, esperar haz estable para rearmar
  if (esperandoRearme) {
    if (haz) {
      // El haz esta presente - contar tiempo estable
      if (inicioHazEstable == 0) {
        inicioHazEstable = ahora;
      } else if (ahora - inicioHazEstable >= TIEMPO_REARME) {
        // Haz estable por 500ms - listo para otro gol
        esperandoRearme = false;
        inicioHazEstable = 0;
      }
    } else {
      // El haz se corto de nuevo - reiniciar contador
      inicioHazEstable = 0;
    }
  }

  hazAnterior = haz;
  delay(5);
}
