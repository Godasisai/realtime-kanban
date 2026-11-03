from pathlib import Path
from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN
from pptx.enum.shapes import MSO_SHAPE

OUTPUT_FILE = Path(__file__).resolve().parent / "Julley_Kanban_Architecture_Presentation_Sai_Ammanna_Naidu.pptx"

# Modern Palette
COLOR_BG_DARK = RGBColor(15, 23, 42)      # #0f172a (Deep Slate)
COLOR_CARD = RGBColor(30, 41, 59)         # #1e293b (Slate 800)
COLOR_PRIMARY = RGBColor(99, 102, 241)    # #6366f1 (Indigo)
COLOR_ACCENT = RGBColor(16, 185, 129)     # #10b981 (Emerald)
COLOR_TEXT_WHITE = RGBColor(248, 250, 252)# #f8fafc (Slate 50)
COLOR_TEXT_MUTED = RGBColor(148, 163, 184)# #94a3b8 (Slate 400)
COLOR_BORDER = RGBColor(51, 65, 85)       # #334155 (Slate 700)


def apply_dark_background(slide):
    background = slide.background
    fill = background.fill
    fill.solid()
    fill.fore_color.rgb = COLOR_BG_DARK


def add_header(slide, title_text, category_text="JULLEY ONLINE PVT. LTD. | ASSIGNMENT SUBMISSION"):
    # Category tag
    cat_box = slide.shapes.add_textbox(Inches(0.8), Inches(0.5), Inches(11.5), Inches(0.4))
    tf_cat = cat_box.text_frame
    tf_cat.word_wrap = True
    p_cat = tf_cat.paragraphs[0]
    p_cat.text = category_text.upper()
    p_cat.font.size = Pt(11)
    p_cat.font.bold = True
    p_cat.font.color.rgb = COLOR_PRIMARY

    # Main Slide Title
    title_box = slide.shapes.add_textbox(Inches(0.8), Inches(0.85), Inches(11.5), Inches(0.8))
    tf_title = title_box.text_frame
    tf_title.word_wrap = True
    p_title = tf_title.paragraphs[0]
    p_title.text = title_text
    p_title.font.size = Pt(24)
    p_title.font.bold = True
    p_title.font.color.rgb = COLOR_TEXT_WHITE


def add_card(slide, left, top, width, height, title, bullet_points, highlight_color=COLOR_PRIMARY):
    # Card Background shape
    shape = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, left, top, width, height)
    shape.fill.solid()
    shape.fill.fore_color.rgb = COLOR_CARD
    shape.line.color.rgb = highlight_color
    shape.line.width = Pt(1.5)

    # Card Content Box
    tb = slide.shapes.add_textbox(left + Inches(0.2), top + Inches(0.2), width - Inches(0.4), height - Inches(0.4))
    tf = tb.text_frame
    tf.word_wrap = True

    # Card Title
    p_title = tf.paragraphs[0]
    p_title.text = title
    p_title.font.size = Pt(15)
    p_title.font.bold = True
    p_title.font.color.rgb = highlight_color
    p_title.space_after = Pt(10)

    # Bullet points
    for pt in bullet_points:
        p = tf.add_paragraph()
        p.text = "• " + pt
        p.font.size = Pt(12)
        p.font.color.rgb = COLOR_TEXT_WHITE
        p.space_after = Pt(6)


def build_presentation():
    prs = Presentation()
    # 16:9 widescreen layout
    prs.slide_width = Inches(13.333)
    prs.slide_height = Inches(7.5)
    blank_layout = prs.slide_layouts[6]

    # ==================== SLIDE 1: Title Slide ====================
    slide1 = prs.slides.add_slide(blank_layout)
    apply_dark_background(slide1)

    title_box = slide1.shapes.add_textbox(Inches(1.2), Inches(1.8), Inches(11), Inches(2.5))
    tf1 = title_box.text_frame
    tf1.word_wrap = True

    p0 = tf1.paragraphs[0]
    p0.text = "JULLEY ONLINE PVT. LTD. • TECHNICAL ASSIGNMENT"
    p0.font.size = Pt(13)
    p0.font.bold = True
    p0.font.color.rgb = COLOR_ACCENT
    p0.space_after = Pt(12)

    p1 = tf1.add_paragraph()
    p1.text = "Real-Time Collaborative Kanban Board"
    p1.font.size = Pt(36)
    p1.font.bold = True
    p1.font.color.rgb = COLOR_TEXT_WHITE
    p1.space_after = Pt(8)

    p2 = tf1.add_paragraph()
    p2.text = "Multi-Organization & Multi-Tenant Enterprise Architecture"
    p2.font.size = Pt(20)
    p2.font.color.rgb = COLOR_PRIMARY
    p2.space_after = Pt(24)

    info_box = slide1.shapes.add_textbox(Inches(1.2), Inches(4.8), Inches(10), Inches(1.5))
    tf_info = info_box.text_frame
    p_name = tf_info.paragraphs[0]
    p_name.text = "Candidate: Sai Ammanna Naidu  |  Email: naidugodasi751@gmail.com"
    p_name.font.size = Pt(14)
    p_name.font.color.rgb = COLOR_TEXT_WHITE
    p_name.font.bold = True

    p_repo = tf_info.add_paragraph()
    p_repo.text = "GitHub: https://github.com/Godasisai/realtime-kanban  |  Live Demo: https://julley-kanban.loca.lt"
    p_repo.font.size = Pt(12)
    p_repo.font.color.rgb = COLOR_TEXT_MUTED

    # ==================== SLIDE 2: Problem Statement & Objectives ====================
    slide2 = prs.slides.add_slide(blank_layout)
    apply_dark_background(slide2)
    add_header(slide2, "Problem Statement & Core Engineering Objectives")

    add_card(
        slide2, Inches(0.8), Inches(1.8), Inches(5.6), Inches(5.0),
        "Core Business & Technical Challenges",
        [
            "Multi-Org to Multi-Tenant Hierarchy: Support holding companies with branches/divisions.",
            "Strict Tenant Isolation: Prevent cross-tenant data leakage across queries and sockets.",
            "Role-Based Access Control (RBAC): Org Admin, Tenant Admin, and Member permissions.",
            "Real-Time Live Sync: Instant multi-user board state updates via WebSockets.",
            "Concurrency Handling: Prevent overwrite collisions and drag-drop race conditions.",
        ],
        highlight_color=COLOR_PRIMARY
    )

    add_card(
        slide2, Inches(6.8), Inches(1.8), Inches(5.6), Inches(5.0),
        "Production Solution Delivered",
        [
            "Full-Stack Platform: FastAPI backend + SQLite WAL + WebSockets + Single Page App.",
            "Strict Security Middleware: Path & JWT token tenant validation preventing cross-branch reads.",
            "Optimistic Concurrency Control (OCC): Version increments with 3-way conflict resolution modal.",
            "Fractional Indexing (LexoRank): O(1) midpoint drag-drop reordering without mass row locks.",
            "Complete Test Coverage: 12 automated pytest integration tests passing in <1s.",
        ],
        highlight_color=COLOR_ACCENT
    )

    # ==================== SLIDE 3: System Architecture & Tenancy Hierarchy ====================
    slide3 = prs.slides.add_slide(blank_layout)
    apply_dark_background(slide3)
    add_header(slide3, "System Architecture: Multi-Organization Hierarchy")

    add_card(
        slide3, Inches(0.8), Inches(1.8), Inches(3.6), Inches(5.0),
        "1. Hierarchy Structure",
        [
            "Organization: Top-level entity (Julley Online, Acme Corp).",
            "Tenants (Branches): Autonomous units (Bangalore HQ, Hyderabad Hub).",
            "Boards: Branch-scoped boards.",
            "Columns: Workflow stages with WIP limits.",
            "Tasks: Work items with version & order.",
            "Activity Logs: Immutable audit trail.",
        ],
        highlight_color=COLOR_PRIMARY
    )

    add_card(
        slide3, Inches(4.8), Inches(1.8), Inches(3.6), Inches(5.0),
        "2. Tenancy Isolation Model",
        [
            "Shared DB + Tenant Discriminator.",
            "Mandatory tenant_id foreign keys.",
            "Indexed tenant_id on all tables.",
            "Zero cross-tenant SQL leakage.",
            "Dependency Guard: require_tenant_access checks membership or Org Admin role.",
            "Dual-Key filtering: id + tenant_id.",
        ],
        highlight_color=COLOR_ACCENT
    )

    add_card(
        slide3, Inches(8.8), Inches(1.8), Inches(3.6), Inches(5.0),
        "3. RBAC Matrix",
        [
            "Org Admin: Manages branches, cross-branch boards, and global memberships.",
            "Tenant Admin: Manages branch boards, columns, WIP limits, and members.",
            "Member: Creates, edits, moves tasks; cannot delete columns or branches.",
            "Automatic role hierarchy enforcement in API dependencies.",
        ],
        highlight_color=COLOR_PRIMARY
    )

    # ==================== SLIDE 4: Database Design & ER Modeling ====================
    slide4 = prs.slides.add_slide(blank_layout)
    apply_dark_background(slide4)
    add_header(slide4, "Database Schema & Entity-Relationship Design")

    add_card(
        slide4, Inches(0.8), Inches(1.8), Inches(5.6), Inches(5.0),
        "Core Tables & Relationships (8 Tables)",
        [
            "organizations: id (UUID PK), name, slug (UNIQUE).",
            "tenants: id (PK), org_id (FK), name, slug, location.",
            "users: id (PK), email (UNIQUE), name, hashed_password, avatar_color.",
            "memberships: id (PK), user_id (FK), org_id (FK), tenant_id (FK), role.",
            "boards: id (PK), tenant_id (FK, INDEX), org_id (FK), name, color.",
            "columns: id (PK), tenant_id (FK), board_id (FK, INDEX), title, order, wip_limit.",
            "tasks: id (PK), tenant_id (FK), column_id (FK), order (FLOAT), version (INT).",
            "activity_logs: id (PK), tenant_id (FK, INDEX), action, details (JSON).",
        ],
        highlight_color=COLOR_ACCENT
    )

    add_card(
        slide4, Inches(6.8), Inches(1.8), Inches(5.6), Inches(5.0),
        "High-Performance Database Strategies",
        [
            "SQLite WAL Mode (Write-Ahead Logging): Concurrent reads alongside writes without locking.",
            "Foreign Key Enforcement: PRAGMA foreign_keys=ON ensures cascading referential integrity.",
            "Composite Indexing: (user_id, tenant_id) and (tenant_id, column_id) for instant lookups.",
            "Partition Isolation: Zero table scans across tenants.",
            "Auditing: Every creation, move, edit, and deletion writes to tenant-scoped activity_logs.",
        ],
        highlight_color=COLOR_PRIMARY
    )

    # ==================== SLIDE 5: Concurrency - OCC & Fractional Indexing ====================
    slide5 = prs.slides.add_slide(blank_layout)
    apply_dark_background(slide5)
    add_header(slide5, "Advanced Concurrency & Conflict Resolution")

    add_card(
        slide5, Inches(0.8), Inches(1.8), Inches(5.6), Inches(5.0),
        "1. Optimistic Concurrency Control (OCC)",
        [
            "Atomic Version Tracking: Each task maintains integer version.",
            "Conflict Detection: Client submits expected_version with update payload.",
            "HTTP 409 Conflict: Triggered if server version != expected_version.",
            "Side-by-Side Diff Modal: Displays local edits vs latest server edits.",
            "3-Way Resolution: Keep Server Version, Overwrite with My Changes, or Merge non-conflicting fields.",
        ],
        highlight_color=RGBColor(244, 63, 94) # Rose
    )

    add_card(
        slide5, Inches(6.8), Inches(1.8), Inches(5.6), Inches(5.0),
        "2. Fractional Indexing (LexoRank)",
        [
            "Problem with Integer Rank: Inserting item at top of 50 tasks triggers 50 SQL UPDATE statements.",
            "Fractional Solution: Midpoint calculation (prev_order + next_order) / 2.0.",
            "O(1) Writes: Exactly 1 task row updated on drag and drop.",
            "Zero Locks: No table locks, eliminating concurrent drag-drop race conditions.",
            "Auto-Rebalancer: Uniform re-spacing triggered if gap falls below 1e-4.",
        ],
        highlight_color=COLOR_ACCENT
    )

    # ==================== SLIDE 6: Scoped WebSockets & Presence ====================
    slide6 = prs.slides.add_slide(blank_layout)
    apply_dark_background(slide6)
    add_header(slide6, "Scoped WebSocket Architecture & Live Presence")

    add_card(
        slide6, Inches(0.8), Inches(1.8), Inches(5.6), Inches(5.0),
        "WebSocket Room Quarantine",
        [
            "Handshake Auth: Validates JWT token and checks tenant membership before accepting connection.",
            "Room Key: tenant:{tenant_id}:board:{board_id}.",
            "Quarantine: Connections in Tenant A cannot receive events from Tenant B.",
            "Heartbeat: Ping/Pong every 25s maintains connectivity through firewalls.",
            "Network Recovery: Auto-reconnect with exponential backoff & board snapshot resynchronization.",
        ],
        highlight_color=COLOR_PRIMARY
    )

    add_card(
        slide6, Inches(6.8), Inches(1.8), Inches(5.6), Inches(5.0),
        "Live Presence & Collaboration Features",
        [
            "Live Presence Stack: Real-time avatar chips in header showing online collaborators.",
            "Active Focus Indicators: When user opens task drawer, peers see a glowing card border ('Alice viewing').",
            "Optimistic UI Updates: Dragged cards snap immediately; rolled back on network/server failure.",
            "Client-Side Undo/Redo: Full history stack with Ctrl+Z and Ctrl+Y keyboard shortcuts.",
            "Tenant Activity Drawer: Real-time stream of all branch operations.",
        ],
        highlight_color=COLOR_ACCENT
    )

    # ==================== SLIDE 7: Verification & Test Results ====================
    slide7 = prs.slides.add_slide(blank_layout)
    apply_dark_background(slide7)
    add_header(slide7, "Rigorous Testing & Automated Verification")

    add_card(
        slide7, Inches(0.8), Inches(1.8), Inches(5.6), Inches(5.0),
        "Automated Test Suite (12/12 Passing)",
        [
            "test_tenant_data_isolation_read (PASSED): Bangalore Member blocked from Hyderabad Hub (403).",
            "test_cross_tenant_task_access_prevention (PASSED): Guessed UUID from other tenant returns 404.",
            "test_cross_organization_leakage_prevention (PASSED): Acme Org Admin blocked from Julley data.",
            "test_member_cannot_delete_column (PASSED): RBAC member boundary enforced (403).",
            "test_optimistic_concurrency_control_conflict (PASSED): Stale version returns 409 Conflict.",
            "test_drag_drop_task_move_api (PASSED): Fractional indexing computes midpoint accurately.",
            "test_websocket_auth_and_tenant_scoping (PASSED): Unauthorized socket rejected (1008).",
        ],
        highlight_color=COLOR_ACCENT
    )

    add_card(
        slide7, Inches(6.8), Inches(1.8), Inches(5.6), Inches(5.0),
        "Demo Personas Pre-Configured",
        [
            "sai@julley.com: Org Admin (Julley Online - All branches).",
            "priya@julley.com: Tenant Admin (Bangalore HQ).",
            "rahul@julley.com: Member (Bangalore HQ).",
            "ananya@julley.com: Tenant Admin (Hyderabad Hub).",
            "john@acme.com: Org Admin (Acme Cloud - External Org).",
            "One-click Persona Switcher in header allows rapid live role testing.",
        ],
        highlight_color=COLOR_PRIMARY
    )

    # ==================== SLIDE 8: Summary & Deliverables ====================
    slide8 = prs.slides.add_slide(blank_layout)
    apply_dark_background(slide8)
    add_header(slide8, "Assignment Deliverables & Conclusion")

    add_card(
        slide8, Inches(0.8), Inches(1.8), Inches(11.6), Inches(5.0),
        "Summary of Complete Deliverables Submitted",
        [
            "1. Published Live Web Application: https://julley-kanban.loca.lt (Tunnel Password: 219.91.208.112).",
            "2. Public GitHub Repository: https://github.com/Godasisai/realtime-kanban (Ready for Render/Railway).",
            "3. Clean ZIP Archive: Julley_RealTime_Kanban_Assignment_Sai_Ammanna_Naidu.zip (Ready for Google Drive).",
            "4. Comprehensive Documentation: docs/ARCHITECTURE.md, docs/DATABASE_SCHEMA.md, docs/API_DOCUMENTATION.md, docs/WEBSOCKET_PROTOCOL.md.",
            "5. Production Codebase: FastAPI + SQLite WAL + Scoped WebSockets + Modern Tailwind Drag-Drop SPA.",
            "6. Concurrency & Tenancy: Fractional Indexing (LexoRank) + Optimistic Concurrency Control (OCC 409).",
            "7. Evaluation Readiness: 100% completed according to all 5 Julley Online evaluation criteria.",
        ],
        highlight_color=COLOR_ACCENT
    )

    prs.save(OUTPUT_FILE)
    print(f"[OK] Presentation successfully generated at: {OUTPUT_FILE}")


if __name__ == "__main__":
    build_presentation()
