# -*- coding: utf-8 -*-
r"""
actualizar_pokopia.py  —  versión 3

Arma un paquete con SOLO los archivos del port de Pokopia (featureJosh/pokopia-recomp) que cambiaron,
para mandarlo a la Steam Deck por LocalSend, sin incluir nunca tus datos protegidos.

Para saber qué tiene la Deck usa un INVENTARIO (inventario_deck.json, junto a este script):
una lista con el tamaño, la fecha y la huella de cada archivo de la Deck.
La primera vez lo arma leyendo D:\PokopiaDeck; después esa carpeta ya no hace falta.

Antes de correrlo (en la PC):
  1. Copia el zip nuevo ENCIMA de D:\PokopiaPC con "Reemplazar".
  2. Abre el launcher. Si pide Set up, termínalo.
  3. Dale Play una vez; si hubo shaders faltantes, ciérralo y dale Play otra vez.
  4. Doble clic en "Actualizar Pokopia.bat".
"""

import hashlib                  # para calcular la "huella" (hash) de un archivo
import json                     # para guardar y leer el inventario
import os                       # para abrir la carpeta del paquete al final
import shutil                   # para copiar y borrar carpetas
import subprocess               # para correr la revisión de Set up que usa el propio launcher
import sys                      # para terminar el programa con un mensaje
from datetime import datetime   # para ponerle fecha y hora a la carpeta de envío
from fnmatch import fnmatch     # para comparar nombres con comodines, como "pkp.log*"
from pathlib import Path        # para manejar rutas de carpetas de forma cómoda

# ============================================================
# 1) TUS CARPETAS
# ============================================================

# La instalación de trabajo: donde corres el Set up y le das Play en la PC.
ORIGEN = Path(r"D:\PokopiaPC")

# Aquí se arma el paquete que mandas por LocalSend (solo se guarda el más reciente).
ENVIO = Path(r"D:\PokopiaEnvio")

# El espejo de la Deck. Solo se usa UNA vez, para armar el inventario. Después puedes borrarlo.
ESPEJO_INICIAL = Path(r"D:\PokopiaDeck")

# El inventario se guarda junto a este script.
INVENTARIO = Path(__file__).resolve().parent / "inventario_deck.json"

# ============================================================
# 2) LO QUE NUNCA SE MANDA
# ============================================================

# Nombres en la raíz del port (mayúsculas o minúsculas da igual).
PROTEGIDOS = {
    "game",                # el dump del juego
    "save",                # tu partida de la Deck
    "pkp.ini",             # el de la Deck tiene rutas relativas y tus ajustes (submit_thread)
    "controls.ini",        # tus ajustes de la Deck
    "nup_dump",            # copia desempaquetada del juego, si usaste un .nup
    "pipeline_cache.bin",  # depende de la tarjeta de video: la PC es NVIDIA, la Deck es AMD
    "pipeline_keys.bin",   # se deja el de la Deck por precaución
}

# Cosas de la raíz que la Deck no necesita.
OMITIR_RAIZ = {
    "build",               # taller del Set up; el juego corre desde pkp.exe
    "pkp_freeze",
    "pokopialauncher.exe", # el launcher no funciona en la Deck
}
OMITIR_RAIZ_PATRONES = ["changelog*", "readme*", "license", "license.*", "pkp_freeze*"]   # ojo: la carpeta "licenses" sí se manda

# Archivos que se omiten estén donde estén (logs y temporales).
OMITIR_EN_CUALQUIER_LUGAR = ["pkp.log*", "*.prev", "*.tmp"]

# ============================================================
# 3) FUNCIONES DE APOYO
# ============================================================

def huella(archivo: Path) -> str:
    """Lee el archivo por pedazos y devuelve su huella SHA-256. Si cambia un solo bit, la huella cambia por completo."""
    h = hashlib.sha256()
    with open(archivo, "rb") as f:
        for pedazo in iter(lambda: f.read(1024 * 1024), b""):   # pedazos de 1 MB para no llenar la memoria
            h.update(pedazo)
    return h.hexdigest()


def clave(relativa: Path) -> str:
    """La ruta como texto, con "/" y en minúsculas, para que el inventario no dependa de cómo la escribe Windows."""
    return relativa.as_posix().lower()


def es_shader(relativa: Path) -> bool:
    """¿Es un archivo de shader_cache\\spirv? Esos se comparan por tamaño y fecha (los genera el Set up)."""
    partes = [p.lower() for p in relativa.parts]
    return len(partes) > 2 and partes[0] == "shader_cache" and partes[1] == "spirv"


def se_salta(relativa: Path) -> bool:
    """¿Esta ruta queda fuera del paquete (y del inventario)?"""
    partes = [p.lower() for p in relativa.parts]
    raiz, nombre = partes[0], partes[-1]

    if raiz in PROTEGIDOS or raiz in OMITIR_RAIZ:
        return True
    if any(fnmatch(raiz, patron) for patron in OMITIR_RAIZ_PATRONES):
        return True
    if any(fnmatch(nombre, patron) for patron in OMITIR_EN_CUALQUIER_LUGAR):
        return True
    if raiz == "shader_cache" and len(partes) > 2 and partes[1] != "spirv":
        return True        # missing, runtime, corpus...: la Deck usa los suyos
    return False


def archivos_del_port(carpeta: Path):
    """Todos los archivos de la carpeta que cuentan para el paquete."""
    for archivo in carpeta.rglob("*"):
        if archivo.is_file():
            relativa = archivo.relative_to(carpeta)
            if not se_salta(relativa):
                yield relativa


def tamano_legible(n: float) -> str:
    for unidad in ("B", "KB", "MB", "GB"):
        if n < 1024:
            return f"{n:.1f} {unidad}"
        n /= 1024
    return f"{n:.1f} TB"


def preguntar(texto: str) -> bool:
    return input(texto + " (si/no): ").strip().lower() in ("si", "sí", "s")


def salir(mensaje: str):
    print("\n" + mensaje)
    sys.exit(1)

# ============================================================
# 4) EL INVENTARIO
# ============================================================

def leer_inventario() -> dict:
    with open(INVENTARIO, "r", encoding="utf-8") as f:
        return json.load(f)


def guardar_inventario(inv: dict):
    """Guarda primero en un archivo temporal y luego lo cambia de nombre: si algo falla a la mitad, el anterior sigue bien."""
    tmp = INVENTARIO.with_suffix(".json.tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(inv, f, ensure_ascii=False, indent=0)
    if INVENTARIO.exists():
        shutil.copy2(INVENTARIO, INVENTARIO.with_suffix(".json.bak"))   # respaldo del anterior
    os.replace(tmp, INVENTARIO)


def crear_inventario():
    """Lee el espejo de la Deck una sola vez y anota tamaño, fecha y huella de cada archivo."""
    if not ESPEJO_INICIAL.is_dir():
        salir(f"No hay inventario y tampoco encuentro el espejo {ESPEJO_INICIAL}. No sé qué tiene la Deck.")
    print(f"Primera vez: armando el inventario a partir de {ESPEJO_INICIAL}.")
    print("Esto lee toda la carpeta (~25 GB) y solo se hace una vez. Puede tardar un rato.\n")
    inv = {"version": 1, "archivos": {}}
    for i, r in enumerate(archivos_del_port(ESPEJO_INICIAL), 1):
        a = ESPEJO_INICIAL / r
        st = a.stat()
        inv["archivos"][clave(r)] = {"tam": st.st_size, "fecha": st.st_mtime, "huella": huella(a)}
        if i % 5000 == 0:
            print(f"   ...{i} archivos anotados")
    guardar_inventario(inv)
    print(f"   Inventario listo: {len(inv['archivos'])} archivos.\n")
    return inv


def cambio(relativa: Path, inv: dict) -> bool:
    """¿Este archivo de la PC es distinto de lo que tiene la Deck según el inventario?"""
    a = ORIGEN / relativa
    st = a.stat()
    dato = inv["archivos"].get(clave(relativa))
    if dato is None:
        return True                                    # la Deck no lo tiene
    if st.st_size != dato["tam"]:
        return True                                    # distinto tamaño: seguro cambió
    if es_shader(relativa) and abs(st.st_mtime - dato["fecha"]) <= 2:
        return False                                   # shader con mismo tamaño y fecha: igual
    if huella(a) != dato["huella"]:                    # archivos del port: siempre por huella
        return True
    dato["fecha"] = st.st_mtime                        # contenido igual: anotamos la fecha nueva para ir rápido la próxima
    return False

# ============================================================
# 5) REVISIÓN DEL SET UP
# ============================================================

def revisar_set_up() -> list:
    """Avisos si parece que el Set up no está completo o no corresponde a esta versión."""
    avisos = []
    if not (ORIGEN / "pkp.exe").is_file():
        return ["No encuentro pkp.exe en la carpeta de origen. ¿Corriste el Set up ahí?"]
    if not (ORIGEN / "shader_cache" / "spirv" / "results.tsv").is_file():
        avisos.append("La caché de shaders no está completa: deja terminar el Set up.")

    # La misma revisión que hace el launcher para decidir si pide Set up (pkp_build.py --check).
    python = ORIGEN / "tools" / "python" / "python.exe"
    revisor = ORIGEN / "tools" / "build" / "pkp_build.py"
    if python.is_file() and revisor.is_file():
        try:
            r = subprocess.run([str(python), "-I", str(revisor), "--check", "--game", str(ORIGEN)],
                               capture_output=True, timeout=300)
            if r.returncode != 0:
                avisos.append("El pkp.exe no corresponde a esta versión: el launcher pediría Set up. "
                              "Córrelo antes de mandar nada (pkp.exe y pkp_rt.dll van en pareja).")
        except Exception as e:
            avisos.append(f"No pude hacer la revisión del Set up ({e}). Abre el launcher para confirmar.")
    else:
        avisos.append("No encontré la herramienta de revisión del launcher. Abre el launcher para confirmar.")
    return avisos

# ============================================================
# 6) PROGRAMA PRINCIPAL
# ============================================================

def main():
    print("=" * 60)
    print("  Actualizador de Pokopia para Steam Deck")
    print("=" * 60)
    print("Recordatorio: si el launcher pidió Set up, termínalo y abre el juego dos veces antes de esto.\n")

    if not ORIGEN.is_dir():
        salir(f"No existe la carpeta de origen {ORIGEN}. Revísala al inicio del script.")
    if ENVIO.resolve() == ORIGEN.resolve() or ORIGEN.resolve() in ENVIO.resolve().parents:
        salir("La carpeta de envío no puede estar dentro de la de origen.")

    # Paso 1: Set up
    print("[1/4] Revisando el Set up...")
    avisos = revisar_set_up()
    if not avisos:
        print("      ok")
    for aviso in avisos:
        print("      AVISO:", aviso)
    if avisos and not preguntar("\n      Hay avisos. ¿Seguir de todos modos?"):
        salir("Cancelado. No se hizo nada.")

    # Paso 2: inventario de la Deck
    print("\n[2/4] Leyendo el inventario de la Deck...")
    inv = leer_inventario() if INVENTARIO.is_file() else crear_inventario()
    print(f"      La Deck tiene {len(inv['archivos'])} archivos registrados.")

    # Paso 3: comparar
    print("\n[3/4] Comparando con la PC...")
    cambios = []
    for i, r in enumerate(archivos_del_port(ORIGEN), 1):
        if cambio(r, inv):
            cambios.append(r)
        if i % 5000 == 0:
            print(f"      ...{i} archivos revisados")
    guardar_inventario(inv)        # guarda las fechas actualizadas de los archivos iguales (no cambia lo que tiene la Deck)

    if not cambios:
        salir("      La Deck ya está al día. No hay nada que mandar.")

    cambios.sort()
    total = sum((ORIGEN / r).stat().st_size for r in cambios)
    print(f"      {len(cambios)} archivos cambiaron ({tamano_legible(total)}):")
    for r in cambios[:25]:
        print("        ", r)
    if len(cambios) > 25:
        print(f"         ... y {len(cambios) - 25} más")
    print("      Nunca se incluye:", ", ".join(sorted(PROTEGIDOS)))

    # Paso 4: armar el paquete
    if not preguntar("\n[4/4] ¿Armar el paquete?"):
        salir("Cancelado. No se copió nada.")

    ENVIO.mkdir(parents=True, exist_ok=True)
    for viejo in ENVIO.glob("envio_*"):             # borra solo los paquetes anteriores que armó este script
        if viejo.is_dir():
            shutil.rmtree(viejo)

    paquete = ENVIO / datetime.now().strftime("envio_%Y-%m-%d_%H-%M")
    for i, r in enumerate(cambios, 1):
        destino = paquete / r
        destino.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(ORIGEN / r, destino)
        st = (ORIGEN / r).stat()
        inv["archivos"][clave(r)] = {"tam": st.st_size, "fecha": st.st_mtime, "huella": huella(destino)}
        if i % 500 == 0:
            print(f"      [{i}/{len(cambios)}]")
    guardar_inventario(inv)        # ahora el inventario cuenta estos archivos como ya enviados

    print("\nListo. Paquete armado en:")
    print("  ", paquete)
    print("\nEn la Deck:")
    print("  1. Respalda la carpeta save.")
    print("  2. Recibe el paquete por LocalSend.")
    print("  3. Copia su CONTENIDO dentro de PokopiaDeck con Dolphin y elige 'Sobrescribir todo'.")

    if hasattr(os, "startfile"):
        os.startfile(paquete)       # abre la carpeta en el Explorador para arrastrarla a LocalSend


if __name__ == "__main__":
    main()
