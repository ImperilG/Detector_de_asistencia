#include <WiFi.h>
#include <WebServer.h>

WebServer server(80);
const int SENSOR = A0;
const int SALIDA = LED_BUILTIN;   
const int ENCENDIDO = LOW;        
const int APAGADO = HIGH;

void handleRoot() {
  int v = analogRead(SENSOR);
  String html = "<html><head>"
    "<meta name='viewport' content='width=device-width'>"
    "<meta http-equiv='refresh' content='2'>"
    "</head><body><h1>Detector de asistencia</h1>"
    "<p>Sensor: " + String(v) + "</p>"
    "<p><a href='/on'>Encender</a> <a href='/off'>Apagar</a></p>"
    "</body></html>";
  server.send(200, "text/html", html);
}

void setup() {
  Serial.begin(115200);
  pinMode(SALIDA, OUTPUT);
  digitalWrite(SALIDA, APAGADO);

  WiFi.softAP("Detector-Asistencia", "12345678");
  Serial.println(WiFi.softAPIP());

  server.on("/", handleRoot);
  server.on("/on", []() {
    digitalWrite(SALIDA, ENCENDIDO);
    server.sendHeader("Location", "/");
    server.send(303);
  });
  server.on("/off", []() {
    digitalWrite(SALIDA, APAGADO);
    server.sendHeader("Location", "/");
    server.send(303);
  });
  server.begin();
}

void loop() {
  server.handleClient();
}