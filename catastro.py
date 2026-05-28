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


def buscar_refcat_por_direccion(
    provincia,
    municipio,
    tipo_via,
    nombre_via,
    numero
):

    url = "https://ovc.catastro.meh.es/ovcservweb/OVCSWLocalizacionRC/OVCCallejero.asmx/Consulta_DNPLOC"

    params = {
        "Provincia": provincia.upper(),
        "Municipio": municipio.upper(),
        "Sigla": tipo_via.upper(),
        "Calle": nombre_via.upper(),
        "Numero": numero,
        "Bloque": "",
        "Escalera": "",
        "Planta": "",
        "Puerta": ""
    }

    headers = {
        "User-Agent": "Mozilla/5.0 OFV-Planos-Catastro/1.0",
        "Accept": "application/xml,text/xml,*/*"
    }

    ultimo_error = None

    for intento in range(3):

        try:

            respuesta = requests.get(
                url,
                params=params,
                headers=headers,
                timeout=30
            )

            if respuesta.status_code != 200:

                ultimo_error = (
                    f"HTTP {respuesta.status_code}"
                )

                continue

            contenido = respuesta.content.strip()

            if not contenido.startswith(b"<"):

                ultimo_error = (
                    "Respuesta no XML del Catastro"
                )

                continue

            root = ET.fromstring(contenido)

            ns = {
                "cat": "http://www.catastro.meh.es/"
            }

            pc1 = root.find(".//cat:pc1", ns)
            pc2 = root.find(".//cat:pc2", ns)

            if pc1 is None or pc2 is None:

                raise Exception(
                    "No se encontró referencia catastral para la dirección."
                )

            return pc1.text + pc2.text

        except requests.exceptions.RequestException as e:

            ultimo_error = str(e)

        except ET.ParseError as e:

            ultimo_error = f"Error XML: {e}"

    raise Exception(
        f"No se pudo consultar la dirección en Catastro. Último error: {ultimo_error}"
    )


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

    respuesta = requests.get(
        url,
        params=params,
        timeout=30
    )

    root = ET.fromstring(respuesta.content)

    parcelas = leer_poslists(root)

    if not parcelas:

        raise Exception(
            "No se encontró parcela principal."
        )

    return parcelas[0]


def obtener_geometrias_bbox(
    url,
    typename,
    bbox
):

    params = {
        "service": "WFS",
        "version": "2.0.0",
        "request": "GetFeature",
        "typenames": typename,
        "srsname": "EPSG::25831",
        "bbox": bbox
    }

    respuesta = requests.get(
        url,
        params=params,
        timeout=30
    )

    root = ET.fromstring(
        respuesta.content
    )

    return leer_poslists(root)


def obtener_datos_plano(
    refcat,
    escalas
):

    parcela_principal = obtener_parcela_principal(
        refcat
    )

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

    ancho_real_m = (
        ancho_util_mm
        * escala_mayor_ambito
        / 1000
    )

    alto_real_m = (
        alto_util_mm
        * escala_mayor_ambito
        / 1000
    )

    min_x = centro_x - ancho_real_m / 2
    max_x = centro_x + ancho_real_m / 2

    min_y = centro_y - alto_real_m / 2
    max_y = centro_y + alto_real_m / 2

    bbox = (
        f"{min_x},{min_y},"
        f"{max_x},{max_y},EPSG:25831"
    )

    url_parcelas = (
        "https://ovc.catastro.meh.es/INSPIRE/wfsCP.aspx"
    )

    url_edificios = (
        "https://ovc.catastro.meh.es/INSPIRE/wfsBU.aspx"
    )

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

    return {
        "parcela_principal": parcela_principal,
        "parcelas": parcelas,
        "edificios": edificios
    }