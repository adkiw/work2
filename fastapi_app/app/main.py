from fastapi import FastAPI, Depends, HTTPException, status
from sqlalchemy.orm import Session
from fastapi.security import OAuth2PasswordRequestForm

from . import models, schemas, crud, auth, dependencies
from .database import engine, Base

Base.metadata.create_all(bind=engine)

app = FastAPI()

@app.post('/login', response_model=schemas.Token)
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(auth.get_db)):
    user = auth.authenticate_user(db, form_data.username, form_data.password)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='Incorrect credentials')
    access_token = auth.create_access_token({'sub': str(user.id)})
    return {'access_token': access_token, 'token_type': 'bearer'}

@app.post('/users', response_model=schemas.User)
def create_user(user: schemas.UserCreate, db: Session = Depends(auth.get_db)):
    db_user = crud.get_user_by_email(db, user.email)
    if db_user:
        raise HTTPException(status_code=400, detail='Email already registered')
    return crud.create_user(db, user)

@app.get('/users/me', response_model=schemas.User)
def read_current_user(current_user=Depends(auth.get_current_user)):
    return current_user
