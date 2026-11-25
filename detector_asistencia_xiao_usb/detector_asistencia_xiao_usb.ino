
#include <ESP32Servo.h>

const int PIN_SERVO = D0;      
const int PIN_LED = D10;       
const int ANGULO_REPOSO = 90;  
const int ANGULO_A = 58;       
const int ANGULO_B = 122;      
const int VECES = 3;           
const int PARPADEOS = 6;      

Servo mano;
String linea = "";

void saludar() {
  for (int i = 0; i < VECES; i++) {
    mano.write(ANGULO_A);
    delay(250);
    mano.write(ANGULO_B);
    delay(250);
  }
  mano.write(ANGULO_REPOSO);
}

void alertaRoja() {
  for (int i = 0; i < PARPADEOS; i++) {
    digitalWrite(PIN_LED, HIGH);
    delay(150);
    digitalWrite(PIN_LED, LOW);
    delay(150);
  }
}

void setup() {
  Serial.begin(115200);
  pinMode(PIN_LED, OUTPUT);
  digitalWrite(PIN_LED, LOW);
  mano.setPeriodHertz(50);
  mano.attach(PIN_SERVO, 500, 2400);
  mano.write(ANGULO_REPOSO);
  Serial.println("Hola, somos detector de asistencia (USB)");
}

void loop() {
  while (Serial.available()) {
    char c = Serial.read();
    if (c == '\n') {
      linea.trim();
      if (linea == "#desconocido") {
        Serial.println("Rostro no registrado: LED rojo");
        alertaRoja();
      } else if (linea.length() > 0) {
        Serial.printf("Saludo para: %s\n", linea.c_str());
        saludar();
      }
      linea = "";
    } else if (c != '\r' && linea.length() < 60) {
      linea += c;
    }
  }
}
