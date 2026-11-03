import pytest
from app.models import Tenant, Board, Task


def test_tenant_data_isolation_read(client, db, user_tokens):
    """
    Ensures a user belonging to Bangalore HQ (Rahul) CANNOT access boards
    or tasks in Hyderabad Hub or Acme Cloud.
    """
    blr_token = user_tokens["rahul@julley.com"]
    hyd_tenant = db.query(Tenant).filter(Tenant.slug == "hyderabad-hub").first()
    acme_tenant = db.query(Tenant).filter(Tenant.slug == "nyc-branch").first()

    # Attempt to list boards in Hyderabad Hub as Bangalore Member -> 403 Forbidden
    res_hyd = client.get(f"/api/tenants/{hyd_tenant.id}/boards", headers=blr_token)
    assert res_hyd.status_code == 403
    assert "Access forbidden" in res_hyd.json()["detail"]

    # Attempt to list boards in Acme Cloud as Bangalore Member -> 403 Forbidden
    res_acme = client.get(f"/api/tenants/{acme_tenant.id}/boards", headers=blr_token)
    assert res_acme.status_code == 403

    # Org Admin (Sai) CAN access both Bangalore and Hyderabad
    sai_token = user_tokens["sai@julley.com"]
    res_sai_hyd = client.get(f"/api/tenants/{hyd_tenant.id}/boards", headers=sai_token)
    assert res_sai_hyd.status_code == 200
    assert len(res_sai_hyd.json()) >= 1


def test_cross_tenant_task_access_prevention(client, db, user_tokens):
    """
    Ensures that even if an attacker guesses a task_id belonging to Tenant B,
    they cannot read or modify it through Tenant A's endpoint.
    """
    blr_token = user_tokens["rahul@julley.com"]
    blr_tenant = db.query(Tenant).filter(Tenant.slug == "bangalore-hq").first()
    blr_board = db.query(Board).filter(Board.tenant_id == blr_tenant.id).first()

    hyd_task = db.query(Task).join(Tenant, Task.tenant_id == Tenant.id).filter(Tenant.slug == "hyderabad-hub").first()

    # Querying hyd_task with blr_tenant path must return 404 (not found in this tenant)
    res = client.get(
        f"/api/tenants/{blr_tenant.id}/boards/{blr_board.id}/tasks/{hyd_task.id}",
        headers=blr_token,
    )
    assert res.status_code == 404
    assert "Task not found in this tenant" in res.json()["detail"]


def test_cross_organization_leakage_prevention(client, db, user_tokens):
    """
    Ensures Acme Cloud Org Admin (John) cannot query or touch Julley Online data.
    """
    john_token = user_tokens["john@acme.com"]
    blr_tenant = db.query(Tenant).filter(Tenant.slug == "bangalore-hq").first()

    res = client.get(f"/api/tenants/{blr_tenant.id}/boards", headers=john_token)
    assert res.status_code == 403
