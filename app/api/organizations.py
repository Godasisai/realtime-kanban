from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import Organization, Tenant, Membership, User
from app.schemas import OrgCreate, OrgResponse, TenantCreate, TenantResponse
from app.security import ROLE_ORG_ADMIN, ROLE_MEMBER
from app.api.deps import get_current_user, require_org_admin

router = APIRouter(prefix="/organizations", tags=["Organizations"])


@router.get("", response_model=List[OrgResponse])
def list_my_organizations(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Lists all organizations where the current user has any active membership."""
    memberships = db.query(Membership).filter(Membership.user_id == current_user.id).all()
    org_ids = list({m.org_id for m in memberships})
    orgs = db.query(Organization).filter(Organization.id.in_(org_ids)).all()
    return orgs


@router.post("", response_model=OrgResponse)
def create_organization(
    org_in: OrgCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Creates a new Organization and assigns the creator as `org_admin`.
    Auto-creates a default 'Main Branch' tenant for instant readiness.
    """
    existing = db.query(Organization).filter(Organization.slug == org_in.slug).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="An organization with this slug already exists.",
        )

    org = Organization(name=org_in.name, slug=org_in.slug)
    db.add(org)
    db.flush()

    # Assign creator as Org Admin
    membership = Membership(
        user_id=current_user.id,
        org_id=org.id,
        tenant_id=None,  # Org-wide admin
        role=ROLE_ORG_ADMIN,
    )
    db.add(membership)

    # Auto-create default branch
    default_branch = Tenant(
        org_id=org.id,
        name="Main Branch",
        slug="main-branch",
        location="Headquarters",
    )
    db.add(default_branch)
    db.flush()

    # Also add user to default branch as admin
    branch_membership = Membership(
        user_id=current_user.id,
        org_id=org.id,
        tenant_id=default_branch.id,
        role=ROLE_ORG_ADMIN,
    )
    db.add(branch_membership)

    db.commit()
    db.refresh(org)
    return org


@router.get("/{org_id}", response_model=OrgResponse)
def get_organization(
    org: Organization = Depends(require_org_admin),
):
    return org


@router.get("/{org_id}/tenants", response_model=List[TenantResponse])
def list_organization_tenants(
    org: Organization = Depends(require_org_admin),
    db: Session = Depends(get_db),
):
    """Lists all branches (tenants) under an organization (Org Admin access)."""
    return db.query(Tenant).filter(Tenant.org_id == org.id).all()


@router.post("/{org_id}/tenants", response_model=TenantResponse)
def create_organization_tenant(
    tenant_in: TenantCreate,
    org: Organization = Depends(require_org_admin),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Creates a new branch/tenant under the organization (Org Admin only)."""
    existing = (
        db.query(Tenant)
        .filter(Tenant.org_id == org.id, Tenant.slug == tenant_in.slug)
        .first()
    )
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"A branch with slug '{tenant_in.slug}' already exists in this organization.",
        )

    tenant = Tenant(
        org_id=org.id,
        name=tenant_in.name,
        slug=tenant_in.slug,
        location=tenant_in.location or "",
    )
    db.add(tenant)
    db.flush()

    # Creator also gets membership in this tenant
    m = Membership(
        user_id=current_user.id,
        org_id=org.id,
        tenant_id=tenant.id,
        role=ROLE_ORG_ADMIN,
    )
    db.add(m)
    db.commit()
    db.refresh(tenant)
    return tenant
