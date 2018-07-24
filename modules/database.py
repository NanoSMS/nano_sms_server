from peewee import *


db = "" # Database system here


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
