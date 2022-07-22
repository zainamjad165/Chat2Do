from fastapi import Depends, FastAPI, Request, responses, status
from typing import List
from app.db import User, create_db_and_tables, get_user_db
from app.schemas import UserCreate, UserRead
from app.users import auth_backend, current_active_user, fastapi_users
from main import todos,texts,messages,database,AddMessage,SeeMessage,AddText,AddTodo,SeeText,SeeTodo
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

app = FastAPI()

app.include_router(fastapi_users.get_auth_router(auth_backend), prefix="/auth/jwt", tags=["auth"])

app.include_router(fastapi_users.get_register_router(UserRead, UserCreate),prefix="/auth",tags=["auth"])

#ADDING HTML RESPONCE
templates = Jinja2Templates(directory="templates")
app.mount("/static/", StaticFiles(directory="static"), name="static")

@app.get("/", include_in_schema=False)
async def get(request:Request):
    return templates.TemplateResponse("home.html",{"request":request})

@app.get("/signup.html", include_in_schema=False)
async def get(request:Request):
    return templates.TemplateResponse("signup.html",{"request":request})

@app.post("/singup.html")
async def registration(request: Request, db: Session = Depends(get_user_db)):
    form = await request.form()
    email = form.get("email")
    password = form.get("password")
    errors = []
    if not password or len(password) < 6:
        errors.append("Password should be greater than 6 chars")
    if not email:
        errors.append("Email can't be blank")
    user = User(email=email, password=password)
    if len(errors) > 0:
        return templates.TemplateResponse(
            "user_register.html", {"request": request, "errors": errors}
        )
    try:
        db.add(user)
        db.commit()
        db.refresh(user)
        return responses.RedirectResponse(
            "/?msg=successfully registered", status_code=status.HTTP_302_FOUND
        )
    except IntegrityError:
        errors.append("Duplicate email")
        return templates.TemplateResponse(
            "user_register.html", {"request": request, "errors": errors}
        )

@app.get("/login.html", include_in_schema=False)
async def get(request:Request):
    return templates.TemplateResponse("login.html",{"request":request})

@app.get("/todos.html", include_in_schema=False)
async def get(request:Request):
    return templates.TemplateResponse("todos.html",{"request":request})

@app.get("/chat.html", include_in_schema=False)
async def get(request:Request):
    return templates.TemplateResponse("chat.html",{"request":request})

@app.on_event("startup")
async def on_startup():
    await create_db_and_tables()

@app.post("/create todos/", response_model=SeeTodo)
async def create_todos(todo: AddTodo, user: User = Depends(current_active_user)):
    query = todos.insert().values(tittle = todo.tittle, description = todo.description, username = user.email)
    last_record_id = await database.execute(query)
    query = todos.select()
    row = await database.fetch_one(query)
    return {**row}

@app.get("/see todos/", response_model=List[SeeTodo])
async def read_todos(user: User = Depends(current_active_user)):
    query = todos.select().where(todos.c.username == user.email)
    return await database.fetch_all(query)

@app.post("/create message for group/", response_model=SeeMessage)
async def create_message(message: AddMessage, user: User = Depends(current_active_user)):
    query = messages.insert().values(message = message.message, by = user.email)
    last_record_id = await database.execute(query)
    query = messages.select()
    contant = await database.fetch_one(query)
    return {**contant}

@app.get("/see group messages/", response_model=List[SeeMessage])
async def read_message(user: User = Depends(current_active_user)): 
    query = messages.select()
    return await database.fetch_all(query)

@app.post("/private text/", response_model=SeeText)
async def create_text(text: AddText,user: User = Depends(current_active_user)):
    query = texts.insert().values(message = text.message , to = text.to , by = user.email)
    last_record_id = await database.execute(query)
    query = messages.select()
    make = await database.fetch_one(query)
    return {**make}

@app.get("/see private text/", response_model=List[SeeText])
async def read_text(user: User = Depends(current_active_user)): 
    query = texts.select().where(texts.c.to == user.email)
    return await database.fetch_all(query)
