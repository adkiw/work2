from fastapi import Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from uuid import UUID

from . import models, auth
from .auth import get_db, get_current_user_and_tenant


def requires_roles(required: List[models.RoleName]):
    def wrapper(user_and_tenant = Depends(get_current_user_and_tenant), db: Session = Depends(get_db)):
        user, tenant_id = user_and_tenant
        membership = db.query(models.UserTenant).filter(
            models.UserTenant.user_id == user.id,
            models.UserTenant.tenant_id == tenant_id
        ).first()
        if not membership or membership.role.name not in [r.value for r in required]:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail='Insufficient role')
        # set session variable for RLS
        db.execute("SET app.current_tenant = '{}'".format(tenant_id))
        return (user, tenant_id)
    return wrapper
