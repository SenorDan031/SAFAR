"""
SAFAR Lane & Ego Corridor System PDF Guide Generator
Generates a publication-quality visual PDF specification with vector diagrams and tables.
"""

import os
import sys
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, KeepTogether, HRFlowable
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.graphics.shapes import Drawing, Rect, String, Line, Group, Polygon
from reportlab.pdfgen import canvas

OUTPUT_PDF_PATH = r"C:\Users\shrey\OneDrive\Desktop\Projects\SAFAR\docs\SAFAR_LANE_SYSTEM_GUIDE.pdf"
BRAIN_PDF_PATH = r"C:\Users\shrey\.gemini\antigravity\brain\4bb433f6-55ac-41c9-951b-c1ec39074f17\SAFAR_LANE_SYSTEM_GUIDE.pdf"


class NumberedCanvas(canvas.Canvas):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._saved_page_states = []

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        num_pages = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self.draw_page_decorations(num_pages)
            super().showPage()
        super().save()

    def draw_page_decorations(self, page_count):
        self.saveState()
        self.setFont("Helvetica", 8)
        self.setFillColor(colors.HexColor("#64748b"))

        if self._pageNumber > 1:
            self.drawString(54, 750, "SAFAR: Lane & Ego Driving Corridor System Specification")
            self.setStrokeColor(colors.HexColor("#cbd5e1"))
            self.setLineWidth(0.5)
            self.line(54, 744, 558, 744)

        self.setStrokeColor(colors.HexColor("#cbd5e1"))
        self.setLineWidth(0.5)
        self.line(54, 48, 558, 48)
        self.drawRightString(558, 36, f"Page {self._pageNumber} of {page_count}")
        self.drawString(54, 36, "SAFAR ADAS ARCHITECTURE — LANE GEOMETRY & TRAJECTORY SYSTEM")
        self.restoreState()


def create_corridor_vector_diagram():
    """Generates an illustrative vector diagram of the 4 lateral zones."""
    d = Drawing(504, 150)

    # Road Background
    d.add(Rect(0, 15, 504, 120, fillColor=colors.HexColor("#1e293b"), strokeColor=colors.HexColor("#0f172a"), strokeWidth=1, rx=4, ry=4))

    # Road Shoulders / Sidewalks (Green zones)
    d.add(Rect(0, 15, 90, 120, fillColor=colors.HexColor("#064e3b"), strokeColor=colors.HexColor("#059669"), strokeWidth=1))
    d.add(Rect(414, 15, 90, 120, fillColor=colors.HexColor("#064e3b"), strokeColor=colors.HexColor("#059669"), strokeWidth=1))
    d.add(String(15, 115, "ZONE 4: SHOULDER", fontName="Helvetica-Bold", fontSize=7, fillColor=colors.HexColor("#6ee7b7")))
    d.add(String(15, 103, "(|X| > 1.85m -> SAFE)", fontName="Helvetica", fontSize=6, fillColor=colors.HexColor("#a7f3d0")))

    d.add(String(422, 115, "ZONE 4: SHOULDER", fontName="Helvetica-Bold", fontSize=7, fillColor=colors.HexColor("#6ee7b7")))
    d.add(String(422, 103, "(|X| > 1.85m -> SAFE)", fontName="Helvetica", fontSize=6, fillColor=colors.HexColor("#a7f3d0")))

    # Lane Margins (Yellow zones)
    d.add(Rect(90, 15, 65, 120, fillColor=colors.HexColor("#78350f"), strokeColor=colors.HexColor("#d97706"), strokeWidth=1))
    d.add(Rect(349, 15, 65, 120, fillColor=colors.HexColor("#78350f"), strokeColor=colors.HexColor("#d97706"), strokeWidth=1))
    d.add(String(95, 115, "ZONE 3: MARGIN", fontName="Helvetica-Bold", fontSize=7, fillColor=colors.HexColor("#fde68a")))
    d.add(String(95, 103, "(1.05m < |X| <= 1.85m)", fontName="Helvetica", fontSize=5.5, fillColor=colors.HexColor("#fef3c7")))

    d.add(String(354, 115, "ZONE 3: MARGIN", fontName="Helvetica-Bold", fontSize=7, fillColor=colors.HexColor("#fde68a")))
    d.add(String(354, 103, "(1.05m < |X| <= 1.85m)", fontName="Helvetica", fontSize=5.5, fillColor=colors.HexColor("#fef3c7")))

    # Chassis Envelope (Zone 2)
    d.add(Rect(155, 15, 194, 120, fillColor=colors.HexColor("#0f172a"), strokeColor=colors.HexColor("#38bdf8"), strokeWidth=1.5))
    d.add(String(200, 125, "ZONE 2: CHASSIS ENVELOPE (|X| <= 1.05m)", fontName="Helvetica-Bold", fontSize=7, fillColor=colors.HexColor("#38bdf8")))

    # Left Wheel Track (Red Zone 1)
    d.add(Rect(165, 20, 36, 95, fillColor=colors.HexColor("#7f1d1d"), strokeColor=colors.HexColor("#ef4444"), strokeWidth=1.5, rx=3, ry=3))
    d.add(String(168, 70, "LEFT TIRE", fontName="Helvetica-Bold", fontSize=6.5, fillColor=colors.HexColor("#fca5a5")))
    d.add(String(168, 60, "(-0.80m)", fontName="Helvetica", fontSize=6, fillColor=colors.white))
    d.add(String(168, 48, "🔴 STRIKE", fontName="Helvetica-Bold", fontSize=6, fillColor=colors.HexColor("#fecaca")))

    # Right Wheel Track (Red Zone 1)
    d.add(Rect(303, 20, 36, 95, fillColor=colors.HexColor("#7f1d1d"), strokeColor=colors.HexColor("#ef4444"), strokeWidth=1.5, rx=3, ry=3))
    d.add(String(306, 70, "RIGHT TIRE", fontName="Helvetica-Bold", fontSize=6.5, fillColor=colors.HexColor("#fca5a5")))
    d.add(String(306, 60, "(+0.80m)", fontName="Helvetica", fontSize=6, fillColor=colors.white))
    d.add(String(306, 48, "🔴 STRIKE", fontName="Helvetica-Bold", fontSize=6, fillColor=colors.HexColor("#fecaca")))

    # Undercarriage Center Zone
    d.add(Rect(205, 30, 94, 75, fillColor=colors.HexColor("#1e1b4b"), strokeColor=colors.HexColor("#818cf8"), strokeWidth=1, strokeDashArray=[3, 3]))
    d.add(String(215, 75, "UNDERCARRIAGE", fontName="Helvetica-Bold", fontSize=6.5, fillColor=colors.HexColor("#c7d2fe")))
    d.add(String(215, 65, "Center (0.0m)", fontName="Helvetica", fontSize=6, fillColor=colors.white))
    d.add(String(215, 52, "Clearance: 16cm", fontName="Helvetica-Bold", fontSize=6, fillColor=colors.HexColor("#a5b4fc")))

    # Centerline Dashed Marking
    d.add(Line(252, 15, 252, 135, strokeColor=colors.HexColor("#fbbf24"), strokeWidth=1.5, strokeDashArray=[6, 4]))

    return d


def build_pdf():
    doc = SimpleDocTemplate(
        OUTPUT_PDF_PATH,
        pagesize=letter,
        leftMargin=54,
        rightMargin=54,
        topMargin=54,
        bottomMargin=54
    )

    styles = getSampleStyleSheet()

    c_primary = colors.HexColor("#0f172a")
    c_accent = colors.HexColor("#1e40af")
    c_cyan = colors.HexColor("#0369a1")
    c_text = colors.HexColor("#334155")
    c_border = colors.HexColor("#e2e8f0")
    c_bg_subtle = colors.HexColor("#f8fafc")

    title_style = ParagraphStyle("TStyle", fontName="Helvetica-Bold", fontSize=22, leading=26, textColor=c_primary, spaceAfter=4)
    subtitle_style = ParagraphStyle("SubStyle", fontName="Helvetica", fontSize=11, leading=15, textColor=c_cyan, spaceAfter=12)
    h1_style = ParagraphStyle("H1Style", fontName="Helvetica-Bold", fontSize=13, leading=17, textColor=c_accent, spaceBefore=10, spaceAfter=4, keepWithNext=True)
    h2_style = ParagraphStyle("H2Style", fontName="Helvetica-Bold", fontSize=10, leading=14, textColor=c_primary, spaceBefore=8, spaceAfter=3, keepWithNext=True)
    body_style = ParagraphStyle("BStyle", fontName="Helvetica", fontSize=8, leading=11.5, textColor=c_text, spaceAfter=3)
    bullet_style = ParagraphStyle("BulStyle", fontName="Helvetica", fontSize=8, leading=11.5, textColor=c_text, leftIndent=10, spaceAfter=2)

    th_style = ParagraphStyle("THStyle", fontName="Helvetica-Bold", fontSize=7.5, leading=9.5, textColor=colors.white)
    td_style = ParagraphStyle("TDStyle", fontName="Helvetica", fontSize=7, leading=9, textColor=c_text)
    td_bold = ParagraphStyle("TDBold", fontName="Helvetica-Bold", fontSize=7, leading=9, textColor=c_primary)

    story = []

    # Title & Header
    story.append(Paragraph("🛣️ SAFAR: Lane & Ego Driving Corridor System", title_style))
    story.append(Paragraph("Geometric Lateral Reasoning, Wheel Track Collision Protection & Trajectory Lookahead", subtitle_style))
    story.append(HRFlowable(width="100%", thickness=1.5, color=c_accent, spaceBefore=0, spaceAfter=8))

    # 1. Executive Purpose
    story.append(Paragraph("1. Executive Purpose: Eliminating Phantom Braking", h1_style))
    story.append(Paragraph(
        "In complex urban and highway driving, obstacles and surface hazards exist constantly in adjacent lanes, on sidewalks, and along road shoulders. "
        "A naive safety system that brakes for every detected object will cause dangerous false alarms. "
        "The <b>SAFAR Lane & Driving Corridor System</b> provides continuous lateral geometric boundary evaluation to determine if an anomaly physically intersects the vehicle's driving path.",
        body_style
    ))
    story.append(Spacer(1, 4))

    # 2. Visual Architecture Diagram
    story.append(Paragraph("2. Multi-Zone Geometric Corridor Architecture", h1_style))
    story.append(create_corridor_vector_diagram())
    story.append(Spacer(1, 6))

    # 3. Zone Breakdown Table
    story.append(Paragraph("3. The Four Lateral Corridor Zones", h1_style))

    zone_data = [
        [Paragraph("Zone", th_style), Paragraph("Coordinates (X)", th_style), Paragraph("Strike Target", th_style), Paragraph("Lateral Multiplier", th_style), Paragraph("Safety Action & Control Logic", th_style)],
        [Paragraph("Zone 1: Wheel Tracks", td_bold), Paragraph("Left: -0.80m ± 0.125m<br/>Right: +0.80m ± 0.125m", td_style), Paragraph("Tires / Rims / Steering Knuckle", td_style), Paragraph("1.00 (Max)", td_style), Paragraph("Direct wheel strike. Applies active braking for deep potholes/craters.", td_style)],
        [Paragraph("Zone 2: Chassis Envelope", td_bold), Paragraph("|X| <= 1.05m (Total: 2.10m)", td_style), Paragraph("Undercarriage / Oil Pan", td_style), Paragraph("0.90 (if D > 14cm)<br/>0.40 (if D <= 12cm)", td_style), Paragraph("Evaluates depth vs 16cm ground clearance. Safe shallow ruts pass over.", td_style)],
        [Paragraph("Zone 3: Lane Margin", td_bold), Paragraph("1.05m < |X| <= 1.85m", td_style), Paragraph("Adjacent Lane / Grazing", td_style), Paragraph("0.50 (Moderate)", td_style), Paragraph("Tagged as POSSIBLE_INTERSECTION. Speed moderated without hard braking.", td_style)],
        [Paragraph("Zone 4: Road Shoulder", td_bold), Paragraph("|X| > 1.85m to 10.0m", td_style), Paragraph("Sidewalk / Opposing Lane", td_style), Paragraph("0.05 (Ignored)", td_style), Paragraph("Tagged as PATH_CLEAR. 100% ignored. Manual driving uninterrupted.", td_style)]
    ]

    t_zone = Table(zone_data, colWidths=[90, 95, 95, 75, 149])
    t_zone.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), c_accent),
        ('GRID', (0, 0), (-1, -1), 0.5, c_border),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, c_bg_subtle]),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, -1), 3),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
    ]))
    story.append(t_zone)
    story.append(Spacer(1, 6))

    # 4. Dynamic Steering & Lookahead
    story.append(Paragraph("4. Dynamic Curved Path & Steering Projection", h1_style))
    story.append(Paragraph(
        "When the vehicle turns, the corridor projects dynamically along the steering radius rather than remaining straight:",
        body_style
    ))
    story.append(Paragraph("<b>Curved Path Formulation:</b> <code>X_effective(d) = X_measured - 0.5 * (v^2 / R) * tan(delta_steering) * (d / v)</code>", body_style))
    story.append(Paragraph("• <b>Steering Left</b>: Shifts the future corridor leftward. Obstacles straight ahead safely exit the corridor.", bullet_style))
    story.append(Paragraph("• <b>Steering Right</b>: Shifts the corridor rightward, detecting hazards inside the curve.", bullet_style))
    story.append(Spacer(1, 4))

    # 5. Trajectory Lookahead & Pre-Corridor Crossing
    story.append(Paragraph("5. Trajectory Lookahead & Crossing Threat Prediction", h1_style))
    story.append(Paragraph(
        "For crossing pedestrians and merging two-wheelers, SAFAR projects lateral motion: <code>X_target(t) = X_0 + V_lat * t</code>. "
        "If a pedestrian currently in Zone 4 (sidewalk) will enter Zone 2 (chassis envelope) at the exact arrival time (<code>t = TTC</code>), "
        "SAFAR flags a <b>Pre-Corridor Crossing Threat</b> and initiates early deceleration.",
        body_style
    ))
    story.append(Spacer(1, 4))

    # 6. Implementation Map
    story.append(Paragraph("6. Implementation Map", h1_style))
    story.append(Paragraph("• <b><code>safar/pothole/path.py</code></b>: Computes wheel strike overlap and undercarriage ground clearance checks.", bullet_style))
    story.append(Paragraph("• <b><code>safar/pothole/config.py</code></b>: Defines <code>VEHICLE_HALF_WIDTH_M = 1.05m</code> and <code>LANE_HALF_WIDTH_M = 1.75m</code>.", bullet_style))
    story.append(Paragraph("• <b><code>Prediction/SAFARTrajectoryPredictor.h</code></b>: 60 Hz UE5 C++ trajectory predictor for curved paths and cut-in traffic.", bullet_style))

    doc.build(story, canvasmaker=NumberedCanvas)

    import shutil
    shutil.copy2(OUTPUT_PDF_PATH, BRAIN_PDF_PATH)
    print(f"Lane System PDF Generated Successfully at:\n  {OUTPUT_PDF_PATH}\n  {BRAIN_PDF_PATH}")


if __name__ == "__main__":
    build_pdf()
