# -*- coding: utf-8 -*-
from flask import Flask, render_template, request, redirect, url_for, jsonify, Response
from datetime import date, timedelta

import base_datos   # el modulo que guarda y lee los boletos en SQLite
import validaciones  # el modulo que revisa lo que se escribio en el formulario
import corte         # el modulo que suma el corte de caja y arma su PDF

app = Flask(__name__)  # crear la instancia de la aplicacion para mostrar la pagina web


def dia_de_hoy():  # la fecha minima que acepta el calendario del formulario
    return date.today().strftime(validaciones.FORMATO_VIAJE)


def dia_maximo():  # un ano hacia adelante, igual que en validaciones.py
    return (date.today() + timedelta(days=365)).strftime(validaciones.FORMATO_VIAJE)


@app.template_filter('bonita')
def fecha_bonita(fecha):  # en las plantillas: {{ '2026-10-16'|bonita }} -> 16/10/2026
    return corte.en_letras(fecha)


@app.template_filter('pesos')
def en_pesos(cantidad):  # en las plantillas: {{ 1842|pesos }} -> $1,842
    return corte.pesos(cantidad)


def mapa_de_asientos(fecha_viaje, ruta):
    # arma la lista de asientos con su numero y si esta libre u ocupado; cada ruta
    # lleva su propio autobus, asi que se necesitan la fecha y el destino.
    # se usa tanto en la pagina como en la respuesta de /api/asientos
    ocupados = base_datos.asientos_ocupados(fecha_viaje, ruta) if fecha_viaje and ruta else {}
    asientos = []
    for numero in range(1, base_datos.TOTAL_ASIENTOS + 1):
        asientos.append({
            'numero': numero,
            'ocupado': numero in ocupados,
            'pasajero': ocupados.get(numero, ''),
        })
    return asientos


@app.route('/')  # pagina de inicio: la bienvenida y el cuadro de rutas
def index():
    return render_template('index.html',
                           vendidos=base_datos.contar_boletos(),
                           total_asientos=base_datos.TOTAL_ASIENTOS,
                           origen=base_datos.ORIGEN,
                           rutas=base_datos.lista_de_rutas(),
                           total_paradas=len(base_datos.PARADAS),
                           ventas_por_ruta=base_datos.boletos_por_ruta())


@app.route('/venta', methods=['GET', 'POST'])  # vender: ruta -> parada -> fecha -> asiento -> nombre
def venta():
    valores = {'pasajero': '', 'fecha_viaje': '', 'asiento': '', 'ruta': '', 'parada': ''}
    errores = {}

    if request.method == 'POST':
        valores, errores = validaciones.validar_venta(request.form)
        if not errores:
            id_boleto = base_datos.guardar_boleto(
                valores['pasajero'], valores['asiento'],
                valores['fecha_viaje'], valores['parada'])
            if id_boleto:  # se vendio: se pasa a la lista con el boleto resaltado
                return redirect(url_for('boletos', nuevo=id_boleto))
            # si llego hasta aqui, alguien mas aparto el asiento mientras se llenaba el nombre
            errores['asiento'] = 'Ese asiento se acaba de vender, elige otro.'  # alguien mas lo aparto

    # si hubo errores se regresa el formulario con lo que ya se habia escogido
    fecha_elegida = valores['fecha_viaje'] if not errores.get('fecha_viaje') else ''
    ruta_elegida = valores['ruta'] if not errores.get('ruta') else ''
    return render_template('venta.html', valores=valores, errores=errores,
                           asientos=mapa_de_asientos(fecha_elegida, ruta_elegida),
                           filas=base_datos.FILAS, por_fila=base_datos.POR_FILA,
                           total_asientos=base_datos.TOTAL_ASIENTOS,
                           origen=base_datos.ORIGEN,
                           rutas=base_datos.lista_de_rutas(),
                           hoy=dia_de_hoy(), maximo=dia_maximo())


@app.route('/boletos')  # boletos vendidos: la tabla con todo lo que se ha vendido
def boletos():
    nuevo = request.args.get('nuevo', type=int)  # el boleto que se acaba de vender
    return render_template('boletos.html', boletos=base_datos.obtener_boletos(),
                           nuevo=base_datos.obtener_boleto(nuevo) if nuevo else None,
                           origen=base_datos.ORIGEN,
                           total=base_datos.total_cobrado())


@app.route('/cancelar/<int:id_boleto>', methods=['POST'])  # el boton de cada renglon
def cancelar(id_boleto):
    base_datos.cancelar_boleto(id_boleto)  # al borrarlo, el asiento vuelve a quedar libre
    return redirect(url_for('boletos'))


@app.route('/corte')  # corte de caja: lo vendido en un dia, un periodo o todo
def corte_de_caja():
    filtros, errores = validaciones.validar_corte(request.args)
    return render_template('corte.html', filtros=filtros, errores=errores,
                           reporte=corte.armar(filtros) if not errores else None,
                           rutas=base_datos.lista_de_rutas(),
                           origen=base_datos.ORIGEN, hoy=dia_de_hoy())


@app.route('/corte.pdf')  # el mismo corte, para descargar
def corte_pdf():
    filtros, errores = validaciones.validar_corte(request.args)
    if errores:  # con filtros malos se regresa a la pagina, que ahi se ven los avisos
        return redirect(url_for('corte_de_caja', **request.args.to_dict()))

    reporte = corte.armar(filtros)
    return Response(corte.hacer_pdf(reporte), mimetype='application/pdf', headers={
        'Content-Disposition': 'attachment; filename=' + corte.nombre_del_archivo(reporte),
    })


@app.route('/api/asientos')  # la venta la llama al elegir el destino y la fecha
def api_asientos():
    ok, ruta = validaciones.validar_ruta(request.args.get('ruta'))
    if not ok:
        return jsonify({'ok': False, 'error': ruta, 'asientos': []}), 400
    ok, fecha = validaciones.validar_fecha(request.args.get('fecha'))
    if not ok:
        return jsonify({'ok': False, 'error': fecha, 'asientos': []}), 400
    asientos = mapa_de_asientos(fecha, ruta)
    libres = sum(1 for asiento in asientos if not asiento['ocupado'])
    return jsonify({'ok': True, 'fecha': fecha, 'ruta': ruta,
                    'destino': base_datos.nombre_de_ruta(ruta),
                    'asientos': asientos, 'libres': libres})


base_datos.crear_tabla()  # si el archivo boletos.db no existe, se crea al arrancar

if __name__ == '__main__':  # verifica si el archivo se esta ejecutando
    app.run(host='0.0.0.0', port=5000, debug=True)
