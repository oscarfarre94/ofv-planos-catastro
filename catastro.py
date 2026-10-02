import time
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


# Servicio REST oficial de Catastro. Mantiene los mismos parámetros de dirección.
URL_DIRECCION = (
    "https://ovc.catastro.meh.es/OVCServWeb/OVCWcfCallejero/"
    "COVCCallejero.svc/rest/Consulta_DNPLOC"
)


class CatastroError(Exception):
    def __init__(self, mensaje, status_code=502, retry_after=None):
        super().__init__(mensaje)
        self.status_code = status_code
        self.retry_after = retry_after


def _nombre(elemento):
    return elemento.tag.rsplit("}", 1)[-1]


def _consultar_xml(url, params, timeout=25):
    """Un reintento para fallos transitorios; nunca reintenta un HTTP 429."""
    for intento in range(2):
        try:
            respuesta = requests.get(
                url, params=params,
                headers={"User-Agent": "OFV-Planos-Catastro/1.2", "Accept": "application/xml,text/xml"},
                timeout=(5, timeout),
            )
        except requests.exceptions.Timeout as exc:
            error = CatastroError("Catastro ha tardado demasiado en responder. Reinténtalo más tarde.", 504)
            causa = exc
        except requests.exceptions.SSLError as exc:
            raise CatastroError("No se ha podido verificar la conexión segura con Catastro.", 502) from exc
        except requests.exceptions.RequestException as exc:
            error = CatastroError("No se ha podido conectar con Catastro. Reinténtalo más tarde.", 503)
            causa = exc
        else:
            if respuesta.status_code == 429:
                raise CatastroError(
                    "Catastro ha limitado las solicitudes. Reinténtalo más tarde.",
                    429, respuesta.headers.get("Retry-After"),
                )
            if respuesta.status_code in (500, 502, 503, 504):
                error = CatastroError("El servicio de Catastro no está disponible temporalmente.", 503)
                causa = None
            elif respuesta.status_code != 200:
                raise CatastroError(f"Catastro ha devuelto HTTP {respuesta.status_code}.", 502)
            else:
                try:
                    root = ET.fromstring(respuesta.content)
                except ET.ParseError as exc:
                    raise CatastroError("Catastro ha devuelto una respuesta XML inválida.", 502) from exc
                # Las respuestas oficiales utilizan varios espacios de nombres.
                errores = [e for e in root.iter() if _nombre(e) == "err"]
                if errores:
                    error_xml = errores[0]
                    campos = {_nombre(e): (e.text or "").strip() for e in error_xml}
                    codigo = campos.get("cod", "")
                    mensaje = campos.get("des", "Error de consulta en Catastro.")
                    estado = 503 if codigo == "1" else 404 if codigo in {"5", "9", "43"} else 422
                    raise CatastroError(f"Catastro: {mensaje}", estado)
                for e in root.iter():
                    if _nombre(e) in {"ExceptionText", "ServiceException"}:
                        raise CatastroError("Catastro ha rechazado la consulta de geometrías: " + (e.text or "error WFS").strip(), 502)
                return root
        if intento == 0:
            time.sleep(1)
        else:
            raise error from causa


def buscar_refcat_por_direccion(provincia, municipio, tipo_via, nombre_via, numero):
    params = {
        "Provincia": provincia.strip().upper(),
        "Municipio": municipio.strip().upper(),
        "Sigla": tipo_via.strip().upper(),
        "Calle": nombre_via.strip().upper(),
        "Numero": str(numero).strip(),
        "Bloque": "", "Escalera": "", "Planta": "", "Puerta": "",
    }
    root = _consultar_xml(URL_DIRECCION, params)
    referencias = set()
    for elem in root.iter():
        if _nombre(elem) == "rc":
            partes = {_nombre(e): (e.text or "").strip() for e in elem}
            if partes.get("pc1") and partes.get("pc2"):
                referencia = partes["pc1"] + partes["pc2"]
                if len(referencia) == 14 and referencia.isalnum():
                    referencias.add(referencia.upper())
    if not referencias:
        raise CatastroError("Catastro no ha encontrado una parcela para esa dirección.", 404)
    if len(referencias) > 1:
        raise CatastroError("La dirección corresponde a varias parcelas. Indica la referencia catastral.", 409)
    return referencias.pop()


def obtener_parcela_principal(refcat):
    params = {
        "service": "WFS", "version": "2.0.0", "request": "GetFeature",
        "STOREDQUERY_ID": "GetParcel", "refcat": refcat[:14], "srsname": "EPSG::25831",
    }
    root = _consultar_xml("https://ovc.catastro.meh.es/INSPIRE/wfsCP.aspx", params)
    parcelas = leer_poslists(root)
    if not parcelas:
        raise CatastroError("No se ha encontrado la geometría de la parcela principal.", 404)
    return parcelas[0]


def obtener_geometrias_bbox(url, typename, bbox):
    params = {
        "service": "WFS", "version": "2.0.0", "request": "GetFeature",
        "typenames": typename, "srsname": "EPSG::25831", "bbox": bbox,
    }
    root = _consultar_xml(url, params)
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