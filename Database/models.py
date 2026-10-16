# -*- coding: utf-8 -*-
# Las tablas de la base, escritas como clases de Flask-SQLAlchemy: cada clase
# es una tabla y cada atributo es una columna. SQLAlchemy arma el SQL, asi que
# el mismo codigo sirve con SQLite (en la computadora) o con PostgreSQL (en un
# servidor), nada mas cambiando la direccion de la base.
from flask_sqlalchemy import SQLAlchemy

# Inicializamos la base de datos; se conecta con la aplicacion en Pagina.py
db = SQLAlchemy()


# Clase Boleto ---> tabla boletos
class Boleto(db.Model):
    # Cada ruta lleva su propio autobus: el asiento 5 del viaje a Oaxaca no es el
    # asiento 5 del viaje a Tlaxiaco, aunque salgan el mismo dia. La parada solo
    # dice donde se baja el pasajero y cuanto pago, no aparta otro lugar: quien se
    # baja en Yolomecatl ocupa un asiento de toda la corrida a Tlaxiaco.
    __tablename__ = 'boletos'
    __table_args__ = (
        # evita vender dos veces el mismo asiento de la misma corrida
        db.UniqueConstraint('asiento', 'fecha_viaje', 'ruta', name='un_asiento_por_corrida'),
        # en SQLite, que un folio cancelado no se le vuelva a dar a otro boleto
        {'sqlite_autoincrement': True},
    )

    id = db.Column(db.Integer, primary_key=True)            # el folio
    pasajero = db.Column(db.String(60), nullable=False)
    ruta = db.Column(db.String(30), nullable=False)         # la clave: 'tlaxiaco'
    parada = db.Column(db.String(30), nullable=False)       # la clave: 'yolomecatl'
    asiento = db.Column(db.Integer, nullable=False)
    fecha_viaje = db.Column(db.String(10), nullable=False)  # 2026-10-16
    precio = db.Column(db.Integer, nullable=False)          # lo que se cobro, tal cual
    fecha_venta = db.Column(db.String(19), nullable=False)  # 16/10/2026 13:44:00
    # La cuenta que lo vendio. Se guarda el nombre de usuario y no el id, para
    # que el boleto siga diciendo quien lo vendio aunque esa cuenta se borre.
    # Los boletos de antes del login lo tienen vacio.
    vendedor = db.Column(db.String(20), nullable=False, default='', server_default='')

    def como_diccionario(self):  # lo que usan las plantillas, el corte y el PDF
        return {
            'id': self.id, 'pasajero': self.pasajero, 'ruta': self.ruta,
            'parada': self.parada, 'asiento': self.asiento,
            'fecha_viaje': self.fecha_viaje, 'precio': self.precio,
            'fecha_venta': self.fecha_venta, 'vendedor': self.vendedor,
        }

    # mostrar la informacion del boleto
    def __repr__(self):
        return f'<Boleto {self.id:04d} - {self.pasajero} - asiento {self.asiento}>'


# Clase Usuario ---> tabla usuarios
class Usuario(db.Model):
    # La contrasena nunca se guarda tal cual: se guarda su hash (werkzeug), y al
    # entrar se compara contra ese hash.
    __tablename__ = 'usuarios'
    __table_args__ = (
        db.CheckConstraint("perfil IN ('admin', 'vendedor')", name='perfil_valido'),
        {'sqlite_autoincrement': True},
    )

    id = db.Column(db.Integer, primary_key=True)
    usuario = db.Column(db.String(20), nullable=False, unique=True)  # con el que se entra
    nombre = db.Column(db.String(60), nullable=False)
    contrasena = db.Column(db.String(255), nullable=False)           # el hash, no la contrasena
    perfil = db.Column(db.String(10), nullable=False)                # 'admin' o 'vendedor'
    creado = db.Column(db.String(19), nullable=False)

    def como_diccionario(self, con_contrasena=False):
        # Para mostrar una cuenta NUNCA se manda el hash; solo el login lo pide,
        # porque es el que lo compara.
        datos = {'id': self.id, 'usuario': self.usuario, 'nombre': self.nombre,
                 'perfil': self.perfil, 'creado': self.creado}
        if con_contrasena:
            datos['contrasena'] = self.contrasena
        return datos

    # mostrar la informacion de la cuenta (sin la contrasena)
    def __repr__(self):
        return f'<Usuario {self.usuario} - {self.perfil}>'
