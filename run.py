import json, re
import random
import time
import binascii
from bitstring import BitArray
from datetime import datetime, timedelta

import phonenumbers
from flask import Flask, request
from twilio.twiml.messaging_response import MessagingResponse
from twilio.rest import Client
from decimal import Decimal
from modules.misc import Config
from modules.database import SystemUser, User, db, TopupCards, Alias
from modules import nano

#nano = NanoFunctions(Config().get("uri")[0])
client = Client(Config().get("account_sid"), Config().get("auth_token"))
wallet_seed = Config().get("seed")

db.connect()

app = Flask(__name__)


def authcode_gen_save(user_details):
    new_authcode = (random.SystemRandom().randint(1000, 9999))
    user_details.authcode = new_authcode
    user_details.save()
    return new_authcode


def register(user_details, text_body):
    print('Found register')
    faucet = nano.get_address(0,str(wallet_seed))
    account = nano.get_address(user_details.id + 1,str(wallet_seed))

    print("Opening Account: ",account)
    nano.send_xrb(account, 1, faucet, 0,str(wallet_seed))
    nano.open_xrb(int(user_details.id + 1), account,str(wallet_seed))

    # Start our response
    resp = MessagingResponse()

    # Add a message
    new_authcode = authcode_gen_save(user_details)
    resp.message(f'Welcome to NanoSMS, your address:\n'
                 f'{account}, Code: {new_authcode}')
    return resp


def commands(user_details, text_body):
    print('Found help')
    resp = MessagingResponse()
    resp.message('balance - get your balance\nsend - send Nano\naddress - your nano address')
    return resp


def address(user_details, text_body):
    print('Found address')
    account = nano.get_address(user_details.id + 1,str(wallet_seed))
    resp = MessagingResponse()
    resp.message(f'{account}')
    return resp

def alias(user_details, text_body):
    print('Found alias request')
    components = text_body.split(" ")
    alias = components[2]
    account = nano.get_address(user_details.id + 1,str(wallet_seed))
    resp = MessagingResponse()

    regex= "(\d{3}[-\.\s]??\d{3}[-\.\s]??\d{4}|\(\d{3}\)\s*\d{3}[-\.\s]??\d{4}|\d{3}[-\.\s]??\d{4})"

    if re.search(regex, alias):
       valid_num = "Yes"
    else:
       valid_num = "No"

    user_alias = Alias.get_or_none(phonenumber=user_details.phonenumber)
    if user_alias is None:
       try:
        if alias[:4] == "xrb_" or valid_num == "Yes":
           print('Restricted Alias ',alias)
           resp.message(f'Set Alias Failed: Restricted Alias {alias}')
           return resp
        else:
           user_alias = Alias.create(
             phonenumber=user_details.phonenumber,
             address=account,
             alias=alias)
           print('User alias set to ',alias)
           resp.message(f'Alias successfully set to {alias}')
           return resp
       except:
         print('Alias Taken')
         resp.message('Alias already claimed')
         return resp

    else:
        print(f'Error Alias Exists\n User Alias is: {user_alias.alias}')
        resp.message(f'Alias Exists\n Your Alias is: {user_alias.alias}')
        return resp

def history(user_details, text_body):
    print('Found address')
    account = nano.get_address(user_details.id + 1,str(wallet_seed))
    resp = MessagingResponse()
    resp.message(
        f'https://www.nanode.co/account/{account}')
    return resp


def balance(user_details, text_body):
    print('Found balance')

    account = nano.get_address(user_details.id + 1,str(wallet_seed))
    faucet = nano.get_address(0,str(wallet_seed))
    print(account)
    previous = nano.get_previous(str(account))
    print(previous)
    print(len(previous))

    pending = nano.get_pending(str(account))
    if (len(previous) == 0):
        print("Opening Account: ",account)
        nano.send_xrb(account, 1, faucet, 0,str(wallet_seed))
        nano.open_xrb(int(user_details.id + 1), account,str(wallet_seed))

    print("Rx Pending: ", pending)
    pending = nano.get_pending(str(account))
    print(f'Pending Len: {len(pending)}')

    while len(pending) > 0:
        pending = nano.get_pending(str(account))
        print(len(pending))
        nano.receive_xrb(int(user_details.id + 1), account,str(wallet_seed))

    if len(previous) == 0:
        balance = "Empty"
    else:
        previous = nano.get_previous(str(account))
        balance = int(nano.get_balance(previous))/ \
                               1000000000000000000000000000000

    print("User balance",str(balance))
    # Start our response
    resp = MessagingResponse()

    # Add a message
    resp.message(f'Balance: {balance} Nano')
    return resp

def sendauthcode(user_details, text_body):
    print('Found authcode request')
    authcode = user_details.authcode
    resp = MessagingResponse()
    resp.message(
        f'New authorization code request success. '
        f'Please use the following authcode: {authcode}')
    return resp


def send(user_details, text_body):
    print('Found send')
    account = nano.get_address(user_details.id + 1,str(wallet_seed))
    components = text_body.split(" ")
    previous = nano.get_previous(str(account))
    balance = int(nano.get_balance(previous))

    # Check amount is real
    try:
        print("Sending: ",Decimal(components[1]) * 1000000000000000000000000000000)
        amount = int(Decimal(components[1])*1000000000000000000000000000000)
        print('Amount to send: ', amount)
        authcode = int(components[3])
    except:
        resp = MessagingResponse()
        resp.message("Error: Incorrect Amount please use the following format\nsend 10 +1234567890 1001")
        return str(resp)
        print('Error with send')
    destination = components[2]

    destination = destination.replace("\u202d", "")
    destination = destination.replace("\u202c", "")
    authcode = int(components[3])

    #Test Number validity
    regex= "(\d{3}[-\.\s]??\d{3}[-\.\s]??\d{4}|\(\d{3}\)\s*\d{3}[-\.\s]??\d{4}|\d{3}[-\.\s]??\d{4})"

    if re.search(regex, destination):
       valid_num = "Yes"
    else:
       valid_num = "No"

    print(f'Destination: {destination}\nValid Number: {valid_num}')

    if authcode == int(user_details.authcode):
        print('Authcode valid!')
        if amount>balance:
            print("Insufficient balance","\nAmount to send: ",str(amount),"\nBalance: ",str(balance/1000000000000000000000000000000))
            resp = MessagingResponse()
            resp.message(f'Insufficient balance!\nYour Balance: {balance}')
            return resp

        #Send to xrb address
        if destination[:4] == "xrb_":
            print("Destination is xrb addresses format")
            nano.send_xrb(destination, amount, account, user_details.id + 1,str(wallet_seed))
            resp = MessagingResponse()
            new_authcode = authcode_gen_save(user_details)

            previous = nano.get_previous(str(account))
            balance = int(nano.get_balance(previous))/\
                                   1000000000000000000000000000000

            resp.message(f'Sent to {destination}!\nYour Balance approx.: {balance}\nNew Authcode: {new_authcode}')
            return resp

       #Send to Alias
        if valid_num == "No":

            print("Sending request to alias address ", destination)
            dest_user_details = Alias.get_or_none(alias=destination)
            if dest_user_details is not None:
               print(dest_user_details)

               dest_address = dest_user_details.address
               alias = dest_user_details.alias
               dest_phone = dest_user_details.phonenumber
               print(f'Sending to {dest_address} \nAlias: , {alias}')
               nano.send_xrb(dest_address, amount, account, user_details.id + 1,str(wallet_seed))
               new_authcode = authcode_gen_save(user_details)

               previous = nano.get_previous(str(account))
               balance = int(nano.get_balance(previous)) / \
                   1000000000000000000000000000000

               resp = MessagingResponse()
               resp.message(f'Sent to {destination}!\nYour Balance approx.: {balance}\nNew Authcode: {new_authcode}')
               return resp

               bodysend = 'You have recieved nano!\nPlease send register or balance to open your block on the Nano Network'
               twilionum = Config().get("twilionum")

               print(f'Sending: {bodysend}'
                     f' to {dest_phone} from {twilionum}')

               message = client.messages.create(
               from_=twilionum, body=bodysend, to=dest_phone)

               print(message.sid)

            else:
               print("Alias not found ", destination)
               resp = MessagingResponse()
               resp.message(f'Error! Unrecognized Alias\nSet an alias with - set alias myAlias')
               return resp

        #send to phonenumber
        else:
            try:
                phonenum = phonenumbers.parse(destination,
                                              user_details.country)
                dest_phone = phonenumbers.format_number(
                    phonenum, phonenumbers.PhoneNumberFormat.E164)
                print('Destination is phonenumber: ',dest_phone)
            except phonenumbers.phonenumberutil.NumberParseException:
                print("Error")
                resp = MessagingResponse()
                resp.message("Error: Incorrect destination address/number try using E164 format")
                return resp

        if not phonenumbers.is_possible_number(phonenum):
            resp = MessagingResponse()
            resp.message("Error: Incorrect destination")
            return resp

        dest_user_details = User.get_or_none(phonenumber=dest_phone)
        print('\nReciepient ID: ', dest_user_details)

        #Send to phonenumber, and register if not registered.
        dest_user_details = User.get_or_none(phonenumber=dest_phone)
        if dest_user_details is None:
            dest_authcode = random.SystemRandom().randint(1000, 9999)
            rec_word = ''.join(
                 random.sample(open("english.txt").read().split(), 5))
            x = phonenumbers.parse(dest_phone, None)
            region =  phonenumbers.region_code_for_number(x)
            print("Destination region: ",region)
            dest_user_details = User.create(
                phonenumber=dest_phone,
                country = region,
                time=datetime.now(),
                count=1,
                authcode=dest_authcode,
                claim_last=0,
                rec_word=rec_word)
        print("User created", dest_phone)

        dest_user_details = User.get_or_none(phonenumber=dest_phone)
        dest_address = nano.get_address(dest_user_details.id + 1,str(wallet_seed))
        print("Sending to: " + dest_address)
        nano.send_xrb(dest_address, amount, account, user_details.id + 1,str(wallet_seed))

        previous = nano.get_previous(str(account))
        balance = int(nano.get_balance(previous))/ \
                               1000000000000000000000000000000

        bodysend = 'You have recieved nano!\nPlease send register or balance to open your block on the Nano Network'
        twilionum = Config().get("twilionum")

        print(f'Sending: {bodysend}'
              f' to {dest_phone} from {twilionum}')

        message = client.messages.create(
            from_=twilionum, body=bodysend, to=dest_phone)

        print(message.sid)

        resp = MessagingResponse()
        new_authcode = authcode_gen_save(user_details)
        resp.message(
            f'Sent to {destination}!\nYour Balance approx.: {balance} \nNew Authcode: {new_authcode}')
        return resp

    else:
        print('Invalid authcode! \nAuthcode submitted: ',authcode)
        new_authcode = authcode_gen_save(user_details)
        print('Authcode required: ',new_authcode)
        resp = MessagingResponse()
        resp.message("Error: Incorrect Auth Code try: "+str(new_authcode))
        return resp


def claim(user_details, text_body):
    faucet = nano.get_address(0,str(wallet_seed))
    print("Found faucet claim")
    account = nano.get_address(user_details.id + 1,str(wallet_seed))
    current_time = int(time.time())
    if int(user_details.claim_last) == 0:
        print("They can claim")
        # Check faucet balance
        previous = nano.get_previous(str(faucet))
        faucet_bal = int(nano.get_balance(previous))/ \
                                  1000000000000000000000000000000

        claim = faucet_bal * 0.01
        print("Faucet claim: ",claim,"\nFaucet balance: ",faucet_bal)
        nano.send_xrb(account, claim, faucet, 0,str(wallet_seed))
        user_details.claim_last = 1
        user_details.save()

        resp = MessagingResponse()
        resp.message(
            f'Claim Success {claim}\n'
            f'Send balance to check your balance'
            f'AD1: Place your ad here!\n'
            f'AD2: Place your ad here!\n')

        print(f'{claim} sent to {account} from faucet\n'
              f'Faucet funds remaining {faucet_bal-claim}')
        return resp
    else:
        print('User has already claimed')
        resp = MessagingResponse()
        resp.message("This number has already made a claim")
        return resp


def trust(user_details, text_body):
    # Only works with local numbers. Do not supply country code.
    print("Found trust")
    components = text_body.split(" ")

    authcode = int(components[2])
    if authcode == int(user_details.authcode):
        if "x" in components[1][0]:
            try:
                if nano.xrb_account(components[1]):
                    xrb_trust = components[1]
                    resp = MessagingResponse()
                    new_authcode = authcode_gen_save(user_details)
                    resp.message(f'Trust address set to {components[1]}'
                                 f', Code: {new_authcode}')

                    user_details.trust_address = xrb_trust
                    user_details.trust_phonenumber = 0
                    user_details.save()
                    return resp
                else:
                    print("Invalid address")
                    resp = MessagingResponse()
                    new_authcode = authcode_gen_save(user_details)
                    resp.message(f'Invalid address, Code:  {new_authcode}')
                    return resp

            except KeyError:
                print("Invalid address")
                resp = MessagingResponse()
                new_authcode = authcode_gen_save(user_details)
                resp.message(f'Invalid address, Code:  {new_authcode}')
                return resp

        elif components[1].isdigit():
            trust_number = components[1]
            resp = MessagingResponse()
            new_authcode = authcode_gen_save(user_details)
            resp.message(
                f'Trust address set to {components[1]}, Code: {new_authcode}')
            user_details.trust_address = ""
            user_details.trust_number = trust_number
            user_details.save()
            return resp

        else:
            print("No valid trust")
            resp = MessagingResponse()
            new_authcode = authcode_gen_save(user_details)
            resp.message(f'No valid trust, Code: {new_authcode}')
            return resp

    else:
        resp = MessagingResponse()
        resp.message("Error: Incorrect Auth Code")
        return resp


def recover(user_details, text_body):
    print('Start Recovery')

    components = text_body.split(" ")
    rec_word_rx = components[1]

    # Check recovery word
    try:
        rec_details = User.get(User.rec_word == rec_word_rx)
        rec_account = nano.get_address(rec_details.id + 1,str(wallet_seed))

        resp = MessagingResponse()
        new_authcode = authcode_gen_save(user_details)
        resp.message(
            f'Recover Success! \nPhone number: {rec_details.phonenumber}\n'
            f'Address: {rec_account}\n'
            f'AuthCode: {new_authcode}')
        return resp

    except:
        resp = MessagingResponse()
        resp.message("Error recovery phrase not recognised")
        return resp


def topup(user_details, text_body):
    print('Found topup request')

    components = text_body.split(" ")
    cardcode = str.upper(components[1])

    account = nano.get_address(user_details.id + 1,str(wallet_seed))
    current_time = int(time.time())

    print('User request: ',account,'\nTime: ',current_time)

    #check card code valid
    card_valid = TopupCards.get_or_none(TopupCards.cardcode == cardcode)
    if card_valid == None:
        print("Card code error " + cardcode)
        resp = MessagingResponse()
        resp.message("Error: Invalid Topup voucher code")
        return resp

    if card_valid.claimed == True:
        print("Card already claimed " + cardcode)
        resp = MessagingResponse()
        resp.message("Card has already been claimed")
        return resp

    topupadd = nano.get_address(1,str(wallet_seed))
    previous = nano.get_previous(str(topupadd))
    topupadd_bal = int(nano.get_balance(previous))

    card_val = card_valid.cardvalue/10 #DELETE AFTER ALPHA TOP UP CARDS ARE DEPLETED
    card_val = card_val*1000000000000000000000000000000 #Card value in RAW

    if topupadd_bal < card_val:
        print(
            f'Insufficient Balance\n'
            f'Address Balance: {topupadd_bal} \nCard request: {card_val}'
        )

    else:
        nano.send_xrb(account, card_val, topupadd, 1,str(wallet_seed))

        previous = nano.get_previous(str(account))
        print("Testing previous: ",previous)
        print("Len previous",len(previous))
        if len(previous) == 0:
           balance = 0
        else:
           balance = int(nano.get_balance(previous))/ \
                                1000000000000000000000000000000
        balance = balance
        resp = MessagingResponse()
        resp.message(f'Topup success!\n'
                     f'Your new account balance is approx {balance}\n')

        print(f'Success topup to {account} from topup address\n'
              f'Address Balance {topupadd_bal-card_val}')
        card_valid.claimed = True
        card_valid.save()
        return resp


@app.route("/sms", methods=['GET', 'POST'])
def sms_ahoy_reply():

    print(request.values)
    from_number = request.values.get('From')
    from_country = request.values.get('FromCountry')

    user_details = User.get_or_none(User.phonenumber == from_number)
    if user_details is None:  # User is not found in the database
        print(f'{from_number} is not in database.')
        authcode = random.SystemRandom().randint(1000, 9999)
        rec_word = ''.join(
            random.sample(open("english.txt").read().split(), 5))
        user_details = User.create(
            phonenumber=from_number,
            country=from_country,
            time=datetime.now(),
            count=1,
            authcode=authcode,
            claim_last=0,
            rec_word=rec_word)

    if (datetime.now() - user_details.time).total_seconds() < 5:
        time.sleep(5)
        print(user_details.phonenumber + ' user rate locked for 5 seconds')

    else:
        print(
            f'{user_details.id} - {user_details.phonenumber} sent a message.')
        user_details.phonenumber = from_number
        user_details.country = from_country
        user_details.time = datetime.now()
        user_details.count += 1
        user_details.save()

    text_body = request.values.get('Body')
    text_body = text_body.lower()
    print("Message details: ",text_body)

    components = text_body.split(" ")
    #amount = int(components[0]) * 1000000000000000000000000

    if 'register' in text_body:
        return str(register(user_details, text_body))

    elif 'commands' in text_body:
        return str(commands(user_details, text_body))

    elif 'address' in text_body:
        return str(address(user_details, text_body))

    elif 'alias' in text_body:
        return str(alias(user_details, text_body))

    elif 'history' in text_body:
        return str(history(user_details, text_body))

    elif 'balance' in text_body:
        return str(balance(user_details, text_body))

    elif 'send' in text_body:
        return str(send(user_details, text_body))

    #check if user is sending value
    elif "authcode" in text_body:
        return str(sendauthcode(user_details, text_body))

    elif 'claim' in text_body:
        return str(claim(user_details, text_body))

    elif 'trust' in text_body:
        return str(trust(user_details, text_body))

    elif 'recover' in text_body:
        return str(recover(user_details, text_body))

    elif 'topup' in text_body:
        return str(topup(user_details, text_body))

    else:
        print('Error ' + text_body)

        # Start our response
        resp = MessagingResponse()

        # Add a message
        resp.message("Command not recognised, send commands for a list of commands")

    return str(resp)


if __name__ == "__main__":
    # Check twilio information
    print('Twilio client: ',client)
    print('Twilio number: ',Config().get("twilionum"))
    # Check faucet address on boot to make sure we are up to date
    account = nano.get_address(0,str(wallet_seed))
    print("Faucet Address: ",account)
    previous = nano.get_previous(str(account))
    print("Previous Hash: ",previous)
    print("Hash Length: ",len(previous))

    # Check faucet and topup address balance
    topupacc = nano.get_address(1,str(wallet_seed))
    faucbal = int(nano.get_balance(nano.get_previous(account)))
    topupbal = int(nano.get_balance(nano.get_previous(topupacc)))
    print("\nFaucet Balance [RAW]: ",faucbal,"\nTopup Balance [RAW]: ",topupbal)
    print("\nFaucet Balance: ",faucbal/1000000000000000000000000000000,"\nTopup Balance: ",topupbal/1000000000000000000000000000000)


    pending = nano.get_pending(str(account))
    if (len(previous) == 0) and (len(pending) > 0):
        print("Opening Account")
        nano.open_xrb(int(0), account,str(wallet_seed))

    print(f'Rx Pending: {pending}')
    pending = nano.get_pending(str(account))
    print(f'Pending Len: {len(pending)}')

    while len(pending) > 0:
        pending = nano.get_pending(str(account))
        print(len(pending))
        nano.receive_xrb(int(0), account,str(wallet_seed))

    app.run(debug=True, host="0.0.0.0", port=5002)
