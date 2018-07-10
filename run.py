from flask import Flask, request
from twilio.twiml.messaging_response import MessagingResponse
import dataset, time, json, settings, random
from websocket import create_connection

import binascii
from bitstring import BitArray
from pyblake2 import blake2b
from pure25519 import ed25519_oop as ed25519

db = dataset.connect('sqlite:///users.db')
user_table = db['user']

app = Flask(__name__)

def private_public(private):
    return ed25519.SigningKey(private).get_verifying_key().to_bytes()

def xrb_account(address):
    # Given a string containing an XRB address, confirm validity and
    # provide resulting hex address
    if len(address) == 64 and (address[:4] == 'xrb_'):
        # each index = binary value, account_lookup[0] == '1'
        account_map = "13456789abcdefghijkmnopqrstuwxyz"
        account_lookup = {}
        # populate lookup index with prebuilt bitarrays ready to append
        for i in range(32):
            account_lookup[account_map[i]] = BitArray(uint=i,length=5)

        # we want everything after 'xrb_' but before the 8-char checksum
        acrop_key = address[4:-8]
        # extract checksum
        acrop_check = address[-8:]

        # convert base-32 (5-bit) values to byte string by appending each
        # 5-bit value to the bitstring, essentially bitshifting << 5 and
        # then adding the 5-bit value.
        number_l = BitArray()
        for x in range(0, len(acrop_key)):
            number_l.append(account_lookup[acrop_key[x]])
        # reduce from 260 to 256 bit (upper 4 bits are never used as account
        # is a uint256)
        number_l = number_l[4:]

        check_l = BitArray()
        for x in range(0, len(acrop_check)):
            check_l.append(account_lookup[acrop_check[x]])

        # reverse byte order to match hashing format
        check_l.byteswap()
        result = number_l.hex.upper()

        # verify checksum
        h = blake2b(digest_size=5)
        h.update(number_l.bytes)
        if (h.hexdigest() == check_l.hex):
            return result
        else:
            return False
    else:
        return False

def account_xrb(account):
    # Given a string containing a hex address, encode to public address
    # format with checksum
    # each index = binary value, account_lookup['00001'] == '3'
    account_map = "13456789abcdefghijkmnopqrstuwxyz"
    account_lookup = {}
    # populate lookup index for binary string to base-32 string character
    for i in range(32):
        account_lookup[BitArray(uint=i,length=5).bin] = account_map[i]
    # hex string > binary
    account = BitArray(hex=account)

    # get checksum
    h = blake2b(digest_size=5)
    h.update(account.bytes)
    checksum = BitArray(hex=h.hexdigest())

    # encode checksum
    # swap bytes for compatibility with original implementation
    checksum.byteswap()
    encode_check = ''
    for x in range(0,int(len(checksum.bin)/5)):
        # each 5-bit sequence = a base-32 character from account_map
        encode_check += account_lookup[checksum.bin[x*5:x*5+5]]

    # encode account
    encode_account = ''
    while len(account.bin) < 260:
        # pad our binary value so it is 260 bits long before conversion
        # (first value can only be 00000 '1' or 00001 '3')
        account = '0b0' + account
    for x in range(0,int(len(account.bin)/5)):
        # each 5-bit sequence = a base-32 character from account_map
        encode_account += account_lookup[account.bin[x*5:x*5+5]]

    # build final address string
    return 'xrb_'+encode_account+encode_check

def seed_account(seed, index):
    # Given an account seed and index #, provide the account private and
    # public keys
    h = blake2b(digest_size=32)

    seed_data = BitArray(hex=seed)
    seed_index = BitArray(int=index,length=32)

    h.update(seed_data.bytes)
    h.update(seed_index.bytes)

    account_key = BitArray(h.digest())
    return account_key.bytes, private_public(account_key.bytes)

def receive_xrb(index, account):
    ws = create_connection('ws://yapraiwallet.space:8000')

    #Get pending blocks

    rx_data = get_pending(str(account))
    if len(rx_data) == 0:
        return
 
    for block in rx_data:
      print(block)
      block_hash = block
      print(rx_data[block])
      balance = int(rx_data[block]['amount'])
      source = rx_data[block]['source']

    previous = get_previous(str(account))

    current_balance = get_balance(previous)
    print(current_balance)
    new_balance = int(current_balance) + int(balance)
    hex_balance = hex(new_balance)
    print(hex_balance)
    hex_final_balance = hex_balance[2:].upper().rjust(32, '0')
    print(hex_final_balance)

    priv_key, pub_key = seed_account(settings.seed, int(index))
    public_key = ed25519.SigningKey(priv_key).get_verifying_key().to_ascii(encoding="hex")

    #print("Starting PoW Generation")
    work = get_pow(previous)
    #print("Completed PoW Generation")

    #Calculate signature
    bh = blake2b(digest_size=32)
    bh.update(BitArray(hex='0x0000000000000000000000000000000000000000000000000000000000000006').bytes)
    bh.update(BitArray(hex=xrb_account(account)).bytes)
    bh.update(BitArray(hex=previous).bytes)
    bh.update(BitArray(hex=xrb_account(account)).bytes)
    bh.update(BitArray(hex=hex_final_balance).bytes)
    bh.update(BitArray(hex=block_hash).bytes)

    sig = ed25519.SigningKey(priv_key+pub_key).sign(bh.digest())
    signature = str(binascii.hexlify(sig), 'ascii')

    finished_block = '{ "type" : "state", "previous" : "%s", "representative" : "%s" , "account" : "%s", "balance" : "%s", "link" : "%s", \
            "work" : "%s", "signature" : "%s" }' % (previous, account, account, new_balance, block_hash, work, signature)

    print(finished_block)

    data = json.dumps({'action' : 'process', 'block' : finished_block})
    #print(data)
    ws.send(data)

    block_reply = ws.recv()

    print(block_reply)
    ws.close()

def get_address(index):
    #Generate address
    print("Generate Address")
    priv_key, pub_key = seed_account(settings.seed, int(index))
    public_key = str(binascii.hexlify(pub_key), 'ascii')
    print("Public Key: ", str(public_key))

    account = account_xrb(str(public_key))
    print("Account Address: ", account)
    return account

def open_xrb(index, account):
    ws = create_connection('ws://yapraiwallet.space:8000')
    representative = 'xrb_1kd4h9nqaxengni43xy9775gcag8ptw8ddjifnm77qes1efuoqikoqy5sjq3'
    #Get pending blocks

    rx_data = get_pending(str(account))
    for block in rx_data:
      print(block)
      block_hash = block
      print(rx_data[block])
      balance = int(rx_data[block]['amount'])
      source = rx_data[block]['source']

    hex_balance = hex(balance)
    print(hex_balance)
    hex_final_balance = hex_balance[2:].upper().rjust(32, '0')
    print(hex_final_balance)

    priv_key, pub_key = seed_account(settings.seed, int(index))
    public_key = ed25519.SigningKey(priv_key).get_verifying_key().to_ascii(encoding="hex")

    #print("Starting PoW Generation")
    work = get_pow(str(public_key, 'ascii'))
    #print("Completed PoW Generation")

    #Calculate signature
    bh = blake2b(digest_size=32)
    bh.update(BitArray(hex='0x0000000000000000000000000000000000000000000000000000000000000006').bytes)
    bh.update(BitArray(hex=xrb_account(account)).bytes)
    bh.update(BitArray(hex='0x0000000000000000000000000000000000000000000000000000000000000000').bytes)
    bh.update(BitArray(hex=xrb_account(account)).bytes)
    bh.update(BitArray(hex=hex_final_balance).bytes)
    bh.update(BitArray(hex=block_hash).bytes)

    sig = ed25519.SigningKey(priv_key+pub_key).sign(bh.digest())
    signature = str(binascii.hexlify(sig), 'ascii')

    finished_block = '{ "type" : "state", "previous" : "0000000000000000000000000000000000000000000000000000000000000000", "representative" : "%s" , "account" : "%s", "balance" : "%s", "link" : "%s", \
            "work" : "%s", "signature" : "%s" }' % (account, account, balance, block_hash, work, signature)

    print(finished_block)

    data = json.dumps({'action' : 'process', 'block' : finished_block})
    #print(data)
    ws.send(data)

    block_reply = ws.recv()

    print(block_reply)
    ws.close()


def send_xrb(dest_account, amount, account, index):
    ws = create_connection('ws://yapraiwallet.space:8000')

    representative = 'xrb_1kd4h9nqaxengni43xy9775gcag8ptw8ddjifnm77qes1efuoqikoqy5sjq3'

    previous = get_previous(str(account))

    current_balance = get_balance(previous)
    print(current_balance)
    new_balance = int(current_balance) - int(amount)
    hex_balance = hex(new_balance)

    print(hex_balance)
    hex_final_balance = hex_balance[2:].upper().rjust(32, '0')
    print(hex_final_balance)

    priv_key, pub_key = seed_account(settings.seed, int(index))
    public_key = ed25519.SigningKey(priv_key).get_verifying_key().to_ascii(encoding="hex")

    #print("Starting PoW Generation")
    work = get_pow(previous)
    #print("Completed PoW Generation")

    #Calculate signature
    bh = blake2b(digest_size=32)
    bh.update(BitArray(hex='0x0000000000000000000000000000000000000000000000000000000000000006').bytes)
    bh.update(BitArray(hex=xrb_account(account)).bytes)
    bh.update(BitArray(hex=previous).bytes)
    bh.update(BitArray(hex=xrb_account(account)).bytes)
    bh.update(BitArray(hex=hex_final_balance).bytes)
    bh.update(BitArray(hex=xrb_account(dest_account)).bytes)

    sig = ed25519.SigningKey(priv_key+pub_key).sign(bh.digest())
    signature = str(binascii.hexlify(sig), 'ascii')

    finished_block = '{ "type" : "state", "previous" : "%s", "representative" : "%s" , "account" : "%s", "balance" : "%s", "link" : "%s", \
            "work" : "%s", "signature" : "%s" }' % (previous, account, account, new_balance, dest_account, work, signature)

    print(finished_block)

    data = json.dumps({'action' : 'process', 'block' : finished_block})
    #print(data)
    ws.send(data)

    block_reply = ws.recv()

    print(block_reply)
    ws.close()


def get_pow(hash):
    ws = create_connection('ws://yapraiwallet.space:8000')
    data = json.dumps({'action' : 'work_generate', 'hash' : hash})
    ws.send(data)
    block_work = json.loads(str(ws.recv()))
    work = block_work['work']
    ws.close()

    return work

def get_previous(account):
    #Get account info
    accounts_list = [account]
    ws = create_connection('ws://yapraiwallet.space:8000')

    data = json.dumps({'action' : 'accounts_frontiers', 'accounts' : accounts_list})
    ws.send(data)
    result =  ws.recv()
    print(result)
    account_info = json.loads(str(result))

    ws.close()

    if len(account_info['frontiers']) == 0:
       return ""
    else:
       previous = account_info['frontiers'][account]
       return previous

def get_balance(hash):
    #Get balance from hash
    ws = create_connection('ws://yapraiwallet.space:8000')
    data = json.dumps({'action' : 'block', 'hash' : hash})

    ws.send(data)

    block =  ws.recv()
    print("Received '%s'" % block)
    ws.close()


    rx_data = json.loads(str(block))
    new_rx = json.loads(str(rx_data['contents']))
    return new_rx['balance']

def get_pending(account):
    #Get pending blocks
    ws = create_connection('ws://yapraiwallet.space:8000')
    data = json.dumps({'action' : 'pending', 'account' : account, "count" : "1","source": "true" })

    ws.send(data)

    pending_blocks =  ws.recv()
    print("Received '%s'" % pending_blocks)

    rx_data = json.loads(str(pending_blocks))
    ws.close()

    return rx_data['blocks']

@app.route("/sms", methods=['GET', 'POST'])
def sms_ahoy_reply():

    print(request.values)
    from_number = request.values.get('From')
    from_country = request.values.get('FromCountry')

    user_details = user_table.find_one(number=from_number)
    print(user_details)

    if user_details == None:
        authcode = (random.SystemRandom().randint(1000,9999))
        user_table.insert(dict(number=from_number, time=int(time.time()), count=1, authcode=authcode, claim_last=0))
        user_details = user_table.find_one(number=from_number)    
    else:
        user_table.update(dict(number=from_number, time=int(time.time()), count=(int(user_details['count']) + 1)), ['number'])

    text_body = request.values.get('Body')
    text_body = text_body.lower()

    new_authcode = (random.SystemRandom().randint(100,9999))

    if 'register' in text_body:
        print('Found register')
        
        account = get_address(user_details['id'])
        # Start our response
        resp = MessagingResponse()

        # Add a message
        resp.message("Welcome to NanoSMS, your address:\n" +  account + ", Code: " + str(new_authcode))

    elif 'details' in text_body:
        print('Found help')
        resp = MessagingResponse()
        resp.message("balance - get your balance\n send - send Nano\n address - your nano address" + ", Code: " + str(new_authcode))

    elif 'address' in text_body:
        print('Found address')
        account = get_address(user_details['id'])
        resp = MessagingResponse()
        resp.message(account  + ", Code: " + str(new_authcode))

    elif 'history' in text_body:
        print('Found address')
        account = get_address(user_details['id'])
        resp = MessagingResponse()
        resp.message("https://www.nanode.co/account/" + account + ", Code: " + str(new_authcode))

    elif 'balance' in text_body:
        print('Found balance')

        account = get_address(user_details['id'])
        print(account)
        previous = get_previous(str(account))
        print(previous)
        print(len(previous))

        pending = get_pending(str(account))
        if (len(previous) == 0) and (len(pending) > 0):
            print("Opening Account")
            open_xrb(int(user_details['id']), account)

        print("Rx Pending: ", pending)
        pending = get_pending(str(account))
        print("Pending Len:" + str(len(pending)))

        while len(pending) > 0:
            pending = get_pending(str(account))
            print(len(pending))
            receive_xrb(int(user_details['id']), account)

        if len(previous) == 0:
            balance = "Empty"
        else:
            previous = get_previous(str(account))
            balance = int(get_balance(previous)) / 1000000000000000000000000

        print(balance)
        # Start our response
        resp = MessagingResponse()

        # Add a message
        resp.message("Balance: " + str(balance) + " nanos" + ", Code: " + str(new_authcode))

    elif 'send' in text_body:
        print('Found send')
        account = get_address(user_details['id'])
        components = text_body.split(" ")

        # Check amount is real
        try:
            amount = int(components[1]) * 1000000000000000000000000
        except:
            resp = MessagingResponse()
            resp.message("Error: Incorrect Amount")
            return str(resp)

        destination = components[2]
        authcode = int(components[3])
        if authcode  == int(user_details['authcode']):
            if destination[0] == "x":
                print("xrb addresses")
                send_xrb(destination, amount, account, user_details['id'])
                resp = MessagingResponse()
                resp.message("Sent!" + ", Code: " + str(new_authcode))
                return str(resp)

            elif from_country == 'US':
                print("US telephone")

                if len(destination) == 12 and destination[0] == "+":
                    dest_address = destination
                elif len(destination) == 11 and destination[0] == "1":
                    dest_address = '+' + str(destination)
                elif len(destination) == 10:
                    dest_address = '+1' + str(destination)
                else:
                    resp = MessagingResponse()
                    resp.message("Error: Incorrect Destination")
                    return str(resp)

            elif from_country == 'GB':
                print("GB telephone: " +  str(len(destination)) + " " + str(destination))

                if len(destination) == 13 and destination[:3] == "+44":
                    dest_address = destination
                elif len(destination) == 11 and destination[:2] == "07":
                    dest_address = '+44' + str(destination[1:])
                else:
                    resp = MessagingResponse()
                    resp.message("Error: Incorrect Destination")
                    return str(resp)

            else:
                print("Error")
                resp = MessagingResponse()
                resp.message("Error: Incorrect destination address/number")
                return str(resp)

            dest_user_details = user_table.find_one(number=dest_address)
            print(dest_user_details)

            if dest_user_details == None:
                user_table.insert(dict(number=dest_address, time=0, count=0, authcode=0, claim_last=0))
                dest_user_details = user_table.find_one(number=dest_address)

            send_xrb(get_address(dest_user_details['id']), amount, account, user_details['id'])

            resp = MessagingResponse()
            resp.message("Sent!" + ", Code: " + str(new_authcode))

        else:
            resp = MessagingResponse()
            resp.message("Error: Incorrect Auth Code")
            return str(resp)

    elif 'claim' in text_body:
        print("Found claim")
        account = get_address(user_details['id'])
        current_time = int(time.time())
        if current_time > (int(user_details['claim_last']) + 86400):
            print("They can claim")
            amount = 10000000000000000000000000
            send_xrb(account, amount, get_address(10), 10)
            user_table.update(dict(number=from_number, claim_last=int(time.time())), ['number'])

            resp = MessagingResponse()
            resp.message("Claim Success (10 nanos)\nAD1: check out localnanos to exchange nano/VEF\nAD2: Cerveza Polar 6 for 1Nano at JeffMart, 424 Caracas\n" + "Code: " + str(new_authcode))
        else:
            resp = MessagingResponse()
            resp.message("Error: Claim too soon")
            return str(resp)
    else:
        print('Error')

        # Start our response
        resp = MessagingResponse()

        # Add a message
        resp.message("Error")

    user_table.update(dict(number=from_number, authcode=new_authcode), ['number'])

    return str(resp)

if __name__ == "__main__":
        #Check faucet address on boot to make sure we are up to date
        account = get_address(10)
        print(account)
        previous = get_previous(str(account))
        print(previous)
        print(len(previous))

        pending = get_pending(str(account))
        if (len(previous) == 0) and (len(pending) > 0):
            print("Opening Account")
            open_xrb(int(10), account)

        print("Rx Pending: ", pending)
        pending = get_pending(str(account))
        print("Pending Len:" + str(len(pending)))

        while len(pending) > 0:
            pending = get_pending(str(account))
            print(len(pending))
            receive_xrb(int(10), account)

        app.run(debug=True, host="0.0.0.0", port=5002)
