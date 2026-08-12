import os
import logging
from pathlib import Path
from typing import Dict, Any
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.listing import Listing
from app.models.tenant import Tenant
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

logger = logging.getLogger(__name__)

BROCHURE_DIR = Path("/app/brochures") if os.path.exists("/app") else Path(__file__).parent.parent.parent / "brochures"

import html

def setup_fonts() -> tuple[str, str]:
    font_candidates = [
        ('/System/Library/Fonts/Supplemental/Arial.ttf', '/System/Library/Fonts/Supplemental/Arial Bold.ttf'),
        ('/Library/Fonts/Arial.ttf', '/Library/Fonts/Arial Bold.ttf'),
        ('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf', '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf')
    ]
    for reg, bold in font_candidates:
        if os.path.exists(reg):
            try:
                pdfmetrics.registerFont(TTFont('CustomAzFont', reg))
                pdfmetrics.registerFont(TTFont('CustomAzFont-Bold', bold if os.path.exists(bold) else reg))
                return ('CustomAzFont', 'CustomAzFont-Bold')
            except Exception:
                pass
    return ('Helvetica', 'Helvetica-Bold')

class BrochureGeneratorService:
    @staticmethod
    async def generate_property_brochure(db: AsyncSession, listing_id: int, tenant_id: int) -> Dict[str, Any]:
        """Generates branded PDF brochure and Instagram carousel text for a property listing."""
        reg_font, bold_font = setup_fonts()
        stmt_l = select(Listing).where(Listing.id == listing_id)
        res_l = await db.execute(stmt_l)
        listing = res_l.scalars().first()

        stmt_t = select(Tenant).where(Tenant.id == tenant_id)
        res_t = await db.execute(stmt_t)
        tenant = res_t.scalars().first()

        if not listing:
            return {"success": False, "error": "Listing not found"}

        agent_name = tenant.name if tenant else "Əmlak Agentliyi"
        agent_phone = tenant.phone if tenant else "+994501234567"

        # Escaped text for ReportLab XML compliance
        title_escaped = html.escape(listing.title or "Əmlak Elanı")
        agent_name_escaped = html.escape(agent_name)
        desc_escaped = html.escape(listing.description or "Ətraflı məlumat üçün əlaqə saxlayın.")

        # 1. Instagram Carousel Text Generation
        instagram_caption = (
            f"🏠 {listing.title}\n\n"
            f"💰 Qiymət: {int(listing.price)} {listing.currency}\n"
            f"📍 Məkan: {listing.district or 'Bakı'}\n"
            f"📐 Otaq: {listing.rooms or '-'} otaqlı | Sahə: {listing.area_sqm or '-'} m²\n"
            f"🏢 Bina: {'Yeni tikili' if listing.building_type == 'new' else 'Köhnə tikili'}\n\n"
            f"📞 Əlaqə & Baxış üçün: {agent_phone} ({agent_name})\n\n"
            f"#emlak #baku #bina #menzil #satilir #yasamal #realestate"
        )

        # 2. PDF Brochure Generation
        BROCHURE_DIR.mkdir(parents=True, exist_ok=True)
        filename = f"brochure_listing_{listing_id}_tenant_{tenant_id}.pdf"
        filepath = BROCHURE_DIR / filename

        doc = SimpleDocTemplate(str(filepath), pagesize=letter, rightMargin=0.5*inch, leftMargin=0.5*inch, topMargin=0.5*inch, bottomMargin=0.5*inch)
        styles = getSampleStyleSheet()

        title_style = ParagraphStyle('BTitle', parent=styles['Heading1'], fontName=bold_font, fontSize=20, leading=24, textColor=colors.HexColor('#0F172A'), spaceAfter=8)
        sub_style = ParagraphStyle('BSub', parent=styles['Normal'], fontName=reg_font, fontSize=10, leading=14, textColor=colors.HexColor('#475569'), spaceAfter=12)
        body_style = ParagraphStyle('BBody', parent=styles['Normal'], fontName=reg_font, fontSize=10, leading=14, textColor=colors.HexColor('#334155'), spaceAfter=6)

        elements = [
            Paragraph(f"<b>{agent_name_escaped}</b> — Eksklüziv Əmlak Broşuru", sub_style),
            Paragraph(title_escaped, title_style),
            HRFlowable(width="100%", thickness=1.5, color=colors.HexColor('#0284C7'), spaceAfter=12),
            Paragraph(f"<b>Qiymət:</b> {int(listing.price)} {listing.currency}", body_style),
            Paragraph(f"<b>Məkan:</b> {html.escape(listing.district or 'Bakı')}", body_style),
            Paragraph(f"<b>Otaq Sayı:</b> {listing.rooms or '-'} otaqlı", body_style),
            Paragraph(f"<b>Sahə:</b> {listing.area_sqm or '-'} m²", body_style),
            Paragraph(f"<b>Təsvir:</b> {desc_escaped}", body_style),
            Spacer(1, 15),
            Paragraph(f"<b>Əlaqədar Agent:</b> {agent_name_escaped} | <b>Tel:</b> {html.escape(agent_phone)}", title_style)
        ]

        doc.build(elements)
        logger.info(f"[BrochureGenerator] Generated brochure PDF: {filepath}")

        return {
            "success": True,
            "filename": filename,
            "pdf_path": str(filepath),
            "instagram_caption": instagram_caption
        }
