import io
from datetime import date

def render_pdf(stmt: dict) -> bytes:
    """Render a single bank statement dict to PDF bytes using reportlab."""
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.units import mm
    from reportlab.lib import colors
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.platypus import (SimpleDocTemplate, Paragraph, Spacer,
                                    Table, TableStyle, HRFlowable)
    from reportlab.lib.enums import TA_LEFT, TA_RIGHT, TA_CENTER

    buf  = io.BytesIO()
    W, H = A4
    margin = 18 * mm

    doc = SimpleDocTemplate(
        buf,
        pagesize=A4,
        leftMargin=margin, rightMargin=margin,
        topMargin=14 * mm, bottomMargin=14 * mm,
    )

    DARK   = colors.HexColor("#1a2340")
    MED    = colors.HexColor("#3a4a6b")
    LIGHT  = colors.HexColor("#e8ecf3")
    RULE   = colors.HexColor("#c5cad8")
    GREEN  = colors.HexColor("#1a6b3a")
    RED    = colors.HexColor("#8b1a1a")
    WHITE  = colors.white
    BLACK  = colors.black

    styles = getSampleStyleSheet()

    def sty(name, **kw):
        base = {k: v for k, v in styles["Normal"].__dict__.items()
                if not k.startswith("_") and k != "name"}
        return ParagraphStyle(name, **{**base, **kw})

    S_BANK   = sty("bank",   fontSize=16, textColor=WHITE,  fontName="Helvetica-Bold", alignment=TA_LEFT)
    S_TAGLINE= sty("tag",    fontSize=7,  textColor=LIGHT,  fontName="Helvetica",      alignment=TA_LEFT)
    S_SMALL  = sty("small",  fontSize=7.5,textColor=MED,    fontName="Helvetica")
    S_SMALL_R= sty("smallR", fontSize=7.5,textColor=MED,    fontName="Helvetica",      alignment=TA_RIGHT)
    S_LABEL  = sty("label",  fontSize=7,  textColor=MED,    fontName="Helvetica",      spaceBefore=2)
    S_VALUE  = sty("value",  fontSize=8.5,textColor=DARK,   fontName="Helvetica-Bold", spaceAfter=4)
    S_TITLE  = sty("title",  fontSize=10, textColor=DARK,   fontName="Helvetica-Bold", spaceBefore=6, spaceAfter=2)
    S_HDRCELL= sty("hdr",    fontSize=7.5,textColor=WHITE,  fontName="Helvetica-Bold", alignment=TA_CENTER)
    S_CELL   = sty("cell",   fontSize=7.5,textColor=BLACK,  fontName="Helvetica",      alignment=TA_LEFT)
    S_CELL_R = sty("cellR",  fontSize=7.5,textColor=BLACK,  fontName="Helvetica",      alignment=TA_RIGHT)
    S_DR     = sty("dr",     fontSize=7.5,textColor=RED,    fontName="Helvetica",      alignment=TA_RIGHT)
    S_CR     = sty("cr",     fontSize=7.5,textColor=GREEN,  fontName="Helvetica",      alignment=TA_RIGHT)
    S_FOOTER = sty("footer", fontSize=6.5,textColor=MED,    fontName="Helvetica",      alignment=TA_CENTER)

    def inr(v):
        if v is None: return ""
        # return f"Rs. {v:,.2f}"
        return f"{v:,.2f}"

    story = []

    bank = stmt["bank_name"]
    initial = bank[0].upper()
    logo_cell = Table(
        [[Paragraph(f'<font size="20" color="white"><b>{initial}</b></font>', S_BANK)]],
        colWidths=[12*mm], rowHeights=[12*mm]
    )
    logo_cell.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (-1,-1), MED),
        ("ALIGN",      (0,0), (-1,-1), "CENTER"),
        ("VALIGN",     (0,0), (-1,-1), "MIDDLE"),
        ("BOX",        (0,0), (-1,-1), 0.5, WHITE),
    ]))

    header_data = [[
        logo_cell,
        [Paragraph(bank.upper(), S_BANK),
         Paragraph("Account Statement  |  Personal Banking", S_TAGLINE)],
        [Paragraph("Statement Date", S_SMALL_R),
         Paragraph(date.today().strftime("%d %b %Y"), sty("sd", fontSize=8, textColor=WHITE, fontName="Helvetica-Bold", alignment=TA_RIGHT))],
    ]]
    header_tbl = Table(header_data, colWidths=[14*mm, 110*mm, None])
    header_tbl.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (-1,-1), DARK),
        ("ALIGN",      (0,0), (0,-1),  "CENTER"),
        ("VALIGN",     (0,0), (-1,-1), "MIDDLE"),
        ("LEFTPADDING",  (0,0), (-1,-1), 6),
        ("RIGHTPADDING", (0,0), (-1,-1), 8),
        ("TOPPADDING",   (0,0), (-1,-1), 8),
        ("BOTTOMPADDING",(0,0), (-1,-1), 8),
    ]))
    story.append(header_tbl)
    story.append(Spacer(1, 6))

    period_start, period_end = stmt["statement_period"]
    summary_data = [[
        [Paragraph("Account Holder",  S_LABEL), Paragraph(stmt["account_holder"], S_VALUE)],
        [Paragraph("Account Number",  S_LABEL), Paragraph(stmt["account_number"], S_VALUE)],
        [Paragraph("IFSC Code",       S_LABEL), Paragraph(stmt["ifsc_code"],      S_VALUE)],
        [Paragraph("Branch",          S_LABEL), Paragraph(stmt["branch"],         S_VALUE)],
    ],[
        [Paragraph("Statement Period",S_LABEL), Paragraph(f"{period_start} to {period_end}", S_VALUE)],
        [Paragraph("Opening Balance", S_LABEL), Paragraph(inr(stmt["opening_balance"]), S_VALUE)],
        [Paragraph("Closing Balance", S_LABEL), Paragraph(inr(stmt["closing_balance"]), S_VALUE)],
        [Paragraph("Total Transactions",S_LABEL),Paragraph(str(len(stmt["transactions"])), S_VALUE)],
    ]]
    for row in summary_data:
        t = Table([row], colWidths=[42*mm]*4)
        t.setStyle(TableStyle([
            ("BACKGROUND",   (0,0), (-1,-1), LIGHT),
            ("LEFTPADDING",  (0,0), (-1,-1), 6),
            ("RIGHTPADDING", (0,0), (-1,-1), 6),
            ("TOPPADDING",   (0,0), (-1,-1), 4),
            ("BOTTOMPADDING",(0,0), (-1,-1), 4),
            ("LINEAFTER",    (0,0), (2,-1), 0.5, RULE),
        ]))
        story.append(t)
        story.append(Spacer(1, 2))

    story.append(Spacer(1, 6))
    story.append(Paragraph("Transaction Details", S_TITLE))
    story.append(HRFlowable(width="100%", thickness=1, color=DARK, spaceAfter=4))

    col_w = [22*mm, 89*mm, 25*mm, 25*mm, 27*mm]
    hdr_row = [Paragraph(h, S_HDRCELL)
               for h in ["Date", "Description", "Debit (Dr)", "Credit (Cr)", "Balance"]]
    rows = [hdr_row]

    for i, tx in enumerate(stmt["transactions"]):
        rows.append([
            Paragraph(tx["date"],             S_CELL),
            Paragraph(tx["description"],      S_CELL),
            Paragraph(inr(tx["debit"]),       S_DR),
            Paragraph(inr(tx["credit"]),      S_CR),
            Paragraph(inr(tx["balance"]),     S_CELL_R),
        ])

    tbl = Table(rows, colWidths=col_w, repeatRows=1)
    tbl_style = [
        ("BACKGROUND",   (0,0), (-1,0),  DARK),
        ("ROWBACKGROUNDS",(0,1),(-1,-1), [WHITE, LIGHT]),
        ("GRID",         (0,0), (-1,-1), 0.3, RULE),
        ("LINEBELOW",    (0,0), (-1,0),  1,   MED),
        ("TOPPADDING",   (0,0), (-1,-1), 3),
        ("BOTTOMPADDING",(0,0), (-1,-1), 3),
        ("LEFTPADDING",  (0,0), (-1,-1), 4),
        ("RIGHTPADDING", (0,0), (-1,-1), 4),
        ("VALIGN",       (0,0), (-1,-1), "MIDDLE"),
    ]
    tbl.setStyle(TableStyle(tbl_style))
    story.append(tbl)

    story.append(Spacer(1, 10))
    story.append(HRFlowable(width="100%", thickness=0.5, color=RULE))
    story.append(Spacer(1, 4))
    story.append(Paragraph(
        f"{bank}  |  {stmt['branch']}  |  IFSC: {stmt['ifsc_code']}  |  "
        "This is a computer-generated statement and does not require a signature.",
        S_FOOTER))
    story.append(Paragraph(
        "For queries contact: 1800-XXX-XXXX  |  customercare@bank.com  |  www.bank.com",
        S_FOOTER))

    doc.build(story)
    return buf.getvalue()
