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

## Corte de caja

En *Corte de caja* se saca lo vendido y se descarga en PDF. Se agrupa por la **fecha del
viaje**, o sea por el día en que sale el autobús, no por el día en que se cobró el boleto.

Los filtros son dos y se combinan:

| Filtro | Opciones |
|---|---|
| Qué tanto | **Todo** · **Un día** · **Un periodo** (de una fecha a otra) |
| Qué ruta | **Todas las rutas** · una sola de las tres |

El corte trae tres bloques:

1. **Resumen por día** — cada día con sus rutas, el subtotal del día y, al final, el total
   del corte.
2. **Desglose por parada** — cuántos boletos y cuánto dinero dejó cada uno de los 13 puntos.
   Las paradas que no vendieron nada salen en gris, para que se vea cuáles no se movieron.
3. **Detalle de boletos** — folio, pasajero, parada, corrida, asiento, fechas y pasaje, para
   que el PDF sirva de comprobante.

El botón *Descargar PDF* manda los mismos filtros que se ven en la pantalla, así que el
archivo trae exactamente lo que se está mirando. El nombre del archivo lo dice:
`corte-de-caja-tlaxiaco-2026-10-01-a-2026-10-31.pdf`.

Los boletos cancelados no aparecen en el corte: al cancelar uno, el asiento se libera y el
renglón se borra de la base.

## Archivos

| Archivo | Para qué sirve |
|---|---|
| `Pagina.py` | La aplicación Flask y sus rutas |
| `corte.py` | Suma el corte de caja y arma el PDF con fpdf2 |
| `base_datos.py` | Las rutas con sus paradas y precios, y todo lo de SQLite: crear la tabla, guardar, consultar y cancelar boletos |
| `validaciones.py` | Revisa la ruta, la parada, el nombre, la fecha y el asiento antes de guardarlos |
| `templates/base.html` | La plantilla con la cabecera y el menú |
| `templates/index.html` | Página de inicio y el cuadro de rutas, paradas y precios |
| `templates/venta.html` | Los cinco pasos de la venta y el mapa del autobús |
| `templates/boletos.html` | Tabla de los boletos vendidos y el total cobrado |
| `templates/corte.html` | Los filtros del corte de caja y sus tres bloques |
| `static/estilos.css` | Los estilos (paleta café) |

## Cómo ejecutarlo

```bash
pip install -r requirements.txt
python Pagina.py
```

Son dos librerías: **Flask** para la aplicación y **fpdf2** para el PDF del corte de caja.

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
| `/corte` | Corte de caja con sus filtros |
| `/corte.pdf?modo=&dia=&desde=&hasta=&ruta=` | Descarga el corte en PDF con esos filtros |
| `/api/asientos?fecha=&ruta=` | Devuelve en JSON qué asientos están libres ese día en esa corrida |
