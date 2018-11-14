from modules.database import User, TopupCards, db
from datetime import datetime, timedelta

db.connect()


#Placeholders, for example only
print("loading cards... ")

load_cards = [
    {'cardcode': 'PNN189', 'cardvalue': 1, 'cardsn': 'NANO-A-154', 'claimed' :False},
    {'cardcode': 'KSL165', 'cardvalue': 2, 'cardsn': 'NANO-A-155', 'claimed' :False},
    {'cardcode': 'ERH498', 'cardvalue': 3, 'cardsn': 'NANO-A-156', 'claimed' :False}

]

TopupCards.insert_many(load_cards).execute()
print("Success!")
