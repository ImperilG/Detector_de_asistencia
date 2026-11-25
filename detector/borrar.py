"""
Ver o borrar personas registradas 

    python borrar.py                 -> lista los registrados y cuantas muestras tiene cada uno
    python borrar.py "Nombre"        -> borra a esa persona (pide confirmacion)
    python borrar.py "Ana" "Luis"    -> borra a varias
"""
import pickle
import shutil
import sys
from pathlib import Path

ARCHIVO = Path("rostros.pkl")


def main():
    if not ARCHIVO.exists():
        sys.exit("No existe rostros.pkl")

    with open(ARCHIVO, "rb") as f:
        base = pickle.load(f)

    nombres_a_borrar = sys.argv[1:]

    if not nombres_a_borrar:
        print("Registrados:")
        for nombre, muestras in base.items():
            print(f"  - {nombre} ({len(muestras)} muestras)")
        return

    faltantes = [n for n in nombres_a_borrar if n not in base]
    if faltantes:
        print("No estan registrados (revisa mayusculas y acentos):", ", ".join(faltantes))
    validos = [n for n in nombres_a_borrar if n in base]
    if not validos:
        return

    if input(f"¿Borrar a {', '.join(validos)}? No se puede deshacer (s/n): ").strip().lower() != "s":
        print("Cancelado.")
        return

    shutil.copy(ARCHIVO, "rostros_respaldo.pkl")  # copia de seguridad por si te equivocas
    for n in validos:
        del base[n]
    with open(ARCHIVO, "wb") as f:
        pickle.dump(base, f)

    print("Borrados:", ", ".join(validos))
    print("Quedan:", ", ".join(base.keys()) if base else "nadie")
    print("Copia anterior en rostros_respaldo.pkl (borrala tambien si esas personas pidieron que no se guardara su rostro).")


if __name__ == "__main__":
    main()
