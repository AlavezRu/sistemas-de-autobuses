# -*- coding: utf-8 -*-
# Todo lo que tiene que ver con la base de datos SQLite vive aqui, para que
# Pagina.py solo pida los datos y no sepa como estan guardados.
import os
import sqlite3
from datetime import datetime

ARCHIVO = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'boletos.db')

FILAS = 10       # el autobus tiene 10 filas
POR_FILA = 4     # dos asientos, el pasillo, y otros dos
TOTAL_ASIENTOS = FILAS * POR_FILA  # 40 lugares en total

FORMATO_FECHA = '%d/%m/%Y %H:%M:%S'  # como se guarda el momento de la venta


def conectar():  # abre la base y devuelve los renglones como diccionarios
    conexion = sqlite3.connect(ARCHIVO)
    conexion.row_factory = sqlite3.Row
    return conexion


def crear_tabla():  # se llama al arrancar; si la tabla ya existe no hace nada
    with conectar() as conexion:
        conexion.execute('''
            CREATE TABLE IF NOT EXISTS boletos (
                id           INTEGER PRIMARY KEY AUTOINCREMENT,
                pasajero     TEXT    NOT NULL,
                asiento      INTEGER NOT NULL,
                fecha_viaje  TEXT    NOT NULL,
                fecha_venta  TEXT    NOT NULL,
                UNIQUE (asiento, fecha_viaje)
            )
        ''')  # el UNIQUE evita vender dos veces el mismo asiento del mismo dia


def asientos_ocupados(fecha_viaje):  # {numero de asiento: nombre del pasajero}
    with conectar() as conexion:
        renglones = conexion.execute(
            'SELECT asiento, pasajero FROM boletos WHERE fecha_viaje = ?',
            (fecha_viaje,)
        ).fetchall()
    return {renglon['asiento']: renglon['pasajero'] for renglon in renglones}


def esta_ocupado(asiento, fecha_viaje):  # se revisa antes de guardar
    return asiento in asientos_ocupados(fecha_viaje)


def guardar_boleto(pasajero, asiento, fecha_viaje):
    # devuelve el id del boleto, o None si alguien mas gano el asiento
    momento = datetime.now().strftime(FORMATO_FECHA)
    try:
        with conectar() as conexion:
            cursor = conexion.execute(
                'INSERT INTO boletos (pasajero, asiento, fecha_viaje, fecha_venta) VALUES (?, ?, ?, ?)',
                (pasajero, asiento, fecha_viaje, momento)
            )
            return cursor.lastrowid
    except sqlite3.IntegrityError:  # el UNIQUE lo rechazo: ya estaba vendido
        return None


def obtener_boletos():  # todos los boletos, los viajes mas cercanos primero
    with conectar() as conexion:
        renglones = conexion.execute(
            'SELECT * FROM boletos ORDER BY fecha_viaje ASC, asiento ASC'
        ).fetchall()
    return [dict(renglon) for renglon in renglones]


def obtener_boleto(id_boleto):  # para mostrar el boleto que se acaba de vender
    with conectar() as conexion:
        renglon = conexion.execute(
            'SELECT * FROM boletos WHERE id = ?', (id_boleto,)
        ).fetchone()
    return dict(renglon) if renglon else None


def cancelar_boleto(id_boleto):  # libera el asiento otra vez
    with conectar() as conexion:
        cursor = conexion.execute('DELETE FROM boletos WHERE id = ?', (id_boleto,))
        return cursor.rowcount > 0


def contar_boletos():  # el numero que se muestra en la pagina de inicio
    with conectar() as conexion:
        return conexion.execute('SELECT COUNT(*) FROM boletos').fetchone()[0]
