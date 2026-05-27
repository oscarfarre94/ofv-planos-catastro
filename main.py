from typing import Optional

from fastapi import FastAPI
from fastapi.responses import FileResponse
from pydantic import BaseModel

from catastro import obtener_datos_plano
from pdf_generator import generar_pdf

app = FastAPI(title="OFV Planos Catastrales")


class PlanoRequest(BaseModel):
    referencia_catastral: str
    escala: Optional[int] = None


@app.post("/generar-plano-catastral")
def generar_plano(data: PlanoRequest):

    escalas = [data.escala] if data.escala else [500, 2000]
    datos = obtener_datos_plano(
        refcat=data.referencia_catastral,
        escalas=escalas
    )

    generar_pdf(
        referencia=data.referencia_catastral,
        escalas=escalas,
        parcela_principal=datos["parcela_principal"],
        parcelas=datos["parcelas"],
        edificios=datos["edificios"]
    )

    return {
        "referencia_catastral": data.referencia_catastral,
        "escalas": [f"1/{e}" for e in escalas],
        "pdf_url": f"/descargar/{data.referencia_catastral}.pdf"
    }


@app.get("/descargar/{filename}")
def descargar_pdf(filename: str):

    path = f"outputs/{filename}"

    return FileResponse(
        path,
        media_type="application/pdf",
        filename=filename
    )