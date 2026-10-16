# -*- coding: utf-8 -*-
from flask import (Flask, render_template, request, redirect, url_for, jsonify, Response,
                   abort, flash, g)
from datetime import date, timedelta
import os

import base_datos   # el modulo que guarda y lee los boletos en SQLite
import validaciones  # el modulo que revisa lo que se escribio en el formulario
import corte         # el modulo que suma el corte de caja y arma su PDF
import sesion        # el modulo del login: quien esta adentro y que puede hacer

app = Flask(__name__)  # crear la instancia de la aplicacion para mostrar la pagina web

app.secret_key = sesion.llave_secreta()  # firma la cookie de la sesion
app.config.update(
    SESSION_COOKIE_HTTPONLY=True,   # el JavaScript de la pagina no puede leer la cookie
    SESSION_COOKIE_SAMESITE='Lax',  # otro sitio no puede mandar formularios con ella
    # en Render todo va por https: la cookie no viaja nunca por una conexion sin cifrar.
    # En la computadora de uno se queda apagado, porque localhost va por http
    SESSION_COOKIE_SECURE=sesion.EN_RENDER,
)

# lo que todas las plantillas pueden usar sin que se les pase a mano
app.jinja_env.globals.update(campo_csrf=sesion.campo_csrf, perfiles=base_datos.PERFILES)

# las paginas que se pueden abrir sin haber entrado
PUBLICAS = {'entrar', 'primer_arranque', 'static'}


@app.before_request
def antes_de_cada_pagina():
    # El portero: corre antes de cualquier ruta, asi ninguna se queda sin revisar
    sesion.cargar_usuario()

    if base_datos.contar_usuarios() == 0:
        # primer arranque: mientras no haya ninguna cuenta, todo lleva a crear el admin
        if request.endpoint not in ('primer_arranque', 'static'):
            return redirect(url_for('primer_arranque'))
    elif not g.usuario and request.endpoint not in PUBLICAS:
        if request.path.startswith('/api/'):  # al JavaScript se le contesta en JSON
            return jsonify({'ok': False, 'error': 'La sesion se cerro, vuelve a entrar.',
                            'asientos': []}), 401
        return redirect(url_for('entrar'))

    if request.method == 'POST' and not sesion.revisar_csrf(request.form):
        abort(400)


@app.errorhandler(400)
def peticion_mala(error):
    return render_template('aviso.html', titulo='No se pudo mandar el formulario',
                           mensaje='La pagina estuvo abierta mucho tiempo o la sesion cambio. '
                                   'Regresa, recarga la pagina y vuelve a intentarlo.'), 400


@app.errorhandler(403)
def sin_permiso(error):
    return render_template('aviso.html', titulo='Esta parte es solo para el administrador',
                           mensaje='Tu cuenta es de vendedor: puedes vender y cancelar boletos.'), 403


@app.errorhandler(404)
def no_existe(error):
    return render_template('aviso.html', titulo='No se encontro',
                           mensaje='Esa pagina, ese boleto o esa cuenta no existe.'), 404


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
                valores['fecha_viaje'], valores['parada'],
                vendedor=g.usuario['usuario'])  # queda anotado quien lo vendio
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
                           editado=request.args.get('editado', type=int),  # el que se corrigio
                           origen=base_datos.ORIGEN,
                           total=base_datos.total_cobrado())


@app.route('/cancelar/<int:id_boleto>', methods=['POST'])  # el boton de cada renglon
def cancelar(id_boleto):
    # los dos perfiles pueden cancelar cualquier boleto, lo haya vendido quien sea
    boleto = base_datos.obtener_boleto(id_boleto)
    if boleto and base_datos.cancelar_boleto(id_boleto):  # el asiento vuelve a quedar libre
        flash(f'Se cancelo el boleto {boleto["id"]:04d} de {boleto["pasajero"]}.', 'listo')
    return redirect(url_for('boletos'))


@app.route('/boletos/<int:id_boleto>/editar', methods=['GET', 'POST'])
@sesion.solo_admin
def editar_boleto(id_boleto):  # el admin corrige un boleto que ya se vendio
    boleto = base_datos.obtener_boleto(id_boleto)
    if not boleto:
        abort(404)

    valores = {'pasajero': boleto['pasajero'], 'parada': boleto['parada'],
               'fecha_viaje': boleto['fecha_viaje'], 'asiento': boleto['asiento']}
    errores = {}
    if request.method == 'POST':
        valores, errores = validaciones.validar_edicion_de_boleto(request.form, boleto)
        if not errores:
            if base_datos.actualizar_boleto(id_boleto, valores['pasajero'], valores['parada'],
                                            valores['fecha_viaje'], valores['asiento']):
                flash(f'Se corrigio el boleto {id_boleto:04d}.', 'listo')
                return redirect(url_for('boletos', editado=id_boleto))
            errores['asiento'] = 'Ese asiento se acaba de vender, elige otro.'

    return render_template('boleto_editar.html', boleto=boleto, valores=valores,
                           errores=errores, rutas=base_datos.lista_de_rutas(),
                           origen=base_datos.ORIGEN, total_asientos=base_datos.TOTAL_ASIENTOS,
                           hoy=dia_de_hoy(), maximo=dia_maximo())


@app.route('/corte')  # corte de caja: lo vendido en un dia, un periodo o todo
@sesion.solo_admin
def corte_de_caja():
    filtros, errores = validaciones.validar_corte(request.args)
    return render_template('corte.html', filtros=filtros, errores=errores,
                           reporte=corte.armar(filtros) if not errores else None,
                           rutas=base_datos.lista_de_rutas(),
                           origen=base_datos.ORIGEN, hoy=dia_de_hoy())


@app.route('/corte.pdf')  # el mismo corte, para descargar
@sesion.solo_admin
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


# --- El login ---

@app.route('/primer-arranque', methods=['GET', 'POST'])
def primer_arranque():  # solo existe mientras la base no tiene ninguna cuenta
    if base_datos.contar_usuarios() > 0:
        return redirect(url_for('entrar'))
    if sesion.EN_RENDER:
        # En internet no se ofrece el formulario: el primero que llegara se haria
        # administrador. Alla el admin sale de las variables de entorno.
        return render_template('aviso.html', titulo='Falta configurar al administrador',
                               mensaje='En Render el administrador se crea con las variables de '
                                       'entorno ADMIN_USUARIO y ADMIN_CONTRASENA. Agregalas en '
                                       'Environment y vuelve a desplegar.',
                               regresar=False), 503

    valores, errores = {'usuario': '', 'nombre': ''}, {}
    if request.method == 'POST':
        valores, errores = validaciones.validar_cuenta_nueva(request.form, con_perfil=False)
        if not errores:
            id_usuario = base_datos.crear_usuario(valores['usuario'], valores['nombre'],
                                                  sesion.cifrar(valores['contrasena']), 'admin')
            if id_usuario:  # se entra de una vez con la cuenta recien hecha
                sesion.iniciar(base_datos.obtener_usuario(id_usuario))
                flash(f'Listo, {valores["nombre"]}: ya eres el administrador.', 'listo')
                return redirect(url_for('index'))
            errores['usuario'] = 'Ya hay una cuenta con ese usuario.'
    return render_template('primer_arranque.html', valores=valores, errores=errores,
                           minimo=validaciones.MINIMO_CONTRASENA)


@app.route('/entrar', methods=['GET', 'POST'])
def entrar():
    if g.usuario:  # ya estaba adentro
        return redirect(url_for('index'))

    usuario, error = '', ''
    if request.method == 'POST':
        usuario = validaciones.limpiar(request.form.get('usuario')).lower()
        cuenta = sesion.comprobar_entrada(usuario, request.form.get('contrasena', ''))
        if cuenta:
            sesion.iniciar(cuenta)
            return redirect(url_for('index'))
        # el mismo aviso para usuario y contrasena: no se le dice cual de los dos fallo
        error = 'El usuario o la contrasena no coinciden.'
    return render_template('entrar.html', usuario=usuario, error=error)


@app.route('/salir', methods=['POST'])
def salir():
    sesion.cerrar()
    return redirect(url_for('entrar'))


# --- Las cuentas: altas, bajas, cambios y la lista; solo el admin ---

@app.route('/usuarios', methods=['GET', 'POST'])
@sesion.solo_admin
def usuarios():  # la lista de cuentas y el formulario para dar de alta una nueva
    valores, errores = {'usuario': '', 'nombre': '', 'perfil': 'vendedor'}, {}
    if request.method == 'POST':
        valores, errores = validaciones.validar_cuenta_nueva(request.form)
        if not errores:
            if base_datos.crear_usuario(valores['usuario'], valores['nombre'],
                                        sesion.cifrar(valores['contrasena']), valores['perfil']):
                flash(f'Se creo la cuenta de {valores["nombre"]} ({valores["usuario"]}).', 'listo')
                return redirect(url_for('usuarios'))
            errores['usuario'] = 'Ya hay una cuenta con ese usuario.'
    return render_template('usuarios.html', usuarios=base_datos.lista_de_usuarios(),
                           valores=valores, errores=errores,
                           minimo=validaciones.MINIMO_CONTRASENA)


@app.route('/usuarios/<int:id_usuario>/editar', methods=['GET', 'POST'])
@sesion.solo_admin
def editar_usuario(id_usuario):
    cuenta = base_datos.obtener_usuario(id_usuario)
    if not cuenta:
        abort(404)

    valores, errores = {'nombre': cuenta['nombre'], 'perfil': cuenta['perfil']}, {}
    if request.method == 'POST':
        valores, errores = validaciones.validar_edicion_de_cuenta(request.form)
        # la linea nunca se puede quedar sin nadie que la administre
        if (not errores and cuenta['perfil'] == 'admin' and valores['perfil'] != 'admin'
                and base_datos.contar_admins() <= 1):
            errores['perfil'] = 'Es el unico administrador: no se le puede quitar el perfil.'
        if not errores:
            nueva = sesion.cifrar(valores['contrasena']) if valores['contrasena'] else None
            base_datos.actualizar_usuario(id_usuario, valores['nombre'], valores['perfil'], nueva)
            flash(f'Se guardaron los cambios de {valores["nombre"]}.', 'listo')
            if id_usuario == g.usuario['id'] and valores['perfil'] != 'admin':
                return redirect(url_for('index'))  # se quito el admin a si mismo: ya no entra aqui
            return redirect(url_for('usuarios'))
    return render_template('usuario_editar.html', cuenta=cuenta, valores=valores,
                           errores=errores, minimo=validaciones.MINIMO_CONTRASENA)


@app.route('/usuarios/<int:id_usuario>/borrar', methods=['POST'])
@sesion.solo_admin
def borrar_usuario(id_usuario):
    cuenta = base_datos.obtener_usuario(id_usuario)
    if not cuenta:
        abort(404)
    if cuenta['id'] == g.usuario['id']:
        flash('No puedes borrar tu propia cuenta mientras estas adentro.', 'error')
    elif cuenta['perfil'] == 'admin' and base_datos.contar_admins() <= 1:
        flash('Es el unico administrador: no se puede borrar.', 'error')
    else:
        base_datos.borrar_usuario(id_usuario)  # sus boletos se quedan, con su nombre
        flash(f'Se borro la cuenta de {cuenta["nombre"]} ({cuenta["usuario"]}).', 'listo')
    return redirect(url_for('usuarios'))


base_datos.crear_tabla()  # si el archivo boletos.db no existe, se crea al arrancar

# Lo que se avisa al arrancar sale en la consola, y en Render en sus Logs
aviso_del_admin = sesion.crear_admin_desde_entorno()
if aviso_del_admin:
    print(aviso_del_admin, flush=True)
if sesion.EN_RENDER and not os.environ.get('SECRET_KEY'):
    print('AVISO: falta la variable SECRET_KEY. Sin ella, todos salen de su sesion '
          'en cada deploy y cada vez que el servicio se duerme.', flush=True)

if __name__ == '__main__':  # verifica si el archivo se esta ejecutando
    app.run(host='0.0.0.0', port=5000, debug=True)
