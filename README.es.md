# Pokopia Deck Updater

Arma un paquete con **solo los archivos que cambiaron** en la instalación del port [Pokopia Recomp](https://github.com/featureJosh/pokopia-recomp) en tu PC, para mandarlo a una Steam Deck sin copiar ~25 GB cada vez y sin sobrescribir la partida ni los ajustes de la Deck.

> **Lee esto primero**
> - Esta herramienta **no** incluye ni descarga archivos del juego, llaves ni firmware. Para usar el port necesitas tu propia copia extraída del juego, versión 2.0.1a.
> - No está afiliada a Nintendo, The Pokémon Company, Koei Tecmo ni a los autores del port.
> - Es una versión temprana (0.x). Lee las [Limitaciones](#limitaciones) antes de usarla.
> - Los mensajes del programa están en inglés.

English version: [README.md](README.md)

## El problema

El port se tiene que preparar en una PC con Windows, y jugarlo en una Steam Deck (vía Proton) tiene un problema:

- El launcher (`PokopiaLauncher.exe`) necesita WebView2, que Proton no trae, así que no funciona en la Deck.
- Por eso el **Set up** (compila el juego desde tu dump y arma la caché de shaders, 1-2 horas) solo se puede hacer en una PC con Windows.
- En cada versión nueva del port hay que pasar a mano los archivos de la PC a la Deck, con dos riesgos:
  1. Sobrescribir archivos que en la Deck deben ser distintos (partida, ajustes, caché de la GPU).
  2. Mandar archivos que solo funcionan en pareja (un `pkp_rt.dll` nuevo con un `pkp.exe` viejo).
- Copiar todo significa mover ~25 GB, casi todo caché de shaders que no cambió.

La herramienta compara la instalación de la PC con lo que tiene la Deck y arma un paquete con solo lo que falta o cambió, sin incluir nunca lo protegido.

## Qué hace

1. **Revisa el Set up.** Avisa si la caché de shaders no está completa (`shader_cache/spirv/results.tsv`) o si `pkp.exe` no corresponde a la versión del port. Para esto último corre la misma revisión que usa el launcher: `tools/build/pkp_build.py --check`. Si hay avisos, pregunta antes de seguir.
2. **Lee el inventario.** `deck_inventory.json` anota el tamaño, la fecha y la huella SHA-256 de cada archivo que tiene la Deck. La primera vez se arma a partir de una copia en la PC de la carpeta de la Deck.
3. **Compara** cada archivo de la instalación de la PC con el inventario y muestra qué cambió y cuánto pesa.
4. **Arma el paquete** (cuando confirmas). Borra el paquete anterior, copia los cambios en una carpeta con fecha dentro de `packages`, actualiza el inventario y abre la carpeta en el Explorador.

### Nunca se manda (protegido)

| Archivo / carpeta | Por qué |
|---|---|
| `game\` | El dump del juego; ya está en la Deck. |
| `save\` | La partida de la Deck es la que importa. |
| `pkp.ini` | El de la Deck usa rutas relativas y ajustes propios; el de la PC tiene rutas absolutas de Windows. |
| `controls.ini` | Los ajustes de la Deck. |
| `nup_dump\` | Copia desempaquetada del juego, si se usó un `.nup`. |
| `pipeline_cache.bin` | Depende de la GPU (por ejemplo, NVIDIA en la PC y AMD en la Deck). |
| `pipeline_keys.bin` | Se deja el de la Deck por precaución. |

### Tampoco se manda (la Deck no lo necesita)

- `build\`, `pkp_freeze*`, `PokopiaLauncher.exe`.
- `CHANGELOG*`, `README*` y `LICENSE` en la raíz (la carpeta `licenses\` **sí** se manda).
- Logs y temporales en cualquier lugar: `pkp.log*`, `*.prev`, `*.tmp`.
- Subcarpetas de `shader_cache` que no son `spirv` (`missing`, `runtime`, `corpus`): cada equipo tiene las suyas.

### Cómo decide si un archivo cambió

- No está en el inventario → la Deck no lo tiene → se manda.
- Tamaño distinto → se manda.
- Archivos del port (todo lo que no es `shader_cache\spirv`, menos de 1 GB en total): siempre se comparan por huella SHA-256, así que se detecta hasta un cambio de una línea.
- Shaders de `shader_cache\spirv` (~99 mil archivos, ~25 GB): mismo tamaño y misma fecha significa que no cambió; si la fecha es distinta, se comparan por huella. El Set up les pone fecha nueva cada vez que los reescribe.

## Requisitos

- PC con Windows (probado en Windows 10), con el port instalado y el Set up terminado.
- Python 3 con el lanzador `py` (probado con Python 3.13). No necesita paquetes extra.
- Steam Deck con el port corriendo vía Proton (probado en una Steam Deck LCD con Proton Experimental).
- Una forma de mandar una carpeta a la Deck (probado con [LocalSend](https://localsend.org)).
- **Solo la primera vez:** una copia en la PC de lo que tiene la Deck. Se lee una sola vez para armar el inventario y después se puede borrar.

## Preparación

1. Pon `pokopia_deck_updater.py` y `Update_Pokopia.bat` en la misma carpeta, **fuera** de la carpeta del port.
2. Doble clic en `Update_Pokopia.bat`. La primera vez:
   - Una ventana te pide la carpeta de tu instalación del port en la PC: donde corriste el Set up (tiene que tener `pkp.exe`).
   - Si todavía no hay inventario, otra ventana te pide la copia en la PC de la carpeta del port de la Deck. Leerla tarda un rato (~40 minutos para ~25 GB en mi caso) y solo pasa una vez.

Si la ventana no se puede abrir, la herramienta te pide pegar la ruta de la carpeta.

La herramienta guarda junto a ella: `config.json` (la carpeta de tu port), `deck_inventory.json` y su `.bak`, y la carpeta `packages`. Si mueves la herramienta, muévelos con ella. Para elegir otra carpeta del port, borra `config.json`.

**Si vienes de la 0.3.x:** pon los archivos nuevos donde estaban los viejos. Tu `inventario_deck.json` se renombra a `deck_inventory.json` y se convierte solo, así que no se vuelve a armar. Puedes borrar los viejos `actualizar_pokopia.py` y `Actualizar Pokopia.bat`.

## Uso

En la PC:

1. Copia la versión nueva del port **encima** de tu instalación de la PC con "Reemplazar" (así se conservan `build\` y la caché de shaders).
2. Abre el launcher. Si pide Set up, déjalo terminar.
3. Dale Play una vez. Si hubo shaders faltantes, ciérralo y dale Play otra vez (el segundo arranque los traduce).
4. Doble clic en `Update_Pokopia.bat`.

En la Deck:

5. Respalda la carpeta `save`, recibe el paquete (por ejemplo, con LocalSend) y copia su **contenido** dentro de la carpeta del port con "Sobrescribir todo".

Dos reglas aprendidas en el camino:

- `pkp.exe` y `pkp_rt.dll` van en pareja: nunca mandes el runtime de una versión sin el `pkp.exe` que le corresponde.
- Algunas versiones piden repetir el Set up y otras no. La forma confiable de saberlo es abrir el launcher.

## Resultados reales

Mis corridas del 5 de noviembre de 2026:

| | Tiempo | Resultado |
|---|---|---|
| Primera vez (armar el inventario + comparar) | ~40 min | 107,323 archivos en el inventario; ~105 mil archivos revisados en la PC |
| Segunda vez (con el inventario ya armado) | ~1 min | 2 archivos cambiados (388.5 MB) |
| Corrida sin nada nuevo (0.4.0) | ~25 s | "The Deck is up to date" |

## Limitaciones

- Del lado de la PC, solo funciona en Windows.
- El inventario da por hecho que todo paquete armado se mandó a la Deck. Si armas uno y no lo mandas, restaura `deck_inventory.json.bak`.
- Si cambias archivos en la Deck a mano, el inventario no se entera.
- No borra en la Deck archivos que una versión nueva del port haya quitado.
- Copiar el paquete en su lugar dentro de la Deck sigue siendo manual.
- Solo está probado con el fork [featureJosh/pokopia-recomp](https://github.com/featureJosh/pokopia-recomp).

## Ideas para siguientes versiones

- Un script del lado de la Deck que respalde `save`, aplique el paquete o reconstruya el inventario.
- Traer a la PC la carpeta `shader_cache\missing` de la Deck para que el launcher traduzca esos shaders, y devolverlos. La Deck no puede traducirlos sola, porque el launcher no corre ahí.
- Mandar por red directamente, sin LocalSend.

## Hecho con IA

No soy programador; es un proyecto para aprender. Yo aporté el problema, las hipótesis y las decisiones, y Claude (Anthropic) escribió el código conmigo. Lo probé en mi propia PC y mi Steam Deck.

## Licencia

[MIT](LICENSE). La herramienta no incluye código del port.
