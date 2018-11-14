import json

# Handles configuration JSON file
class Config:
    def get(self, *args):
        with open("config.json") as json_data_file:
            config_dict = json.load(json_data_file)

        for argument in args:
            config_dict = config_dict[argument]

        return config_dict
