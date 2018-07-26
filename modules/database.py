import os

from peewee import *

dirname = os.path.dirname(__file__)
filename = os.path.join(dirname, '../database.db')
db = SqliteDatabase(filename)  # Database system here


class BaseModel(Model):
    class Meta:
        database = db


class User(BaseModel):
    phonenumber = CharField(unique=True)
    authcode = IntegerField()

    time = DateTimeField()  # Last interaction
    count = IntegerField()  # Number of interactions

    claim_last = DateTimeField()

    trust_address = CharField(null=True)
    trust_phonenumber = CharField(null=True)

    rec_word = CharField()

class SystemUser(BaseModel):
    name = CharField(unique=True)

    time = DateTimeField(null=True)  # Last interaction
    count = IntegerField(null=True)  # Number of interactions

class TopupCards(BaseModel):
    cardcode = CharField(unique=True)
    cardvalue = IntegerField()
    cardsn = CharField(unique=True)
    claimed = BooleanField(default=False)

tables = [SystemUser, User, TopupCards, ]


if __name__ == "__main__":
    db.create_tables(tables)
    
    # Create system users
    faucet = SystemUser.get_or_create(name="faucet")
    top_up = SystemUser.get_or_create(name="top_up")
