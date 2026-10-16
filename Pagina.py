# -*- coding: utf-8 -*-
from flask import Flask, render_template, request, redirect, url_for, jsonify
from datetime import date, timedelta

import base_datos   # el modulo que guarda y lee los boletos en SQLite
import validaciones  # el modulo que revisa lo que se escribio en el formulario

app = Flask(__name__)  # crear la instancia de la aplicacion para mostrar la pagina web


def dia_de_hoy():  # la fecha minima que acepta el calendario del formulario
    return date.today().strftime(validaciones.FORMATO_VIAJE)


def dia_maximo():  # un ano hacia adelante, igual que en validaciones.py
    return (date.today() + timedelta(days=365)).strftime(validaciones.FORMATO_VIAJE)


def mapa_de_asientos(fecha_viaje):
    # arma la lista de asientos con su numero y si esta libre u ocupado;
    # se usa tanto en la pagina como en la respuesta de /api/asientos
    ocupados = base_datos.asientos_ocupados(fecha_viaje) if fecha_viaje else {}
    asientos = []
    for numero in range(1, base_datos.TOTAL_ASIENTOS + 1):
        asientos.append({
            'numero': numero,
            'ocupado': numero in ocupados,
            'pasajero': ocupados.get(numero, ''),
        })
    return asientos


@app.route('/')  # pagina de inicio: la bienvenida
def index():
    vendidos = base_datos.contar_boletos()
    return render_template('index.html', vendidos=vendidos,
                           total_asientos=base_datos.TOTAL_ASIENTOS)


@app.route('/venta', methods=['GET', 'POST'])  # vender boleto: fecha -> asiento -> nombre
def venta():
    valores = {'pasajero': '', 'fecha_viaje': '', 'asiento': ''}
    errores = {}

    if request.method == 'POST':
        valores, errores = validaciones.validar_venta(request.form)
        if not errores:
            id_boleto = base_datos.guardar_boleto(
                valores['pasajero'], valores['asiento'], valores['fecha_viaje'])
            if id_boleto:  # se vendio: se pasa a la lista con el boleto resaltado
                return redirect(url_for('boletos', nuevo=id_boleto))
            # si llego hasta aqui, alguien mas aparto el asiento mientras se llenaba el nombre
            errores['asiento'] = 'Ese asiento se acaba de vender, elige otro.'

    # si hubo errores se regresa el formulario con la fecha y el asiento que ya se habian escogido
    fecha_elegida = valores['fecha_viaje'] if not errores.get('fecha_viaje') else ''
    return render_template('venta.html', valores=valores, errores=errores,
                           asientos=mapa_de_asientos(fecha_elegida),
                           filas=base_datos.FILAS, por_fila=base_datos.POR_FILA,
                           total_asientos=base_datos.TOTAL_ASIENTOS,
                           hoy=dia_de_hoy(), maximo=dia_maximo())


@app.route('/boletos')  # boletos vendidos: la tabla con todo lo que se ha vendido
def boletos():
    nuevo = request.args.get('nuevo', type=int)  # el boleto que se acaba de vender
    return render_template('boletos.html', boletos=base_datos.obtener_boletos(),
                           nuevo=base_datos.obtener_boleto(nuevo) if nuevo else None)


@app.route('/cancelar/<int:id_boleto>', methods=['POST'])  # el boton de cada renglon
def cancelar(id_boleto):
    base_datos.cancelar_boleto(id_boleto)  # al borrarlo, el asiento vuelve a quedar libre
    return redirect(url_for('boletos'))


@app.route('/api/asientos')  # la pagina de venta la llama cuando se elige una fecha
def api_asientos():
    ok, resultado = validaciones.validar_fecha(request.args.get('fecha'))
    if not ok:
        return jsonify({'ok': False, 'error': resultado, 'asientos': []}), 400
    asientos = mapa_de_asientos(resultado)
    libres = sum(1 for asiento in asientos if not asiento['ocupado'])
    return jsonify({'ok': True, 'fecha': resultado, 'asientos': asientos, 'libres': libres})


base_datos.crear_tabla()  # si el archivo boletos.db no existe, se crea al arrancar

if __name__ == '__main__':  # verifica si el archivo se esta ejecutando
    app.run(host='0.0.0.0', port=5000, debug=True)
