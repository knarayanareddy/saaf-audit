import os
import hmac
from functools import wraps
from flask import Flask, request, jsonify, abort
import anthropic

app = Flask(__name__)
client = anthropic.Anthropic()
API_TOKEN = os.environ["APP_API_TOKEN"]


def require_token(fn):
    @wraps(fn)
    def wrapper(*a, **kw):
        supplied = request.headers.get("Authorization", "")
        if not hmac.compare_digest(supplied, "Bearer " + API_TOKEN):
            abort(401)
        return fn(*a, **kw)
    return wrapper


@app.route("/review", methods=["POST"])
@require_token
def review():
    text = request.json["text"]
    msg = client.messages.create(model="demo-model", max_tokens=300,
                                 messages=[{"role": "user", "content": text}])
    return jsonify(result=msg.content[0].text)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)
