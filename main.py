from typing import Optional

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, HTMLResponse
from pydantic import BaseModel

from catastro import obtener_datos_plano, buscar_refcat_por_direccion
from pdf_generator import generar_pdf

app = FastAPI(title="OFV Planos Catastro API")


class PlanoRequest(BaseModel):
    referencia_catastral: Optional[str] = None
    provincia: Optional[str] = None
    municipio: Optional[str] = None
    tipo_via: Optional[str] = None
    nombre_via: Optional[str] = None
    numero: Optional[str] = None
    escala: Optional[int] = None


@app.post("/generar-plano-catastral")
def generar_plano(data: PlanoRequest):

    refcat = data.referencia_catastral

    if not refcat:
        if not all([
            data.provincia,
            data.municipio,
            data.tipo_via,
            data.nombre_via,
            data.numero
        ]):
            raise HTTPException(
                status_code=400,
                detail="Debes indicar referencia catastral o dirección completa."
            )

        refcat = buscar_refcat_por_direccion(
            provincia=data.provincia,
            municipio=data.municipio,
            tipo_via=data.tipo_via,
            nombre_via=data.nombre_via,
            numero=data.numero
        )

    escalas = [data.escala] if data.escala else [500, 2000]

    datos = obtener_datos_plano(
        refcat=refcat,
        escalas=escalas
    )

    generar_pdf(
        referencia=refcat,
        escalas=escalas,
        parcela_principal=datos["parcela_principal"],
        parcelas=datos["parcelas"],
        edificios=datos["edificios"]
    )

    return {
        "referencia_catastral": refcat,
        "escalas": [f"1/{e}" for e in escalas],
        "pdf_url": f"https://ofv-planos-catastro.onrender.com/descargar/{refcat}.pdf"
    }


@app.get("/descargar/{filename}")
def descargar_pdf(filename: str):

    path = f"outputs/{filename}"

    return FileResponse(
        path,
        media_type="application/pdf",
        filename=filename
    )


@app.get("/privacy", response_class=HTMLResponse)
def privacy_policy():

    return """
    <html>
    <head>
        <title>Política de privacidad</title>
    </head>
    <body style="font-family: Arial; padding: 40px; max-width: 900px;">
        <h1>Política de privacidad</h1>
        <p>
        OFV Planos Catastro utiliza referencias catastrales o direcciones proporcionadas por el usuario
        únicamente para generar planos catastrales vectoriales en PDF.
        </p>
        <p>
        No se almacenan datos personales. No se comparten datos con terceros.
        </p>
        <p>
        La información utilizada procede de servicios públicos oficiales del Catastro de España.
        </p>
    </body>
    </html>
    """