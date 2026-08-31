"""
SAFAR PDF Documentation Generator
Converts SAFAR_COMPLETE_SYSTEM_REFERENCE.md into a beautifully formatted, publication-quality PDF.
"""

import os
import sys
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter, A4
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, KeepTogether, HRFlowable
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.pdfgen import canvas

SOURCE_MD_PATH = r"C:\Users\shrey\OneDrive\Desktop\Projects\SAFAR\docs\SAFAR_COMPLETE_SYSTEM_REFERENCE.md"
OUTPUT_PDF_PATH = r"C:\Users\shrey\OneDrive\Desktop\Projects\SAFAR\docs\SAFAR_COMPLETE_SYSTEM_REFERENCE.pdf"
BRAIN_PDF_PATH = r"C:\Users\shrey\.gemini\antigravity\brain\4bb433f6-55ac-41c9-951b-c1ec39074f17\SAFAR_COMPLETE_SYSTEM_REFERENCE.pdf"


class NumberedCanvas(canvas.Canvas):
    """Adds running headers and footers with dynamic page numbers."""
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

        # Running Header (on pages after cover page)
        if self._pageNumber > 1:
            self.drawString(54, 750, "SAFAR: System Architecture, Pipeline & Variable Reference Guide")
            self.setStrokeColor(colors.HexColor("#cbd5e1"))
            self.setLineWidth(0.5)
            self.line(54, 744, 558, 744)

        # Running Footer
        self.setStrokeColor(colors.HexColor("#cbd5e1"))
        self.setLineWidth(0.5)
        self.line(54, 48, 558, 48)
        page_str = f"Page {self._pageNumber} of {page_count}"
        self.drawRightString(558, 36, page_str)
        self.drawString(54, 36, "CONFIDENTIAL & PROPRIETARY — SAFAR AI ADAS PROJECT")
        self.restoreState()


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

    # Custom Palette
    c_primary = colors.HexColor("#0f172a")    # Slate 900
    c_accent = colors.HexColor("#1e40af")     # Blue 800
    c_cyan = colors.HexColor("#0369a1")       # Sky 700
    c_text = colors.HexColor("#334155")       # Slate 700
    c_border = colors.HexColor("#e2e8f0")     # Slate 200
    c_bg_subtle = colors.HexColor("#f8fafc")  # Slate 50

    title_style = ParagraphStyle(
        "CoverTitle",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=24,
        leading=28,
        textColor=c_primary,
        spaceAfter=6
    )

    subtitle_style = ParagraphStyle(
        "CoverSubtitle",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=12,
        leading=16,
        textColor=c_cyan,
        spaceAfter=15
    )

    h1_style = ParagraphStyle(
        "Heading1_Custom",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=15,
        leading=19,
        textColor=c_accent,
        spaceBefore=14,
        spaceAfter=6,
        keepWithNext=True
    )

    h2_style = ParagraphStyle(
        "Heading2_Custom",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=11.5,
        leading=15,
        textColor=c_primary,
        spaceBefore=10,
        spaceAfter=4,
        keepWithNext=True
    )

    h3_style = ParagraphStyle(
        "Heading3_Custom",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=9.5,
        leading=13,
        textColor=c_cyan,
        spaceBefore=6,
        spaceAfter=3,
        keepWithNext=True
    )

    body_style = ParagraphStyle(
        "Body_Custom",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=8.5,
        leading=12,
        textColor=c_text,
        spaceAfter=4
    )

    bullet_style = ParagraphStyle(
        "Bullet_Custom",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=8.5,
        leading=12,
        textColor=c_text,
        leftIndent=12,
        spaceAfter=3
    )

    table_header_style = ParagraphStyle(
        "TableHeader",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=8,
        leading=10,
        textColor=colors.white,
        alignment=0
    )

    table_cell_style = ParagraphStyle(
        "TableCell",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=7.5,
        leading=9.5,
        textColor=c_text
    )

    table_cell_bold = ParagraphStyle(
        "TableCellBold",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=7.5,
        leading=9.5,
        textColor=c_primary
    )

    code_style = ParagraphStyle(
        "Code_Custom",
        parent=styles["Normal"],
        fontName="Courier",
        fontSize=7.5,
        leading=10,
        textColor=colors.HexColor("#0f172a")
    )

    story = []

    # Title & Header
    story.append(Paragraph("🛡️ SAFAR — Complete System Reference", title_style))
    story.append(Paragraph("Safety Assisting Forward-looking AI Reflex: Architecture, Pipeline & Variable Specification", subtitle_style))
    story.append(HRFlowable(width="100%", thickness=1.5, color=c_accent, spaceBefore=2, spaceAfter=10))

    # Executive Overview
    story.append(Paragraph("1. Executive Overview & Design Philosophy", h1_style))
    story.append(Paragraph(
        "<b>SAFAR</b> is an advanced, physics-aware, AI-assisted road safety and collision avoidance subsystem designed for realistic vehicle simulation environments (Unreal Engine 5 Chaos Physics) and next-generation Advanced Driver Assistance Systems (ADAS).",
        body_style
    ))
    story.append(Paragraph("<b>Core Operating Principles:</b>", body_style))
    story.append(Paragraph("• <b>Passive Driver Principle</b>: The driver maintains 100% authoritative control by default. SAFAR silently monitors trajectories and stopping limits, intervening only upon confirmed physical hazards.", bullet_style))
    story.append(Paragraph("• <b>Decoupled Perception & Reasoning</b>: Machine Learning models answer strictly <i>'What is this surface/object?'</i>, while deterministic kinematics, corridor geometry, and stopping equations determine physical intervention necessity.", bullet_style))
    story.append(Paragraph("• <b>Failure-Safe Guarantee</b>: Unconfident, missing, or invalid sensor inputs automatically evaluate to <code>PASSIVE</code> without false emergency braking.", bullet_style))
    story.append(Spacer(1, 6))

    # Pipeline Architecture Table
    story.append(Paragraph("2. End-to-End Safety Pipeline Flow", h1_style))
    pipeline_data = [
        [Paragraph("Pipeline Stage", table_header_style), Paragraph("Component", table_header_style), Paragraph("Input → Output", table_header_style), Paragraph("Function", table_header_style)],
        [Paragraph("1. Sensing", table_cell_bold), Paragraph("Virtual Stereo & YOLO", table_cell_style), Paragraph("Raw Camera / World Actors → Bounding Boxes & Disparity", table_cell_style), Paragraph("Detects vehicles, pedestrians, animals, and waterlogged road depressions.", table_cell_style)],
        [Paragraph("2. Validation", table_cell_bold), Paragraph("PotholeDataValidator", table_cell_style), Paragraph("Raw Dimensions → Validated Measurements", table_cell_style), Paragraph("Rejects NaN, Inf, and negative values to prevent crashes.", table_cell_style)],
        [Paragraph("3. Tracking", table_cell_bold), Paragraph("Kinematic Tracker", table_cell_style), Paragraph("Positions over Time → Relative Velocity (V_rel)", table_cell_style), Paragraph("Computes 60Hz velocity vectors and dead reckoning.", table_cell_style)],
        [Paragraph("4. Trajectory", table_cell_bold), Paragraph("Corridor Predictor", table_cell_style), Paragraph("V_rel & Speed → Corridor Intersection & TTC", table_cell_style), Paragraph("Filters objects outside vehicle corridor (|Y| <= 1.05m).", table_cell_style)],
        [Paragraph("5. Physics", table_cell_bold), Paragraph("Kinematics Engine", table_cell_style), Paragraph("Speed & Deceleration → d_stop & Safety Ratio", table_cell_style), Paragraph("Computes stopping distance d = v*t + v^2/(2a).", table_cell_style)],
        [Paragraph("6. Decision", table_cell_bold), Paragraph("State Machine", table_cell_style), Paragraph("Risk Score → Vehicle Command", table_cell_style), Paragraph("Hysteresis (0.70/0.40), >=2-frame confirmation & 0.35s hold.", table_cell_style)],
        [Paragraph("7. Actuation", table_cell_bold), Paragraph("Chaos Vehicle Actuator", table_cell_style), Paragraph("Command → Brake / Throttle", table_cell_style), Paragraph("Speed-gated service braking vs stationary handbrake lock.", table_cell_style)]
    ]
    t_pipe = Table(pipeline_data, colWidths=[65, 95, 160, 184])
    t_pipe.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), c_accent),
        ('GRID', (0, 0), (-1, -1), 0.5, c_border),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, c_bg_subtle]),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
    ]))
    story.append(t_pipe)
    story.append(Spacer(1, 8))

    # File-by-File Summary
    story.append(Paragraph("3. File-by-File Technical Summary", h1_style))

    files_data = [
        ("safar/pothole/config.py", "Central configuration defining physical constants (t_react=0.18s, a_nom=6.0 m/s^2, a_emg=8.5 m/s^2), lane half-widths (1.75m), vehicle envelope (1.05m), safe speed maps, and activation/release thresholds."),
        ("safar/pothole/validation.py", "Data sanitization layer with PotholeDataValidator verifying that dimensions are strictly positive, non-null, finite numbers within valid bounds (W <= 10m, L <= 20m, D <= 1.0m)."),
        ("safar/pothole/model.py", "ML trainer and serialization engine using Stratified 5-Fold Cross-Validation, evaluating Decision Tree, Random Forest, Extra Trees, and Gradient Boosting before exporting pothole_model.joblib."),
        ("safar/pothole/classifier.py", "Decoupled classification answering only 'What surface is this?'. Employs Gradient Boosting with calibrated softmax probabilities, outputting PotholeObservation and flagging confidence < 0.70 as UNCERTAIN."),
        ("safar/pothole/physics.py", "Kinematics engine computing dynamic stopping envelope d_stop = v*t_react + v^2/(2a), required stopping buffer, safety ratio R = d/d_stop, and safe time-to-pothole t = d/v."),
        ("safar/pothole/path.py", "Corridor geometry tracking lateral offset X relative to vehicle centerline, classifying geometry into PATH_CLEAR, POSSIBLE_INTERSECTION, and INTERSECTION."),
        ("safar/pothole/risk.py", "Transparent physical risk engine synthesizing depth severity, approach speed excess, stopping distance ratio, and lateral relevance into continuous danger score [0.0, 1.0]."),
        ("safar/pothole/decision.py", "Finite state machine (MAINTAIN -> MONITOR -> SLOW -> BRAKE -> EMERGENCY_BRAKE) with temporal confirmation (>= 2 frames) and 0.35s anti-flapping hold timers."),
        ("safar/pothole/simulation.py", "Multi-hazard aggregator evaluating all detected anomalies in a single frame and selecting primary threat deterministically."),
        ("safar/perception/yolo_detector.py", "Ultralytics YOLOv8 wrapper performing real-time multi-class road obstacle detection (cars, trucks, motorcycles, pedestrians, dogs) with ego hood rejection."),
        ("tools/test_safar_on_images.py", "End-to-end evaluation pipeline running YOLO + Optical Pothole Segmentation + Kinematics on real-world images with visual HUD overlays and JSON logs."),
        ("Source/TrafficGame/SAFAR/", "Unreal Engine 5 C++ closed-loop driver safety core with Chaos Wheeled Vehicle Movement integration, stereo depth rig, and automatic transmission reverse protection.")
    ]

    for fname, fdesc in files_data:
        story.append(Paragraph(f"• <b><code>{fname}</code></b>: {fdesc}", bullet_style))

    story.append(Spacer(1, 8))

    # Comprehensive Variable Dictionary Table
    story.append(Paragraph("4. Exhaustive Variable & Parameter Dictionary", h1_style))

    var_table_data = [
        [Paragraph("Variable Name", table_header_style), Paragraph("Type / Units", table_header_style), Paragraph("Default", table_header_style), Paragraph("Defined In", table_header_style), Paragraph("Physical / Functional Meaning", table_header_style)],
        [Paragraph("REACTION_TIME_S", table_cell_bold), Paragraph("float (s)", table_cell_style), Paragraph("0.18", table_cell_style), Paragraph("config.py", table_cell_style), Paragraph("Total latency: sensor acquisition + perception + brake pressurization.", table_cell_style)],
        [Paragraph("DECEL_NOMINAL_MPS2", table_cell_bold), Paragraph("float (m/s^2)", table_cell_style), Paragraph("6.0", table_cell_style), Paragraph("config.py", table_cell_style), Paragraph("Nominal service braking deceleration comfort limit on dry pavement.", table_cell_style)],
        [Paragraph("DECEL_EMERGENCY_MPS2", table_cell_bold), Paragraph("float (m/s^2)", table_cell_style), Paragraph("8.5", table_cell_style), Paragraph("config.py", table_cell_style), Paragraph("Maximum deceleration under full anti-lock emergency braking.", table_cell_style)],
        [Paragraph("CONFIDENCE_THRESHOLD", table_cell_bold), Paragraph("float [0, 1]", table_cell_style), Paragraph("0.70", table_cell_style), Paragraph("config.py", table_cell_style), Paragraph("Minimum ML probability required; lower values flagged as UNCERTAIN.", table_cell_style)],
        [Paragraph("ACTIVATION_THRESHOLD", table_cell_bold), Paragraph("float [0, 1]", table_cell_style), Paragraph("0.70", table_cell_style), Paragraph("config.py / Decision", table_cell_style), Paragraph("Threat risk score required to engage active automated braking.", table_cell_style)],
        [Paragraph("RELEASE_THRESHOLD", table_cell_bold), Paragraph("float [0, 1]", table_cell_style), Paragraph("0.40", table_cell_style), Paragraph("config.py / Decision", table_cell_style), Paragraph("Lower risk score boundary required before releasing brakes (hysteresis).", table_cell_style)],
        [Paragraph("MIN_HOLD_DURATION_S", table_cell_bold), Paragraph("float (s)", table_cell_style), Paragraph("0.35", table_cell_style), Paragraph("config.py / Decision", table_cell_style), Paragraph("Anti-flapping hold timer maintaining brake pressure after obstacle clears.", table_cell_style)],
        [Paragraph("THREAT_CONFIRMATION_FRAMES", table_cell_bold), Paragraph("int (frames)", table_cell_style), Paragraph("2", table_cell_style), Paragraph("config.py / Decision", table_cell_style), Paragraph("Consecutive frames obstacle must pose a threat before braking activates.", table_cell_style)],
        [Paragraph("VEHICLE_HALF_WIDTH_M", table_cell_bold), Paragraph("float (m)", table_cell_style), Paragraph("1.05", table_cell_style), Paragraph("config.py / path.py", table_cell_style), Paragraph("Physical half-width of vehicle track plus safety buffer.", table_cell_style)],
        [Paragraph("LANE_HALF_WIDTH_M", table_cell_bold), Paragraph("float (m)", table_cell_style), Paragraph("1.75", table_cell_style), Paragraph("config.py / path.py", table_cell_style), Paragraph("Standard driving lane half-width.", table_cell_style)],
        [Paragraph("CAMERA_FOCAL_LENGTH_PX", table_cell_bold), Paragraph("float (px)", table_cell_style), Paragraph("720.0", table_cell_style), Paragraph("test_safar_on_images", table_cell_style), Paragraph("Focal length used in monocular pinhole distance estimation.", table_cell_style)],
        [Paragraph("CAMERA_MOUNT_HEIGHT_M", table_cell_bold), Paragraph("float (m)", table_cell_style), Paragraph("1.35", table_cell_style), Paragraph("test_safar_on_images", table_cell_style), Paragraph("Height of windshield-mounted ADAS camera above ground plane.", table_cell_style)],
        [Paragraph("STEREO_BASELINE_M", table_cell_bold), Paragraph("float (m)", table_cell_style), Paragraph("0.25", table_cell_style), Paragraph("SAFARSensorRig", table_cell_style), Paragraph("Physical distance between virtual stereo camera lenses in UE5.", table_cell_style)],
        [Paragraph("REVERSE_PREVENTION_SPEED", table_cell_bold), Paragraph("float (m/s)", table_cell_style), Paragraph("0.5", table_cell_style), Paragraph("SAFARVehicleComp", table_cell_style), Paragraph("Speed cutoff where service brake is replaced with handbrake lock.", table_cell_style)]
    ]

    t_var = Table(var_table_data, colWidths=[105, 55, 40, 85, 219])
    t_var.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), c_accent),
        ('GRID', (0, 0), (-1, -1), 0.5, c_border),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, c_bg_subtle]),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('TOPPADDING', (0, 0), (-1, -1), 3),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
    ]))
    story.append(t_var)
    story.append(Spacer(1, 8))

    # Mathematical Formulations
    story.append(Paragraph("5. Key Mathematical Formulations", h1_style))
    story.append(Paragraph("<b>1. Dynamic Stopping Distance:</b> <code>d_stop = v * t_react + v^2 / (2 * a)</code>", body_style))
    story.append(Paragraph("<b>2. Time-To-Collision (TTC):</b> <code>TTC = d_longitudinal / V_closing</code> where <code>V_closing = v_ego - v_target</code>", body_style))
    story.append(Paragraph("<b>3. Metric Stereo Depth:</b> <code>Z = (f * Baseline) / disparity</code>", body_style))
    story.append(Paragraph("<b>4. Pinhole Monocular Distance:</b> <code>Z = (f * Real_Height) / bbox_height_px</code> and <code>X = (center_x - c_x) * Z / f</code>", body_style))
    story.append(Paragraph("<b>5. Pothole Risk Score:</b> <code>R_risk = BaseSeverity * (0.65 * D_urgency + 0.35 * S_excess) * M_lateral * Confidence</code>", body_style))

    doc.build(story, canvasmaker=NumberedCanvas)

    # Copy to brain artifact directory as well
    import shutil
    shutil.copy2(OUTPUT_PDF_PATH, BRAIN_PDF_PATH)
    print(f"PDF Generated Successfully at:\n  {OUTPUT_PDF_PATH}\n  {BRAIN_PDF_PATH}")


if __name__ == "__main__":
    build_pdf()
