from typing import List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import User, Membership, Organization, Tenant
from app.schemas import UserCreate, UserLogin, UserResponse, Token, UserPublic
from app.security import (
    get_password_hash,
    verify_password,
    create_access_token,
    ROLE_ORG_ADMIN,
    ROLE_TENANT_ADMIN,
    ROLE_MEMBER,
)
from app.api.deps import get_current_user

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/register", response_model=UserResponse)
def register(user_in: UserCreate, db: Session = Depends(get_db)):
    """Registers a new global user account."""
    existing_user = db.query(User).filter(User.email == user_in.email.lower()).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A user with this email already exists.",
        )

    user = User(
        email=user_in.email.lower(),
        name=user_in.name,
        hashed_password=get_password_hash(user_in.password),
        avatar_color=user_in.avatar_color or "#3b82f6",
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@router.post("/login", response_model=Token)
def login(login_data: UserLogin, db: Session = Depends(get_db)):
    """Authenticates user and returns JWT access token."""
    user = db.query(User).filter(User.email == login_data.email.lower()).first()
    if not user or not verify_password(login_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
        )

    access_token = create_access_token(data={"sub": user.id, "email": user.email, "name": user.name})
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": user,
    }


@router.get("/me")
def get_me(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Returns current user details along with organizations and tenants they have access to."""
    memberships = (
        db.query(Membership)
        .filter(Membership.user_id == current_user.id)
        .all()
    )

    org_map: Dict[str, Dict[str, Any]] = {}

    for m in memberships:
        org = db.query(Organization).filter(Organization.id == m.org_id).first()
        if not org:
            continue
        if org.id not in org_map:
            org_map[org.id] = {
                "id": org.id,
                "name": org.name,
                "slug": org.slug,
                "role": m.role if m.tenant_id is None else None,
                "tenants": [],
            }

        # If user is org_admin, they have implicit access to ALL tenants under this org
        if m.role == ROLE_ORG_ADMIN and m.tenant_id is None:
            org_map[org.id]["role"] = ROLE_ORG_ADMIN
            all_tenants = db.query(Tenant).filter(Tenant.org_id == org.id).all()
            for t in all_tenants:
                if not any(x["id"] == t.id for x in org_map[org.id]["tenants"]):
                    org_map[org.id]["tenants"].append({
                        "id": t.id,
                        "name": t.name,
                        "slug": t.slug,
                        "location": t.location,
                        "role": ROLE_ORG_ADMIN,
                    })
        elif m.tenant_id:
            tenant = db.query(Tenant).filter(Tenant.id == m.tenant_id).first()
            if tenant and not any(x["id"] == tenant.id for x in org_map[org.id]["tenants"]):
                org_map[org.id]["tenants"].append({
                    "id": tenant.id,
                    "name": tenant.name,
                    "slug": tenant.slug,
                    "location": tenant.location,
                    "role": m.role,
                })

    return {
        "user": {
            "id": current_user.id,
            "email": current_user.email,
            "name": current_user.name,
            "avatar_color": current_user.avatar_color,
        },
        "organizations": list(org_map.values()),
    }


@router.get("/demo-users", response_model=List[Dict[str, Any]])
def get_demo_users(db: Session = Depends(get_db)):
    """
    Returns seeded demo users for quick role switching during assignment evaluation.
    Allows testing multi-tenant isolation and concurrent collaboration in real time.
    """
    users = db.query(User).all()
    demo_list = []
    for u in users:
        # Determine highest role and primary tenant
        primary_membership = (
            db.query(Membership)
            .filter(Membership.user_id == u.id)
            .first()
        )
        role = primary_membership.role if primary_membership else "member"
        tenant_name = primary_membership.tenant.name if primary_membership and primary_membership.tenant else "All Branches (Org Admin)"
        demo_list.append({
            "id": u.id,
            "email": u.email,
            "name": u.name,
            "role": role,
            "tenant_name": tenant_name,
            "avatar_color": u.avatar_color,
        })
    return demo_list
