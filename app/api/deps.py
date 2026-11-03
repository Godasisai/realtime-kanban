from typing import Optional, Callable
from fastapi import Depends, HTTPException, status, Path
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import User, Tenant, Membership, Organization
from app.security import (
    decode_access_token,
    has_sufficient_role,
    ROLE_ORG_ADMIN,
    ROLE_TENANT_ADMIN,
    ROLE_MEMBER,
)

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/token", auto_error=False)


def get_current_user(
    token: Optional[str] = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> User:
    """Extracts and verifies the JWT token, returning the authenticated User."""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    if not token:
        raise credentials_exception

    payload = decode_access_token(token)
    if payload is None:
        raise credentials_exception

    user_id: str = payload.get("sub")
    if user_id is None:
        raise credentials_exception

    user = db.query(User).filter(User.id == user_id).first()
    if user is None:
        raise credentials_exception

    return user


def require_tenant_access(required_role: str = ROLE_MEMBER) -> Callable:
    """
    Dependency factory enforcing strict tenant data isolation and RBAC.
    Rules:
      1. Tenant must exist.
      2. User must have a membership in this tenant meeting `required_role`, OR
      3. User must have an `org_admin` membership in the parent organization.
      4. Any cross-tenant attempt returns 403 Forbidden.
    """
    def tenant_access_checker(
        tenant_id: str = Path(..., description="ID of the tenant / branch"),
        current_user: User = Depends(get_current_user),
        db: Session = Depends(get_db),
    ) -> Tenant:
        tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()
        if not tenant:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Tenant '{tenant_id}' not found",
            )

        # Check tenant-specific membership
        tenant_membership = (
            db.query(Membership)
            .filter(
                Membership.user_id == current_user.id,
                Membership.tenant_id == tenant_id,
            )
            .first()
        )

        if tenant_membership and has_sufficient_role(tenant_membership.role, required_role):
            return tenant

        # Check Org-wide admin membership
        org_membership = (
            db.query(Membership)
            .filter(
                Membership.user_id == current_user.id,
                Membership.org_id == tenant.org_id,
                Membership.role == ROLE_ORG_ADMIN,
            )
            .first()
        )

        if org_membership:
            return tenant

        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access forbidden: You do not have sufficient permissions in this tenant/branch.",
        )

    return tenant_access_checker


def require_org_admin(
    org_id: str = Path(..., description="Organization ID"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Organization:
    """Verifies that the current user has Org Admin rights for the target organization."""
    org = db.query(Organization).filter(Organization.id == org_id).first()
    if not org:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Organization '{org_id}' not found",
        )

    org_membership = (
        db.query(Membership)
        .filter(
            Membership.user_id == current_user.id,
            Membership.org_id == org_id,
            Membership.role == ROLE_ORG_ADMIN,
        )
        .first()
    )

    if not org_membership:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Org Admin role required to perform this action.",
        )

    return org
