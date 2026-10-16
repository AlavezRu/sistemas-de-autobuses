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


def validar_dia(texto):
    # Una fecha cualquiera, sin el limite de validar_fecha: el corte de caja
    # mira hacia atras, a dias que ya pasaron.
    texto = limpiar(texto)
    if not texto:
        return False, 'Escribe la fecha.'
    try:
        dia = datetime.strptime(texto, FORMATO_VIAJE).date()
    except ValueError:
        return False, 'La fecha no tiene un formato valido.'
    return True, dia.strftime(FORMATO_VIAJE)


MODOS_DEL_CORTE = ('todo', 'dia', 'periodo')


def validar_corte(datos):
    # Los filtros del corte de caja: que tanto se mira (todo, un dia o un
    # periodo), las fechas y la ruta. Devuelve (filtros, errores).
    modo = limpiar(datos.get('modo')).lower()
    if modo not in MODOS_DEL_CORTE:
        modo = 'todo'  # lo que no se entiende se trata como "todo"
    filtros = {'modo': modo, 'dia': '', 'desde': '', 'hasta': '', 'ruta': ''}
    errores = {}

    clave = limpiar(datos.get('ruta')).lower()
    if clave and clave != 'todas':  # vacio o "todas" es sin filtro de ruta
        ok, resultado = validar_ruta(clave)
        filtros['ruta'] = resultado if ok else clave
        if not ok:
            errores['ruta'] = resultado

    if modo == 'dia':
        ok, resultado = validar_dia(datos.get('dia'))
        filtros['dia'] = resultado if ok else limpiar(datos.get('dia'))
        if not ok:
            errores['dia'] = resultado

    if modo == 'periodo':
        bien_desde, desde = validar_dia(datos.get('desde'))
        filtros['desde'] = desde if bien_desde else limpiar(datos.get('desde'))
        if not bien_desde:
            errores['desde'] = desde

        bien_hasta, hasta = validar_dia(datos.get('hasta'))
        filtros['hasta'] = hasta if bien_hasta else limpiar(datos.get('hasta'))
        if not bien_hasta:
            errores['hasta'] = hasta

        if bien_desde and bien_hasta and desde > hasta:
            errores['hasta'] = 'La fecha de hasta no puede ser antes que la de desde.'

    return filtros, errores


def validar_ruta(clave):
    clave = limpiar(clave).lower()
    if not clave:
        return False, 'Elige la ruta del viaje.'
    if not base_datos.obtener_ruta(clave):
        return False, f'Esa ruta no esta entre las que salen de {base_datos.ORIGEN}.'
    return True, clave


def validar_parada(clave, ruta):
    clave = limpiar(clave).lower()
    if not clave:
        return False, 'Elige en que punto te bajas.'
    if not base_datos.obtener_parada(clave):
        return False, 'Ese punto no esta en las rutas de la linea.'
    if not base_datos.obtener_parada(clave, ruta):
        return False, (f'{base_datos.nombre_de_parada(clave)} no esta en el camino '
                       f'a {base_datos.nombre_de_ruta(ruta)}.')
    return True, clave


def validar_asiento(asiento):
    try:
        numero = int(str(asiento).strip())
    except (TypeError, ValueError):
        return False, 'Selecciona un asiento en el mapa del autobus.'
    if not 1 <= numero <= base_datos.TOTAL_ASIENTOS:
        return False, f'El asiento debe estar entre 1 y {base_datos.TOTAL_ASIENTOS}.'
    return True, numero


def validar_venta(datos):
    # revisa todos los campos de una vez y devuelve (valores limpios, errores por campo)
    valores = {}
    errores = {}

    ok, resultado = validar_ruta(datos.get('ruta'))
    valores['ruta'] = resultado if ok else limpiar(datos.get('ruta'))
    if not ok:
        errores['ruta'] = resultado

    ok, resultado = validar_parada(datos.get('parada'), valores['ruta'])
    valores['parada'] = resultado if ok else limpiar(datos.get('parada'))
    if not ok and 'ruta' not in errores:  # si la ruta esta mal, ese es el error que importa
        errores['parada'] = resultado

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

    # el asiento ocupado solo se puede revisar si la ruta, la fecha y el asiento son validos
    if not errores and base_datos.esta_ocupado(
            valores['asiento'], valores['fecha_viaje'], valores['ruta']):
        errores['asiento'] = (f'El asiento {valores["asiento"]} ya esta vendido '
                              f'para el viaje a {base_datos.nombre_de_ruta(valores["ruta"])} de ese dia.')

    return valores, errores
