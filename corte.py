# -*- coding: utf-8 -*-
# El corte de caja: junta los boletos de un periodo y los acomoda en el resumen
# por dia, el desglose por parada y el detalle boleto por boleto. Tambien arma
# el PDF que se descarga. El corte se agrupa por la FECHA DEL VIAJE, o sea por
# el dia en que sale el autobus, no por el dia en que se cobro el boleto.
from datetime import datetime

from fpdf import FPDF

import base_datos

FORMATO_VIAJE = '%Y-%m-%d'          # como se guardan las fechas en la base
FORMATO_BONITO = '%d/%m/%Y'         # como se ven en la pantalla y en el PDF

# El PDF usa las letras que ya trae fpdf2 (Helvetica), que solo saben de
# latin-1. Los acentos y la ñ si entran; las flechas y los guiones largos no,
# por eso aqui todo se escribe con guion normal.
COLOR_FUERTE = (90, 58, 34)
COLOR_SUAVE = (139, 107, 69)
COLOR_ACENTO = (156, 96, 52)
COLOR_FONDO = (243, 231, 213)
COLOR_BORDE = (201, 166, 124)


def periodo(filtros):  # (desde, hasta) para la consulta; None es sin limite
    if filtros['modo'] == 'dia':
        return filtros['dia'], filtros['dia']
    if filtros['modo'] == 'periodo':
        return filtros['desde'], filtros['hasta']
    return None, None


def en_letras(fecha):  # 2026-10-16 ---> 16/10/2026
    try:
        return datetime.strptime(fecha, FORMATO_VIAJE).strftime(FORMATO_BONITO)
    except (ValueError, TypeError):
        return fecha or ''


def pesos(cantidad):  # 1842 ---> $1,842
    return '$' + format(int(cantidad), ',')


def titulo_del_periodo(filtros):
    desde, hasta = periodo(filtros)
    if not desde and not hasta:
        return 'Todas las fechas'
    if desde == hasta:
        return 'Dia ' + en_letras(desde)
    return 'Del ' + en_letras(desde) + ' al ' + en_letras(hasta)


def armar(filtros):
    # devuelve todo lo que la pagina y el PDF necesitan, ya sumado
    desde, hasta = periodo(filtros)
    boletos = base_datos.boletos_para_corte(desde, hasta, filtros['ruta'] or None)

    # Resumen: un bloque por dia y, dentro de cada dia, un renglon por ruta
    dias = {}
    for boleto in boletos:
        dia = dias.setdefault(boleto['fecha_viaje'],
                              {'fecha': boleto['fecha_viaje'], 'rutas': {},
                               'cantidad': 0, 'total': 0})
        renglon = dia['rutas'].setdefault(boleto['ruta'],
                                          {'destino': boleto['corrida'],
                                           'cantidad': 0, 'total': 0})
        renglon['cantidad'] += 1
        renglon['total'] += boleto['precio']
        dia['cantidad'] += 1
        dia['total'] += boleto['precio']

    resumen = []
    for dia in sorted(dias.values(), key=lambda dia: dia['fecha']):
        # las rutas de cada dia se dejan en el orden de siempre, no en el que cayeron
        dia['rutas'] = [dia['rutas'][clave] for clave in base_datos.RUTAS
                        if clave in dia['rutas']]
        resumen.append(dia)

    # Desglose por parada: salen todas las paradas de las rutas del filtro,
    # aunque no hayan vendido nada, para que se vea cual no se movio
    cuentas = {}
    for boleto in boletos:
        cuenta = cuentas.setdefault(boleto['parada'], {'cantidad': 0, 'total': 0})
        cuenta['cantidad'] += 1
        cuenta['total'] += boleto['precio']

    paradas = []
    for clave, ruta in base_datos.RUTAS.items():
        if filtros['ruta'] and clave != filtros['ruta']:
            continue
        for parada in ruta['paradas']:
            cuenta = cuentas.get(parada['clave'], {'cantidad': 0, 'total': 0})
            paradas.append({'nombre': parada['nombre'], 'corrida': ruta['destino'],
                            'precio': parada['precio'],
                            'cantidad': cuenta['cantidad'], 'total': cuenta['total']})

    return {
        'filtros': filtros,
        'titulo': titulo_del_periodo(filtros),
        'ruta': base_datos.nombre_de_ruta(filtros['ruta']) if filtros['ruta'] else 'Todas las rutas',
        'resumen': resumen,
        'paradas': paradas,
        'boletos': boletos,
        'cantidad': len(boletos),
        'total': sum(boleto['precio'] for boleto in boletos),
        'momento': datetime.now().strftime('%d/%m/%Y %H:%M'),
    }


def nombre_del_archivo(reporte):
    # algo como corte-de-caja-tlaxiaco-2026-10-01-a-2026-10-16.pdf
    partes = ['corte-de-caja']
    filtros = reporte['filtros']
    if filtros['ruta']:
        partes.append(filtros['ruta'])
    desde, hasta = periodo(filtros)
    if desde and desde == hasta:
        partes.append(desde)
    elif desde and hasta:
        partes.append(desde + '-a-' + hasta)
    else:
        partes.append('todo')
    return '-'.join(partes) + '.pdf'


def recortar(texto, letras):  # para que un nombre largo no se salga de su columna
    texto = str(texto or '')
    return texto if len(texto) <= letras else texto[:letras - 1] + '.'


class Hoja(FPDF):
    """La hoja del PDF: la cabecera y el pie se repiten en cada pagina."""

    def __init__(self, reporte):
        super().__init__(orientation='P', unit='mm', format='A4')
        self.reporte = reporte
        self.set_margins(15, 15, 15)
        self.set_auto_page_break(auto=True, margin=18)
        self.set_title('Corte de caja')

    def header(self):
        self.set_font('Helvetica', 'B', 16)
        self.set_text_color(*COLOR_FUERTE)
        self.cell(0, 8, 'CORTE DE CAJA', new_x='LMARGIN', new_y='NEXT')

        self.set_font('Helvetica', '', 9)
        self.set_text_color(*COLOR_SUAVE)
        self.cell(0, 5, 'Terminal de autobuses de ' + base_datos.ORIGEN,
                  new_x='LMARGIN', new_y='NEXT')
        self.cell(0, 5, self.reporte['titulo'] + '   |   ' + self.reporte['ruta'] +
                  '   |   agrupado por fecha de viaje', new_x='LMARGIN', new_y='NEXT')
        self.cell(0, 5, 'Generado el ' + self.reporte['momento'],
                  new_x='LMARGIN', new_y='NEXT')

        self.ln(2)
        self.set_draw_color(*COLOR_BORDE)
        self.line(15, self.get_y(), 195, self.get_y())
        self.ln(4)

    def footer(self):
        self.set_y(-15)
        self.set_font('Helvetica', '', 8)
        self.set_text_color(*COLOR_SUAVE)
        self.cell(0, 5, 'Pagina ' + str(self.page_no()) + ' de {nb}', align='C')

    # --- las piezas con las que se arman las tablas ---

    def seccion(self, texto):
        self.ln(3)
        self.set_font('Helvetica', 'B', 11)
        self.set_text_color(*COLOR_FUERTE)
        self.cell(0, 7, texto, new_x='LMARGIN', new_y='NEXT')

    def fila(self, celdas, negritas=False, fondo=False, color=None, sangria=0):
        # celdas = [(ancho en mm, texto, alineacion), ...]
        self.set_font('Helvetica', 'B' if negritas else '', 8)
        self.set_text_color(*(color or COLOR_FUERTE))
        if fondo:
            self.set_fill_color(*COLOR_FONDO)
        if sangria:
            self.cell(sangria, 5.5, '', fill=fondo)
        for ancho, texto, alinear in celdas:
            self.cell(ancho, 5.5, str(texto), align=alinear, fill=fondo)
        self.ln()

    def linea_tenue(self):
        self.set_draw_color(*COLOR_BORDE)
        self.line(15, self.get_y(), 195, self.get_y())
        self.ln(1)

    def cabe(self, milimetros):  # si no cabe lo que sigue, se pasa a otra hoja
        if self.get_y() + milimetros > self.h - 18:
            self.add_page()


def hacer_pdf(reporte):
    # los anchos de cada tabla van en milimetros; el ancho util de la hoja es 180
    hoja = Hoja(reporte)
    hoja.alias_nb_pages()
    hoja.add_page()

    if not reporte['boletos']:
        hoja.set_font('Helvetica', '', 10)
        hoja.set_text_color(*COLOR_SUAVE)
        hoja.cell(0, 8, 'No hubo ventas con estos filtros.', new_x='LMARGIN', new_y='NEXT')
        return bytes(hoja.output())

    # --- Resumen por dia, con las rutas de cada dia ---
    hoja.seccion('RESUMEN POR DIA')
    for dia in reporte['resumen']:
        hoja.cabe(10 + 5.5 * (len(dia['rutas']) + 1))
        hoja.fila([(90, en_letras(dia['fecha']), 'left'),
                   (90, '', 'right')], negritas=True, fondo=True)
        for ruta in dia['rutas']:
            hoja.fila([(62, 'Ruta ' + ruta['destino'], 'left'),
                       (40, str(ruta['cantidad']) + ' boleto(s)', 'center'),
                       (70, pesos(ruta['total']), 'right')], sangria=8)
        hoja.fila([(62, 'Subtotal del dia', 'left'),
                   (40, str(dia['cantidad']) + ' boleto(s)', 'center'),
                   (70, pesos(dia['total']), 'right')],
                  negritas=True, color=COLOR_ACENTO, sangria=8)
        hoja.ln(2)

    # --- El total de todo el corte ---
    hoja.cabe(14)
    hoja.linea_tenue()
    hoja.fila([(90, 'TOTAL DEL CORTE', 'left'),
               (40, str(reporte['cantidad']) + ' boleto(s)', 'center'),
               (50, pesos(reporte['total']), 'right')], negritas=True, fondo=True)

    # --- Cuanto dejo cada parada ---
    hoja.seccion('DESGLOSE POR PARADA')
    hoja.cabe(16)
    hoja.fila([(50, 'Parada', 'left'), (40, 'Corrida', 'left'), (30, 'Pasaje', 'right'),
               (30, 'Boletos', 'center'), (30, 'Total', 'right')],
              negritas=True, fondo=True)
    for parada in reporte['paradas']:
        hoja.cabe(6)
        sin_ventas = parada['cantidad'] == 0
        hoja.fila([(50, parada['nombre'], 'left'),
                   (40, parada['corrida'], 'left'),
                   (30, pesos(parada['precio']), 'right'),
                   (30, str(parada['cantidad']), 'center'),
                   (30, pesos(parada['total']), 'right')],
                  color=COLOR_SUAVE if sin_ventas else None)

    # --- Boleto por boleto ---
    hoja.seccion('DETALLE DE BOLETOS')
    hoja.cabe(16)
    # los anchos suman 180 mm, el ancho util de la hoja
    encabezado = [(13, 'Folio', 'left'), (36, 'Pasajero', 'left'),
                  (26, 'Se baja en', 'left'), (22, 'Corrida', 'left'),
                  (9, 'As.', 'center'), (19, 'Viaja', 'center'),
                  (19, 'Vendido', 'center'), (20, 'Vendedor', 'left'),
                  (16, 'Pasaje', 'right')]
    hoja.fila(encabezado, negritas=True, fondo=True)
    for boleto in reporte['boletos']:
        if hoja.get_y() + 6 > hoja.h - 18:   # se repite el encabezado en la hoja nueva
            hoja.add_page()
            hoja.fila(encabezado, negritas=True, fondo=True)
        hoja.fila([(13, format(boleto['id'], '04d'), 'left'),
                   (36, recortar(boleto['pasajero'], 25), 'left'),
                   (26, recortar(boleto['destino'], 16), 'left'),
                   (22, recortar(boleto['corrida'], 13), 'left'),
                   (9, boleto['asiento'], 'center'),
                   (19, en_letras(boleto['fecha_viaje']), 'center'),
                   (19, boleto['fecha_venta'].split(' ')[0], 'center'),
                   (20, recortar(boleto.get('vendedor') or '-', 12), 'left'),
                   (16, pesos(boleto['precio']), 'right')])

    return bytes(hoja.output())
