import json
import random
import time
from datetime import datetime, timedelta

import phonenumbers
from flask import Flask, request
from twilio.twiml.messaging_response import MessagingResponse

import settings  # Importing settings file
from modules import nano
from modules.database import SystemUser, User, db
from modules.nano import NanoFunctions

nano = NanoFunctions(settings.uri)

db.connect()

app = Flask(__name__)


def authcode_gen_save(user_details):
    new_authcode = (random.SystemRandom().randint(1000, 9999))
    user_details.authcode = new_authcode
    user_details.save()
    return new_authcode


def register(user_details, text_body):
    print('Found register')
    account = nano.get_address(user_details.id)
    # Start our response
    resp = MessagingResponse()

    # Add a message
    new_authcode = authcode_gen_save(user_details)
    resp.message(f'Welcome to NanoSMS, your address:\n'
                 f'{account}, Code: {new_authcode}')
    return resp


def details(user_details, text_body):
    print('Found help')
    resp = MessagingResponse()
    new_authcode = authcode_gen_save(user_details)
    resp.message(f'balance - get your balance\n'
                 f'send - send Nano\n'
                 f'address - your nano address, Code: {new_authcode}')
    return resp


def address(user_details, text_body):
    print('Found address')
    account = nano.get_address(user_details.id)
    resp = MessagingResponse()
    new_authcode = authcode_gen_save(user_details)
    resp.message(f'{account}, Code: {new_authcode}')
    return resp


def history(user_details, text_body):
    print('Found address')
    account = nano.get_address(user_details.id)
    resp = MessagingResponse()
    new_authcode = authcode_gen_save(user_details)
    resp.message(f'https://www.nanode.co/account/{account}, Code: {new_authcode}')
    return resp


def balance(user_details, text_body):
    print('Found balance')

    account = nano.get_address(user_details.id)
    print(account)
    previous = nano.get_previous(str(account))
    print(previous)
    print(len(previous))

    pending = nano.get_pending(str(account))
    if (len(previous) == 0) and (len(pending) > 0):
        print("Opening Account")
        nano.open_xrb(int(user_details.id), account)

    print("Rx Pending: ", pending)
    pending = nano.get_pending(str(account))
    print(f'Pending Len: {len(pending)}')

    while len(pending) > 0:
        pending = nano.get_pending(str(account))
        print(len(pending))
        nano.receive_xrb(int(user_details.id), account)

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
    new_authcode = authcode_gen_save(user_details)
    resp.message(f'Balance: {balance} nanos, Code: {new_authcode}')
    return resp


def send(user_details, text_body):
    print('Found send')
    account = nano.get_address(user_details.id)
    components = text_body.split(" ")

    # Check amount is real
    try:
        amount = int(components[1]) * 1000000000000000000000000
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
            print("xrb addresses")
            nano.send_xrb(destination, amount, account, user_details.id)
            resp = MessagingResponse()
            new_authcode = authcode_gen_save(user_details)
            resp.message(f'Sent! Code: {new_authcode}')
            return resp

        else:
            try:
                phonenum = phonenumbers.parse(destination, user_details.country)
                dest_address = phonenumbers.format_number(
                    phonenum, phonenumbers.PhoneNumberFormat.E164)
            except phonenumbers.phonenumberutil.NumberParseException:
                print("Error")
                resp = MessagingResponse()
                resp.message("Error: Incorrect destination address/number")
                return resp

        if not phonenumbers.is_possible_number(phonenum):
            resp = MessagingResponse()
            resp.message("Error: Incorrect destination")
            return resp

        dest_user_details = User.get_or_none(phonenumber=dest_address)
        print(dest_user_details)

        if dest_user_details is None:
            dest_user_details = User.create(
                phonenumber=dest_address,
                time=0,
                count=0,
                authcode=0,
                claim_last=0)

        nano.send_xrb(
            nano.get_address(dest_user_details.id), amount, account,
            user_details.id)

        resp = MessagingResponse()
        new_authcode = authcode_gen_save(user_details)
        resp.message(f'Sent! Code: {new_authcode}')
        return resp

    else:
        resp = MessagingResponse()
        resp.message("Error: Incorrect Auth Code")
        return resp


def claim(user_details, text_body):
    print("Found claim")
    account = nano.get_address(user_details.id)
    current_time = int(time.time())
    if current_time > (int(user_details.claim_last) + 86400):
        print("They can claim")
        amount = 10000000000000000000000000
        nano.send_xrb(account, amount, nano.get_address(10), 10)
        user_details.claim_last = datetime.now()
        user_details.save()

        resp = MessagingResponse()
        new_authcode = authcode_gen_save(user_details)
        resp.message(
            f'Claim Success (10 nanos)\n'
            f'AD1: check out localnanos to exchange nano/VEF\n'
            f'AD2: Cerveza Polar 6 for 1Nano at JeffMart, 424 Caracas\n'
            f'Code: {new_authcode}')
        return resp
    else:
        resp = MessagingResponse()
        resp.message("Error: Claim too soon")
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
                f'Trust address set to {components[1]}, Code: {new_authcode}'
            )
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

# Always return return.

@app.route("/sms", methods=['GET', 'POST'])
def sms_ahoy_reply():

    print(request.values)
    from_number = request.values.get('From')
    from_country = request.values.get('FromCountry')

    user_details = User.get_or_none(User.phonenumber == from_number)
    if user_details is None:  # User is not found in the database
        print(f'{from_number} is not in database.')
        authcode = (random.SystemRandom().randint(1000, 9999))
        user_details = User.create(
            phonenumber=from_number,
            country=from_country,
            time=datetime.now(),
            count=1,
            authcode=authcode,
            claim_last=0)
    else:
        print(f'{user_details.id} - {user_details.phonenumber} sent a message.')
        user_details.phonenumber = from_number
        user_details.country = from_country
        user_details.time = datetime.now()
        user_details.count += 1
        user_details.save()

    text_body = request.values.get('Body')
    text_body = text_body.lower()

    if 'register' in text_body:
        return str(register(user_details, text_body))

    elif 'details' in text_body:
        return str(details(user_details, text_body))

    elif 'address' in text_body:
        return str(address(user_details, text_body))

    elif 'history' in text_body:
        return str(history(user_details, text_body))

    elif 'balance' in text_body:
        return str(balance(user_details, text_body))

    elif 'send' in text_body:
        return str(send(user_details, text_body))

    elif 'claim' in text_body:
        return str(claim(user_details, text_body))

    elif 'trust' in text_body:
        return str(trust(user_details, text_body))

    else:
        print('Error')

        # Start our response
        resp = MessagingResponse()

        # Add a message
        resp.message("Error")

    return str(resp)


if __name__ == "__main__":
    # Check faucet address on boot to make sure we are up to date
    # Todo use SystemUser for faucet
    account = nano.get_address(0)
    print(account)
    previous = nano.get_previous(str(account))
    print(previous)
    print(len(previous))

    pending = nano.get_pending(str(account))
    if (len(previous) == 0) and (len(pending) > 0):
        print("Opening Account")
        nano.open_xrb(int(10), account)

    print(f'Rx Pending: {pending}')
    pending = nano.get_pending(str(account))
    print(f'Pending Len: {len(pending)}')

    while len(pending) > 0:
        pending = nano.get_pending(str(account))
        print(len(pending))
        nano.receive_xrb(int(10), account)

    app.run(debug=True, host="0.0.0.0", port=5002)
