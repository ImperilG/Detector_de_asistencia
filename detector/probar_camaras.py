"""
Muestra cada camara que ve la computadora, con su numero, para saber cual poner en CAMARA.

    python probar_camaras.py

  - ESPACIO = pasar a la siguiente camara
  - q = salir
"""
import cv2

MAXIMO = 6  # cuantos indices probar (0 a 5)


def main():
    encontradas = []
    for i in range(MAXIMO):
        cam = cv2.VideoCapture(i)
        if not cam.isOpened():
            cam.release()
            continue
        ok, frame = cam.read()
        if not ok:
            cam.release()
            continue
        alto, ancho = frame.shape[:2]
        encontradas.append(i)
        print(f"Camara {i}: {ancho}x{alto}")

        salir = False
        while True:
            ok, frame = cam.read()
            if not ok:
                break
            cv2.putText(frame, f"CAMARA {i}  ({ancho}x{alto})   ESPACIO = siguiente   q = salir",
                        (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)
            cv2.imshow("Probar camaras", frame)
            tecla = cv2.waitKey(1) & 0xFF
            if tecla == ord(" "):
                break
            if tecla == ord("q"):
                salir = True
                break
        cam.release()
        if salir:
            break

    cv2.destroyAllWindows()
    if encontradas:
        print("Camaras encontradas:", encontradas)
        print("Pon el numero de tu webcam en CAMARA, en enrolar.py y en asistencia.py.")
    else:
        print("No se encontro ninguna camara. Revisa el cable y el permiso de camara para Terminal.")


if __name__ == "__main__":
    main()
