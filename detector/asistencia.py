"""
Detector de asistencia 

Una clase dura lo que se escriba en la variable de DURACCION_MIN
  - Quien llega dentro de los primeros TOLERANCIA_MIN minutos queda como "Puntual";
    despues de eso, como "Retardo".
  - Si cierras el programa a mitad de la clase tecla q ,o se apaga la laptop, NO se reinicia la clase.
    nada: al abrirlo otra vez retoma la misma clase, con la misma hora de inicio y los mismos presentes.
  - Al cumplirse la duracion de la clase se cierra sola: se anotan los ausentes en el Excel y el programa
    termina. La siguiente vez que lo abras empieza una clase nueva, en una hoja nueva del mismo Excel.

Uso:
    python asistencia.py            normal
Teclas:  q = cerrar el programa pero sigue la clase abierta   f = terminar la clase ahora y calcular ausentes
"""
import json
import pickle
import re
import subprocess
import sys
import threading
import time
from datetime import datetime
from pathlib import Path

import cv2
import face_recognition
import numpy as np
import requests
from openpyxl import Workbook, load_workbook
from openpyxl.styles import Alignment, Font
from openpyxl.worksheet.table import Table, TableStyleInfo

# ------------------ CONFIGURACION ------------------
MODO_XIAO = "usb"                                      
PUERTO_XIAO = ""             
XIAO_IP = "192.168.1.50"     # solo para modo wifi
UMBRAL = 0.60                
CUADROS_CONFIRMACION = 3     
CUADROS_DESCONOCIDO = 6     
ENFRIAMIENTO_ALERTA_S = 2    
DURACION_MIN = 3           
TOLERANCIA_MIN = 1          
NTFY_TOPIC = "NOSEQUEPONER"              
VOZ_MAC = "Paulina"          
CAMARA = 1                   
ESCALA = 0.5                 
# --- zona de registro ---
ZONA_ANCHO = 0.50            
ZONA_ALTO = 1            
TAMANO_MIN_ROSTRO = 0.20     
# ---------------------------------------------------

K = round(1 / ESCALA)         

ARCHIVO_ROSTROS = Path("rostros.pkl")
ARCHIVO_EXCEL = Path("asistencia.xlsx")     
ARCHIVO_SESION = Path("sesion_actual.json")  
ENCABEZADO = ["Nombre", "Hora", "Estado"]  


# ---------------------- base de rostros ----------------------
def cargar_base():
    if not ARCHIVO_ROSTROS.exists():
        sys.exit("No existe rostros.pkl. Primero registra alumnos con enrolar.py")
    with open(ARCHIVO_ROSTROS, "rb") as f:
        base = pickle.load(f)
    nombres, vectores = [], []
    for nombre, muestras in base.items():
        for v in muestras:
            nombres.append(nombre)
            vectores.append(v)
    return base, nombres, np.array(vectores)


# ---------------------- Excel ----------------------
def dar_formato(ws):
    ws.column_dimensions["A"].width = 30
    ws.column_dimensions["B"].width = 12
    ws.column_dimensions["C"].width = 12
    ws["A1"].font = Font(bold=True, size=12)
    ws["A1"].alignment = Alignment(horizontal="left")
    for celda in ws[2]:
        celda.font = Font(bold=True)
    if ws.max_row >= 3:  # una tabla necesita al menos una fila de datos
        ref = f"A2:C{ws.max_row}"
        nombre_tabla = "T_" + re.sub(r"\W", "_", ws.title)
        if nombre_tabla in ws.tables:
            tabla = ws.tables[nombre_tabla]
            tabla.ref = ref
            if tabla.autoFilter is not None:
                tabla.autoFilter.ref = ref
        else:
            tabla = Table(displayName=nombre_tabla, ref=ref)
            tabla.tableStyleInfo = TableStyleInfo(name="TableStyleMedium2", showRowStripes=True)
            ws.add_table(tabla)


def guardar(wb):
    for ws in wb.worksheets:
        if ws["A2"].value == "Nombre":  # solo las hojas con el formato actual
            dar_formato(ws)
    try:
        wb.save(ARCHIVO_EXCEL)
    except Exception as e:  # por ejemplo, el archivo esta bloqueado: no tiramos la camara
        print("No se pudo guardar el Excel (se reintentara en el siguiente registro):", e)


def abrir_libro():
    if ARCHIVO_EXCEL.exists():
        return load_workbook(ARCHIVO_EXCEL)
    wb = Workbook()
    wb.remove(wb.active)  # se crea una hoja por clase
    return wb


def nombre_hoja_nueva(wb, inicio):
    base = f"{datetime.fromtimestamp(inicio):%Y-%m-%d}"
    nombre, n = base, 2
    while nombre in wb.sheetnames:  # segunda clase el mismo dia: 2026-11-24_2
        nombre = f"{base}_{n}"
        n += 1
    return nombre


def leer_sesion():
    if ARCHIVO_SESION.exists():
        try:
            return json.loads(ARCHIVO_SESION.read_text(encoding="utf-8"))
        except (ValueError, OSError):
            return None
    return None


def leer_presentes(ws):
    return {f[0] for f in ws.iter_rows(min_row=3, values_only=True) if f[0] and f[2] != "Ausente"}


def enviar_ausentes(ausentes):
    texto = "Ausentes: " + (", ".join(sorted(ausentes)) if ausentes else "ninguno")
    print(texto)
    Path("ausentes.txt").write_text(texto + "\n", encoding="utf-8")
    if NTFY_TOPIC:
        try:
            requests.post(f"https://ntfy.sh/{NTFY_TOPIC}", data=texto.encode("utf-8"), timeout=5)
        except requests.RequestException as e:
            print("No se pudo enviar la notificacion:", e)


def cerrar_clase(wb, ws, todos):
    presentes = leer_presentes(ws)
    ausentes = todos - presentes
    ya_cerrada = any(f[2] == "Ausente" for f in ws.iter_rows(min_row=3, values_only=True))
    if not ya_cerrada:
        for n in sorted(ausentes):
            ws.append([n, "", "Ausente"])
        guardar(wb)
    enviar_ausentes(ausentes)
    ARCHIVO_SESION.unlink(missing_ok=True)


def preparar_clase(wb, todos, nueva=False):
    sesion = None if nueva else leer_sesion()
    if sesion and sesion.get("hoja") not in wb.sheetnames:
        sesion = None  # borraron el Excel o la hoja

    if sesion and time.time() - sesion["inicio"] >= DURACION_MIN * 60:
        print(f"La clase de la hoja {sesion['hoja']} ya habia terminado: se cierra y se anotan ausentes.")
        cerrar_clase(wb, wb[sesion["hoja"]], todos)
        sesion = None

    if sesion:
        fin = datetime.fromtimestamp(sesion["inicio"] + DURACION_MIN * 60)
        print(f"Retomando la clase en curso (hoja {sesion['hoja']}), termina a las {fin:%H:%M}.")
        return wb[sesion["hoja"]], sesion["inicio"]

    inicio = time.time()
    hoja = nombre_hoja_nueva(wb, inicio)
    ws = wb.create_sheet(hoja)
    ws.append([f"Inicio de la clase: {datetime.fromtimestamp(inicio):%d/%m/%Y %H:%M:%S}"])
    ws.merge_cells("A1:C1")
    ws.append(ENCABEZADO)
    guardar(wb)
    ARCHIVO_SESION.write_text(json.dumps({"inicio": inicio, "hoja": hoja}), encoding="utf-8")
    fin = datetime.fromtimestamp(inicio + DURACION_MIN * 60)
    print(f"Clase nueva (hoja {hoja}). Puntual hasta {datetime.fromtimestamp(inicio + TOLERANCIA_MIN * 60):%H:%M}, "
          f"termina a las {fin:%H:%M}.")
    return ws, inicio


# ---------------------- aviso (mano + voz) ----------------------
def decir(nombre):
    texto = f"Hola, {nombre}"
    try:
        if sys.platform == "darwin":
            subprocess.run(["say", "-v", VOZ_MAC, texto], check=False)
        else:
            import pyttsx3
            motor = pyttsx3.init()
            motor.say(texto)
            motor.runAndWait()
    except Exception as e:
        print("No se pudo reproducir la voz:", e)


_xiao_serial = None
_candado_xiao = threading.Lock()


def encontrar_puerto():
    if PUERTO_XIAO:
        return PUERTO_XIAO
    from serial.tools import list_ports
    for p in list_ports.comports():
        if p.vid == 0x303A or "usbmodem" in p.device:  # 0x303A = Espressif (la XIAO ESP32-C6)
            return p.device
    return None


def abrir_xiao():
    global _xiao_serial
    try:
        import serial
        puerto = encontrar_puerto()
        if not puerto:
            print("No encuentro la XIAO por USB. Revisa el cable o pon PUERTO_XIAO a mano.")
            return
        conexion = serial.Serial()
        conexion.port = puerto
        conexion.baudrate = 115200
        conexion.timeout = 1
        conexion.dtr = False  # asi no se reinicia la placa al abrir el puerto
        conexion.rts = False
        conexion.open()
        _xiao_serial = conexion
        print(f"XIAO conectada por USB en {puerto}")
    except Exception as e:
        print("No se pudo abrir la XIAO por USB (cierra el Monitor Serie de Arduino):", e)


def saludar_xiao(nombre):
    global _xiao_serial
    if MODO_XIAO == "wifi":
        try:
            requests.get(f"http://{XIAO_IP}/saludo", params={"nombre": nombre}, timeout=3)
        except requests.RequestException as e:
            print("No se pudo contactar a la XIAO:", e)
        return
    enviar_serial(nombre)


def enviar_serial(linea):
    global _xiao_serial
    with _candado_xiao:
        try:
            if _xiao_serial is None or not _xiao_serial.is_open:
                abrir_xiao()
            if _xiao_serial is not None:
                _xiao_serial.write((linea + "\n").encode("utf-8"))
        except Exception as e:
            print("No se pudo hablar con la XIAO por USB:", e)
            _xiao_serial = None


def alertar_desconocido():
    if MODO_XIAO == "usb":
        threading.Thread(target=enviar_serial, args=("#desconocido",)).start()


def avisar(nombre, t_deteccion):
    hilos = [threading.Thread(target=saludar_xiao, args=(nombre,)),
             threading.Thread(target=decir, args=(nombre,))]
    for h in hilos:
        h.start()
    print(f"  -> {time.time() - t_deteccion:.2f} s desde que se detecto hasta mandar el saludo")


# ---------------------- programa principal ----------------------
def main():
    base, nombres, vectores = cargar_base()
    todos = set(base.keys())
    racha = {"nombre": None, "cuadros": 0, "t0": 0.0}
    cuadros_desconocido = 0
    ultima_alerta = 0.0

    wb = abrir_libro()
    ws, inicio = preparar_clase(wb, todos, nueva="--nueva" in sys.argv)
    presentes = leer_presentes(ws)  

    if MODO_XIAO == "usb":
        abrir_xiao()

    cam = cv2.VideoCapture(CAMARA)
    if not cam.isOpened():
        sys.exit("No se pudo abrir la camara.")
    cam.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
    cam.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)

    print(f"Alumnos en la base: {', '.join(sorted(todos))}")
    print("Teclas: q = cerrar (la clase sigue abierta)  |  f = terminar la clase ahora")

    terminar_clase = False
    while True:
        ok, frame = cam.read()
        if not ok:
            break

        alto, ancho = frame.shape[:2]
        zx0 = int(ancho * (1 - ZONA_ANCHO) / 2)
        zx1 = ancho - zx0
        zy0 = int(alto * (1 - ZONA_ALTO) / 2)
        zy1 = alto - zy0

  
        recorte = frame[zy0:zy1, zx0:zx1]
        chico = cv2.resize(recorte, (0, 0), fx=ESCALA, fy=ESCALA)
        rgb = cv2.cvtColor(chico, cv2.COLOR_BGR2RGB)
        ubicaciones = face_recognition.face_locations(rgb, model="hog")
        ch_alto, ch_ancho = rgb.shape[:2]

       
        validas, lejos = [], False
        for (arriba, derecha, abajo, izquierda) in ubicaciones:
            if izquierda <= 2 or arriba <= 2 or derecha >= ch_ancho - 2 or abajo >= ch_alto - 2:
                continue
            if (abajo - arriba) * K / alto < TAMANO_MIN_ROSTRO:
                lejos = True
                continue
            validas.append((arriba, derecha, abajo, izquierda))

       
        validas.sort(key=lambda u: (u[2] - u[0]) * (u[1] - u[3]), reverse=True)
        principal = validas[:1]
        en_espera = validas[1:]

       
        oscuro = (frame * 0.35).astype(np.uint8)
        oscuro[zy0:zy1, zx0:zx1] = frame[zy0:zy1, zx0:zx1]
        frame = oscuro

        nombre_cuadro = None
        hay_desconocido = False
        if principal:
            codigos = face_recognition.face_encodings(rgb, principal)
        else:
            codigos = []
        for (arriba, derecha, abajo, izquierda), codigo in zip(principal, codigos):
            distancias = face_recognition.face_distance(vectores, codigo)
            mejor = int(np.argmin(distancias))
            if distancias[mejor] < UMBRAL:
                nombre_cuadro = nombres[mejor]
                etiqueta = f"{nombre_cuadro} ({distancias[mejor]:.2f})"
                color = (0, 255, 0)
            else:
                etiqueta = "desconocido"
                color = (0, 0, 255)
                hay_desconocido = True
            cv2.rectangle(frame, (zx0 + izquierda * K, zy0 + arriba * K), (zx0 + derecha * K, zy0 + abajo * K), color, 2)
            cv2.putText(frame, etiqueta, (zx0 + izquierda * K, zy0 + arriba * K - 8),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, color, 2)
        for (arriba, derecha, abajo, izquierda) in en_espera:
            cv2.rectangle(frame, (zx0 + izquierda * K, zy0 + arriba * K), (zx0 + derecha * K, zy0 + abajo * K),
                          (160, 160, 160), 1)
            cv2.putText(frame, "espera tu turno", (zx0 + izquierda * K, zy0 + arriba * K - 8),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (160, 160, 160), 1)

   
        color_zona = (0, 255, 0) if principal else (255, 255, 255)
        cv2.rectangle(frame, (zx0, zy0), (zx1, zy1), color_zona, 2)
        if lejos and not principal:
            ayuda = "Acercate"
        elif not principal:
            ayuda = "Parate aqui, frente al lente"
        else:
            ayuda = ""
        if ayuda:
            cv2.putText(frame, ayuda, (zx0 + 10, zy1 - 15), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)

        # Confirmacion: el mismo nombre varios cuadros seguidos (reduce falsos positivos)
        if nombre_cuadro and nombre_cuadro == racha["nombre"]:
            racha["cuadros"] += 1
        else:
            racha = {"nombre": nombre_cuadro, "cuadros": 1 if nombre_cuadro else 0, "t0": time.time()}

       
        cuadros_desconocido = cuadros_desconocido + 1 if hay_desconocido else 0
        if cuadros_desconocido >= CUADROS_DESCONOCIDO and time.time() - ultima_alerta > ENFRIAMIENTO_ALERTA_S:
            ultima_alerta = time.time()
            cuadros_desconocido = 0
            print("! Rostro no registrado: LED rojo")
            alertar_desconocido()

        transcurrido = time.time() - inicio
        puntual = transcurrido <= TOLERANCIA_MIN * 60

        if nombre_cuadro and racha["cuadros"] >= CUADROS_CONFIRMACION and nombre_cuadro not in presentes:
            presentes.add(nombre_cuadro)
            estado = "Puntual" if puntual else "Retardo"
            hora = datetime.now().strftime("%H:%M:%S")
            ws.append([nombre_cuadro, hora, estado])
            guardar(wb)
            print(f"✓ {nombre_cuadro}: {estado} ({hora})")
            avisar(nombre_cuadro, racha["t0"])

        restante = max(0, DURACION_MIN * 60 - transcurrido)
        cv2.putText(frame,
                    f"Presentes: {len(presentes)}/{len(todos)}  |  quedan {int(restante // 3600)}:"
                    f"{int(restante % 3600 // 60):02d}:{int(restante % 60):02d}",
                    (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
        cv2.putText(frame, "Registro: PUNTUAL" if puntual else "Registro: RETARDO",
                    (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.7,
                    (0, 255, 0) if puntual else (0, 165, 255), 2)
        cv2.imshow("Detector de asistencia", frame)

        tecla = cv2.waitKey(1) & 0xFF
        if tecla == ord("q"):
            break
        if tecla == ord("f") or restante <= 0:
            terminar_clase = True
            break

    cam.release()
    cv2.destroyAllWindows()

    if terminar_clase:
        cerrar_clase(wb, ws, todos)
        print("Clase terminada. La proxima vez que abras el programa empieza una clase nueva (hoja nueva).")
    else:
        fin = datetime.fromtimestamp(inicio + DURACION_MIN * 60)
        print(f"Programa cerrado. La clase sigue abierta hasta las {fin:%H:%M}: vuelve a abrirlo para continuar.")


if __name__ == "__main__":
    main()
