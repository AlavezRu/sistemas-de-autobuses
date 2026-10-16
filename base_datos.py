# -*- coding: utf-8 -*-
# Todo lo que tiene que ver con la base de datos vive aqui, para que Pagina.py
# solo pida los datos y no sepa como estan guardados. Las tablas estan en
# Database/models.py; aqui estan las consultas, hechas con Flask-SQLAlchemy.
# Las funciones regresan diccionarios, asi las plantillas, el corte de caja y
# el PDF no dependen de los modelos.
import os
import shutil
from datetime import datetime

from sqlalchemy import inspect
from sqlalchemy.exc import IntegrityError

from Database.models import db, Boleto, Usuario

NOMBRE_DE_LA_BASE = 'boletos.db'  # vive dentro de la carpeta instance
# donde vivia la base antes de usar Flask-SQLAlchemy: junto al codigo
BASE_DE_ANTES = os.path.join(os.path.dirname(os.path.abspath(__file__)), NOMBRE_DE_LA_BASE)

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

# Los perfiles de las cuentas y como se llaman en la pantalla
PERFILES = {'admin': 'Administrador', 'vendedor': 'Vendedor'}


# --- La conexion con la base ---

def direccion_de_la_base(carpeta_instance):
    # En la computadora: SQLite dentro de la carpeta instance. En un servidor
    # se puede usar otra base con la variable DATABASE_URL (por ejemplo un
    # PostgreSQL), sin tocar nada del codigo.
    direccion = os.environ.get('DATABASE_URL')
    if direccion:
        # Render la da como postgres://, pero SQLAlchemy 2 solo entiende postgresql://
        if direccion.startswith('postgres://'):
            direccion = 'postgresql://' + direccion[len('postgres://'):]
        return direccion
    return 'sqlite:///' + os.path.join(carpeta_instance, NOMBRE_DE_LA_BASE)


def traer_la_base_de_antes(carpeta_instance):
    # Antes la base vivia junto al codigo; ahora vive en instance. Si hay una
    # vieja y todavia no hay nueva, se COPIA (la vieja se queda de respaldo),
    # para no perder los boletos ni las cuentas. Devuelve un aviso, o None.
    if os.environ.get('DATABASE_URL'):  # con otra base, la de SQLite no importa
        return None
    nueva = os.path.join(carpeta_instance, NOMBRE_DE_LA_BASE)
    if os.path.exists(BASE_DE_ANTES) and not os.path.exists(nueva):
        shutil.copy2(BASE_DE_ANTES, nueva)
        return ('Se copio la base de antes a ' + nueva +
                '; la que estaba junto al codigo se quedo de respaldo.')
    return None


def crear_tablas():
    # Crea las tablas que falten; las que ya existen no las toca. Hay que
    # llamarla dentro de app.app_context().
    db.create_all()
    # create_all no le agrega columnas a una tabla que ya existe, asi que una
    # base de antes de las rutas, las paradas o el login no serviria: se avisa
    # claro en lugar de tronar despues con un error raro.
    columnas = {columna['name'] for columna in inspect(db.engine).get_columns('boletos')}
    faltan = {'ruta', 'parada', 'vendedor'} - columnas
    if faltan:
        raise RuntimeError('La tabla boletos es de una version vieja: le faltan las columnas '
                           + ', '.join(sorted(faltan)) + '. Borra la base para que se cree de nuevo.')


def confirmar():
    # Guarda los cambios pendientes. Si la base los rechaza por un UNIQUE (un
    # asiento o un usuario repetido), los deshace y regresa False.
    try:
        db.session.commit()
        return True
    except IntegrityError:
        db.session.rollback()
        return False


# --- Las rutas y las paradas (estan en el codigo, no en la base) ---

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


# --- Los boletos ---

# los viajes mas cercanos primero, y dentro de cada uno por ruta y asiento
EN_ORDEN = (Boleto.fecha_viaje, Boleto.ruta, Boleto.asiento)


def con_destino(boleto):  # el boleto como diccionario, con los nombres bonitos ya puestos
    datos = boleto.como_diccionario()
    datos['destino'] = nombre_de_parada(boleto.parada)  # donde se baja
    datos['corrida'] = nombre_de_ruta(boleto.ruta)      # hasta donde va el autobus
    return datos


def asientos_ocupados(fecha_viaje, ruta):  # {numero de asiento: nombre del pasajero}
    boletos = Boleto.query.filter_by(fecha_viaje=fecha_viaje, ruta=ruta).all()
    return {boleto.asiento: boleto.pasajero for boleto in boletos}


def esta_ocupado(asiento, fecha_viaje, ruta):  # se revisa antes de guardar
    return asiento in asientos_ocupados(fecha_viaje, ruta)


def guardar_boleto(pasajero, asiento, fecha_viaje, parada, vendedor=''):
    # la parada ya dice de que ruta es y cuanto cuesta, no hay que pasarlos
    # devuelve el folio del boleto, o None si alguien mas gano el asiento
    donde_baja = obtener_parada(parada)
    if not donde_baja:
        return None
    boleto = Boleto(pasajero=pasajero, ruta=donde_baja['ruta'], parada=donde_baja['clave'],
                    asiento=asiento, fecha_viaje=fecha_viaje,
                    precio=donde_baja['precio'],  # el precio se copia tal como se vendio
                    fecha_venta=datetime.now().strftime(FORMATO_FECHA), vendedor=vendedor)
    db.session.add(boleto)
    return boleto.id if confirmar() else None  # si no se guardo, el UNIQUE lo rechazo


def asiento_de_otro(asiento, fecha_viaje, ruta, id_boleto):
    # al corregir un boleto: ¿ese asiento ya lo tiene OTRO boleto de la corrida?
    otro = Boleto.query.filter(Boleto.asiento == asiento, Boleto.fecha_viaje == fecha_viaje,
                               Boleto.ruta == ruta, Boleto.id != id_boleto).first()
    return otro is not None


def actualizar_boleto(id_boleto, pasajero, parada, fecha_viaje, asiento):
    # El admin corrige un boleto ya vendido. Si cambia la parada, el precio pasa
    # a ser el de la parada nueva; si no, se queda el que se cobro.
    # Devuelve True si se guardo, False si el asiento ya era de otro boleto.
    # (Para buscar por id se usa db.session.get(): Boleto.query.get() es la forma
    # vieja y SQLAlchemy 2 avisa que ya no se use.)
    boleto = db.session.get(Boleto, id_boleto)
    donde_baja = obtener_parada(parada)
    if not boleto or not donde_baja:
        return False
    if donde_baja['clave'] != boleto.parada:
        boleto.precio = donde_baja['precio']
    boleto.pasajero = pasajero
    boleto.ruta = donde_baja['ruta']
    boleto.parada = donde_baja['clave']
    boleto.fecha_viaje = fecha_viaje
    boleto.asiento = asiento
    return confirmar()


def obtener_boletos():  # todos los boletos, los viajes mas cercanos primero
    return [con_destino(boleto) for boleto in Boleto.query.order_by(*EN_ORDEN).all()]


def obtener_boleto(id_boleto):  # para mostrar el boleto que se acaba de vender
    boleto = db.session.get(Boleto, id_boleto)
    return con_destino(boleto) if boleto else None


def cancelar_boleto(id_boleto):  # al borrarlo, el asiento vuelve a quedar libre
    boleto = db.session.get(Boleto, id_boleto)
    if not boleto:
        return False
    db.session.delete(boleto)
    db.session.commit()
    return True


def boletos_para_corte(desde=None, hasta=None, ruta=None):
    # Los boletos de un periodo, por fecha de viaje, y de una sola ruta si se
    # pide. Las fechas se guardan como 2026-10-16, asi que se comparan de
    # frente como texto y salen en orden. Lo que no se manda, no filtra.
    consulta = Boleto.query
    if desde:
        consulta = consulta.filter(Boleto.fecha_viaje >= desde)
    if hasta:
        consulta = consulta.filter(Boleto.fecha_viaje <= hasta)
    if ruta:
        consulta = consulta.filter(Boleto.ruta == ruta)
    return [con_destino(boleto) for boleto in consulta.order_by(*EN_ORDEN).all()]


def contar_boletos():  # el numero que se muestra en la pagina de inicio
    return Boleto.query.count()


def total_cobrado():  # la suma de todos los boletos vendidos
    return db.session.query(db.func.coalesce(db.func.sum(Boleto.precio), 0)).scalar()


def boletos_por_ruta():  # {clave de la ruta: cuantos boletos lleva vendidos}
    filas = db.session.query(Boleto.ruta, db.func.count(Boleto.id)).group_by(Boleto.ruta).all()
    cuenta = {clave: 0 for clave in RUTAS}
    for ruta, cuantos in filas:
        cuenta[ruta] = cuantos
    return cuenta


# --- Las cuentas de usuario ---
# Las funciones que regresan cuentas para mostrarlas NUNCA traen el hash de la
# contrasena; solo buscar_para_entrar() lo trae, porque es la que lo compara.

def contar_usuarios():  # cero quiere decir que es el primer arranque
    return Usuario.query.count()


def contar_admins():  # siempre tiene que quedar por lo menos uno
    return Usuario.query.filter_by(perfil='admin').count()


def crear_usuario(usuario, nombre, contrasena_hash, perfil):
    # devuelve el id de la cuenta, o None si ese nombre de usuario ya existe
    cuenta = Usuario(usuario=usuario, nombre=nombre, contrasena=contrasena_hash,
                     perfil=perfil, creado=datetime.now().strftime(FORMATO_FECHA))
    db.session.add(cuenta)
    return cuenta.id if confirmar() else None  # si no se guardo, ya habia una cuenta asi


def buscar_para_entrar(usuario):  # la cuenta CON su hash, solo para revisar la contrasena
    cuenta = Usuario.query.filter_by(usuario=usuario).first()
    return cuenta.como_diccionario(con_contrasena=True) if cuenta else None


def obtener_usuario(id_usuario):  # la cuenta sin su hash
    cuenta = db.session.get(Usuario, id_usuario)
    return cuenta.como_diccionario() if cuenta else None


def lista_de_usuarios():  # todas las cuentas con cuantos boletos ha vendido cada una
    filas = (db.session.query(Usuario, db.func.count(Boleto.id))
             .outerjoin(Boleto, Boleto.vendedor == Usuario.usuario)
             .group_by(Usuario.id)
             .order_by(Usuario.perfil, Usuario.usuario)  # los admin primero
             .all())
    return [dict(cuenta.como_diccionario(), vendidos=vendidos) for cuenta, vendidos in filas]


def actualizar_usuario(id_usuario, nombre, perfil, contrasena_hash=None):
    # el nombre de usuario no se cambia nunca: es lo que queda guardado en los
    # boletos que vendio. Sin contrasena nueva, se queda la de antes.
    cuenta = db.session.get(Usuario, id_usuario)
    if not cuenta:
        return False
    cuenta.nombre = nombre
    cuenta.perfil = perfil
    if contrasena_hash:
        cuenta.contrasena = contrasena_hash
    db.session.commit()
    return True


def borrar_usuario(id_usuario):  # los boletos que vendio se quedan, con su nombre
    cuenta = db.session.get(Usuario, id_usuario)
    if not cuenta:
        return False
    db.session.delete(cuenta)
    db.session.commit()
    return True
