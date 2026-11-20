
## Captura

![Captura de la página en el celular](captura-pagina-web.png)

## Código

```cpp

#include <WiFi.h>
#include <WebServer.h>

WebServer server(80);


const int SENSOR = D0;                
const int SALIDA = LED_BUILTIN;     
const char* RED   = "detector_de_asistencia";   
const char* CLAVE = "08092008";      


const int ENCENDIDO = LOW;
const int APAGADO   = HIGH;

void handleRoot() {
  int v = analogRead(SENSOR);         
  Serial.print("Sensor: ");
  Serial.println(v);

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
  delay(1500);                        

  pinMode(SALIDA, OUTPUT);
  digitalWrite(SALIDA, APAGADO);

  WiFi.softAP(RED, CLAVE);
  Serial.print("Red: ");
  Serial.println(RED);
  Serial.print("Abre en el celular: ");
  Serial.println(WiFi.softAPIP());     

  server.on("/", handleRoot);

  server.on("/on", []() {
    digitalWrite(SALIDA, ENCENDIDO);
    Serial.println("Salida: ENCENDIDA");
    server.sendHeader("Location", "/");
    server.send(303);
  });

  server.on("/off", []() {
    digitalWrite(SALIDA, APAGADO);
    Serial.println("Salida: APAGADA");
    server.sendHeader("Location", "/");
    server.send(303);
  });

  server.begin();
  Serial.println("Servidor listo");
}

void loop() {
  server.handleClient();
}
```

