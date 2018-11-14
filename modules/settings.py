#
# new Config call to improve configuration
#

import os
import json
from typing import NamedTuple
import random

dirname = os.path.dirname(__file__)
filename = os.path.join(dirname, "../", "config.json")

default_config = dict(
    seed=hex(random.SystemRandom().getrandbits(256))[2:].upper(),
    secret_api=hex(random.SystemRandom().getrandbits(256))[2:].upper(),
    twilionum="",
    uri=[],
    account_sid=[],
    auth_token=[],
    work_uri=[],
)

# Like a NamedTouple, but less strict.
# Todo Switch to a more strict NamedTouple in the future.
class Config:
    seed: str
    secret_api: str
    twilionum: str  # Unsure
    uri: list
    account_sid: list
    auth_token: list
    work_uri: list

    def __init__(self, **data):
        self.__dict__.update(data)

    @classmethod
    def load(cls, filename=filename):
        with open(filename, "r") as file:
            settings_content = json.load(file)

        return Config(**settings_content)

    @staticmethod
    def initiate(json_data: dict = default_config):
        with open(filename, "w") as file:
            json.dump(json_data, file, indent=4)

    @staticmethod
    def new_seed(
        seed: str = hex(random.SystemRandom().getrandbits(256))[2:].upper()
    ) -> str:
        with open(filename, "r") as file:
            content = json.load(file)

        content["seed"] = seed

        with open(filename, "w") as file:
            json.dump(content, file, indent=4)

        return seed

    @staticmethod
    def check(value: str = "seed") -> bool:
        try:
            with open(filename, "r") as file:
                settings_content = json.load(file)

            if settings_content.get(value):
                return True
            return False
        except json.decoder.JSONDecodeError:
            return False


try:
    config = Config.load()
except (FileNotFoundError):
    Config.initiate()
    config = Config.load()
    pass
