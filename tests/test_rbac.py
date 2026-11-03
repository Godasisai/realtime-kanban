from app.models import Tenant, Board, BoardColumn, Organization


def test_member_cannot_delete_column(client, db, user_tokens):
    """Members should not be allowed to delete columns (requires Tenant Admin)."""
    member_token = user_tokens["rahul@julley.com"]
    blr_tenant = db.query(Tenant).filter(Tenant.slug == "bangalore-hq").first()
    blr_board = db.query(Board).filter(Board.tenant_id == blr_tenant.id).first()
    col = db.query(BoardColumn).filter(BoardColumn.board_id == blr_board.id).first()

    res = client.delete(
        f"/api/tenants/{blr_tenant.id}/boards/{blr_board.id}/columns/{col.id}",
        headers=member_token,
    )
    assert res.status_code == 403
    assert "Access forbidden" in res.json()["detail"]


def test_tenant_admin_can_manage_columns(client, db, user_tokens):
    """Tenant Admin (Priya) can create columns."""
    admin_token = user_tokens["priya@julley.com"]
    blr_tenant = db.query(Tenant).filter(Tenant.slug == "bangalore-hq").first()
    blr_board = db.query(Board).filter(Board.tenant_id == blr_tenant.id).first()

    res = client.post(
        f"/api/tenants/{blr_tenant.id}/boards/{blr_board.id}/columns",
        json={"title": "QA Testing", "wip_limit": 2},
        headers=admin_token,
    )
    assert res.status_code == 200
    data = res.json()
    assert data["title"] == "QA Testing"
    assert data["wip_limit"] == 2


def test_org_admin_can_create_branch(client, db, user_tokens):
    """Org Admin (Sai) can create new branches under Julley Online."""
    org_admin_token = user_tokens["sai@julley.com"]
    org = db.query(Organization).filter(Organization.slug == "julley-online").first()

    res = client.post(
        f"/api/organizations/{org.id}/tenants",
        json={"name": "Pune Tech Park", "slug": "pune-tech", "location": "Pune, MH, India"},
        headers=org_admin_token,
    )
    assert res.status_code == 200
    assert res.json()["name"] == "Pune Tech Park"


def test_member_cannot_create_branch(client, db, user_tokens):
    """Regular member cannot create new branches (Org Admin required)."""
    member_token = user_tokens["rahul@julley.com"]
    org = db.query(Organization).filter(Organization.slug == "julley-online").first()

    res = client.post(
        f"/api/organizations/{org.id}/tenants",
        json={"name": "Rogue Branch", "slug": "rogue-branch"},
        headers=member_token,
    )
    assert res.status_code == 403
