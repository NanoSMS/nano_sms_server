import os
import random
import subprocess
import sys
from pathlib import Path


def settings_file(path):
    print("Generating random seed")
    seed = hex(random.SystemRandom().getrandbits(266))[2:].upper()
    with open(path, "w") as file:
        file.write("""# This file was generated with setup.py
seed = "{seed}"
""".replace('{seed}', seed))
    return "Done"


if __name__ == "__main__":

    print(
        "This will install requirements, generate a seed and write everything to settings.py."
    )
    if "y" in input("Are you sure (y/n): ").lower():
        print("Setting up project.")

        print("Installing requirements.")
        subprocess.call(
            [sys.executable, "-m", "pip", "install", "-r", "requirements.txt"])
        print("Installed requirements")
        print("Creating config file:")
        dirname = os.path.dirname(__file__)
        filename = os.path.join(dirname, 'settings.py')
        print("Checking for settings file")
        file = Path(filename)
        if file.is_file():
            if "y" in input("Overwrite settings file? (y/n): ").lower():
                settings_file(filename)
        else:
            settings_file(filename)
        print("Generating database")

        from modules.database import tables, db
        db.create_tables(tables)

        print(
            "Setup finished. It is advised to write down the seed somewhere else."
        )
