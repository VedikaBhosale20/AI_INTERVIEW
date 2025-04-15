from flask import Flask, jsonify, request
from flask_cors import CORS
from test import interview_module 

app = Flask(__name__)
CORS(app)  # This allows cross-origin requests from the React frontend

import requests

url = 'http://127.0.0.1:11434/api/generate'
response = requests.post(url, json={"input": "Hello, Ollama!"})
print(response.json())

@app.route('/api/get-question', methods=['GET'])
def get_question():
    # return the next question
    pass

@app.route('/api/submit-answer', methods=['POST'])
def submit_answer():
    # accept the answer and return next question or end message
    pass


@app.route('/api/interview', methods=['POST'])
def ai_interview():
    data = request.get_json()
    print("Received data from frontend:", data)

    name = data.get("name")
    skills = data.get("skills")

    # Run the AI interview logic
    interview_module()

    response = {
        "status": "success",
        "message": f"Interview scheduled for {name} with skills: {', '.join(skills)}"
    }

    return jsonify(response)


if __name__ == '__main__':
    app.run(debug=True)

