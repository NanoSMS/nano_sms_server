import os
import json
import random
import subprocess
import sys

dirname = os.path.dirname(__file__)
conf_file = os.path.join(dirname, 'config.json')


def settings_file():
    print("Generating random seed")
    seed = hex(random.SystemRandom().getrandbits(256))[2:].upper()

    with open(conf_file, 'r') as file:
        config = json.load(file)

    config["seed"] = seed

    with open(conf_file, 'w') as file:
        json.dump(config, file, indent=4)

    return "Done"


if __name__ == "__main__":

    print("This will install requirements, generate a seed.")
    if "y" in input("Are you sure (y/n): ").lower():
        print("Setting up project.")

        print("Installing / updating requirements.")
        subprocess.call(
            [sys.executable, "-m", "pip", "install", "-r", "requirements.txt"])
        print("Installed requirements")
        print("Checking for settings file")
        with open(conf_file, 'r') as file:
            config = json.load(file)
        if config["seed"]:
            if "y" in input("Overwrite settings file? (y/n): ").lower():
                settings_file()
        else:
            settings_file()
        print("Generating database")

        from modules.database import tables, db
        db.create_tables(tables)

        print(
            "Setup finished. It is advised to write down the seed somewhere else."
        )
