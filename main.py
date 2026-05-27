from fastapi.responses import HTMLResponse


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
        OFV Planos Catastro utiliza referencias catastrales proporcionadas por el usuario
        únicamente para generar planos catastrales vectoriales en PDF.
        </p>

        <p>
        No se almacenan datos personales.
        No se comparten datos con terceros.
        </p>

        <p>
        La información catastral utilizada procede de servicios públicos oficiales del Catastro de España.
        </p>

        <p>
        Esta herramienta tiene finalidad técnica y documental para proyectos de arquitectura y urbanismo.
        </p>
    </body>
    </html>
    """