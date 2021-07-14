import jwt
from typing import Optional
from pydantic import BaseModel
from passlib.hash import bcrypt
from datetime import date, datetime
from fastapi import FastAPI, Depends, HTTPException, status, Form
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from tortoise.contrib.fastapi import register_tortoise, HTTPNotFoundError
from models import User_Pydantic, Users, Posts, Likes

app = FastAPI()

JWT_SECRET = 'myjwtsecret'

oauth2_scheme = OAuth2PasswordBearer(tokenUrl='token')


class Status(BaseModel):
    message: str


class Token(BaseModel):
    access_token: str
    token_type: str


class Activity(BaseModel):
    last_logged_in: datetime
    last_request: datetime


async def authenticate_user(username: str, password: str):
    try:
        user = await Users.get(username=username)
        if not user.verify_password(password):
            raise
        return user
    except:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail='Invalid username or password'
        )


@app.post('/api/login', response_model=Token)
async def generate_token(form_data: OAuth2PasswordRequestForm = Depends()):
    user = await authenticate_user(form_data.username, form_data.password)
    user_obj = await User_Pydantic.from_tortoise_orm(user)
    token = jwt.encode(user_obj.dict(exclude={"last_login_time", "last_request_time"}), JWT_SECRET)
    return {'access_token': token, 'token_type': 'bearer'}


async def get_current_user(token: str = Depends(oauth2_scheme)):
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=['HS256'])
        user = await Users.get(user_id=payload.get('user_id'))
    except:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail='Invalid username or password'
        )
    await user.save()
    return user


@app.post('/api/signup', response_model=Status)
async def create_user(username: str = Form(...), password: str = Form(...)):
    user_obj = Users(username=username, password_hash=bcrypt.hash(password))
    await user_obj.save()
    return Status(message="Account created")


@app.get("/api/user_activity/{username}", response_model=Activity, responses={404: {"model": HTTPNotFoundError}})
async def get_user_activity(username: str):
    user = await Users.get(username=username)
    return Activity(last_logged_in=user.last_login_time, last_request=user.last_request_time)


@app.post("/api/posts/create")
async def create_post(user: Users = Depends(get_current_user),
                      content: str = Form(...)):
    post = await Posts.create(content=content, posted_by=user, creation_date=date.today())
    return post


@app.post("/api/posts/like/{post_id}", response_model=Status, responses={404: {"model": HTTPNotFoundError}})
async def like_post(post_id: int,
                    user: User_Pydantic = Depends(get_current_user)):
    post = await Posts.get(post_id=post_id)
    try:
        if await Likes.get(liked_post=post, liked_by=user):
            return Status(message="Post already liked")
    except:
        await Likes.create(liked_post=post, liked_by=user, liked_date=date.today())
        post.total_likes += 1
        await post.save()
        return Status(message="Post liked")


@app.delete("/api/posts/unlike/{post_id}", response_model=Status, responses={404: {"model": HTTPNotFoundError}})
async def unlike_post(post_id: int,
                      user: User_Pydantic = Depends(get_current_user)):
    post = await Posts.get(post_id=post_id)
    try:
        like = await Likes.get(liked_post=post, liked_by=user)
        if like:
            await like.delete()
            post.total_likes -= 1
            await post.save()
            return Status(message="Post unliked")
    except:
        return Status(message="Posts haven't been liked by a current user")


@app.get("/api/posts/analytics")
async def get_analytics(date_from: Optional[date] = None, date_to: Optional[date] = None):
    if date_from is None and date_to is None:
        analytics = await Likes.all().order_by("liked_date")
    elif date_from is not None and date_to is None:
        analytics = await Likes.filter(liked_date__gte=date_from).order_by("liked_date")
    elif date_from is None and date_to is not None:
        analytics = await Likes.filter(liked_date__lte=date_to).order_by("liked_date")
    else:
        analytics = await Likes.filter(liked_date__range=[date_from, date_to]).order_by("liked_date")
    return analytics


"""connect to database"""
register_tortoise(
    app,
    db_url='sqlite://db.sqlite3',
    modules={'models': ['models']},
    generate_schemas=True,
    add_exception_handlers=True
)
