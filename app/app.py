from fastapi import Depends, FastAPI, Request, Response, status, responses
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


@app.on_event("startup")
async def on_startup():
    await create_db_and_tables()



@app.get("/", include_in_schema=False)
async def get(request:Request, msg:str=None):
    return templates.TemplateResponse("home.html",{"request":request, "msg":msg})

@app.post("/", include_in_schema=False)
async def login(response: Response, request: Request, user: User = Depends(get_user_db)):
    form = await request.form()
    email = form.get("email")
    password = form.get("password")
    errors = []
    if not email:
        errors.append("Please Enter valid Email")
    if not password:
        errors.append("Password enter invalid")
    if len(errors) > 0:
        return templates.TemplateResponse("home.html", {"request": request, "errors": errors})
    try:
        user.email=email
        user.password=password
        if user.email is None:
            errors.append("Email does not exists")
            return templates.TemplateResponse("home.html", {"request": request, "errors": errors})
        if user.password is None:
            errors.append("Invalid Password")
            return templates.TemplateResponse("home.html", {"request": request, "errors": errors})
        else:
            return templates.TemplateResponse("afterlogin.html", {"request": request, "errors": errors})
    except:
        errors.append("Something Wrong while authentication or storing tokens!")
        return templates.TemplateResponse("home.html", {"request": request, "errors": errors})



@app.get("/signup.html", include_in_schema=False)
async def get(request:Request):
    return templates.TemplateResponse("signup.html",{"request":request})

@app.post("/signup.html", include_in_schema=False)
async def registration(request: Request, user: User = Depends(get_user_db)):
    form = await request.form()
    email = form.get("email")
    password = form.get("password")
    errors = []
    if not password or len(password) < 6:
        errors.append("Password should be greater than 6 chars")
    if not email:
        errors.append("Email can't be blank")
    
    if len(errors) > 0:
        return templates.TemplateResponse("signup.html", {"request": request, "errors": errors})
    try:
        user.email=email
        user.password=password
        return responses.RedirectResponse("/?msg=successfully registered", status_code=status.HTTP_302_FOUND)
    except IntegrityError:
        errors.append("Duplicate email")
        return templates.TemplateResponse("signup.html", {"request": request, "errors": errors})



@app.get("/afterlogin.html", include_in_schema=False)
async def get(request:Request):
    return templates.TemplateResponse("afterlogin.html",{"request":request})



@app.get("/todos.html", include_in_schema=False)
async def get(request:Request):
    return templates.TemplateResponse("todos.html",{"request":request})



@app.get("/creatatodo.html", include_in_schema=False)
async def get(request:Request):
    return templates.TemplateResponse("creatatodo.html",{"request":request})

@app.post("/creatatodo.html",include_in_schema=False)
async def create_a_todo(todo: AddTodo ,request: Request, user: User = Depends(current_active_user)):
    form = await request.form()
    title = form.get("title")
    description = form.get("description")
    query = todos.insert().values(title = todo.tittle, description = todo.description, username = user.email)
    last_record_id = await database.execute(query)
    errors = []
    if not title or len(title) < 4:
        errors.append("Title should be > 4 chars")
    if not description or len(description) < 10:
        errors.append("Description should be > 10 chars")
    if len(errors) > 0:
        return templates.TemplateResponse("creatatodo.html", {"request": request, "errors": errors})

@app.get("/seetodos.html", include_in_schema=False)
async def get(request:Request,user: User = Depends(current_active_user)):
    query = todos.select().where(todos.c.username == user.email)
    todos_in_db=await database.fetch_all(query)
    return templates.TemplateResponse("seetodos.html",{"request":request, "todos_in_db":todos_in_db})


@app.get("/chat.html", include_in_schema=False)
async def get(request:Request):
    return templates.TemplateResponse("chat.html",{"request":request})


@app.get("/private.html", include_in_schema=False)
async def get(request:Request):
    return templates.TemplateResponse("private.html",{"request":request})


@app.post("/private.html", include_in_schema=False)
async def create_text(text: AddText,request: Request,user: User = Depends(current_active_user)):
    form = await request.form()
    message = form.get("message")
    to = form.get("to")
    query = texts.insert().values(message = text.message , to = text.to , by = user.email)
    last_record_id = await database.execute(query)


@app.get("/groupchat.html", include_in_schema=False)
async def get(request:Request):
    return templates.TemplateResponse("groupchat.html",{"request":request})


@app.post("/groupchat.html", include_in_schema=False)
async def create_text(text: AddText,request: Request,user: User = Depends(current_active_user)):
    form = await request.form()
    message = form.get("message")
    by = form.get("by")
    query = messages.insert().values(message = message.message, by = user.email)
    last_record_id = await database.execute(query)

#FASTAPI DOCS
########################################################################################################################

@app.post("/create a todo", response_model=SeeTodo)
async def create_todos(todo: AddTodo, user: User = Depends(current_active_user)):
    query = todos.insert().values(tittle = todo.tittle, description = todo.description, username = user.email)
    last_record_id = await database.execute(query)
    query = todos.select()
    created_todo = await database.fetch_one(query)
    return {**created_todo}

@app.get("/see todos", response_model=List[SeeTodo])
async def read_todos(user: User = Depends(current_active_user)):
    query = todos.select().where(todos.c.username == user.email)
    todos_in_db=await database.fetch_all(query)
    return todos_in_db

@app.post("/create message for group", response_model=SeeMessage)
async def create_message(message: AddMessage, user: User = Depends(current_active_user)):
    query = messages.insert().values(message = message.message, by = user.email)
    last_record_id = await database.execute(query)
    query = messages.select()
    created_text_for_group = await database.fetch_one(query)
    return {**created_text_for_group}

@app.get("/see group messages", response_model=List[SeeMessage])
async def read_message(user: User = Depends(current_active_user)): 
    query = messages.select()
    messages_in_group=await database.fetch_all(query)
    return messages_in_group

@app.post("/create a private text", response_model=SeeText)
async def create_text(text: AddText,user: User = Depends(current_active_user)):
    query = texts.insert().values(message = text.message , to = text.to , by = user.email)
    last_record_id = await database.execute(query)
    query = messages.select()
    addtext = await database.fetch_one(query)
    return {**addtext}

@app.get("/see a private text", response_model=List[SeeText])
async def read_text(user: User = Depends(current_active_user)): 
    query = texts.select().where(texts.c.to == user.email)
    text_in_private=await database.fetch_all(query)
    return text_in_private