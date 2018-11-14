import os
import json
import random
import sys

from modules.settings import Config


def settings_file():
    print("Generating random seed")
    Config.new_seed()

    return "Done"


if __name__ == "__main__":

    print("This will generate a seed and a config file.")
    print(
        "Checking for settings file. If you did not have one before, one has been generated."
    )
    if Config.check():
        if "y" in input("Generate a new seed? (y/n): ").lower():
            settings_file()

    print("Generating tables.")
    from modules.database import tables, db

    db.create_tables(tables)

    print("Setup finished. It is advised to write down the seed somewhere else.")
