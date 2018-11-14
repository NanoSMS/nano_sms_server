import json

from flask import Flask, abort, jsonify, request

from modules.misc import Config
from modules import secrets
from modules.database import User
from modules.nano import NanoFunctions
from modules.settings import Config as NewConfig

# nano = NanoFunctions(Config.uri[0])
app = Flask(__name__)
nano = ""

#
# AUTH
#


def AUTH(request=request):
    if request.headers.get("Authorization"):
        auth_header = request.headers.get("Authorization")
        secret = auth_header.replace("Secret ", "")
        if secret.verify(secret):
            return True
    else:
        response = abort(403)
        response.headers["WWW-Authenticate"] = "Secret, charset='UTF-8'"
        return response


#
# PRIVATE API SERVER
#


@app.route("/api", methods=["GET"])
def api_index():
    AUTH()  # Requres authorization
    response = dict(success=True)
    return jsonify(response)


@app.route("/api/phonenum", methods=["GET"])
def api_phonenum():
    AUTH()  # Requres authorization
    response = {}
    if not request.args.get("phonenum"):
        return abort(400)

    user = User.get_or_none(User.phonenumber == request.args.get("phonenum"))
    if user:
        account = nano.get_address(user.id + 1)
        responce = dict(success=True, account=account)
        return jsonify()
    abort(404)


if __name__ == "__main__":
    app.run()
