from fastapi import Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from uuid import UUID

from . import models, auth
from .auth import get_db, get_current_user


def requires_roles(required: List[str]):
    def wrapper(current_user = Depends(get_current_user), db: Session = Depends(get_db)):
        roles = getattr(current_user, 'current_roles', [])
        if not any(role in roles for role in required):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail='Insufficient role')
        return current_user
    return wrapper
