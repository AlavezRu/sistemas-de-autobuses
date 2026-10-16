# Sistema de Autobuses — Venta de Boletos

Aplicación web para vender boletos de autobús, hecha con **Flask** y **SQLite**.

Autor: Mario Ruiz Alavez

## Las rutas

Las tres corridas salen de **Teposcolula** y paran en 13 puntos. El precio de cada punto es
lo que se cobra desde Teposcolula hasta ahí:

| Ruta Tlaxiaco | | Ruta Tamazulapam | | Ruta Oaxaca | |
|---|---|---|---|---|---|
| Yolomécatl | $22 | Tejupan | $40 | Desviación | $25 |
| Totonondo | $25 | Las Pilas | $55 | Yanhuitlán | $65 |
| Yucuxaco | $30 | **Tamazulapam** | **$80** | Nochixtlán | $80 |
| Huamelulpan | $35 | | | **Oaxaca** | **$150** |
| Boca del Perro | $38 | | | | |
| **Tlaxiaco** | **$45** | | | | |

Cada ruta lleva **su propio autobús de 40 asientos**, así que el asiento 7 del viaje a Oaxaca
del día 20 no es el asiento 7 del viaje a Tlaxiaco de ese mismo día: los lugares de una
corrida no le quitan lugares a las otras.

Dentro de una misma corrida, en cambio, el autobús es uno solo: quien compra un boleto a
Yolomécatl ocupa un asiento de **todo** el viaje a Tlaxiaco, aunque se baje antes. El punto
donde se baja solo dice cuánto paga, no aparta otro lugar.

## Cómo funciona la venta

La venta se hace en cinco pasos que se van descubriendo en la misma página:

1. **La ruta** — se escoge una de las tres corridas.
2. **El punto donde se baja** — aparecen los puntos de esa ruta con su pasaje; el que se
   escoge es el que pone el precio del boleto.
3. **La fecha del viaje** — se elige en el calendario; no se aceptan días que ya pasaron.
4. **El asiento** — aparece el mapa del autobús de esa corrida (10 filas de 4 asientos, con
   pasillo) con los lugares libres de ese día. Café = libre, rojo = vendido, verde = el que se
   escogió.
5. **Confirmar la venta** — se escribe el nombre del pasajero y se pica *Confirmar venta*.
   Este paso siempre está a la vista: mientras falten datos, debajo del nombre dice qué falta,
   y al picar el botón se pregunta una vez más con los datos del boleto antes de guardarlo.

El precio se copia al boleto cuando se vende, así que el boleto guarda lo que se cobró. Al
terminar se muestra el pase de abordar con el folio, el viaje, la corrida, el asiento y el
pasaje, y en *Boletos vendidos* está la tabla con todas las ventas y el total cobrado, con
opción de cancelar (el asiento vuelve a quedar libre).

## Archivos

| Archivo | Para qué sirve |
|---|---|
| `Pagina.py` | La aplicación Flask y sus rutas |
| `base_datos.py` | Las rutas con sus paradas y precios, y todo lo de SQLite: crear la tabla, guardar, consultar y cancelar boletos |
| `validaciones.py` | Revisa la ruta, la parada, el nombre, la fecha y el asiento antes de guardarlos |
| `templates/base.html` | La plantilla con la cabecera y el menú |
| `templates/index.html` | Página de inicio y el cuadro de rutas, paradas y precios |
| `templates/venta.html` | Los cinco pasos de la venta y el mapa del autobús |
| `templates/boletos.html` | Tabla de los boletos vendidos y el total cobrado |
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
| `/venta` | Formulario de venta (ruta → parada → fecha → asiento → nombre) |
| `/boletos` | Lista de los boletos vendidos |
| `/cancelar/<id>` | Cancela un boleto y libera el asiento |
| `/api/asientos?fecha=&ruta=` | Devuelve en JSON qué asientos están libres ese día en esa corrida |
