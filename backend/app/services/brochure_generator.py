import html
import os
import logging
from pathlib import Path
from typing import Dict, Any, Tuple
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.listing import Listing
from app.models.tenant import Tenant

logger = logging.getLogger(__name__)

BROCHURE_DIR = Path("/app/brochures") if os.path.exists("/app") else Path(__file__).parent.parent.parent / "brochures"

def setup_fonts() -> Tuple[str, str]:
    try:
        from reportlab.pdfbase import pdfmetrics
        from reportlab.pdfbase.ttfonts import TTFont

        app_fonts_dir = Path(__file__).parent.parent / "fonts"
        font_candidates = [
            # 1. Bundled application fonts
            (str(app_fonts_dir / "DejaVuSans.ttf"), str(app_fonts_dir / "DejaVuSans-Bold.ttf")),
            (str(app_fonts_dir / "Arial.ttf"), str(app_fonts_dir / "Arial Bold.ttf")),
            # 2. Linux / Debian / Docker system fonts
            ('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf', '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf'),
            ('/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf', '/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf'),
            ('/usr/share/fonts/truetype/freefont/FreeSans.ttf', '/usr/share/fonts/truetype/freefont/FreeSansBold.ttf'),
            # 3. macOS system fonts
            ('/System/Library/Fonts/Supplemental/Arial.ttf', '/System/Library/Fonts/Supplemental/Arial Bold.ttf'),
            ('/Library/Fonts/Arial.ttf', '/Library/Fonts/Arial Bold.ttf'),
            ('/System/Library/Fonts/Supplemental/Arial Unicode.ttf', '/System/Library/Fonts/Supplemental/Arial Unicode.ttf')
        ]
        for reg, bold in font_candidates:
            if os.path.exists(reg):
                try:
                    pdfmetrics.registerFont(TTFont('CustomAzFont', reg))
                    bold_file = bold if os.path.exists(bold) else reg
                    pdfmetrics.registerFont(TTFont('CustomAzFont-Bold', bold_file))
                    return ('CustomAzFont', 'CustomAzFont-Bold')
                except Exception as e_reg:
                    logger.debug(f"[BrochureGenerator] Font registration error for {reg}: {e_reg}")
    except Exception as e:
        logger.warning(f"[BrochureGenerator] setup_fonts error: {e}")
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

        # Property type and deal classification
        prop_map = {
            "apartment": "Mənzil",
            "house": "Həyət evi / Villa",
            "villa": "Həyət evi / Villa",
            "office": "Ofis",
            "commercial": "Obyekt / Qeyri-yaşayış",
            "land": "Torpaq sahəsi"
        }
        prop_type_val = getattr(listing, 'property_type', 'apartment') or 'apartment'
        prop_label = prop_map.get(prop_type_val, "Mənzil")
        offer_val = getattr(listing, 'offer_type', 'sale') or 'sale'

        # Clean title to prevent duplicate price or portal artifacts
        import re
        clean_title = re.sub(r'\s*\d+\s*(?:AZN|₼|USD|\$|\/\s*ay|\/\s*gün)', '', listing.title or '').strip()
        clean_title = re.sub(r'\s*\(?\s*satılır\s*\)?', '', clean_title, flags=re.I)
        clean_title = re.sub(r'\s*\(?\s*icarə\s*\)?', '', clean_title, flags=re.I)
        clean_title = re.sub(r'\s*,\s*$', '', clean_title).strip()
        if not clean_title or len(clean_title) < 5:
            loc_name = listing.district or listing.metro_station or 'Bakı'
            clean_title = f"{listing.rooms or ''} otaqlı {prop_label} ({loc_name})".strip()

        # Price formatting
        if offer_val == 'daily_rent':
            price_str = f"{int(listing.price)} {listing.currency} / gün (günlük)"
        elif offer_val in ['rent', 'kiraye', 'icare']:
            price_str = f"{int(listing.price)} {listing.currency} / ay (kirayə)"
        else:
            price_str = f"{int(listing.price)} {listing.currency}"

        # Location formatting
        loc_display = listing.district or listing.metro_station or listing.address_raw or "Bakı"
        if listing.district and listing.metro_station:
            loc_display = f"{listing.district} ({listing.metro_station} m.)"

        # Building / Property classification line
        type_line = ""
        if prop_type_val in ["house", "villa"]:
            type_line = "🏷️ Növ: Həyət evi / Villa"
        elif prop_type_val in ["office", "commercial"]:
            type_line = f"🏷️ Növ: {prop_label}"
        elif prop_type_val == "land":
            type_line = "🏷️ Növ: Torpaq sahəsi"
        elif listing.building_type == "new":
            type_line = "🏢 Bina: Yeni tikili"
        elif listing.building_type == "old":
            type_line = "🏢 Bina: Köhnə tikili"

        type_block = f"{type_line}\n" if type_line else ""

        # Floor line
        floor_line = ""
        if listing.floor and listing.total_floors:
            floor_line = f"🏢 Mərtəbə: {listing.floor}/{listing.total_floors}\n"
        elif listing.floor:
            floor_line = f"🏢 Mərtəbə: {listing.floor}-ci mərtəbə\n"

        # Dynamic hashtags
        dist_tag = re.sub(r'\W+', '', (listing.district or 'baku').lower())
        prop_tag = "villa" if prop_type_val in ["house", "villa"] else ("ofis" if prop_type_val == "office" else ("obyekt" if prop_type_val == "commercial" else ("torpaq" if prop_type_val == "land" else "menzil")))
        deal_tag = "kiraye" if offer_val in ["rent", "daily_rent"] else "satilir"
        hashtags = f"#emlak #baku #{deal_tag} #{prop_tag} #{dist_tag} #realestate"

        # 1. Instagram / Client Sharing Text Generation
        instagram_caption = (
            f"🏠 {clean_title}\n\n"
            f"💰 Qiymət: {price_str}\n"
            f"📍 Məkan: {loc_display}\n"
            f"📐 Otaq: {listing.rooms or '-'} otaqlı | Sahə: {listing.area_sqm or '-'} m²\n"
            f"{type_block}"
            f"{floor_line}\n"
            f"📞 Əlaqə & Baxış üçün: {agent_phone} ({agent_name})\n\n"
            f"{hashtags}"
        )

        # Escaped text for ReportLab XML compliance
        title_escaped = html.escape(clean_title)
        agent_name_escaped = html.escape(agent_name)
        desc_escaped = html.escape(listing.description or "Ətraflı məlumat üçün əlaqə saxlayın.")

        # 2. PDF Brochure Generation
        pdf_generated = False
        filename = f"brochure_listing_{listing_id}_tenant_{tenant_id}.pdf"
        filepath = BROCHURE_DIR / filename
        from app.core.config import settings
        base_domain = (settings.PUBLIC_BASE_URL or "https://realtor-api.erma.shop").rstrip('/')
        brochure_url = f"{base_domain}/brochures/{filename}"

        try:
            from reportlab.lib.pagesizes import letter
            from reportlab.lib import colors
            from reportlab.lib.units import inch
            from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
            from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle

            BROCHURE_DIR.mkdir(parents=True, exist_ok=True)
            doc = SimpleDocTemplate(str(filepath), pagesize=letter, rightMargin=0.5*inch, leftMargin=0.5*inch, topMargin=0.5*inch, bottomMargin=0.5*inch)
            styles = getSampleStyleSheet()

            title_style = ParagraphStyle('BTitle', parent=styles['Heading1'], fontName=bold_font, fontSize=18, leading=22, textColor=colors.HexColor('#0F172A'), spaceAfter=8)
            sub_style = ParagraphStyle('BSub', parent=styles['Normal'], fontName=reg_font, fontSize=10, leading=14, textColor=colors.HexColor('#475569'), spaceAfter=12)
            body_style = ParagraphStyle('BBody', parent=styles['Normal'], fontName=reg_font, fontSize=10, leading=14, textColor=colors.HexColor('#334155'), spaceAfter=6)

            elements = [
                Paragraph(f"<b>{agent_name_escaped}</b> — Eksklüziv Əmlak Təqdimatı", sub_style),
                Paragraph(title_escaped, title_style),
                HRFlowable(width="100%", thickness=1.5, color=colors.HexColor('#0284C7'), spaceAfter=12),
                Paragraph(f"<b>Qiymət:</b> {price_str}", body_style),
                Paragraph(f"<b>Məkan:</b> {html.escape(loc_display)}", body_style),
                Paragraph(f"<b>Otaq Sayı:</b> {listing.rooms or '-'} otaqlı", body_style),
                Paragraph(f"<b>Sahə:</b> {listing.area_sqm or '-'} m²", body_style),
                Paragraph(f"<b>Təsvir:</b> {desc_escaped}", body_style),
                Spacer(1, 15),
                Paragraph(f"<b>Əlaqədar Agent:</b> {agent_name_escaped} | <b>Tel:</b> {html.escape(agent_phone)}", title_style)
            ]

            doc.build(elements)
            pdf_generated = True
            logger.info(f"[BrochureGenerator] Generated brochure PDF: {filepath}")
        except Exception as e:
            logger.warning(f"[BrochureGenerator] PDF generation skipped/fallback ({e})")

        return {
            "success": True,
            "filename": filename if pdf_generated else None,
            "pdf_path": str(filepath) if pdf_generated else None,
            "brochure_url": brochure_url if pdf_generated else None,
            "instagram_caption": instagram_caption
        }
