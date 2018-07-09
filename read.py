import dataset

db = dataset.connect('sqlite:///users.db')

print(Read Database)

for user in db['user']:
   print(user)
