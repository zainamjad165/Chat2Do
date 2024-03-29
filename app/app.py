from fastapi import Depends, FastAPI, Request, Response
from app.db import User, create_db_and_tables, get_user_db,get_async_session
from app.schemas import UserCreate, UserRead
from app.users import auth_backend, current_active_user, fastapi_users, get_jwt_strategy
from main import users,todos,texts,messages,reciver,database,group,groupuser,member,group_contant,groupname
from fastapi.security import OAuth2PasswordRequestForm
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse , RedirectResponse
import contextlib
from app.users import get_user_manager
from datetime import datetime,date

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

async def create_user(email: str, password: str):
    async with get_async_session_context() as session:
        async with get_user_db_context(session) as user_db:
            async with get_user_manager_context(user_db) as user_manager:
                user = await user_manager.create(UserCreate(email=email, password=password))
                print(f"User created {user}")


@app.get("/signup", include_in_schema=False)
async def get(request:Request):
    return templates.TemplateResponse("signup.html",{"request":request})


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
        return RedirectResponse(url=f"/", status_code=303)
        

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
    response = RedirectResponse(url=f"/", status_code=303)
    response.delete_cookie("fastapiusersauth")
    return response


@app.get("/home", include_in_schema=False)
async def get(request:Request,user: User = Depends(current_active_user)):
    username=user.email.split('@')[0]
    query = todos.select().where(todos.c.username == user.email)
    todos_in_db=await database.fetch_all(query)
    query = texts.select().where(texts.c.to == username )
    text_in_private=await database.fetch_all(query)
    return templates.TemplateResponse("home.html",{"request":request,"todos_in_db":todos_in_db,"text_in_private":text_in_private,"username":username})

@app.get("/todo", include_in_schema=False)
async def get(request:Request,user: User = Depends(current_active_user)):
    username=user.email.split('@')[0]
    query = todos.select().where(todos.c.username == user.email)
    todos_in_db=await database.fetch_all(query)
    return templates.TemplateResponse("todos.html",{"request":request,"todos_in_db":todos_in_db,"username":username})

@app.post("/todo", include_in_schema=False)
async def get(request:Request,user: User = Depends(current_active_user)):
    username=user.email.split('@')[0]
    form = await request.form()
    tittle = form.get("tittle")
    description = form.get("description")
    id = form.get("id")
    if id:
        query = todos.delete().where(todos.c.id == id and todos.c.username == user.email)
        await database.execute(query)
    else:
        query = todos.insert().values(tittle = tittle,description = description, username = user.email)
        await database.execute(query)
    query = todos.select().where(todos.c.username == user.email)
    todos_in_db=await database.fetch_all(query)
    return templates.TemplateResponse("todos.html",{"request":request,"todos_in_db":todos_in_db,"username":username})


@app.get("/chat", include_in_schema=False)
async def get(request:Request,msg: str = None,user: User = Depends(current_active_user)):
    username=user.email.split('@')[0]
    query = users.select().where(users.c.username != username)
    users_in_db=await database.fetch_all(query)
    a = [tup[0] for tup in users_in_db]
    b = a[0]
    query = texts.select()
    c = await database.fetch_all(query)
    d = c[-1]
    e = d[1]
    if e in a :
        a.remove(e)
        a.insert(0,e)
        f = c[-2]
        g = f[1]
        if g in a :
            a.remove(g)
            a.insert(1,g)
        else:
            g = f[2]
            a.remove(g)
            a.insert(1,g)
    else:
        e = d[2]
        a.remove(e)
        a.insert(0,e)
        f = c[-2]
        g = f[1]
        a.remove(g)
        a.insert(1,g)
    query = reciver.select()
    is_for = await database.fetch_all(query)
    for item in is_for:
        to=item.reciver
    if to == username:
        query = reciver.update().values(reciver = b)
        await database.execute(query)
        query = reciver.select()
        is_for = await database.fetch_all(query)
        for item in is_for:
            to=item.reciver
        query = texts.select().where(texts.c.to == username, texts.c.by == to )
        text_in_private=await database.fetch_all(query)
        query = texts.select().where(texts.c.to == to, texts.c.by == username )
        text_by_in_private=await database.fetch_all(query)
        all_messages = text_in_private + text_by_in_private
        asd = sorted(all_messages, key=lambda time: time[3])
        zxc= sorted(asd, key=lambda date: date[4])
        zxc.reverse()
    else:
        query = texts.select().where(texts.c.to == username, texts.c.by == to )
        text_in_private=await database.fetch_all(query)
        query = texts.select().where(texts.c.to == to, texts.c.by == username )
        text_by_in_private=await database.fetch_all(query)
        all_messages = text_in_private + text_by_in_private
        asd = sorted(all_messages, key=lambda time: time[3])
        zxc= sorted(asd, key=lambda date: date[4])
        zxc.reverse()
    return templates.TemplateResponse("chat.html",{"request":request,"is_for":is_for,"zxc":zxc,"username":username,"msg":msg,"a":a,"users_in_db":users_in_db})


@app.post("/chat", include_in_schema=False)
async def get(request:Request,msg: str = None,user: User = Depends(current_active_user)):
    username=user.email.split('@')[0]
    form = await request.form()
    to = form.get("username")
    message = form.get("message")
    if to:
        query = reciver.update().values(reciver = to)
        await database.execute(query)
        query = reciver.select()
        is_for = await database.fetch_all(query)
        for item in is_for:
            to=item.reciver
        query = texts.select().where(texts.c.to == username, texts.c.by == to )
        text_in_private=await database.fetch_all(query)
        query = texts.select().where(texts.c.to == to, texts.c.by == username )
        text_by_in_private=await database.fetch_all(query)
        all_messages = text_in_private + text_by_in_private
        asd = sorted(all_messages, key=lambda time: time[3])
        zxc= sorted(asd, key=lambda date: date[4])
        zxc.reverse()
    else:
        query = reciver.select()
        is_for = await database.fetch_all(query)
        for item in is_for:
            to=item.reciver
        query = texts.insert().values(message = message ,to = to, by = username, created_at = (datetime.now()).strftime("%I:%M%p"),
        date = date.today().strftime("%m/%d/%y"))
        await database.execute(query)
        query = texts.select().where(texts.c.to == username, texts.c.by == to )
        text_in_private=await database.fetch_all(query)
        query = texts.select().where(texts.c.to == to, texts.c.by == username )
        text_by_in_private=await database.fetch_all(query)
        all_messages = text_in_private + text_by_in_private
        asd = sorted(all_messages, key=lambda time: time[3])
        zxc= sorted(asd, key=lambda date: date[4])
        zxc.reverse()
    query = users.select().where(users.c.username != username)
    users_in_db=await database.fetch_all(query)
    a = [tup[0] for tup in users_in_db]
    b = a[0]
    query = texts.select()
    c = await database.fetch_all(query)
    d = c[-1]
    e = d[1]
    if e in a :
        a.remove(e)
        a.insert(0,e)
        f = c[-2]
        g = f[1]
        if g in a :
            a.remove(g)
            a.insert(1,g)
        else:
            g = f[2]
            a.remove(g)
            a.insert(1,g)
    else:
        e = d[2]
        a.remove(e)
        a.insert(0,e)
        f = c[-2]
        g = f[1]
        a.remove(g)
        a.insert(1,g)
    return templates.TemplateResponse("chat.html",{"request":request,"is_for":is_for,"zxc":zxc,"username":username,"msg":msg,"a":a,"users_in_db":users_in_db})


@app.get("/creatgroup", include_in_schema=False)
async def get(request:Request,msg: str = None,user: User = Depends(current_active_user)):
    username=user.email.split('@')[0]
    return templates.TemplateResponse("creatgroup.html",{"request":request,"username":username})

@app.post("/creatgroup", include_in_schema=False)
async def get(request:Request,msg: str = None,user: User = Depends(current_active_user)):
    username=user.email.split('@')[0]
    form = await request.form()
    groupname = form.get("groupname")
    errors = []
    query = groupuser.select().where(groupuser.c.groupname == groupname)
    mygroups = await database.fetch_all(query)
    taken = [tup[0] for tup in mygroups]
    if groupname in taken:
        errors.append("Groupname is taken")
        return templates.TemplateResponse("creatgroup.html",{"request":request,"username":username,"errors":errors}) 
    else:
        query = group.insert().values(groupname = groupname, admin = username)
        await database.execute(query)
        query = groupuser.insert().values(groupname = groupname, username = username)
        await database.execute(query)
        return RedirectResponse(url=f"/managegroups", status_code=303)


@app.get("/managegroups", include_in_schema=False)
async def get(request:Request,user: User = Depends(current_active_user)):
    username=user.email.split('@')[0]
    query = group.select().where(group.c.admin == username)
    mygroups=await database.fetch_all(query)
    h= [tup[0] for tup in mygroups]
    query = groupuser.select().where(groupuser.c.username == username)
    ingroups=await database.fetch_all(query)
    G= [tup[0] for tup in ingroups]
    l3 = [x for x in G if x not in h]
    return templates.TemplateResponse("managegroups.html",{"request":request,"ingroups":ingroups,"mygroups":mygroups,"username":username,"l3":l3})


@app.post("/managegroups", include_in_schema=False)
async def get(request:Request,user: User = Depends(current_active_user)):
    username=user.email.split('@')[0]
    form = await request.form()
    id = form.get("id")
    groupname = form.get("adduserin")
    kickuser = form.get("kickuser")
    left = form.get("left")
    if id:
        query = group.delete().where(group.c.groupname == id)
        await database.execute(query)
        query = groupuser.delete().where(groupuser.c.groupname == id)
        await database.execute(query)
        query = group_contant.delete().where(group_contant.c.groupname == id)
        await database.execute(query)
        return RedirectResponse(url=f"managegroups", status_code=303)
    elif groupname:
        query = member.update().values(member = groupname)
        await database.execute(query)
        return RedirectResponse(url=f"adduser", status_code=303)
    elif kickuser:
        query = member.update().values(member = kickuser)
        await database.execute(query)
        return RedirectResponse(url=f"kickuser", status_code=303)
    elif left:
        query = groupuser.delete().where(groupuser.c.groupname == left , groupuser.c.username == username)
        await database.execute(query) 
        return RedirectResponse(url=f"managegroups", status_code=303)


@app.get("/kickuser", include_in_schema=False)
async def get(request:Request,msg: str = None,user: User = Depends(current_active_user)):
    username=user.email.split('@')[0]
    query = member.select()
    is_of = await database.fetch_all(query)
    for item in is_of:
        groupname=item.member
    query = groupuser.select().where(groupuser.c.groupname == groupname ,groupuser.c.username != username)
    userin = await database.fetch_all(query)
    return templates.TemplateResponse("kickuser.html",{"request":request,"username":username,"userin":userin,"is_of":is_of})  


@app.post("/kickuser", include_in_schema=False)
async def get(request:Request,msg: str = None,user: User = Depends(current_active_user)):
    form = await request.form()
    uzer = form.get("uzer")
    query = member.select()
    is_of = await database.fetch_all(query)
    for item in is_of:
        groupname=item.member
    query = groupuser.delete().where(groupuser.c.groupname == groupname, groupuser.c.username == uzer)
    await database.execute(query)
    return RedirectResponse(url=f"managegroups", status_code=303)
    

@app.get("/adduser", include_in_schema=False)
async def get(request:Request,msg: str = None,user: User = Depends(current_active_user)):
    username=user.email.split('@')[0]
    query = member.select()
    is_of = await database.fetch_all(query)
    for item in is_of:
        groupname=item.member
    query = groupuser.select().where(groupuser.c.groupname == groupname ,groupuser.c.username != username)
    userin = await database.fetch_all(query)
    userisin= [tup[-1] for tup in userin] 
    query = users.select().where(users.c.username != username)
    users_in_db=await database.fetch_all(query)
    users_in= [tup[-1] for tup in users_in_db] 
    l3 = [x for x in users_in if x not in userisin]
    return templates.TemplateResponse("adduser.html",{"request":request,"username":username,"users_in_db":users_in_db,"is_of":is_of,"l3":l3})

@app.post("/adduser", include_in_schema=False)
async def get(request:Request,msg: str = None,user: User = Depends(current_active_user)):
    form = await request.form()
    uzer = form.get("uzer")
    query = member.select()
    is_of = await database.fetch_all(query)
    for item in is_of:
        groupname=item.member
    query = groupuser.insert().values(groupname = groupname, username = uzer)
    await database.execute(query)
    return RedirectResponse(url=f"managegroups", status_code=303)
    

@app.get("/groupchat", include_in_schema=False)
async def get(request:Request,msg: str = None,user: User = Depends(current_active_user)):
    username=user.email.split('@')[0]
    query = groupuser.select().where(groupuser.c.username == username)
    ingroups=await database.fetch_all(query)
    a = [tup[0] for tup in ingroups]
    b = a[0]
    query = groupname.select()
    is_for = await database.fetch_all(query)
    for item in is_for:
        to=item.groupname
    if to in a:
        query = group_contant.select().where(group_contant.c.groupname == to)
        all_messages = await database.fetch_all(query)
        asd = sorted(all_messages, key=lambda time: time[3])
        zxc= sorted(asd, key=lambda date: date[4])
        zxc.reverse()
    else:
        query = groupname.update().values(groupname = b)
        await database.execute(query)
        query = groupname.select()
        is_for = await database.fetch_all(query)
        for item in is_for:
            to=item.groupname
        query = group_contant.select().where(group_contant.c.groupname == to)
        all_messages = await database.fetch_all(query)
        asd = sorted(all_messages, key=lambda time: time[3])
        zxc= sorted(asd, key=lambda date: date[4])
        zxc.reverse()
    return templates.TemplateResponse("groupchat.html",{"request":request,"is_for":is_for,"zxc":zxc,"msg":msg,"username":username,"ingroups":ingroups})


@app.post("/groupchat", include_in_schema=False)
async def create_text(request: Request,user: User = Depends(current_active_user)):
    username=user.email.split('@')[0]
    form = await request.form()
    to = form.get("groupname")
    message = form.get("message")
    if to:
        query = groupname.update().values(groupname = to)
        await database.execute(query)
        query = groupname.select()
        is_for = await database.fetch_all(query)
        for item in is_for:
            to=item.groupname
        query = group_contant.select().where(group_contant.c.groupname == to)
        all_messages = await database.fetch_all(query)
        asd = sorted(all_messages, key=lambda time: time[3])
        zxc= sorted(asd, key=lambda date: date[4])
        zxc.reverse()
    else:
        query = groupname.select()
        is_for = await database.fetch_all(query)
        for item in is_for:
            to=item.groupname
        query = group_contant.insert().values(message = message ,groupname = to, by = username, created_at = (datetime.now()).strftime("%I:%M%p"),
        date = date.today().strftime("%m/%d/%y"))
        await database.execute(query)
        query = group_contant.select().where(group_contant.c.groupname == to)
        all_messages = await database.fetch_all(query)
        asd = sorted(all_messages, key=lambda time: time[3])
        zxc= sorted(asd, key=lambda date: date[4])
        zxc.reverse()
    query = groupuser.select().where(groupuser.c.username == username)
    ingroups=await database.fetch_all(query)
    return templates.TemplateResponse("groupchat.html",{"request":request,"zxc":zxc,"is_for":is_for,"username":username,"ingroups":ingroups})











