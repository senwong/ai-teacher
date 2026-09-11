from io import BytesIO
from pathlib import Path

import qrcode
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader


def render_worksheet_pdf(worksheet: dict, output: Path) -> Path:
    output.parent.mkdir(parents=True, exist_ok=True)
    c = canvas.Canvas(str(output), pagesize=A4)
    width, height = A4

    c.setTitle(f"AI Teacher Worksheet {worksheet['id']}")
    c.setFont("Helvetica-Bold", 18)
    c.drawString(20 * mm, height - 22 * mm, "AI Teacher - Grade 3 Math")
    c.setFont("Helvetica", 10)
    c.drawString(20 * mm, height - 30 * mm, f"Worksheet ID: {worksheet['id']}")
    c.drawString(20 * mm, height - 36 * mm, "Write your calculation steps clearly, then photograph the whole page.")

    qr = qrcode.make(f"ai-teacher:worksheet:{worksheet['id']}")
    buf = BytesIO()
    qr.save(buf, format="PNG")
    buf.seek(0)
    c.drawImage(ImageReader(buf), width - 42 * mm, height - 40 * mm, 25 * mm, 25 * mm)

    y = height - 58 * mm
    for index, question in enumerate(worksheet["questions"], start=1):
        c.setFont("Helvetica-Bold", 14)
        c.drawString(22 * mm, y, f"{index}.  {question['a']} x {question['b']} =")
        c.setLineWidth(0.6)
        c.line(70 * mm, y - 2, 100 * mm, y - 2)
        c.setFont("Helvetica", 9)
        c.drawString(22 * mm, y - 8 * mm, "Work:")
        c.rect(22 * mm, y - 33 * mm, 160 * mm, 20 * mm)
        y -= 43 * mm
        if y < 35 * mm and index != len(worksheet["questions"]):
            c.showPage()
            y = height - 25 * mm

    c.setFont("Helvetica", 8)
    c.drawCentredString(width / 2, 12 * mm, f"AI Teacher worksheet {worksheet['id']}")
    c.save()
    return output
