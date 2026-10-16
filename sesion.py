# -*- coding: utf-8 -*-
# Todo lo del login vive aqui: la llave que firma la sesion, quien esta
# adentro, que puede hacer cada perfil y la proteccion de los formularios.
import os
import secrets
import shutil
from functools import wraps

from flask import abort, g, session
from markupsafe import Markup
from werkzeug.security import check_password_hash, generate_password_hash

import base_datos
import validaciones

NOMBRE_LLAVE = '.clave_secreta'  # vive dentro de la carpeta instance, junto a la base
# donde vivia antes: junto al codigo
LLAVE_DE_ANTES = os.path.join(os.path.dirname(os.path.abspath(__file__)), NOMBRE_LLAVE)

# Render pone sola la variable RENDER en sus servidores. Alla el disco se borra
# en cada deploy y cada vez que el servicio se duerme, y algunas cosas tienen
# que portarse distinto que en la computadora de uno.
EN_RENDER = bool(os.environ.get('RENDER'))

# Un hash de a mentiras para cuando el usuario no existe: se compara contra el
# para que tarde lo mismo que con una cuenta de verdad, y nadie pueda adivinar
# que usuarios existen por lo rapido que contesta el login.
HASH_DE_RELLENO = generate_password_hash('relleno-que-nunca-coincide')


def llave_secreta(carpeta_instance):
    # Con esta llave se firma la cookie de la sesion: quien la conozca puede
    # hacerse pasar por cualquiera. En un servidor se pone en la variable
    # SECRET_KEY; si no esta, se guarda en un archivo de la carpeta instance
    # que se crea solo. No se inventa una nueva en cada arranque: con gunicorn
    # cada proceso tendria la suya y la sesion de uno no le serviria al otro.
    if os.environ.get('SECRET_KEY'):
        return os.environ['SECRET_KEY']
    archivo_llave = os.path.join(carpeta_instance, NOMBRE_LLAVE)
    if not os.path.exists(archivo_llave) and os.path.exists(LLAVE_DE_ANTES):
        shutil.copy2(LLAVE_DE_ANTES, archivo_llave)  # la de antes: nadie sale de su sesion
    try:
        with open(archivo_llave, encoding='utf-8') as archivo:
            llave = archivo.read().strip()
        if llave:
            return llave
    except FileNotFoundError:
        pass
    llave = secrets.token_hex(32)
    try:
        with open(archivo_llave, 'x', encoding='utf-8') as archivo:  # 'x': solo si no existe
            archivo.write(llave)
        return llave
    except FileExistsError:  # otro proceso la creo justo antes: se usa esa
        with open(archivo_llave, encoding='utf-8') as archivo:
            return archivo.read().strip()


def cifrar(contrasena):  # lo que se guarda en la base en lugar de la contrasena
    return generate_password_hash(contrasena)


def crear_admin_desde_entorno():
    # Cuando la base no tiene cuentas y estan las variables ADMIN_USUARIO y
    # ADMIN_CONTRASENA, el administrador se crea solo con esos datos.
    # Es lo que se usa en Render: alla la base se borra seguido, y si la
    # pantalla de primer arranque quedara abierta en internet, el primero que
    # llegara se haria administrador. Asi, en cada arranque el admin ya existe.
    # Devuelve un renglon para la consola (sin la contrasena), o None.
    if base_datos.contar_usuarios() > 0:
        return None
    usuario = os.environ.get('ADMIN_USUARIO', '')
    contrasena = os.environ.get('ADMIN_CONTRASENA', '')
    if not usuario and not contrasena:
        return None

    bien_usuario, usuario = validaciones.validar_usuario(usuario)
    bien_contrasena, contrasena = validaciones.validar_contrasena(contrasena, contrasena)
    bien_nombre, nombre = validaciones.validar_nombre(
        os.environ.get('ADMIN_NOMBRE') or 'Administrador')
    if not (bien_usuario and bien_contrasena and bien_nombre):
        problemas = [texto for bien, texto in ((bien_usuario, usuario),
                                               (bien_contrasena, contrasena),
                                               (bien_nombre, nombre)) if not bien]
        return 'AVISO: no se creo el administrador. ' + ' '.join(problemas)

    if base_datos.crear_usuario(usuario, nombre, cifrar(contrasena), 'admin'):
        return f'Se creo el administrador "{usuario}" con las variables de entorno.'
    return None  # otro proceso lo creo al mismo tiempo: ya existe


def comprobar_entrada(usuario, contrasena):
    # devuelve la cuenta (sin su hash) si el usuario y la contrasena coinciden
    cuenta = base_datos.buscar_para_entrar(usuario)
    if not cuenta:
        check_password_hash(HASH_DE_RELLENO, contrasena)  # se gasta el mismo tiempo
        return None
    if not check_password_hash(cuenta['contrasena'], contrasena):
        return None
    return base_datos.obtener_usuario(cuenta['id'])


def iniciar(cuenta):
    # se borra lo que hubiera antes: si alguien dejo preparada una sesion,
    # no se le hereda al que entra
    session.clear()
    session['id_usuario'] = cuenta['id']


def cerrar():
    session.clear()


def cargar_usuario():
    # En cada peticion se vuelve a leer la cuenta de la base, asi un cambio de
    # perfil o una cuenta borrada surte efecto de inmediato, sin esperar a
    # que la persona salga y vuelva a entrar.
    g.usuario = None
    id_usuario = session.get('id_usuario')
    if id_usuario:
        g.usuario = base_datos.obtener_usuario(id_usuario)
        if not g.usuario:  # la cuenta se borro mientras estaba adentro
            session.clear()


def es_admin():
    return bool(g.get('usuario')) and g.usuario['perfil'] == 'admin'


def solo_admin(vista):  # se pone encima de las rutas que el vendedor no puede abrir
    @wraps(vista)
    def envuelta(*args, **kwargs):
        if not es_admin():
            abort(403)
        return vista(*args, **kwargs)
    return envuelta


# --- Proteccion de los formularios ---
# Cada formulario POST lleva un campo escondido con un numero al azar que solo
# conoce esta sesion. Una pagina de otro sitio no lo puede leer, asi que no
# puede mandar un formulario a nombre de alguien que tenga la sesion abierta
# (por ejemplo, para cancelarle boletos sin que se de cuenta).

def token_csrf():
    if '_csrf' not in session:
        session['_csrf'] = secrets.token_urlsafe(32)
    return session['_csrf']


def campo_csrf():  # en las plantillas: {{ campo_csrf() }} dentro de cada <form method="POST">
    return Markup('<input type="hidden" name="_csrf" value="%s">') % token_csrf()


def revisar_csrf(formulario):
    enviado = formulario.get('_csrf', '')
    guardado = session.get('_csrf', '')
    return bool(enviado and guardado) and secrets.compare_digest(enviado, guardado)
