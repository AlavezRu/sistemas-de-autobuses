# -*- coding: utf-8 -*-
# Aqui se revisa lo que el usuario escribio antes de que llegue a la base de datos.
# Cada funcion devuelve (True, valor limpio) o (False, el mensaje del error).
import re
from datetime import date, datetime

import base_datos

FORMATO_VIAJE = '%Y-%m-%d'  # el que manda el <input type="date"> del formulario

# letras (con acentos y ñ), espacios, puntos y apostrofes; nada de numeros ni simbolos raros
LETRAS = re.compile(r"^[A-Za-zÁÉÍÓÚÜÑáéíóúüñ' .]+$")


def limpiar(texto):  # quita los espacios de las orillas y los dobles de en medio
    return ' '.join(str(texto or '').split())


def validar_pasajero(nombre):
    nombre = limpiar(nombre)
    if not nombre:
        return False, 'Escribe el nombre del pasajero.'
    if len(nombre) < 3:
        return False, 'El nombre debe tener al menos 3 letras.'
    if len(nombre) > 60:
        return False, 'El nombre es demasiado largo (maximo 60 letras).'
    if not LETRAS.match(nombre):
        return False, 'El nombre solo puede llevar letras y espacios.'
    return True, nombre.title()  # se guarda con la primera letra de cada palabra en mayuscula


def validar_fecha(fecha_viaje):
    fecha_viaje = limpiar(fecha_viaje)
    if not fecha_viaje:
        return False, 'Elige la fecha del viaje.'
    try:
        dia = datetime.strptime(fecha_viaje, FORMATO_VIAJE).date()
    except ValueError:
        return False, 'La fecha no tiene un formato valido.'
    if dia < date.today():
        return False, 'No se pueden vender boletos para una fecha que ya paso.'
    if (dia - date.today()).days > 365:
        return False, 'Solo se venden boletos para el proximo ano.'
    return True, dia.strftime(FORMATO_VIAJE)


def validar_asiento(asiento):
    try:
        numero = int(str(asiento).strip())
    except (TypeError, ValueError):
        return False, 'Selecciona un asiento en el mapa del autobus.'
    if not 1 <= numero <= base_datos.TOTAL_ASIENTOS:
        return False, f'El asiento debe estar entre 1 y {base_datos.TOTAL_ASIENTOS}.'
    return True, numero


def validar_venta(datos):
    # revisa los tres campos de una vez y devuelve (valores limpios, errores por campo)
    valores = {}
    errores = {}

    ok, resultado = validar_pasajero(datos.get('pasajero'))
    valores['pasajero'] = resultado if ok else limpiar(datos.get('pasajero'))
    if not ok:
        errores['pasajero'] = resultado

    ok, resultado = validar_fecha(datos.get('fecha_viaje'))
    valores['fecha_viaje'] = resultado if ok else limpiar(datos.get('fecha_viaje'))
    if not ok:
        errores['fecha_viaje'] = resultado

    ok, resultado = validar_asiento(datos.get('asiento'))
    valores['asiento'] = resultado if ok else limpiar(datos.get('asiento'))
    if not ok:
        errores['asiento'] = resultado

    # el asiento ocupado solo se puede revisar si la fecha y el asiento son validos
    if not errores and base_datos.esta_ocupado(valores['asiento'], valores['fecha_viaje']):
        errores['asiento'] = f'El asiento {valores["asiento"]} ya esta vendido para ese dia.'

    return valores, errores
