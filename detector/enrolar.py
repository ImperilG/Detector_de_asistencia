"""
Controles:  ESPACIO = tomar muestra   |   q = terminar y guardar

"""
import pickle
import sys
from pathlib import Path

import cv2
import face_recognition

ARCHIVO = Path("rostros.pkl")
CAMARA = 1  
MUESTRAS_OBJETIVO = 8  


def cargar():
    if ARCHIVO.exists():
        with open(ARCHIVO, "rb") as f:
            return pickle.load(f)
    return {}


def main():
    if len(sys.argv) < 2:
        print('Uso: python enrolar.py "Nombre"')
        return
    nombre = sys.argv[1]

    ok = input(f"¿{nombre} dio su consentimiento para guardar su rostro? (s/n): ")
    if ok.strip().lower() != "s":
        print("Sin consentimiento no se registra. Saliendo.")
        return

    base = cargar()
    muestras = base.get(nombre, [])

    cam = cv2.VideoCapture(CAMARA)
    if not cam.isOpened():
        print("No se pudo abrir la camara.")
        return

    print("ESPACIO = tomar muestra, q = terminar")
    while True:
        ok, frame = cam.read()
        if not ok:
            break
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        ubicaciones = face_recognition.face_locations(rgb, model="hog")

        for (arriba, derecha, abajo, izquierda) in ubicaciones:
            cv2.rectangle(frame, (izquierda, arriba), (derecha, abajo), (0, 255, 0), 2)
        cv2.putText(frame, f"{nombre}: {len(muestras)}/{MUESTRAS_OBJETIVO}  (ESPACIO / q)",
                    (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
        cv2.imshow("Enrolar rostro", frame)

        tecla = cv2.waitKey(1) & 0xFF
        if tecla == ord("q"):
            break
        if tecla == ord(" "):
            if len(ubicaciones) != 1:
                print("Debe verse exactamente UN rostro. Intenta de nuevo.")
                continue
            vector = face_recognition.face_encodings(rgb, ubicaciones)[0]
            muestras.append(vector)
            print(f"Muestra {len(muestras)} guardada.")

    cam.release()
    cv2.destroyAllWindows()

    if muestras:
        base[nombre] = muestras
        with open(ARCHIVO, "wb") as f:
            pickle.dump(base, f)
        print(f"{nombre}: {len(muestras)} muestras guardadas en {ARCHIVO}.")
        print(f"Alumnos registrados: {', '.join(base.keys())}")
    else:
        print("No se tomaron muestras.")


if __name__ == "__main__":
    main()
