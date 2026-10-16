# -*- coding: utf-8 -*-
# Revisa lo que hay en la base sin abrir la pagina: cuenta los boletos y las
# cuentas y los enlista. Se corre con:  python verificar_db.py
import Pagina as Mi_pagina
from Database.models import Boleto, Usuario

with Mi_pagina.app.app_context():  # para hablar con la base hace falta el contexto de la app
    print('Base de datos:', Mi_pagina.app.config['SQLALCHEMY_DATABASE_URI'])

    total = Boleto.query.count()  # cuenta el total de registros en la tabla boletos
    print(f'\nTotal de boletos: {total}')
    for boleto in Boleto.query.order_by(Boleto.id).all():  # todos, por folio
        print(f'  Folio {boleto.id:04d}: {boleto.pasajero}, baja en {boleto.parada}, '
              f'asiento {boleto.asiento}, viaja el {boleto.fecha_viaje}, ${boleto.precio}, '
              f'lo vendio: {boleto.vendedor or "-"}')

    total = Usuario.query.count()  # cuenta el total de cuentas
    print(f'\nTotal de cuentas: {total}')
    for cuenta in Usuario.query.order_by(Usuario.id).all():
        print(f'  {cuenta.usuario} ({cuenta.perfil}): {cuenta.nombre}')  # sin la contrasena
