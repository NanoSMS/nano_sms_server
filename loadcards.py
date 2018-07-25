from modules.database import User, TopupCards, db
from datetime import datetime, timedelta

db.connect()

#Placeholders, for example only
load_cards = [
	{'cardcode': 'AAA123', 'cardvalue': 100, 'cardsn': 'NANO-S-TEST'},
    {'cardcode': 'BBB123', 'cardvalue': 1, 'cardsn': 'NANO-S-001'},
    {'cardcode': 'CCC123', 'cardvalue': 2, 'cardsn': 'NANO-S-002'},
    {'cardcode': 'DDD123', 'cardvalue': 3, 'cardsn': 'NANO-S-003'},
    # ...
]

print("loading cards... ")
TopupCards.insert_many(load_cards).execute()
