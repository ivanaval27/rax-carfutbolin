/*
 * RAX CARFUTBOLÍN — Diagnóstico TSOP38438
 * 
 * Monitorea pin 7 y reporta CADA cambio de estado por serial.
 * INCLUYE la portadora 38kHz para que el haz IR funcione igual que en el firmware real.
 * 
 * Placa: Arduino Nano
 * Processor: ATmega328P (Old Bootloader)
 */

const byte EMISOR_IR = 3;   // D3 → 1kΩ → Base 2N2222 → LED IR 940nm
const byte SENSOR_IR = 7;   // D7 ← OUT TSOP38438

volatile bool huboCambio = false;
volatile bool valorActual = LOW;

unsigned long arranque = 0;
const unsigned long ESTABILIZACION = 3000; // 3 segundos igual que firmware real

// Pin Change Interrupt para pin 7 (PD7 = PCINT23)
ISR(PCINT2_vect) {
  huboCambio = true;
  valorActual = (PIND & (1 << PD7));
}

void configurar38kHz() {
  pinMode(EMISOR_IR, OUTPUT);
  TCCR2A = _BV(COM2B1) | _BV(WGM20) | _BV(WGM21);
  TCCR2B = _BV(WGM22) | _BV(CS21);
  OCR2A = 51;   // 16MHz / (8 * 52) = 38.46 kHz
  OCR2B = 26;   // ~50% duty cycle
}

void setup() {
  Serial.begin(115200);
  pinMode(SENSOR_IR, INPUT);
  
  // Iniciar LED IR (portadora 38kHz)
  configurar38kHz();
  
  // Configurar PCINT para pin 7
  PCICR  |= (1 << PCIE2);    // Habilitar grupo PCINT[23:16]
  PCMSK2 |= (1 << PCINT23);  // Habilitar PCINT23 (pin 7 / PD7)

  delay(400);
  arranque = millis();
  
  Serial.println("=== DIAGNOSTICO TSOP38438 ===");
  Serial.println("HAZ IR ACTIVO (38kHz)");
  Serial.println("Monitoreando pin 7...");
  Serial.print("Estado inicial: P7=");
  Serial.println(digitalRead(SENSOR_IR) ? "HIGH (HAZ ROTO)" : "LOW (HAZ OK)");
  Serial.println("Formato: P7_CAMBIO:<timestamp_ms>:<ESTADO>");
  Serial.println("MOVÉ LA PELOTA POR EL HAZ RÁPIDO Y LENTO");
}

void loop() {
  unsigned long ahora = millis();
  
  // Periodo de estabilización (igual que firmware real)
  if (ahora - arranque < ESTABILIZACION) {
    huboCambio = false;
    return;
  }
  
  if (huboCambio) {
    huboCambio = false;
    
    Serial.print("P7_CAMBIO:");
    Serial.print(ahora);
    Serial.print(":");
    Serial.println(valorActual ? "ROTO" : "OK");
  }
}
