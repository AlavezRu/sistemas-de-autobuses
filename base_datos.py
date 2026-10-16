# -*- coding: utf-8 -*-
# Todo lo que tiene que ver con la base de datos SQLite vive aqui, para que
# Pagina.py solo pida los datos y no sepa como estan guardados.
import os
import sqlite3
from datetime import datetime

ARCHIVO = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'boletos.db')

FILAS = 10       # cada autobus tiene 10 filas
POR_FILA = 4     # dos asientos, el pasillo, y otros dos
TOTAL_ASIENTOS = FILAS * POR_FILA  # 40 lugares por autobus

FORMATO_FECHA = '%d/%m/%Y %H:%M:%S'  # como se guarda el momento de la venta

ORIGEN = 'Teposcolula'  # las tres corridas salen de aqui

# Las tres rutas de la linea, de la mas corta a la mas larga, con los puntos
# donde para el autobus. El precio de cada parada es lo que se cobra desde
# Teposcolula hasta ahi, y la ultima parada es la punta de la corrida.
# La clave es el nombre corto que viaja en el formulario y se guarda en la base.
RUTAS = {
    'tlaxiaco': {
        'clave': 'tlaxiaco',
        'destino': 'Tlaxiaco',
        'paradas': [
            {'clave': 'yolomecatl',     'nombre': 'Yolomécatl',     'precio': 22},
            {'clave': 'totonondo',      'nombre': 'Totonondo',      'precio': 25},
            {'clave': 'yucuxaco',       'nombre': 'Yucuxaco',       'precio': 30},
            {'clave': 'huamelulpan',    'nombre': 'Huamelulpan',    'precio': 35},
            {'clave': 'boca-del-perro', 'nombre': 'Boca del Perro', 'precio': 38},
            {'clave': 'tlaxiaco',       'nombre': 'Tlaxiaco',       'precio': 45},
        ],
    },
    'tamazulapam': {
        'clave': 'tamazulapam',
        'destino': 'Tamazulapam',
        'paradas': [
            {'clave': 'tejupan',     'nombre': 'Tejupan',     'precio': 40},
            {'clave': 'las-pilas',   'nombre': 'Las Pilas',   'precio': 55},
            {'clave': 'tamazulapam', 'nombre': 'Tamazulapam', 'precio': 80},
        ],
    },
    'oaxaca': {
        'clave': 'oaxaca',
        'destino': 'Oaxaca',
        'paradas': [
            {'clave': 'desviacion', 'nombre': 'Desviación', 'precio': 25},
            {'clave': 'yanhuitlan', 'nombre': 'Yanhuitlán', 'precio': 65},
            {'clave': 'nochixtlan', 'nombre': 'Nochixtlán', 'precio': 80},
            {'clave': 'oaxaca',     'nombre': 'Oaxaca',     'precio': 150},
        ],
    },
}

# Lo que se puede sacar de las paradas se calcula una sola vez, al cargar el
# modulo, para no repetirlo en cada consulta: el indice de todas las paradas
# juntas y, de cada ruta, su parada mas barata y la de la punta.
PARADAS = {}  # clave de la parada -> sus datos, con la ruta a la que pertenece
for _ruta in RUTAS.values():
    for _orden, _parada in enumerate(_ruta['paradas'], start=1):
        _parada['ruta'] = _ruta['clave']
        _parada['orden'] = _orden  # el lugar que ocupa en el camino
        PARADAS[_parada['clave']] = _parada
    _ruta['precio'] = _ruta['paradas'][-1]['precio']  # llegar hasta la punta
    _ruta['desde'] = _ruta['paradas'][0]['precio']    # la parada mas barata

# Cada ruta lleva su propio autobus: el asiento 5 del viaje a Oaxaca no es el
# asiento 5 del viaje a Tlaxiaco, aunque salgan el mismo dia. La parada solo
# dice donde se baja el pasajero y cuanto pago, no aparta otro lugar: quien se
# baja en Yolomecatl ocupa un asiento de toda la corrida a Tlaxiaco.
ESQUEMA = '''
    CREATE TABLE IF NOT EXISTS boletos (
        id           INTEGER PRIMARY KEY AUTOINCREMENT,
        pasajero     TEXT    NOT NULL,
        ruta         TEXT    NOT NULL,
        parada       TEXT    NOT NULL,
        asiento      INTEGER NOT NULL,
        fecha_viaje  TEXT    NOT NULL,
        precio       INTEGER NOT NULL,
        fecha_venta  TEXT    NOT NULL,
        UNIQUE (asiento, fecha_viaje, ruta)
    )
'''  # el UNIQUE evita vender dos veces el mismo asiento de la misma corrida

RUTA_DE_ANTES = 'oaxaca'  # los boletos que ya estaban guardados eran viajes a Oaxaca


def conectar():  # abre la base y devuelve los renglones como diccionarios
    conexion = sqlite3.connect(ARCHIVO)
    conexion.row_factory = sqlite3.Row
    return conexion


def lista_de_rutas():  # las tres rutas en orden, para los menus y las tablas
    return list(RUTAS.values())


def obtener_ruta(clave):  # los datos de una ruta, o None si la clave no existe
    return RUTAS.get(str(clave or '').strip().lower())


def nombre_de_ruta(clave):  # para mostrar "Oaxaca" donde se guardo "oaxaca"
    ruta = obtener_ruta(clave)
    return ruta['destino'] if ruta else str(clave or '')


def precio_de_ruta(clave):  # lo que cuesta llegar hasta la punta de la ruta
    ruta = obtener_ruta(clave)
    return ruta['precio'] if ruta else 0


def obtener_parada(clave, ruta=None):
    # los datos de una parada; si se da la ruta, solo la devuelve cuando la
    # parada de veras es de esa corrida
    parada = PARADAS.get(str(clave or '').strip().lower())
    if parada and ruta and parada['ruta'] != str(ruta or '').strip().lower():
        return None
    return parada


def nombre_de_parada(clave):  # para mostrar "Yolomécatl" donde se guardo "yolomecatl"
    parada = obtener_parada(clave)
    return parada['nombre'] if parada else str(clave or '')


def precio_de_parada(clave):  # lo que se cobra de Teposcolula hasta esa parada
    parada = obtener_parada(clave)
    return parada['precio'] if parada else 0


def columnas_de_la_tabla(conexion):  # vacio si la tabla todavia no existe
    return [renglon['name'] for renglon in conexion.execute('PRAGMA table_info(boletos)')]


def crear_tabla():  # se llama al arrancar; si la tabla ya esta al dia no hace nada
    with conectar() as conexion:
        columnas = columnas_de_la_tabla(conexion)
        if not columnas:  # no habia base: se crea ya con todo
            conexion.execute(ESQUEMA)
            return
        if 'ruta' not in columnas:  # la base es de antes de que hubiera rutas
            agregar_las_rutas(conexion)
            columnas = columnas_de_la_tabla(conexion)
        if 'parada' not in columnas:  # y de antes de los puntos intermedios
            agregar_las_paradas(conexion)


def agregar_las_rutas(conexion):
    # La tabla vieja no sabia de rutas ni de precios y su UNIQUE era solo
    # (asiento, fecha_viaje), que ya no sirve: hay que copiarla a una nueva.
    ruta = RUTAS[RUTA_DE_ANTES]
    conexion.execute('ALTER TABLE boletos RENAME TO boletos_sin_ruta')
    conexion.execute(ESQUEMA)
    conexion.execute(
        'INSERT INTO boletos (id, pasajero, ruta, parada, asiento, fecha_viaje, precio, fecha_venta) '
        'SELECT id, pasajero, ?, ?, asiento, fecha_viaje, ?, fecha_venta FROM boletos_sin_ruta',
        (ruta['clave'], ruta['paradas'][-1]['clave'], ruta['precio'])
    )
    conexion.execute('DROP TABLE boletos_sin_ruta')


def agregar_las_paradas(conexion):
    # Los boletos de antes se vendieron al precio de la punta de su ruta, asi
    # que su parada es la ultima de esa corrida. Aqui el UNIQUE no cambia, por
    # eso basta con agregar la columna en lugar de copiar la tabla.
    conexion.execute("ALTER TABLE boletos ADD COLUMN parada TEXT NOT NULL DEFAULT ''")
    for ruta in RUTAS.values():
        conexion.execute('UPDATE boletos SET parada = ? WHERE ruta = ?',
                         (ruta['paradas'][-1]['clave'], ruta['clave']))


def con_destino(renglon):  # el boleto con los nombres bonitos ya puestos
    boleto = dict(renglon)
    boleto['destino'] = nombre_de_parada(boleto.get('parada'))  # donde se baja
    boleto['corrida'] = nombre_de_ruta(boleto.get('ruta'))      # hasta donde va el autobus
    return boleto


def asientos_ocupados(fecha_viaje, ruta):  # {numero de asiento: nombre del pasajero}
    with conectar() as conexion:
        renglones = conexion.execute(
            'SELECT asiento, pasajero FROM boletos WHERE fecha_viaje = ? AND ruta = ?',
            (fecha_viaje, ruta)
        ).fetchall()
    return {renglon['asiento']: renglon['pasajero'] for renglon in renglones}


def esta_ocupado(asiento, fecha_viaje, ruta):  # se revisa antes de guardar
    return asiento in asientos_ocupados(fecha_viaje, ruta)


def guardar_boleto(pasajero, asiento, fecha_viaje, parada):
    # la parada ya dice de que ruta es y cuanto cuesta, no hay que pasarlos
    # devuelve el id del boleto, o None si alguien mas gano el asiento
    donde_baja = obtener_parada(parada)
    if not donde_baja:
        return None
    momento = datetime.now().strftime(FORMATO_FECHA)
    try:
        with conectar() as conexion:
            cursor = conexion.execute(
                'INSERT INTO boletos (pasajero, ruta, parada, asiento, fecha_viaje, precio, fecha_venta) '
                'VALUES (?, ?, ?, ?, ?, ?, ?)',
                (pasajero, donde_baja['ruta'], donde_baja['clave'], asiento,
                 fecha_viaje, donde_baja['precio'], momento)  # el precio se copia tal como se vendio
            )
            return cursor.lastrowid
    except sqlite3.IntegrityError:  # el UNIQUE lo rechazo: ya estaba vendido
        return None


def obtener_boletos():  # todos los boletos, los viajes mas cercanos primero
    with conectar() as conexion:
        renglones = conexion.execute(
            'SELECT * FROM boletos ORDER BY fecha_viaje ASC, ruta ASC, asiento ASC'
        ).fetchall()
    return [con_destino(renglon) for renglon in renglones]


def obtener_boleto(id_boleto):  # para mostrar el boleto que se acaba de vender
    with conectar() as conexion:
        renglon = conexion.execute(
            'SELECT * FROM boletos WHERE id = ?', (id_boleto,)
        ).fetchone()
    return con_destino(renglon) if renglon else None


def cancelar_boleto(id_boleto):  # libera el asiento otra vez
    with conectar() as conexion:
        cursor = conexion.execute('DELETE FROM boletos WHERE id = ?', (id_boleto,))
        return cursor.rowcount > 0


def contar_boletos():  # el numero que se muestra en la pagina de inicio
    with conectar() as conexion:
        return conexion.execute('SELECT COUNT(*) FROM boletos').fetchone()[0]


def total_cobrado():  # la suma de todos los boletos vendidos
    with conectar() as conexion:
        return conexion.execute('SELECT COALESCE(SUM(precio), 0) FROM boletos').fetchone()[0]


def boletos_por_ruta():  # {clave de la ruta: cuantos boletos lleva vendidos}
    with conectar() as conexion:
        renglones = conexion.execute(
            'SELECT ruta, COUNT(*) AS cuantos FROM boletos GROUP BY ruta'
        ).fetchall()
    cuenta = {clave: 0 for clave in RUTAS}
    for renglon in renglones:
        cuenta[renglon['ruta']] = renglon['cuantos']
    return cuenta
