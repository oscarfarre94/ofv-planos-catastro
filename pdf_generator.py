import os

from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.colors import Color


MM_TO_POINTS = 2.834645669

COLOR_FONDO = Color(0.98, 0.98, 0.97)
COLOR_PARCELAS = Color(0.82, 0.82, 0.80)
COLOR_EDIFICIOS = Color(0.88, 0.88, 0.86)
COLOR_CONTORNO_EDIFICIOS = Color(0.35, 0.35, 0.35)
COLOR_PARCELA_OBJETIVO = Color(0.75, 0.22, 0.18)
COLOR_TEXTO = Color(0.25, 0.25, 0.25)


def calcular_viewport(parcela_principal, escala):
    xs = [p[0] for p in parcela_principal]
    ys = [p[1] for p in parcela_principal]

    centro_x = (min(xs) + max(xs)) / 2
    centro_y = (min(ys) + max(ys)) / 2

    ancho_a4_mm = 297
    alto_a4_mm = 210
    margen_mm = 12

    ancho_util_mm = ancho_a4_mm - margen_mm * 2
    alto_util_mm = alto_a4_mm - margen_mm * 2

    ancho_real_m = ancho_util_mm * escala / 1000
    alto_real_m = alto_util_mm * escala / 1000

    return {
        "min_x": centro_x - ancho_real_m / 2,
        "max_x": centro_x + ancho_real_m / 2,
        "min_y": centro_y - alto_real_m / 2,
        "max_y": centro_y + alto_real_m / 2
    }


def transformar_punto(x, y, viewport, offset_x, offset_y, escala_factor):
    px = ((x - viewport["min_x"]) * escala_factor * MM_TO_POINTS) + offset_x
    py = ((y - viewport["min_y"]) * escala_factor * MM_TO_POINTS) + offset_y
    return px, py


def dibujar_poligono(
    c,
    puntos,
    viewport,
    offset_x,
    offset_y,
    escala_factor,
    color,
    grosor,
    relleno=False,
    transparencia=None
):
    if not puntos:
        return

    c.saveState()

    if transparencia is not None:
        c.setFillAlpha(transparencia)

    c.setStrokeColor(color)
    c.setFillColor(color)
    c.setLineWidth(grosor)

    path = c.beginPath()

    x0, y0 = puntos[0]
    px0, py0 = transformar_punto(
        x0,
        y0,
        viewport,
        offset_x,
        offset_y,
        escala_factor
    )

    path.moveTo(px0, py0)

    for x, y in puntos[1:]:
        px, py = transformar_punto(
            x,
            y,
            viewport,
            offset_x,
            offset_y,
            escala_factor
        )
        path.lineTo(px, py)

    path.close()

    c.drawPath(path, stroke=1, fill=1 if relleno else 0)

    c.restoreState()


def dibujar_escala_grafica(c, escala, page_width):
    escala_grafica_m = 10

    if escala >= 1000:
        escala_grafica_m = 20

    if escala >= 2000:
        escala_grafica_m = 50

    barra_mm = escala_grafica_m * 1000 / escala
    barra_pt = barra_mm * MM_TO_POINTS

    barra_x = page_width - barra_pt - 18
    barra_y = 18

    c.setStrokeColor(COLOR_TEXTO)
    c.setFillColor(COLOR_TEXTO)
    c.setLineWidth(0.6)

    c.line(barra_x, barra_y, barra_x + barra_pt, barra_y)
    c.line(barra_x, barra_y - 2, barra_x, barra_y + 2)
    c.line(barra_x + barra_pt, barra_y - 2, barra_x + barra_pt, barra_y + 2)

    c.setFont("Helvetica", 6)
    c.drawCentredString(
        barra_x + barra_pt / 2,
        barra_y - 9,
        f"{escala_grafica_m} m"
    )


def dibujar_pagina(
    c,
    referencia,
    escala,
    parcela_principal,
    parcelas,
    edificios
):
    page_width, page_height = landscape(A4)

    c.setFillColor(COLOR_FONDO)
    c.rect(0, 0, page_width, page_height, stroke=0, fill=1)

    margen_mm = 12
    margen_pt = margen_mm * MM_TO_POINTS

    offset_x = margen_pt
    offset_y = margen_pt

    escala_factor = 1000 / escala

    ancho_util_pt = page_width - margen_pt * 2
    alto_util_pt = page_height - margen_pt * 2

    viewport = calcular_viewport(parcela_principal, escala)

    c.saveState()

    clip = c.beginPath()
    clip.rect(offset_x, offset_y, ancho_util_pt, alto_util_pt)
    c.clipPath(clip, stroke=0, fill=0)

    for parcela in parcelas:
        dibujar_poligono(
            c,
            parcela,
            viewport,
            offset_x,
            offset_y,
            escala_factor,
            COLOR_PARCELAS,
            0.18,
            relleno=False
        )

    for edificio in edificios:
        dibujar_poligono(
            c,
            edificio,
            viewport,
            offset_x,
            offset_y,
            escala_factor,
            COLOR_EDIFICIOS,
            0,
            relleno=True
        )

    for edificio in edificios:
        dibujar_poligono(
            c,
            edificio,
            viewport,
            offset_x,
            offset_y,
            escala_factor,
            COLOR_CONTORNO_EDIFICIOS,
            0.35,
            relleno=False
        )

    dibujar_poligono(
        c,
        parcela_principal,
        viewport,
        offset_x,
        offset_y,
        escala_factor,
        COLOR_PARCELA_OBJETIVO,
        0,
        relleno=True,
        transparencia=0.50
    )

    dibujar_poligono(
        c,
        parcela_principal,
        viewport,
        offset_x,
        offset_y,
        escala_factor,
        COLOR_PARCELA_OBJETIVO,
        0.6,
        relleno=False
    )

    c.restoreState()

    c.setFillColor(COLOR_TEXTO)

    c.setFont("Helvetica-Bold", 12)
    c.drawString(15, page_height - 18, "PLANO DE EMPLAZAMIENTO")

    c.setFont("Helvetica", 7)
    c.drawString(15, page_height - 30, f"Referencia catastral: {referencia}")
    c.drawString(15, page_height - 40, f"Escala 1/{escala}")

    dibujar_escala_grafica(c, escala, page_width)


def generar_pdf(
    referencia,
    escalas,
    parcela_principal,
    parcelas,
    edificios
):
    os.makedirs("outputs", exist_ok=True)

    output_path = f"outputs/{referencia}.pdf"

    c = canvas.Canvas(output_path, pagesize=landscape(A4))

    for index, escala in enumerate(escalas):
        if index > 0:
            c.showPage()

        dibujar_pagina(
            c,
            referencia,
            escala,
            parcela_principal,
            parcelas,
            edificios
        )

    c.save()

    return output_path