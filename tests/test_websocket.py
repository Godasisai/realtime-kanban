import pytest
from app.models import Tenant
from app.security import create_access_token


def test_websocket_auth_and_tenant_scoping(client, db):
    """
    Verifies WebSocket authentication and tenant authorization scoping.
    Unauthorized connections or cross-tenant attempts are closed.
    """
    # 1. Invalid token should be rejected
    with pytest.raises(Exception):
        with client.websocket_connect("/ws?token=invalid_token&tenant_id=abc&board_id=123"):
            pass

    # 2. Valid token but unauthorized tenant
    tenant_acme = db.query(Tenant).filter(Tenant.slug == "nyc-branch").first()
    # Rahul only has access to Bangalore HQ, NOT Acme NYC
    from app.models import User
    rahul = db.query(User).filter(User.email == "rahul@julley.com").first()
    rahul_token = create_access_token({"sub": rahul.id, "email": rahul.email, "name": rahul.name})

    with pytest.raises(Exception):
        with client.websocket_connect(f"/ws?token={rahul_token}&tenant_id={tenant_acme.id}&board_id=123"):
            pass
