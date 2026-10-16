# Sistema de Autobuses — Venta de Boletos

Aplicación web para vender boletos de autobús, hecha con **Flask** y **SQLite**.

Autor: Mario Ruiz Alavez

## Las cuentas y los perfiles

Para usar la taquilla hay que entrar con una cuenta. Hay dos perfiles:

| Puede... | Vendedor | Administrador |
|---|:---:|:---:|
| Vender boletos | ✔ | ✔ |
| Ver la lista de boletos vendidos | ✔ | ✔ |
| Cancelar cualquier boleto (lo haya vendido quien sea) | ✔ | ✔ |
| Corregir un boleto ya vendido (pasajero, parada, fecha, asiento) | | ✔ |
| Sacar el corte de caja y descargarlo en PDF | | ✔ |
| Dar de alta, cambiar, borrar y ver las cuentas | | ✔ |

Al vendedor ni le salen en el menú las pestañas de *Corte de caja* y *Usuarios*, y si abre
esas direcciones a mano le sale el aviso de que son solo para el administrador.

Cada boleto guarda **quién lo vendió**, y eso se ve en la tabla de boletos, en el pase de
abordar y en el corte de caja. Los boletos que se vendieron antes de que hubiera login se ven
con una raya.

### El primer arranque

La primera vez que se abre, la base no tiene ninguna cuenta y cualquier página manda a una
pantalla para **crear al administrador** con el usuario y la contraseña que tú escojas. En
cuanto existe la primera cuenta, esa pantalla ya no se puede volver a abrir. No hay ninguna
contraseña por defecto escrita en el código.

Después, el administrador da de alta a los vendedores desde *Usuarios*.

### Reglas de las cuentas

- El **usuario** lleva de 3 a 20 letras sin acentos, números, punto o guion, sin espacios. Se
  guarda en minúsculas y **no se puede cambiar**, porque es lo que queda anotado en los boletos.
- La **contraseña** lleva por lo menos 8 caracteres (`MINIMO_CONTRASENA` en `validaciones.py`).
  Al editar una cuenta, si se deja en blanco se queda la de antes.
- Siempre tiene que quedar **por lo menos un administrador**: al último no se le puede quitar
  el perfil, y nadie puede borrar su propia cuenta.
- Si el admin le cambia el perfil a alguien o le borra la cuenta, surte efecto en el siguiente
  clic de esa persona, sin esperar a que salga y vuelva a entrar.
- Al borrar una cuenta, los boletos que vendió se quedan, con su nombre.

### Seguridad

- Las contraseñas nunca se guardan tal cual: se guarda su hash (scrypt, de werkzeug).
- Si el usuario o la contraseña están mal, el aviso es el mismo para los dos, y el login tarda
  lo mismo exista o no el usuario, para que no se pueda averiguar qué cuentas existen.
- Cada formulario lleva un campo escondido que solo conoce la sesión, y la cookie va con
  `SameSite=Lax`: otra página no puede mandar formularios a nombre de quien tenga la sesión
  abierta (por ejemplo, para cancelarle boletos).
- La sesión se firma con una llave que se crea sola en el archivo `.clave_secreta`. **Ese
  archivo no se sube nunca** (está en el `.gitignore`): con él cualquiera podría hacerse pasar
  por el administrador. En un servidor conviene ponerla en la variable de entorno `SECRET_KEY`.

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
| `Pagina.py` | La aplicación Flask, sus rutas y el portero que revisa cada petición |
| `sesion.py` | El login: la llave de la sesión, quién está adentro, los permisos y la protección de formularios |
| `corte.py` | Suma el corte de caja y arma el PDF con fpdf2 |
| `base_datos.py` | Las rutas con sus paradas y precios, y todo lo de SQLite: los boletos y las cuentas |
| `validaciones.py` | Revisa lo que se escribe en cada formulario antes de guardarlo |
| `templates/base.html` | La plantilla con la cabecera, la cuenta de quien está adentro y el menú según su perfil |
| `templates/entrar.html` | El login |
| `templates/primer_arranque.html` | La creación del primer administrador |
| `templates/index.html` | Página de inicio y el cuadro de rutas, paradas y precios |
| `templates/venta.html` | Los cinco pasos de la venta y el mapa del autobús |
| `templates/boletos.html` | Tabla de los boletos vendidos y el total cobrado |
| `templates/corte.html` | Los filtros del corte de caja y sus tres bloques |
| `templates/boleto_editar.html` | La corrección de un boleto (solo admin) |
| `templates/usuarios.html` | La lista de cuentas y el alta de una nueva (solo admin) |
| `templates/usuario_editar.html` | El cambio de nombre, perfil o contraseña de una cuenta (solo admin) |
| `templates/aviso.html` | Los avisos de sin permiso, no existe y formulario vencido |
| `static/estilos.css` | Los estilos (paleta café) |

## Cómo ejecutarlo

```bash
pip install -r requirements.txt
python Pagina.py
```

Las librerías son **Flask** para la aplicación, **fpdf2** para el PDF del corte de caja y
**gunicorn** para subirla a un servidor.

Después se abre <http://localhost:5000> en el navegador.

La base de datos `boletos.db` se crea sola la primera vez que se arranca, por eso no viene en
el repositorio.

## Subirlo a Render

El servicio corre con `gunicorn Pagina:app`. En el servicio, en **Environment**, van estas
variables:

| Variable | Qué poner | Para qué |
|---|---|---|
| `SECRET_KEY` | Botón **Generate** de Render | Firma las sesiones. Sin ella, todos salen de su sesión en cada deploy |
| `ADMIN_USUARIO` | Ej. `mario.ruiz` | El usuario del administrador |
| `ADMIN_CONTRASENA` | Por lo menos 8 caracteres | Su contraseña |
| `ADMIN_NOMBRE` | Ej. `Mario Ruiz Alavez` (opcional) | Su nombre; si no se pone, queda "Administrador" |
| `BOLETOS_DB` | Opcional, ej. `/var/data/boletos.db` | Dónde guardar la base, si se le pone un disco persistente |

**En Render no existe la pantalla de primer arranque.** Render pone sola la variable `RENDER`, y
con ella la app sabe que está en internet: ahí el formulario dejaría que el primero que llegara
se hiciera administrador. En su lugar, al arrancar se crea el admin con `ADMIN_USUARIO` y
`ADMIN_CONTRASENA`, siempre que la base no tenga ninguna cuenta. Si faltan esas variables, la
página dice que hay que configurarlas y no deja crear a nadie. Allá la cookie de la sesión
además va marcada como `Secure`, para que solo viaje por https.

Lo que pasa al arrancar (el admin que se creó, o lo que le falta a las variables) sale en los
**Logs** del servicio. La contraseña nunca se escribe ahí.

### Ojo: en el plan gratis los datos no duran

El disco de un servicio gratis de Render se borra en cada deploy y cada vez que el servicio
se duerme por falta de visitas. Con él se van **los boletos y las cuentas de los vendedores**.
El administrador se vuelve a crear solo con las variables, pero lo demás empieza de cero.

Para que los datos duren hay dos caminos:

- **Un disco persistente** (pide un plan de pago): se monta, por ejemplo, en `/var/data` y se
  pone `BOLETOS_DB=/var/data/boletos.db`. El código ya lo soporta.
- **Una base de datos de Render (PostgreSQL)**: habría que cambiar `base_datos.py`, que hoy
  habla con SQLite.

## Rutas

| Ruta | Qué hace |
|---|---|
| `/primer-arranque` | Crea al primer administrador (solo mientras no hay cuentas) |
| `/entrar` | El login |
| `/salir` | Cierra la sesión (POST) |
| `/` | Página de inicio |
| `/venta` | Formulario de venta (ruta → parada → fecha → asiento → nombre) |
| `/boletos` | Lista de los boletos vendidos |
| `/cancelar/<id>` | Cancela un boleto y libera el asiento |
| `/boletos/<id>/editar` | Corrige un boleto ya vendido (solo admin) |
| `/corte` | Corte de caja con sus filtros (solo admin) |
| `/corte.pdf?modo=&dia=&desde=&hasta=&ruta=` | Descarga el corte en PDF con esos filtros (solo admin) |
| `/usuarios` | La lista de cuentas y el alta de una nueva (solo admin) |
| `/usuarios/<id>/editar` | Cambia el nombre, el perfil o la contraseña de una cuenta (solo admin) |
| `/usuarios/<id>/borrar` | Borra una cuenta (solo admin, POST) |
| `/api/asientos?fecha=&ruta=` | Devuelve en JSON qué asientos están libres ese día en esa corrida |
