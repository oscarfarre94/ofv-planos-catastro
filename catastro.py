import requests
import xml.etree.ElementTree as ET


def leer_poslists(root):
    geometrias = []

    for elem in root.iter():
        if elem.tag.endswith("posList") and elem.text:
            valores = elem.text.split()
            puntos = []

            for i in range(0, len(valores), 2):
                x = float(valores[i])
                y = float(valores[i + 1])
                puntos.append((x, y))

            if len(puntos) >= 3:
                geometrias.append(puntos)

    return geometrias


def obtener_parcela_principal(refcat):
    url = "https://ovc.catastro.meh.es/INSPIRE/wfsCP.aspx"

    params = {
        "service": "WFS",
        "version": "2.0.0",
        "request": "GetFeature",
        "STOREDQUERY_ID": "GetParcel",
        "refcat": refcat,
        "srsname": "EPSG::25831"
    }

    respuesta = requests.get(url, params=params)
    root = ET.fromstring(respuesta.content)

    parcelas = leer_poslists(root)

    if not parcelas:
        raise Exception("No se encontró la parcela principal")

    return parcelas[0]


def obtener_geometrias_bbox(url, typename, bbox):
    params = {
        "service": "WFS",
        "version": "2.0.0",
        "request": "GetFeature",
        "typenames": typename,
        "srsname": "EPSG::25831",
        "bbox": bbox
    }

    respuesta = requests.get(url, params=params)
    root = ET.fromstring(respuesta.content)

    return leer_poslists(root)


def obtener_datos_plano(refcat, escalas):
    parcela_principal = obtener_parcela_principal(refcat)

    escala_mayor_ambito = max(escalas)

    xs = [p[0] for p in parcela_principal]
    ys = [p[1] for p in parcela_principal]

    centro_x = (min(xs) + max(xs)) / 2
    centro_y = (min(ys) + max(ys)) / 2

    ancho_a4_mm = 297
    alto_a4_mm = 210
    margen_mm = 12

    ancho_util_mm = ancho_a4_mm - margen_mm * 2
    alto_util_mm = alto_a4_mm - margen_mm * 2

    ancho_real_m = ancho_util_mm * escala_mayor_ambito / 1000
    alto_real_m = alto_util_mm * escala_mayor_ambito / 1000

    min_x = centro_x - ancho_real_m / 2
    max_x = centro_x + ancho_real_m / 2
    min_y = centro_y - alto_real_m / 2
    max_y = centro_y + alto_real_m / 2

    bbox = f"{min_x},{min_y},{max_x},{max_y},EPSG:25831"

    url_parcelas = "https://ovc.catastro.meh.es/INSPIRE/wfsCP.aspx"
    url_edificios = "https://ovc.catastro.meh.es/INSPIRE/wfsBU.aspx"

    parcelas = obtener_geometrias_bbox(
        url=url_parcelas,
        typename="CP:CadastralParcel",
        bbox=bbox
    )

    edificios = obtener_geometrias_bbox(
        url=url_edificios,
        typename="BU:Building",
        bbox=bbox
    )

    print("BBOX plano:", bbox)
    print("Parcelas encontradas:", len(parcelas))
    print("Edificios encontrados:", len(edificios))

    return {
        "parcela_principal": parcela_principal,
        "parcelas": parcelas,
        "edificios": edificios
    }