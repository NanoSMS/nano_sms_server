import binascii
import json

import requests
from bitstring import BitArray
from flask import request

from modules.misc import Config
from modules.settings import Config as NewConfig
from nano25519.nano25519 import ed25519_oop as ed25519
from pyblake2 import blake2b


class NanoRPC:

    # source: https://github.com/nanocurrency/raiblocks/wiki/RPC-protocol
    # makes nano node requests using RPC protocol

    def __init__(self, uri):
        self.uri = uri

    def rpc_request(self, data):
        data = json.dumps(data)
        headers = {"Content-type": "application/json", "Accept": "application/json"}
        try:

            response = requests.post(self.uri, data=data, headers=headers)

            if not response.ok:
                return None
            resp_dict = json.loads(response.text)
        except:
            resp_dict = {"message": "Timeout or invalid uri"}
        finally:
            return resp_dict

    def version(self):
        """
        source:
        https://github.com/nanocurrency/raiblocks/wiki/RPC-protocol#retrieve-node-versions
        """
        data = {"action": "version"}
        return self.rpc_request(data)

    def block_count(self):
        """
        source:
        https://github.com/nanocurrency/raiblocks/wiki/RPC-protocol#block-count
        """
        data = {"action": "block_count"}
        return self.rpc_request(data)

    def account_info(self, account):
        """
        source:
        https://github.com/nanocurrency/raiblocks/wiki/RPC-protocol#account-information
        """
        data = {"action": "account_info", "representative": "true", "account": account}
        return self.rpc_request(data)

    def accounts_pending(self, accounts, count=1):
        """
        source:
        https://github.com/nanocurrency/raiblocks/wiki/RPC-protocol#accounts-pending
        """
        data = {"action": "accounts_pending", "accounts": accounts, "count": str(count)}
        return self.rpc_request(data)

    def block(self, block):
        """
        source:
        https://github.com/nanocurrency/raiblocks/wiki/RPC-protocol#retrieve-block
        """
        data = {"action": "block", "hash": block}
        return self.rpc_request(data)

    def blocks_info(self, block):
        """
        source:
        https://github.com/nanocurrency/raiblocks/wiki/RPC-protocol#retrieve-multiple-blocks-with-additional-info
        """
        data = {"action": "blocks_info", "hashes": [block]}
        return self.rpc_request(data)

    def block_confirm(self, block):
        """
        source:
        https://github.com/nanocurrency/raiblocks/wiki/RPC-protocol#block-confirm
        """
        data = {"action": "block_confirm", "hash": block}
        return self.rpc_request(data)

    def block_account(self, block):
        """
        source:
        https://github.com/nanocurrency/raiblocks/wiki/RPC-protocol#block-account
        """
        data = {"action": "block_account", "hash": block}
        return self.rpc_request(data)

    def key_expand(self, key):
        """
        source:
        https://github.com/nanocurrency/raiblocks/wiki/RPC-protocol#key-expand
        """
        data = {"action": "key_expand", "key": key}
        return self.rpc_request(data)

    def pending(self, account, count=1):
        """
        source:
        https://github.com/nanocurrency/raiblocks/wiki/RPC-protocol#pending
        """
        data = {
            "action": "pending",
            "account": account,
            "count": str(count),
            "source": "true",
        }
        return self.rpc_request(data)

    def wallet_create(self):
        """
        source:
        https://github.com/nanocurrency/raiblocks/wiki/RPC-protocol#wallet-create
        """
        data = {"action": "wallet_create"}
        return self.rpc_request(data)

    def wallet_add_watch(self, wallet, account):
        """
        source:
        https://github.com/nanocurrency/raiblocks/wiki/RPC-protocol#wallet-add-watch-only-accounts
        """
        data = {"action": "wallet_add_watch", "wallet": wallet, "accounts": [account]}
        return self.rpc_request(data)

    def wallet_pending(self, wallet, count=1):
        """
        source:
        https://github.com/nanocurrency/raiblocks/wiki/RPC-protocol#wallet-pending
        """
        data = {
            "action": "wallet_pending",
            "wallet": wallet,
            "count": str(count),
            "source": "true",
        }
        return self.rpc_request(data)

    def process(self, block):
        """
        source:
        https://github.com/nanocurrency/raiblocks/wiki/RPC-protocol#process-block
        """
        data = {"action": "process", "block": block}
        return self.rpc_request(data)

    def work_generate(self, _hash):
        """
        source:
        https://github.com/nanocurrency/raiblocks/wiki/RPC-protocol#work-generate
        """
        data = {"action": "work_generate", "hash": _hash}
        return self.rpc_request(data)


class NanoFunctions:
    def __init__(self, uri):
        self.rpc = NanoRPC(uri)

    def private_to_public(self, private):
        return ed25519.SigningKey(private).get_verifying_key().to_bytes()

    def get_work(self, frontier):
        uri = NewConfig.work_uri[0]
        json_request = '{"hash" : "%s" }' % frontier
        response = requests.post(uri + "/work", data=json_request)
        if not response.ok:
            return None
        return json.loads(response.text)["work"]

    def xrb_account(self, address):

        # Transforms account form into hexadecimal format

        if len(address) == 64 and (address[:4] == "xrb_"):
            acrop_key = address[4:-8]
        elif len(address) == 65 and (address[:5] == "nano_"):
            acrop_key = address[5:-8]
        else:
            return None

        account_map = "13456789abcdefghijkmnopqrstuwxyz"
        account_lookup = {}
        for i in range(0, 32):
            account_lookup[account_map[i]] = BitArray(uint=i, length=5)

        acrop_check = address[-8:]

        number_l = BitArray()
        for x in range(0, len(acrop_key)):
            number_l.append(account_lookup[acrop_key[x]])
        number_l = number_l[4:]

        check_l = BitArray()
        for x in range(0, len(acrop_check)):
            check_l.append(account_lookup[acrop_check[x]])
        check_l.byteswap()

        result = number_l.hex.upper()

        h = blake2b(digest_size=5)
        h.update(number_l.bytes)
        if h.hexdigest() == check_l.hex:
            return result
        return False

    def account_xrb(self, account):

        # Transforms hexadecimal form into account format

        account_map = "13456789abcdefghijkmnopqrstuwxyz"
        account_lookup = {}
        for i in range(0, 32):
            account_lookup[BitArray(uint=i, length=5).bin] = account_map[i]

        account = BitArray(hex=account)

        h = blake2b(digest_size=5)
        h.update(account.bytes)
        checksum = BitArray(hex=h.hexdigest())

        checksum.byteswap()
        encode_check = str()

        for x in range(0, int(len(checksum.bin) / 5)):
            encode_check += account_lookup[checksum.bin[x * 5 : x * 5 + 5]]

        encode_account = str()
        while len(account.bin) < 260:
            account = "0b0" + account

        for x in range(0, int(len(account.bin) / 5)):
            encode_account += account_lookup[account.bin[x * 5 : x * 5 + 5]]

        return "xrb_" + encode_account + encode_check

    def seed_account(self, seed, index):

        # Generates deterministic key set from seed and index

        h = blake2b(digest_size=32)

        seed_data = BitArray(hex=seed)
        seed_index = BitArray(int=index, length=32)

        h.update(seed_data.bytes)
        h.update(seed_index.bytes)

        account_key = BitArray(h.digest())

        return account_key.bytes, self.private_to_public(account_key.bytes)

    def sign_block(self, private_key, account, previous, representative, balance, link):

        # Returns universal block signature

        public_key = self.private_to_public(private_key)

        bh = blake2b(digest_size=32)

        balance = int(balance)
        balance = str(hex(balance)[2:])
        for _ in range(32 - len(balance)):
            balance = "0" + balance

        hex_priv = private_key.hex()
        hex_pub = public_key.hex()

        priv_key = BitArray(hex=hex_priv).bytes
        pub_key = BitArray(hex=hex_pub).bytes

        preamble = BitArray(hex=(hex(6)[2:].rjust(64, "0"))).bytes
        account = BitArray(hex=self.xrb_account(account)).bytes
        previous = BitArray(hex=previous).bytes
        representative = BitArray(hex=self.xrb_account(representative)).bytes
        balance = BitArray(hex=balance).bytes
        link = BitArray(hex=link).bytes

        p = preamble + account + previous + representative + balance + link
        bh.update(p)

        sig = ed25519.SigningKey(priv_key + pub_key).sign(bh.digest())
        return sig.hex().upper()[:128]

    def work_threshold(self, check):
        if check > b"\xFF\xFF\xFF\xC0\x00\x00\x00\x00":
            return {"valid": "1"}
        return {"valid": "0"}

    def work_validate(self, _hash, work):

        # Checks if PoW is valid

        work_data = bytearray.fromhex(work)
        hash_data = bytearray.fromhex(_hash)

        h = blake2b(digest_size=8)
        work_data.reverse()
        h.update(work_data)
        h.update(hash_data)
        final = bytearray(h.digest())
        final.reverse()

        return self.work_threshold(final)

    def get_address(self, index):

        # Generate address

        _, pub_key = self.seed_account(NewConfig.seed, index)
        public_key = str(binascii.hexlify(pub_key), "ascii")
        account = self.account_xrb(str(public_key))
        return account

    def get_previous(self, account):

        try:
            acc_info = self.rpc.account_info(account)
            previous = acc_info["frontier"]
            return previous
        except:
            return str()

    def get_balance(self, _hash):

        try:
            account = self.rpc.block_account(_hash)["account"]
            acc_info = self.rpc.account_info(account)
            current_balance = acc_info["balance"]
            return current_balance
        except:
            return str(0)

    def get_pending(self, account):

        try:
            pending = self.rpc.pending(account)
            return pending["blocks"]
        except:
            return str()

    def assemble_block(
        self,
        account,
        previous,
        representative,
        balance,
        link,
        link_as_account,
        signature,
        work,
    ):

        # Returns universal blocks in string format

        block = (
            '{\n    "type": "state",\n    "account": "'
            + account
            + '",\n    "previous": "'
            + previous
            + '",\n    "representative": "'
            + representative
            + '",\n    "balance": "'
            + balance
            + '",\n    "link": "'
            + link
            + '",\n    "link_as_account": "'
            + link_as_account
            + '",\n    "signature": "'
            + signature
            + '",\n    "work": "'
            + work
            + '"\n}\n'
        )

        return block

    def block_create(self, previous, account, representative, balance, link, key, work):

        # Creates universal block with signature and PoW

        signature = self.sign_block(
            key, account, previous, representative, balance, link
        )
        link_as_account = self.account_xrb(link)

        block = self.assemble_block(
            account,
            previous,
            representative,
            balance,
            link,
            link_as_account,
            signature,
            work,
        )
        return block

    def receive_assemble(
        self, account, key, block, work, previous, current_balance, representative
    ):

        # Assembles receive block

        blocks_info = self.rpc.block_confirm(block)
        amount = int(blocks_info["blocks"][block]["amount"])

        new_balance = str(int(current_balance) + int(amount))

        link = block
        block = self.block_create(
            previous, account, representative, new_balance, link, key, work
        )
        return self.rpc.process(block)

    def send_assemble(
        self,
        account,
        destination,
        key,
        amount,
        work,
        previous,
        current_balance,
        representative,
    ):

        # Assembles send block

        new_balance = str(int(current_balance) - int(amount))

        link = self.xrb_account(destination)
        block = self.block_create(
            previous, account, representative, new_balance, link, key, work
        )
        return self.rpc.process(block)

    def change_assemble(
        self, account, key, new_representative, previous, current_balance, work
    ):

        # Assembles change block

        link = hex(0)[2:].rjust(64, "0")

        block = self.block_create(
            previous, account, new_representative, current_balance, link, key, work
        )
        return self.rpc.process(block)

    def open_assemble(self, account, key, previous, block, new_representative, work):

        # Assembles open block

        blocks_info = self.rpc.blocks_info(block)
        amount = int(blocks_info["blocks"][block]["amount"])
        new_balance = str(amount)

        link = block
        block = self.block_create(
            previous, account, new_representative, new_balance, link, key, work
        )
        return self.rpc.process(block)

    def send_xrb(self, dest_account, amount, account, index):

        private_key, _ = self.seed_account(NewConfig.seed, index)

        acc_info = self.rpc.account_info(account)
        previous = acc_info["frontier"]
        current_balance = acc_info["balance"]
        representative = acc_info["representative"]
        work = self.get_work(previous)

        self.send_assemble(
            account,
            dest_account,
            private_key,
            amount,
            work,
            previous,
            current_balance,
            representative,
        )

    def receive_xrb(self, index, account):

        private_key, _ = self.seed_account(NewConfig.seed, index)

        blocks = self.rpc.pending(account)
        block = list(blocks.keys())[0]

        acc_info = self.rpc.account_info(account)
        previous = acc_info["frontier"]
        current_balance = acc_info["balance"]
        representative = acc_info["representative"]
        work = self.get_work(previous)

        self.receive_assemble(
            account, private_key, block, work, previous, current_balance, representative
        )

    def open_xrb(self, index, account):

        private_key, public_key = self.seed_account(NewConfig.seed, index)

        new_representative = (
            "xrb_1kd4h9nqaxengni43xy9775gcag8ptw8ddjifnm77qes1efuoqikoqy5sjq3"
        )

        blocks = self.rpc.accounts_pending([account], 1)["blocks"]
        block = blocks[account][0]

        previous = hex(0)[2:].rjust(64, "0")
        work = self.get_work(public_key.hex().upper())

        self.open_assemble(
            account, private_key, previous, block, new_representative, work
        )

    def change_xrb(self, index, account, new_representative):

        private_key, _ = self.seed_account(NewConfig.seed, index)

        acc_info = self.rpc.account_info(account)
        previous = acc_info["frontier"]
        current_balance = acc_info["balance"]
        work = self.get_work(previous)

        self.change_assemble(
            account, private_key, new_representative, previous, current_balance, work
        )

