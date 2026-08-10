import os
from pathlib import Path
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, HRFlowable
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

def setup_fonts():
    font_candidates = [
        ('/System/Library/Fonts/Supplemental/Arial.ttf', '/System/Library/Fonts/Supplemental/Arial Bold.ttf'),
        ('/Library/Fonts/Arial.ttf', '/Library/Fonts/Arial Bold.ttf')
    ]
    for reg, bold in font_candidates:
        if os.path.exists(reg):
            try:
                pdfmetrics.registerFont(TTFont('AzArial', reg))
                pdfmetrics.registerFont(TTFont('AzArial-Bold', bold if os.path.exists(bold) else reg))
                return
            except Exception:
                pass
    pdfmetrics.registerFont(TTFont('AzArial', 'Helvetica'))
    pdfmetrics.registerFont(TTFont('AzArial-Bold', 'Helvetica-Bold'))

def build_pdf():
    setup_fonts()
    artifact_dir = Path("/Users/nargiznuriyeva/.gemini/antigravity/brain/23bedcbc-85c9-468f-96ab-7724edd32eda")
    artifact_dir.mkdir(parents=True, exist_ok=True)
    pdf_path = artifact_dir / "AI_Real_Estate_Agent_SaaS_Guide.pdf"

    doc = SimpleDocTemplate(
        str(pdf_path),
        pagesize=letter,
        rightMargin=0.4*inch,
        leftMargin=0.4*inch,
        topMargin=0.4*inch,
        bottomMargin=0.4*inch
    )

    styles = getSampleStyleSheet()
    
    title_style = ParagraphStyle(
        'DocTitle',
        parent=styles['Heading1'],
        fontName='AzArial-Bold',
        fontSize=18,
        leading=22,
        textColor=colors.HexColor('#0F172A'),
        alignment=1,
        spaceAfter=6
    )

    subtitle_style = ParagraphStyle(
        'SubTitle',
        parent=styles['Normal'],
        fontName='AzArial',
        fontSize=10,
        leading=13,
        textColor=colors.HexColor('#475569'),
        alignment=1,
        spaceAfter=10
    )

    h1_style = ParagraphStyle(
        'SectionH1',
        parent=styles['Heading2'],
        fontName='AzArial-Bold',
        fontSize=13,
        leading=16,
        textColor=colors.HexColor('#0284C7'),
        spaceBefore=10,
        spaceAfter=5
    )

    h2_style = ParagraphStyle(
        'SectionH2',
        parent=styles['Heading3'],
        fontName='AzArial-Bold',
        fontSize=10,
        leading=13,
        textColor=colors.HexColor('#0F172A'),
        spaceBefore=6,
        spaceAfter=2
    )

    body_style = ParagraphStyle(
        'BodyTextCustom',
        parent=styles['Normal'],
        fontName='AzArial',
        fontSize=8.5,
        leading=11.5,
        textColor=colors.HexColor('#334155'),
        spaceAfter=4
    )

    table_header_style = ParagraphStyle(
        'TableHeader',
        parent=styles['Normal'],
        fontName='AzArial-Bold',
        fontSize=8,
        leading=10,
        textColor=colors.white,
        alignment=0
    )

    table_cell_style = ParagraphStyle(
        'TableCell',
        parent=styles['Normal'],
        fontName='AzArial',
        fontSize=7.5,
        leading=10,
        textColor=colors.HexColor('#1E293B')
    )

    elements = []

    # Title Banner
    elements.append(Paragraph("AI Real Estate Agent SaaS Master Guide", title_style))
    elements.append(Paragraph("6 Market-Dominating Killer Features, User Journey & Subscription Tiers<br/><b>Dillər / Languages / Языки:</b> English | Azərbaycan Dili | Русский", subtitle_style))
    elements.append(HRFlowable(width="100%", thickness=1.5, color=colors.HexColor('#0284C7'), spaceAfter=10))

    # Section 1: Executive Overview
    elements.append(Paragraph("1. Executive Platform Overview", h1_style))
    elements.append(Paragraph(
        "<b>AI Real Estate Agent SaaS</b> daşınmaz əmlak agentlikləri üçün 17 əmlak saytından və Telegram kanallarından elan toplayan, "
        "AI (Gemini, Claude, GPT) vasitəsilə uyğunlaşdıran və WhatsApp/Telegram bota anında çatdıran platformadır.", body_style
    ))

    # Section 2: 6 Killer Features
    elements.append(Paragraph("2. Top 6 Market-Dominating Killer Features", h1_style))
    
    killer_features = [
        ("1. AI Makler & First-Posting Detector", "Detects disguised realtors and verifies if a property is the 1st original posting or a duplicate post with earlier links."),
        ("2. 30-Second Speed-Dial Call Button", "Embeds 1-tap direct phone dial buttons in WhatsApp/Telegram so agents call owners within 30 seconds."),
        ("3. AI AVM & Bargain Deal Finder", "Computes district average price/sqm and flags deals tagged 🔥 TƏCİLİ FÜRSƏT ELAN! (-15% Below Market Rate)."),
        ("4. Private B2B Agent Co-Brokering Network", "Safely matches Agent A's buyer criteria with Agent B's listing for 50/50 commission co-brokering (B2B Qəbul et)."),
        ("5. 1-Click Instagram & PDF Brochure Generator", "Generates branded PDF brochures and Azerbaijani social media captions (Broşur <id>)."),
        ("6. AI Client Qualification Intake Bot", "Public API intake endpoint for agents' Instagram bios and WhatsApp links (POST /api/v1/client-intake/{tenant_id})."),
        ("7. Referral Program & Promo Code Discounts", "Unique referral codes (REF-XXXX-NAME) with 10 AZN bonus credits + discount promo coupons (/referral, Promokod <code>).")
    ]

    for title, desc in killer_features:
        elements.append(Paragraph(f"<b>{title}</b>", h2_style))
        elements.append(Paragraph(desc, body_style))

    elements.append(Spacer(1, 8))

    # Section 3: Subscription Tiers Table
    elements.append(Paragraph("3. Subscription Plan Tiering Matrix", h1_style))

    plan_table_data = [
        [
            Paragraph("Feature", table_header_style),
            Paragraph("Free", table_header_style),
            Paragraph("Starter", table_header_style),
            Paragraph("Pro", table_header_style),
            Paragraph("Agency / Enterprise", table_header_style)
        ],
        [
            Paragraph("Saved Searches", table_cell_style),
            Paragraph("1", table_cell_style),
            Paragraph("5", table_cell_style),
            Paragraph("15", table_cell_style),
            Paragraph("Unlimited", table_cell_style)
        ],
        [
            Paragraph("Instant Alerts (WA/TG)", table_cell_style),
            Paragraph("Yes", table_cell_style),
            Paragraph("Yes", table_cell_style),
            Paragraph("Yes", table_cell_style),
            Paragraph("Yes", table_cell_style)
        ],
        [
            Paragraph("30s Speed Dial Link", table_cell_style),
            Paragraph("No", table_cell_style),
            Paragraph("Yes", table_cell_style),
            Paragraph("Yes", table_cell_style),
            Paragraph("Yes", table_cell_style)
        ],
        [
            Paragraph("AI Makler & First-Posting Check", table_cell_style),
            Paragraph("No", table_cell_style),
            Paragraph("No", table_cell_style),
            Paragraph("Yes", table_cell_style),
            Paragraph("Yes", table_cell_style)
        ],
        [
            Paragraph("AVM Bargain Deal Finder", table_cell_style),
            Paragraph("No", table_cell_style),
            Paragraph("No", table_cell_style),
            Paragraph("Yes", table_cell_style),
            Paragraph("Yes", table_cell_style)
        ],
        [
            Paragraph("Social Kit & PDF Brochure", table_cell_style),
            Paragraph("No", table_cell_style),
            Paragraph("No", table_cell_style),
            Paragraph("Yes", table_cell_style),
            Paragraph("Yes", table_cell_style)
        ],
        [
            Paragraph("BaaS Automated Backups", table_cell_style),
            Paragraph("No", table_cell_style),
            Paragraph("No", table_cell_style),
            Paragraph("Weekly", table_cell_style),
            Paragraph("Daily", table_cell_style)
        ],
        [
            Paragraph("B2B Co-Brokering & Client Intake Bot", table_cell_style),
            Paragraph("No", table_cell_style),
            Paragraph("No", table_cell_style),
            Paragraph("No", table_cell_style),
            Paragraph("Yes", table_cell_style)
        ]
    ]

    t_plan = Table(plan_table_data, colWidths=[1.8*inch, 0.8*inch, 1.0*inch, 1.8*inch, 2.1*inch])
    t_plan.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#0284C7')),
        ('ALIGN', (0,0), (-1,-1), 'LEFT'),
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#CBD5E1')),
        ('BACKGROUND', (0,1), (-1,1), colors.HexColor('#F8FAFC')),
        ('BACKGROUND', (0,3), (-1,3), colors.HexColor('#F8FAFC')),
        ('BACKGROUND', (0,5), (-1,5), colors.HexColor('#F8FAFC')),
        ('BACKGROUND', (0,7), (-1,7), colors.HexColor('#F8FAFC')),
        ('TOPPADDING', (0,0), (-1,-1), 3),
        ('BOTTOMPADDING', (0,0), (-1,-1), 3),
    ]))
    elements.append(t_plan)
    elements.append(Spacer(1, 10))

    # Section 4: Master Bot Command Reference
    elements.append(Paragraph("4. Master Bot Command Reference (Azerbaijani / English)", h1_style))

    cmd_data = [
        [
            Paragraph("Əmr / Mətn", table_header_style),
            Paragraph("Qısayol / Shortcut", table_header_style),
            Paragraph("Təsvir / Description", table_header_style),
            Paragraph("Nümunə Bot Cavabı", table_header_style)
        ],
        [
            Paragraph("<b>Kömək</b>", table_cell_style),
            Paragraph("<code>/help</code>, <code>menu</code>", table_cell_style),
            Paragraph("Displays help guide & command list", table_cell_style),
            Paragraph("<i>🤖 Əmr Siyahısı...</i>", table_cell_style)
        ],
        [
            Paragraph("<b>Axtarışlarım</b>", table_cell_style),
            Paragraph("<code>/list</code>, <code>1</code>", table_cell_style),
            Paragraph("Lists saved client property searches", table_cell_style),
            Paragraph("<i>🟢 #102 Axtarış: Yasamal</i>", table_cell_style)
        ],
        [
            Paragraph("<b>Yeni axtarış</b>", table_cell_style),
            Paragraph("<code>/add</code>, <code>2</code>", table_cell_style),
            Paragraph("Parses free text with AI to create a search", table_cell_style),
            Paragraph("<i>✅ Yeni axtarış saxlanıldı!</i>", table_cell_style)
        ],
        [
            Paragraph("<b>Broşur &lt;id&gt;</b>", table_cell_style),
            Paragraph("<code>/brochure</code>", table_cell_style),
            Paragraph("Generates PDF brochure & Instagram caption", table_cell_style),
            Paragraph("<i>📸 Instagram Caption & PDF hazır!</i>", table_cell_style)
        ],
        [
            Paragraph("<b>B2B Qəbul et &lt;id&gt;</b>", table_cell_style),
            Paragraph("Reaction button", table_cell_style),
            Paragraph("Accepts B2B 50/50 co-brokering deal", table_cell_style),
            Paragraph("<i>B2B Status: Accepted 🤝</i>", table_cell_style)
        ],
        [
            Paragraph("<b>Kanalı dəyiş</b>", table_cell_style),
            Paragraph("<code>/channel</code>, <code>3</code>", table_cell_style),
            Paragraph("Toggles WhatsApp ↔ Telegram routing", table_cell_style),
            Paragraph("<i>Kanal: WhatsApp 📲</i>", table_cell_style)
        ],
        [
            Paragraph("<b>Planım nə vaxt bitir?</b>", table_cell_style),
            Paragraph("<code>/status</code>, <code>4</code>", table_cell_style),
            Paragraph("Shows plan status and expiry date", table_cell_style),
            Paragraph("<i>▪️ Status: Aktiv ✅</i>", table_cell_style)
        ]
    ]

    t_cmd = Table(cmd_data, colWidths=[1.4*inch, 1.3*inch, 2.4*inch, 2.4*inch])
    t_cmd.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#0F172A')),
        ('ALIGN', (0,0), (-1,-1), 'LEFT'),
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#CBD5E1')),
        ('BACKGROUND', (0,1), (-1,1), colors.HexColor('#F8FAFC')),
        ('BACKGROUND', (0,3), (-1,3), colors.HexColor('#F8FAFC')),
        ('BACKGROUND', (0,5), (-1,5), colors.HexColor('#F8FAFC')),
        ('BACKGROUND', (0,7), (-1,7), colors.HexColor('#F8FAFC')),
        ('TOPPADDING', (0,0), (-1,-1), 3),
        ('BOTTOMPADDING', (0,0), (-1,-1), 3),
    ]))
    elements.append(t_cmd)

    doc.build(elements)
    print(f"PDF successfully generated at: {pdf_path}")
    return str(pdf_path)

if __name__ == "__main__":
    build_pdf()
