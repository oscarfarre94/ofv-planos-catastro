def buscar_refcat_por_direccion(
    provincia,
    municipio,
    tipo_via,
    nombre_via,
    numero
):
    url = "https://ovc.catastro.meh.es/ovcservweb/OVCSWLocalizacionRC/OVCCallejero.asmx/Consulta_DNPLOC"

    params = {
        "Provincia": provincia,
        "Municipio": municipio,
        "Sigla": tipo_via,
        "Calle": nombre_via,
        "Numero": numero,
        "Bloque": "",
        "Escalera": "",
        "Planta": "",
        "Puerta": ""
    }

    respuesta = requests.get(url, params=params)
    root = ET.fromstring(respuesta.content)

    ns = {"cat": "http://www.catastro.meh.es/"}

    pc1 = root.find(".//cat:pc1", ns)
    pc2 = root.find(".//cat:pc2", ns)

    if pc1 is None or pc2 is None:
        raise Exception("No se ha encontrado referencia catastral para esa dirección.")

    return pc1.text + pc2.text