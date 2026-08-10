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
    """Register UTF-8 TTF fonts that support Azerbaijani characters (ə, ş, ç, ğ, ı, ö, ü)."""
    font_candidates = [
        ('/System/Library/Fonts/Supplemental/Arial.ttf', '/System/Library/Fonts/Supplemental/Arial Bold.ttf'),
        ('/Library/Fonts/Arial.ttf', '/Library/Fonts/Arial Bold.ttf'),
        ('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf', '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf'),
        ('/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf', '/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf')
    ]

    registered = False
    for regular_path, bold_path in font_candidates:
        if os.path.exists(regular_path):
            try:
                pdfmetrics.registerFont(TTFont('AzArial', regular_path))
                if os.path.exists(bold_path):
                    pdfmetrics.registerFont(TTFont('AzArial-Bold', bold_path))
                else:
                    pdfmetrics.registerFont(TTFont('AzArial-Bold', regular_path))
                registered = True
                break
            except Exception as e:
                print(f"Warning registering font {regular_path}: {e}")

    if not registered:
        # Fallback to standard Helvetica if no TTF found
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
        fontSize=20,
        leading=24,
        textColor=colors.HexColor('#0F172A'),
        alignment=1,
        spaceAfter=8
    )

    subtitle_style = ParagraphStyle(
        'SubTitle',
        parent=styles['Normal'],
        fontName='AzArial',
        fontSize=10.5,
        leading=14,
        textColor=colors.HexColor('#475569'),
        alignment=1,
        spaceAfter=12
    )

    h1_style = ParagraphStyle(
        'SectionH1',
        parent=styles['Heading2'],
        fontName='AzArial-Bold',
        fontSize=14,
        leading=18,
        textColor=colors.HexColor('#0284C7'),
        spaceBefore=12,
        spaceAfter=6
    )

    h2_style = ParagraphStyle(
        'SectionH2',
        parent=styles['Heading3'],
        fontName='AzArial-Bold',
        fontSize=11,
        leading=15,
        textColor=colors.HexColor('#0F172A'),
        spaceBefore=8,
        spaceAfter=3
    )

    body_style = ParagraphStyle(
        'BodyTextCustom',
        parent=styles['Normal'],
        fontName='AzArial',
        fontSize=9,
        leading=13,
        textColor=colors.HexColor('#334155'),
        spaceAfter=5
    )

    table_header_style = ParagraphStyle(
        'TableHeader',
        parent=styles['Normal'],
        fontName='AzArial-Bold',
        fontSize=8.5,
        leading=11,
        textColor=colors.white,
        alignment=0
    )

    table_cell_style = ParagraphStyle(
        'TableCell',
        parent=styles['Normal'],
        fontName='AzArial',
        fontSize=8,
        leading=11,
        textColor=colors.HexColor('#1E293B')
    )

    elements = []

    # Title Banner
    elements.append(Paragraph("AI Real Estate Agent SaaS Platform Guide", title_style))
    elements.append(Paragraph("Comprehensive Feature Matrix, User Journey & Bot Command Reference<br/><b>Dillər / Languages / Языки:</b> English | Azərbaycan Dili | Русский", subtitle_style))
    elements.append(HRFlowable(width="100%", thickness=1.5, color=colors.HexColor('#0284C7'), spaceAfter=12))

    # Section 1: Executive Overview
    elements.append(Paragraph("1. Platformaya Ümumi Baxış / Executive Overview", h1_style))
    elements.append(Paragraph(
        "<b>AI Real Estate Agent SaaS</b> daşınmaz əmlak agentlikləri və fərdi vasitəçilər üçün hazırlanmış yüksək sürətli SaaS platformasıdır. "
        "Sistem 17 məşhur əmlak portalından (bina.az, tap.az, yeniemlak.az, lalafo.az və s.) və Telegram kanallarından elanları avtomatik toplayır, "
        "süni intellekt (Gemini, Claude, GPT) vasitəsilə agentlərin sərbəst mətndə yazdığı axtarış tələblərini analiz edir və uyğun elanları dərhal WhatsApp və Telegram botlarına çatdırır.", body_style
    ))

    # Section 2: Trilingual Feature Matrix
    elements.append(Paragraph("2. Xüsusiyyətlər Siyahısı (3 Dildə / 3 Languages)", h1_style))
    
    table_data = [
        [
            Paragraph("Modul", table_header_style),
            Paragraph("🇬🇧 English", table_header_style),
            Paragraph("🇦🇿 Azərbaycan Dili", table_header_style),
            Paragraph("🇷🇺 Русский", table_header_style)
        ],
        [
            Paragraph("<b>Portal Scrapers</b>", table_cell_style),
            Paragraph("17 Website Crawlers (bina.az, tap.az, lalafo.az, homdom.az, etc.) + Telethon Telegram Crawler", table_cell_style),
            Paragraph("17 Əmlak Saytı Scraper-i + Telegram İctimai Kanal Crawleri", table_cell_style),
            Paragraph("17 Парсеров Сайтов + Скрапер Публичных Telegram-Каналов", table_cell_style)
        ],
        [
            Paragraph("<b>Owner Detection</b>", table_cell_style),
            Paragraph("Automatic 'Sahibindən' (Direct Owner) vs Agency classification & phone analysis", table_cell_style),
            Paragraph("Avtomatik 'Sahibindən' (Ev yiyəsi) və Vasitəçi filtrləməsi", table_cell_style),
            Paragraph("Авто-классификация «От собственника» и «От агентства»", table_cell_style)
        ],
        [
            Paragraph("<b>AI Matching</b>", table_cell_style),
            Paragraph("Multi-LLM Engine (Gemini, Claude, GPT) + Azerbaijani natural language criteria parsing", table_cell_style),
            Paragraph("Çox-modellı AI (Gemini, Claude, GPT) + Azərbaycan dilində təbii mətn analizi", table_cell_style),
            Paragraph("Многомодельный ИИ-движок + Анализ запросов на азербайджанском", table_cell_style)
        ],
        [
            Paragraph("<b>Agent Bots</b>", table_cell_style),
            Paragraph("Shared WhatsApp (Evolution API) & Telegram bot with Azerbaijani command handler", table_cell_style),
            Paragraph("WhatsApp və Telegram üzərindən ortaq Azərbaycan dilli bot idarəetməsi", table_cell_style),
            Paragraph("Общий Бот для WhatsApp и Telegram на азербайджанском языке", table_cell_style)
        ],
        [
            Paragraph("<b>Admin Dashboard</b>", table_cell_style),
            Paragraph("React + Vite + Tailwind CSS dashboard with cash tracker, AI model routing, and source health", table_cell_style),
            Paragraph("React paneli: nağd ödənişlər, AI model nizamlamaları və scraper monitoru", table_cell_style),
            Paragraph("Панель React: учет наличных оплат, маршрутизация ИИ и мониторинг", table_cell_style)
        ],
        [
            Paragraph("<b>BaaS & Security</b>", table_cell_style),
            Paragraph("Backup-as-a-Service plan add-on (Daily/Weekly/Monthly) + Fernet AES key encryption + JWT auth", table_cell_style),
            Paragraph("Ehtiyat Nüsxə Xidməti (BaaS), Fernet AES şifrələməsi və JWT təhlükəsizliyi", table_cell_style),
            Paragraph("Бэкап как услуга (BaaS), шифрование ключей Fernet AES и JWT-авторизация", table_cell_style)
        ]
    ]

    t = Table(table_data, colWidths=[1.2*inch, 2.1*inch, 2.1*inch, 2.1*inch])
    t.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#0284C7')),
        ('ALIGN', (0,0), (-1,-1), 'LEFT'),
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#CBD5E1')),
        ('BACKGROUND', (0,1), (-1,1), colors.HexColor('#F8FAFC')),
        ('BACKGROUND', (0,3), (-1,3), colors.HexColor('#F8FAFC')),
        ('BACKGROUND', (0,5), (-1,5), colors.HexColor('#F8FAFC')),
        ('TOPPADDING', (0,0), (-1,-1), 4),
        ('BOTTOMPADDING', (0,0), (-1,-1), 4),
    ]))
    elements.append(t)
    elements.append(Spacer(1, 10))

    # Section 3: End-to-End User Journey
    elements.append(Paragraph("3. Agent İstifadəçi Prosesi / Agent User Journey", h1_style))
    
    journey_steps = [
        ("Mərhələ 1: Qeydiyyat və Bot Başlanğıcı", "Agent Telegram (@bot) və ya WhatsApp nömrəsinə (+994 50 123 45 67) 'Salam' yazır. Bot agentin adını və növünü (Fərdi Agent / Agentlik) qeyd edərək hesabı 'pending' statusunda yaradır."),
        ("Mərhələ 2: Tarif Seçimi və Aktivasiya", "Agent abunəlik tarifini (Free, Starter, Pro, Agency) seçir. Admin nağd/M10 ödənişini Admin Panelində qeyd edir və hesabı 30 günlük aktiv edir."),
        ("Mərhələ 3: Axtarış Yaratmaq (Təbii Mətnlə)", "Agent sərbəst şəkildə yazır: 'Yasamalda 100-150 min AZN 3 otaqlı yeni tikili ev sahibindən'. AI mətn analiz edir və parametr kimi yadda saxlayır."),
        ("Mərhələ 4: Avtomatik İzləmə və AI Uyğunluq", "Celery hər 15 dəqiqədən bir 17 saytdan yeni elanları toplayır. AI elanı agent kriteriyası ilə müqayisə edir (>=65% uyğunluq olduqda bildiriş hazırlayır)."),
        ("Mərhələ 5: Anında Bildiriş və Düymələr", "Elan WhatsApp/Telegram bota interaktiv düymələrlə ('Maraqlanıram' / 'Keç' / 'Satılıb') çatdırılır."),
        ("Mərhələ 6: Avtomatik Ehtiyat Nüsxə (BaaS)", "Pro və Agency abunəçiləri üçün sistem həftəlik/gündəlik avtomatik client axtarışlarının ehtiyat nüsxəsini (backup.gz) çıxarır.")
    ]

    for title, desc in journey_steps:
        elements.append(Paragraph(f"<b>{title}</b>", h2_style))
        elements.append(Paragraph(desc, body_style))

    elements.append(Spacer(1, 10))

    # Section 4: Master Bot Command Reference
    elements.append(Paragraph("4. Bot Əmr Siyahısı və Nümunələr (Azerbaijani / English)", h1_style))

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
            Paragraph("Əsas əmr menyusunu və kömək təlimatını göstərir", table_cell_style),
            Paragraph("<i>🤖 RealEstate AI Agent - Əmr Siyahısı...</i>", table_cell_style)
        ],
        [
            Paragraph("<b>Axtarışlarım</b>", table_cell_style),
            Paragraph("<code>/list</code>, <code>1</code>", table_cell_style),
            Paragraph("Sizin aktiv və dayandırılmış axtarışlarınızı sadalayır", table_cell_style),
            Paragraph("<i>🟢 #102 Axtarış: Yasamal (3 otaqlı)</i>", table_cell_style)
        ],
        [
            Paragraph("<b>Yeni axtarış</b>", table_cell_style),
            Paragraph("<code>/add</code>, <code>2</code>", table_cell_style),
            Paragraph("Sərbəst mətni AI ilə analiz edib yeni axtarış yaradır", table_cell_style),
            Paragraph("<i>✅ Yeni axtarış saxlanıldı! (#102)</i>", table_cell_style)
        ],
        [
            Paragraph("<b>Kanalı dəyiş</b>", table_cell_style),
            Paragraph("<code>/channel</code>, <code>3</code>", table_cell_style),
            Paragraph("Bildiriş kanalını keçirir (WhatsApp ↔ Telegram)", table_cell_style),
            Paragraph("<i>Bildiriş kanalı: WhatsApp 📲</i>", table_cell_style)
        ],
        [
            Paragraph("<b>Planım nə vaxt bitir?</b>", table_cell_style),
            Paragraph("<code>/status</code>, <code>4</code>", table_cell_style),
            Paragraph("Tarif statusunu və abunəliyin bitmə tarixini göstərir", table_cell_style),
            Paragraph("<i>▪️ Status: Aktiv ✅ Bitmə: 2026-09-10</i>", table_cell_style)
        ],
        [
            Paragraph("<b>Dayandır &lt;id&gt; / Aktiv et &lt;id&gt;</b>", table_cell_style),
            Paragraph("<code>/pause</code>, <code>/resume</code>", table_cell_style),
            Paragraph("Seçilmiş axtarışı müvəqqəti saxlayır və ya bərpa edir", table_cell_style),
            Paragraph("<i>Axtarış #102 dayandırıldı ⏸️</i>", table_cell_style)
        ],
        [
            Paragraph("<b>Sil &lt;id&gt;</b>", table_cell_style),
            Paragraph("<code>/delete</code>, <code>7</code>", table_cell_style),
            Paragraph("Köhnə axtarış parametrlərini silir", table_cell_style),
            Paragraph("<i>Axtarış #102 silindi 🗑️</i>", table_cell_style)
        ]
    ]

    t_cmd = Table(cmd_data, colWidths=[1.4*inch, 1.4*inch, 2.3*inch, 2.4*inch])
    t_cmd.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#0F172A')),
        ('ALIGN', (0,0), (-1,-1), 'LEFT'),
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#CBD5E1')),
        ('BACKGROUND', (0,1), (-1,1), colors.HexColor('#F8FAFC')),
        ('BACKGROUND', (0,3), (-1,3), colors.HexColor('#F8FAFC')),
        ('BACKGROUND', (0,5), (-1,5), colors.HexColor('#F8FAFC')),
        ('BACKGROUND', (0,7), (-1,7), colors.HexColor('#F8FAFC')),
        ('TOPPADDING', (0,0), (-1,-1), 4),
        ('BOTTOMPADDING', (0,0), (-1,-1), 4),
    ]))
    elements.append(t_cmd)

    doc.build(elements)
    print(f"PDF successfully generated at: {pdf_path}")
    return str(pdf_path)

if __name__ == "__main__":
    build_pdf()
