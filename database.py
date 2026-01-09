from peewee import *

db = SqliteDatabase('bot.db')

class BaseModel(Model):
    class Meta:
        database = db

class User(BaseModel):
    telegram_id = IntegerField(unique=True)
    username = CharField(null=True)
    first_name = CharField()
    last_name = CharField(null=True)
    created_at = DateTimeField(constraints=[SQL('DEFAULT CURRENT_TIMESTAMP')])
    messages_count = IntegerField(default=0)

class Message(BaseModel):
    user = ForeignKeyField(User, backref='messages')
    text = TextField()
    direction = CharField()  # 'incoming' или 'outgoing'
    created_at = DateTimeField(constraints=[SQL('DEFAULT CURRENT_TIMESTAMP')])

def init_database():
    db.connect()
    db.create_tables([User, Message], safe=True)
    db.close()

def get_or_create_user(user_data):
    db.connect()
    user, created = User.get_or_create(
        telegram_id=user_data.id,
        defaults={
            'username': user_data.username,
            'first_name': user_data.first_name,
            'last_name': user_data.last_name
        }
    )
    db.close()
    return user, created