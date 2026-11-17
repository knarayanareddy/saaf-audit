import os
from flask import Flask, request, jsonify
import anthropic

app = Flask(__name__)
client = anthropic.Anthropic()


@app.route("/review", methods=["POST"])
def review():
    text = request.json["text"]
    msg = client.messages.create(model="demo-model", max_tokens=300,
                                 messages=[{"role": "user", "content": text}])
    return jsonify(result=msg.content[0].text)


@app.route("/reset", methods=["POST"])
def reset():
    os.remove("data.json")
    return "ok"


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)
