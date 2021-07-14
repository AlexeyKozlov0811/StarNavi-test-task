from tortoise import fields
from tortoise.models import Model
from tortoise.contrib.pydantic import pydantic_model_creator
from passlib.hash import bcrypt


class Users(Model):
    user_id = fields.IntField(pk=True)
    username = fields.CharField(50, unique=True)
    password_hash = fields.CharField(128)
    last_login_time = fields.DatetimeField(auto_now_add=True)
    last_request_time = fields.DatetimeField(auto_now=True)

    def verify_password(self, password):
        return bcrypt.verify(password, self.password_hash)


class Posts(Model):
    post_id = fields.IntField(pk=True)
    posted_by = fields.ForeignKeyField("models.Users", related_name="Posts")
    creation_date = fields.DateField()
    total_likes = fields.IntField(default=0)
    content = fields.CharField(255)


class Likes(Model):
    like_id = fields.IntField(pk=True)
    liked_post = fields.ForeignKeyField("models.Posts", related_name="Liked_Post")
    liked_by = fields.ForeignKeyField("models.Users", related_name="Likes")
    liked_date = fields.DateField()


User_Pydantic = pydantic_model_creator(Users, name='Users')
