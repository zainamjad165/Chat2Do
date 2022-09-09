from queue import Empty
from fastapi import Depends, FastAPI, Request, Response
from typing import List
from app.db import User, create_db_and_tables, get_user_db,get_async_session
from app.schemas import UserCreate, UserRead
from app.users import auth_backend, current_active_user, fastapi_users, get_jwt_strategy
from main import users,todos,texts,messages,reciver,database,AddMessage,SeeMessage,AddText,AddTodo,SeeText,SeeTodo,SeeUser
from fastapi.security import OAuth2PasswordRequestForm
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse , RedirectResponse
import contextlib,re
from app.users import get_user_manager
from datetime import datetime

app = FastAPI()

app.include_router(fastapi_users.get_auth_router(auth_backend), prefix="/auth/jwt", tags=["auth"])

app.include_router(fastapi_users.get_register_router(UserRead, UserCreate),prefix="/auth",tags=["auth"])

get_async_session_context = contextlib.asynccontextmanager(get_async_session)
get_user_db_context = contextlib.asynccontextmanager(get_user_db)
get_user_manager_context = contextlib.asynccontextmanager(get_user_manager)

templates = Jinja2Templates(directory="templates")
app.mount("/static/", StaticFiles(directory="static"), name="static")

@app.on_event("startup")
async def on_startup():
    await create_db_and_tables()


@app.get("/signup", include_in_schema=False)
async def get(request:Request):
    return templates.TemplateResponse("signup.html",{"request":request})


async def create_user(email: str, password: str):
    async with get_async_session_context() as session:
        async with get_user_db_context(session) as user_db:
            async with get_user_manager_context(user_db) as user_manager:
                user = await user_manager.create(UserCreate(email=email, password=password))
                print(f"User created {user}")


@app.post("/signup", include_in_schema=False)
async def registration(response: Response,request: Request):
    form = await request.form()
    email = form.get("email")
    password = form.get("password")
    errors = []
    try:
        await create_user(email, password)
    except:
        errors.append("Duplicate email")
    if len(errors) > 0:
        return templates.TemplateResponse("signup.html", {"request": request, "errors": errors})
    else:
        username=email.split('@')[0]
        query = users.insert().values(username = username)
        await database.execute(query)
        html_content = """
            <html>
            <head>
                <meta http-equiv="refresh" content="7; url='/" />
            </head>
            <body>
                <p>Successfully Registered! Redirecting to login Please follow <a href="/">this link</a>.</p>
            </body>
            </html>

        """
        return HTMLResponse(content=html_content, headers=response.headers, status_code=200)
        

@app.get("/", include_in_schema=False)
async def login(request:Request, msg:str=None):
    try:
        token = request.cookies.get("fastapiusersauth")
        if not token:
            return templates.TemplateResponse("login.html",{"request":request, "msg":msg})
        else:
            return templates.TemplateResponse("home.html",{"request":request, "msg":msg})
    except:
        return templates.TemplateResponse("home.html",{"request":request, "msg":msg})


@app.post("/", include_in_schema=False)
async def login(response: Response, request: Request, credentials: OAuth2PasswordRequestForm = Depends(),user_manager=Depends(get_user_manager)):
    user = await user_manager.authenticate(credentials)
    errors = []
    if user:
        await auth_backend.login(get_jwt_strategy(), user, response)
        html_content = """
        <html>
        <head>
            <meta http-equiv="refresh" content="7; url='/home" />
        </head>
        <body>
            <p>Successfully logged in! Redirecting to home Please follow <a href="/home">this link</a>.</p>
        </body>
        </html>
        """
        return HTMLResponse(content=html_content, headers=response.headers, status_code=200)
    else:
        errors.append("incorrect password or email")
        return templates.TemplateResponse("login.html",{"request":request, "errors": errors})


@app.get("/ask", include_in_schema=False)
async def get(request:Request, msg:str=None):
    response = templates.TemplateResponse("ask.html",{"request":request, "msg":msg})
    return response


@app.get("/logout", include_in_schema=False)
async def get():
    html_content = """
            <html>
            <head>
                <meta http-equiv="refresh" content="7; url='/" />
            </head>
            <body>
                <p>You have been logged out! Redirecting to login Please follow <a href="/">this link</a>.</p>
            </body>
            </html>

        """
    response = HTMLResponse(content=html_content, status_code=200)
    response.delete_cookie("fastapiusersauth")
    return response


@app.get("/home", include_in_schema=False)
async def get(request:Request,user: User = Depends(current_active_user)):
    username=user.email.split('@')[0]
    return templates.TemplateResponse("home.html",{"request":request,"username":username})


@app.get("/todo", include_in_schema=False)
async def get(request:Request,user: User = Depends(current_active_user)):
    username=user.email.split('@')[0]
    return templates.TemplateResponse("todos.html",{"request":request,"username":username})


@app.get("/creatatodo", include_in_schema=False)
async def get(request:Request,msg: str = None,user: User = Depends(current_active_user)):
    query = todos.select().where(todos.c.username == user.email)
    todos_in_db=await database.fetch_all(query)
    return templates.TemplateResponse("creatatodo.html",{"request":request,"todos_in_db":todos_in_db,"msg":msg})


@app.post("/creatatodo",include_in_schema=False)
async def create_a_todo(request: Request,user: User = Depends(current_active_user)):
    form = await request.form()
    tittle = form.get("tittle")
    description = form.get("description")
    query = todos.insert().values(tittle = tittle,description = description, username = user.email)
    adding_todo=await database.execute(query)
    msg = "todo created"
    query = todos.select().where(todos.c.username == user.email)
    todos_in_db=await database.fetch_all(query)
    return templates.TemplateResponse("creatatodo.html",{"request":request,"todos_in_db":todos_in_db,"msg":msg})


@app.post("/seetodos", include_in_schema=False)
async def get(request:Request,user: User = Depends(current_active_user)):
    form = await request.form()
    id = form.get("id")
    query = todos.delete().where(todos.c.id == id and todos.c.username == user.email)
    del_todo=await database.execute(query)
    msg = "completed todo has been removed"
    query = todos.select().where(todos.c.username == user.email)
    todos_in_db=await database.fetch_all(query)
    return templates.TemplateResponse("seetodos.html",{"request":request,"todos_in_db":todos_in_db,"msg":msg})
    

@app.get("/seetodos", include_in_schema=False)
async def get(request:Request,msg: str = None,user: User = Depends(current_active_user)):
    query = todos.select().where(todos.c.username == user.email)
    todos_in_db=await database.fetch_all(query)
    return templates.TemplateResponse("seetodos.html",{"request":request,"todos_in_db":todos_in_db,"msg":msg})


@app.get("/chat", include_in_schema=False)
async def get(request:Request,user: User = Depends(current_active_user)):
    username=user.email.split('@')[0]
    return templates.TemplateResponse("chat.html",{"request":request,"username":username})


@app.get("/users", include_in_schema=False)
async def get(request:Request,msg: str = None,user: User = Depends(current_active_user)):
    username=user.email.split('@')[0]
    query = users.select().where(users.c.username != username)
    users_in_db=await database.fetch_all(query)
    return templates.TemplateResponse("users.html",{"request":request,"users_in_db":users_in_db,"msg":msg,"username":username})


@app.post("/users", include_in_schema=False)
async def get(response: Response,request:Request):
    form = await request.form()
    to = form.get("username")
    query = reciver.update().values(reciver = to)
    await database.execute(query)
    return RedirectResponse(url=f"/privatechat", status_code=303)


@app.get("/privatechat", include_in_schema=False)
async def get(request:Request,msg: str = None,user: User = Depends(current_active_user)):
    username=user.email.split('@')[0]
    query = reciver.select()
    is_for = await database.fetch_all(query)
    for item in is_for:
        to=item.reciver
    query = texts.select().where(texts.c.to == user.email.split('@')[0] and texts.c.by == to)
    text_in_private=await database.fetch_all(query)
    query = texts.select().where(texts.c.to == to and texts.c.by == user.email.split('@')[0])
    text_by_in_private=await database.fetch_all(query)
    return templates.TemplateResponse("privatechat.html",{"request":request,"is_for":is_for,"text_in_private":text_in_private,
    "text_by_in_private":text_by_in_private,"username":username,"msg":msg})


@app.post("/privatechat", include_in_schema=False)
async def create_text(request: Request,user: User = Depends(current_active_user)):
    username=user.email.split('@')[0]
    form = await request.form()
    message = form.get("message")
    query = reciver.select()
    is_for = await database.fetch_all(query)
    for item in is_for:
        to=item.reciver
    query = texts.insert().values(message = message ,to = to, by = user.email.split('@')[0], created_at = (datetime.now()).strftime("%H:%M"))
    await database.execute(query)
    query = texts.select().where(texts.c.to == user.email.split('@')[0] and texts.c.by == to)
    text_in_private=await database.fetch_all(query)
    query = texts.select().where(texts.c.by == user.email.split('@')[0] and texts.c.to == to)
    text_by_in_private=await database.fetch_all(query)
    return templates.TemplateResponse("privatechat.html",{"request":request,"is_for":is_for,"text_in_private":text_in_private,
    "text_by_in_private":text_by_in_private,"username":username})



@app.get("/groupchat", include_in_schema=False)
async def get(request:Request,msg: str = None,user: User = Depends(current_active_user)):
    username=user.email.split('@')[0]
    query = messages.select().where(messages.c.by != user.email.split('@')[0])
    messages_in_group=await database.fetch_all(query)
    query = messages.select().where(messages.c.by == user.email.split('@')[0])
    my_messages=await database.fetch_all(query)
    return templates.TemplateResponse("groupchat.html",{"request":request,"my_messages":my_messages,
    "messages_in_group":messages_in_group,"msg":msg,"username":username})


@app.post("/groupchat", include_in_schema=False)
async def create_text(request: Request,user: User = Depends(current_active_user)):
    username=user.email.split('@')[0]
    form = await request.form()
    message = form.get("message")
    query = messages.insert().values(message = message, by = user.email.split('@')[0],created_at = (datetime.now()).strftime("%H:%M"))
    await database.execute(query)
    query = messages.select().where(messages.c.by != user.email.split('@')[0] )
    messages_in_group=await database.fetch_all(query)
    query = messages.select().where(messages.c.by == user.email.split('@')[0] )
    my_messages=await database.fetch_all(query)
    return templates.TemplateResponse("groupchat.html",{"request":request,"my_messages":my_messages,
    "messages_in_group":messages_in_group,"username":username})


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

@app.get("/see users", response_model=List[SeeUser])
async def read_users(user: User = Depends(current_active_user)):
    query = users.select()
    users_in_db=await database.fetch_all(query)
    return users_in_db

@app.post("/create message for group", response_model=SeeMessage)
async def create_message(message: AddMessage, user: User = Depends(current_active_user)):
    query = messages.insert().values(message = message.message, by = user.email,created_at = (datetime.now()).strftime("%H:%M"))
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