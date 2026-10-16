# Sistema de Autobuses — Venta de Boletos

Aplicación web para vender boletos de autobús, hecha con **Flask** y **SQLite**.

Autor: Mario Ruiz Alavez

## Cómo funciona la venta

La venta se hace en tres pasos que se van descubriendo en la misma página:

1. **La fecha del viaje** — se elige en el calendario; no se aceptan días que ya pasaron.
2. **El asiento** — aparece el mapa del autobús (10 filas de 4 asientos, con pasillo) con los
   lugares libres de ese día. Café = libre, rojo = vendido, verde = el que se escogió.
3. **El pasajero** — solo se escribe el nombre y el boleto queda guardado.

Al terminar se muestra el pase de abordar con el folio y el asiento, y en *Boletos vendidos*
está la tabla con todas las ventas, con opción de cancelar (el asiento vuelve a quedar libre).

## Archivos

| Archivo | Para qué sirve |
|---|---|
| `Pagina.py` | La aplicación Flask y sus rutas |
| `base_datos.py` | Todo lo de SQLite: crear la tabla, guardar, consultar y cancelar boletos |
| `validaciones.py` | Revisa el nombre, la fecha y el asiento antes de guardarlos |
| `templates/base.html` | La plantilla con la cabecera y el menú |
| `templates/index.html` | Página de inicio |
| `templates/venta.html` | Los tres pasos de la venta y el mapa del autobús |
| `templates/boletos.html` | Tabla de los boletos vendidos |
| `static/estilos.css` | Los estilos (paleta café) |

## Cómo ejecutarlo

```bash
pip install flask
python Pagina.py
```

Después se abre <http://localhost:5000> en el navegador.

La base de datos `boletos.db` se crea sola la primera vez que se arranca, por eso no viene en
el repositorio.

## Rutas

| Ruta | Qué hace |
|---|---|
| `/` | Página de inicio |
| `/venta` | Formulario de venta (fecha → asiento → nombre) |
| `/boletos` | Lista de los boletos vendidos |
| `/cancelar/<id>` | Cancela un boleto y libera el asiento |
| `/api/asientos?fecha=` | Devuelve en JSON qué asientos están libres ese día |
