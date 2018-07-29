import json
import random
import time
from datetime import datetime, timedelta

import phonenumbers
from flask import Flask, request
from twilio.twiml.messaging_response import MessagingResponse
from twilio.rest import Client

from modules.misc import Config
from modules.database import SystemUser, User, db
from modules.nano import NanoFunctions

nano = NanoFunctions(Config().get("uri")[0])

#to do: move to config
account_sid = 'AC3816271493b14891c0a02e676c74195d'
auth_token = 'auth_code'
twilionum = 'twilio_number'
client = Client(account_sid, auth_token)

db.connect()

app = Flask(__name__)

@app.route("/sms", methods=['GET', 'POST'])
def sms_ahoy_reply():

    print(request.values)
    from_number = request.values.get('From')
    from_country = request.values.get('FromCountry')

    user_details = User.get_or_none(User.phonenumber == from_number)
    if user_details is None:  # User is not found in the database
        print(f'{from_number} is not in database.')
        authcode = random.SystemRandom().randint(1000, 9999)
        rec_word = ''.join(random.sample(open("english.txt").read().split(),5))
        user_details = User.create(
            phonenumber=from_number,
            time=datetime.now(),
            count=1,
            authcode=authcode,
            claim_last=0,
            rec_word=rec_word)

    else:
        print(
            f'{user_details.id + 1} - {user_details.phonenumber} sent a message.')
        user_details.phonenumber = from_number
        user_details.time = datetime.now()
        user_details.count += 1
        user_details.save()

    text_body = request.values.get('Body')
    text_body = text_body.lower()

    newauthcode = (random.SystemRandom().randint(1000, 9999))

    if 'register' in text_body:
        print('Found register')
        account = nano.get_address(user_details.id + 1)
        # Start our response
        resp = MessagingResponse()

        # Add a message
        resp.message(f'Welcome to NanoSMS, your address:\n'
                     f'{account}, \nAuthCode: {newauthcode}'
                     f'\nYour recovery phrase : {user_details.rec_word}')

    elif 'commands' in text_body:
        print('Found help')
        resp = MessagingResponse()
        resp.message(f'balance - get your balance\n'
                     f'send - send Nano\n'
                     f'address - your nano address, AuthCode: {newauthcode}')

    elif 'address' in text_body:
        print('Found address')
        account = nano.get_address(user_details.id + 1)
        resp = MessagingResponse()
        resp.message(f'{account}, AuthCode: {newauthcode}')

    elif 'history' in text_body:
        print('Found address')
        account = nano.get_address(user_details.id + 1)
        resp = MessagingResponse()
        resp.message(
            f'https://www.nanode.co/account/{account}, AuthCode: {newauthcode}')

    elif 'balance' in text_body:
        print('Found balance')

        account = nano.get_address(user_details.id + 1)
        print(account)
        previous = nano.get_previous(str(account))
        print(previous)
        print(len(previous))

        pending = nano.get_pending(str(account))
        if (len(previous) == 0) and (len(pending) > 0):
            print("Opening Account")
            nano.open_xrb(int(user_details.id + 1), account)

        print("Rx Pending: ", pending)
        pending = nano.get_pending(str(account))
        print(f'Pending Len: {len(pending)}')

        while len(pending) > 0:
            pending = nano.get_pending(str(account))
            print(len(pending))
            nano.receive_xrb(int(user_details.id + 1), account)

        if len(previous) == 0:
            balance = "Empty"
        else:
            previous = nano.get_previous(str(account))
            balance = int(nano.get_balance(previous)) / \
                1000000000000000000000000

        print(balance)
        # Start our response
        resp = MessagingResponse()

        # Add a message
        resp.message(f'Balance: {balance} nanos, AuthCode: {newauthcode}')

    elif 'send' in text_body:
        print('Found send')
        account = nano.get_address(user_details.id + 1)
        components = text_body.split(" ")

        # Check amount is real
        try:
            amount = int(components[1]) * 1
        except:
            resp = MessagingResponse()
            resp.message("Error: Incorrect Amount")
            return str(resp)

        destination = components[2]
        destination = destination.replace("\u202d", "")
        destination = destination.replace("\u202c", "")
        authcode = int(components[3])
        if authcode == int(user_details.authcode):
            if destination[0] == "x":
                print("Sent direct to xrb_address: " + destination)
                nano.send_xrb(destination, amount, account, user_details.id + 1)
                resp = MessagingResponse()
                resp.message(f'Sent!, AuthCode: {newauthcode}')
                return str(resp)

            else:
                try:
                    phonenum = phonenumbers.parse(destination, from_country)
                    dest_phone = phonenumbers.format_number(
                        phonenum, phonenumbers.PhoneNumberFormat.E164)
                except phonenumbers.phonenumberutil.NumberParseException:
                    print("Error")
                    resp = MessagingResponse()
                    resp.message("Error: Incorrect destination address/number")
                    return str(resp)

            if not phonenumbers.is_possible_number(phonenum):
                resp = MessagingResponse()
                resp.message("Error: Incorrect destination")
                return str(resp)

            #Send to phonenumber, and register if not registered.
            dest_user_details = User.get_or_none(phonenumber=dest_phone)

            if dest_user_details is None:
                dest_user_details = User.create(
                    phonenumber=dest_phone,
                    time=0,
                    count=0,
                    authcode=0,
                    claim_last=0)

            dest_address = nano.get_address(dest_user_details.id + 1)
            print("Sending to: " + dest_address)
            nano.send_xrb(dest_address, amount, account,user_details.id + 1)

            previous = nano.get_previous(str(account))
            balance = int(nano.get_balance(previous)) / \
                1000000000000000000000000

            resp = MessagingResponse()
            resp.message(f'Sent!, AuthCode: {newauthcode}\nYour Balance: {balance}')

            previous = nano.get_previous(str(dest_address))
            balance = int(nano.get_balance(previous)) / \
                1000000000000000000000000

            bodysend = 'You have recieved nano!\nYour balance: ' + str(balance)
            message = client.messages.create(
                                            from_=twilionum,
                                            body=bodysend,
                                            to=dest_phone
                                            )

            print(message.sid)

        else:
            resp = MessagingResponse()
            resp.message("Error: Incorrect Auth Code")
            return str(resp)

    elif 'claim' in text_body:
        print("Found claim")
        account = nano.get_address(user_details.id + 1)
        current_time = int(time.time())
        if int(user_details.claim_last) == 0:
            print("They can claim")

            #check faucet balance
            faucet = nano.get_address(0)
            previous = nano.get_previous(str(faucet))
            faucet_bal = int(nano.get_balance(previous)) / \
                1000000000000000000000000

            claim = faucet_bal*0.01
            nano.send_xrb(account, claim, faucet, 0)
            user_details.claim_last = 1
            user_details.save()

            resp = MessagingResponse()
            resp.message(
                f'Claim Success {claim}\n'
                f'AD1: check out localnanos to exchange nano\n'
                f'AD2: Cerveza Polar 6 for 1 Nano at JeffMart, 424 Caracas\n'
                f'AuthCode: {newauthcode}')

            print(
                f'{claim} sent to {account} from faucet\n'
                f'Faucet funds remaining {faucet_bal-claim}')
        else:
            resp = MessagingResponse()
            resp.message("This number has already made a claim")
            return str(resp)

    elif 'trust' in text_body:
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
                        resp.message(f'Trust address set to {components[1]}'
                                     f', Authcode: {new_authcode}')

                        user_details.trust_address = xrb_trust
                        user_details.trust_phonenumber = 0
                        user_details.save()
                    else:
                        print("Invalid address")
                        resp = MessagingResponse()
                        resp.message(f'Invalid address, Authcode:  {new_authcode}')
                except KeyError:
                    print("Invalid address")
                    resp = MessagingResponse()
                    resp.message(f'Invalid address, Authcode:  {new_authcode}')

            elif components[1].isdigit():
                trust_number = components[1]
                resp = MessagingResponse()
                resp.message(
                    f'Trust address set to {components[1]}, AuthCode: {newauthcode}'
                )
                user_details.trust_address = ""
                user_details.trust_number = trust_number
                user_details.save()
            else:
                print("No valid trust")
                resp = MessagingResponse()
                resp.message(f'No valid trust, Authcode: {new_authcode}')

        else:
            resp = MessagingResponse()
            resp.message("Error: Incorrect Auth Code")
            return str(resp)
        
    elif 'recover' in text_body:
        print('Start Recovery')
        
        components = text_body.split(" ")
        rec_word_rx = components[1]

        # Check recovery word
        try:
            rec_details = User.get(User.rec_word==rec_word_rx)
            rec_account = nano.get_address(rec_details.id)
            
            resp = MessagingResponse()
            resp.message(
                f'Recover Success! \nPhone number: {rec_details.phonenumber}\n'
                f'Address: {rec_account}\n'
                f'AuthCode: {newauthcode}')

        except:
            resp = MessagingResponse()
            resp.message("Error recovery phrase not recognised")
            return str(resp)

    elif 'topup' in text_body:
        print('Found topup request')

        components = text_body.split(" ")
        cardcode = components[1]

        account = nano.get_address(user_details.id + 1)
        current_time = int(time.time())

        #check card code valid
        card_valid = TopupCards.get_or_none(TopupCards.cardcode == cardcode)
        if card_valid == None:
            print("Card code error " + cardcode)
            resp = MessagingResponse()
            resp.message("Error: Invalid Topup voucher code")
            return str(resp)

        if card_valid.claimed == True:
            print("Card already claimed " + cardcode)
            resp = MessagingResponse()
            resp.message("Card has already been claimed")
            return str(resp)

        else:
            topupadd = nano.get_address(1)
            previous = nano.get_previous(str(topupadd))
            topupadd_bal = int(nano.get_balance(previous)) / \
                1000000000000000000000000

            if topupadd_bal < card_valid.cardvalue:
                print(
                    f'Insufficient Balance\n'
                    f'Address Balance {topupadd_bal}, Card request {card_valid.cardvalue}')

            nano.send_xrb(account, card_valid.cardvalue, topupadd, 0)

            previous = nano.get_previous(str(account))
            balance = int(nano.get_balance(previous)) / \
                1000000000000000000000000

            resp = MessagingResponse()
            resp.message(
                    f'Topup success!\n'
                    f'Your new account balance {balance}\n'
                    f'AuthCode: {newauthcode}')

            print(
                f'Success topup to {account} from topup address\n'
                f'Address Balance {topupadd_bal-card_valid.cardvalue}')
            card_valid.claimed = True
            card_valid.save()

    else:
        print('Error ' + text_body)

        # Start our response
        resp = MessagingResponse()

        # Add a message
        resp.message("Command not recognised, send " + commands + "for a list of commands")

    user_details.authcode = newauthcode
    user_details.save()

    return str(resp)


if __name__ == "__main__":
    # Check faucet address on boot to make sure we are up to date
    # Todo, use systemuser for faucet

    account = nano.get_address(0)
    print(account)
    previous = nano.get_previous(str(account))
    print(previous)
    print(len(previous))

    pending = nano.get_pending(str(account))
    if (len(previous) == 0) and (len(pending) > 0):
        print("Opening Account")
        nano.open_xrb(int(0), account)

    print(f'Rx Pending: {pending}')
    pending = nano.get_pending(str(account))
    print(f'Pending Len: {len(pending)}')

    while len(pending) > 0:
        pending = nano.get_pending(str(account))
        print(len(pending))
        nano.receive_xrb(int(0), account)

    app.run(debug=True, host="0.0.0.0", port=5002)
