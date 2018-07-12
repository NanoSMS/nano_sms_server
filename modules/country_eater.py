import re
from modules.countrycodes import all_codes, all_length, readability_chars


# Used to kill chars people add to numbers to make them easier to read.
def multiple_replace(string, rep_dict):
    pattern = re.compile("|".join([re.escape(k) for k in rep_dict.keys()]), re.M)
    return pattern.sub(lambda x: rep_dict[x.group(0)], string)


# Validates numbers according to countrycodes.py
def validate_number(from_country, number):
    number = multiple_replace(number, readability_chars)
    country_code = all_codes[from_country]

    # ToDo Send to other countries than own
    if "+" in number:
        number = number[len(country_code):]
        return len(number) == all_length[from_country]+len(country_code)

    if len(number) == all_length[from_country]:
        return True

    if len(number) == all_length[from_country]+len(country_code):
        if number[0] == country_code:
            return True
    return False


# Turns a number into a real number with countrycode.
def number_real(from_country, destination):
    # Cooking down destination:
    destination = multiple_replace(destination, readability_chars)

    if '+' in destination[0]:
        # Todo: Find which country to send to and check for their valid number
        if destination[1:].replace(" ", "").isdigit():
            return destination
        else:
            return False
    else:

        if destination.isdigit():
            country_code = all_codes[from_country]

            if country_code in destination[:len(country_code)]\
                    and len(destination) == all_length[from_country]+len(country_code):
                return f'+{destination}'
            return f'+{country_code}{destination}'
        else:
            return False


if __name__ == "__main__":
    user_input1 = input("from_country: ")
    user_input2 = input("destination: ")
    if validate_number(user_input1, user_input2):
        print(number_real(user_input1, user_input2))
    else:
        print("Phone number invalid")
