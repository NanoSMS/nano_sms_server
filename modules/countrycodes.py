#
# List of valid country codes
#

all_codes = dict(
        US="1",
        GB="44"
        # Comment non-valid out

        # DK = "+45"
)

#
# length of country numbers
#

all_length = dict(
        US=10,
        GB=10
        # Comment non-valid out

        # DK = 8
)

#
# Common stuff in phone numbers
#

readability_chars = {
    ' ': "",
    '(': "",
    ')': "",
    '-': "",
    '\u202d': "",
    '\u202c': ""
}