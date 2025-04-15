# app.py (Updated)

from flask import Flask, jsonify, request
from flask_cors import CORS
from test import interview_module
import threading
import queue
import time

app = Flask(__name__)
CORS(app)  # This allows cross-origin requests from the React frontend
CORS(app, resources={r"/api/*": {"origins": "http://localhost:3000"}})

# Add this line to explicitly allow 127.0.0.1 origin
CORS(app, resources={r"/api/*": {"origins": ["http://localhost:3000", "http://127.0.0.1:3000"]}})

# Shared state between routes
interview_state = {
    "active": False,
    "questions": [],
    "current_index": 0,
    "analysis": "",
    "completed": False
}

# Queue to communicate between threads
question_queue = queue.Queue()
analysis_queue = queue.Queue()

def run_interview(name, skills):
    """Background thread to run the interview process"""
    global interview_state
    
    try:
        # Simulate getting questions from your existing code
        from question_gen import generate_custom_questions
        from read_file_json import read_file, read_json
        from langchain_community.llms import Ollama
        
        llm = Ollama(model="llama3")
        
        # Read job description and resume
        job_description = read_file('/Users/vedikasachinbhosale/Desktop/MINOR_PROJECT/AI_INTERVIEW/jd.txt')
        candidate_resume = read_json('/Users/vedikasachinbhosale/Desktop/MINOR_PROJECT/AI_INTERVIEW/portfolio.json')
        
        # Generate questions
        questions = generate_custom_questions(5, job_description, candidate_resume, llm)
        
        # Store questions in shared state
        interview_state["questions"] = questions
        
        # Put first question in queue
        if questions:
            question_queue.put(questions[0])
        
        # Wait for all questions to be answered
        while interview_state["current_index"] < len(interview_state["questions"]):
            time.sleep(1)  # Check periodically
        
        # After all questions are answered, analyze strengths and weaknesses
        from analyzeSW import analyze_strengths_and_weaknesses
        
        # Use your existing analysis function
        strengths_weaknesses_analysis = analyze_strengths_and_weaknesses(
            interview_state["interview_data"], 
            llm
        )
        
        # Store analysis in shared state
        interview_state["analysis"] = strengths_weaknesses_analysis
        interview_state["completed"] = True
        
        # Update portfolio file as in your original code
        from extract_SW import add_strengths_and_weaknesses_to_portfolio
        portfolio_file = '/Users/vedikasachinbhosale/Desktop/MINOR_PROJECT/AI_INTERVIEW/portfolio.json'
        add_strengths_and_weaknesses_to_portfolio(portfolio_file, strengths_weaknesses_analysis)
        
        # Put analysis in queue
        analysis_queue.put(strengths_weaknesses_analysis)
        
    except Exception as e:
        print(f"Error in interview thread: {e}")
        # Notify main thread of error
        question_queue.put(f"ERROR: {str(e)}")

@app.route('/api/start-interview', methods=['POST'])
def start_interview():
    global interview_state
    
    # Reset state
    interview_state = {
        "active": True,
        "questions": [],
        "current_index": 0,
        "interview_data": {},  # Store question-answer pairs
        "analysis": "",
        "completed": False
    }
    
    data = request.get_json()
    name = data.get("name")
    skills = data.get("skills", [])
    
    # Start interview process in background thread
    thread = threading.Thread(target=run_interview, args=(name, skills))
    thread.daemon = True
    thread.start()
    
    return jsonify({
        "status": "success",
        "message": f"Interview started for {name}"
    })

@app.route('/api/get-question', methods=['GET'])
def get_question():
    global interview_state

    if not interview_state["active"]:
        return jsonify({
            "status": "error",
            "message": "No active interview"
        }), 400
    
    if interview_state["completed"]:
        return jsonify({
            "status": "complete",
            "analysis": interview_state["analysis"]
        })
    
    # If there's a current question, return it
    if interview_state["current_index"] < len(interview_state["questions"]):
        current_question = interview_state["questions"][interview_state["current_index"]]
        
        # Use TTS to speak the question (simulate your existing code)
        try:
            import pyttsx3
            engine = pyttsx3.init()
            engine.setProperty('rate', 160)
            voices = engine.getProperty('voices')
            engine.setProperty('voice', voices[1].id)
            engine.say(current_question)
            engine.runAndWait()
        except Exception as e:
            print(f"Error with TTS: {e}")
        
        return jsonify({
            "status": "question",
            "question": current_question,
            "question_number": interview_state["current_index"] + 1,
            "total_questions": len(interview_state["questions"])
        })
    
    # Wait for next question from interview thread
    try:
        question = question_queue.get(timeout=1)
        
        # Check if it's an error message
        if isinstance(question, str) and question.startswith("ERROR:"):
            return jsonify({
                "status": "error",
                "message": question
            }), 500
        
        return jsonify({
            "status": "question",
            "question": question,
            "question_number": interview_state["current_index"] + 1,
            "total_questions": len(interview_state["questions"])
        })
    except queue.Empty:
        # If no question is available yet
        return jsonify({
            "status": "waiting",
            "message": "Preparing next question"
        })

@app.route('/api/submit-answer', methods=['POST'])
def submit_answer():
    global interview_state
    
    if not interview_state["active"]:
        return jsonify({
            "status": "error",
            "message": "No active interview"
        }), 400
    
    # In a real implementation, you'd record and transcribe the audio
    # For now, we'll simulate as if we received the answer
    
    # Store the question and answer
    current_question = interview_state["questions"][interview_state["current_index"]]
    
    # In a real implementation, you'd use speech_to_text from your code
    # Here we'll just simulate it
    answer = "Simulated answer from speech recognition"
    
    # Store in interview data
    interview_state["interview_data"][current_question] = answer
    
    # Simulate your follow-up question logic
    try:
        from follow_up_gen import generate_follow_up
        from langchain_community.llms import Ollama
        
        llm = Ollama(model="llama3")
        follow_up = generate_follow_up(current_question, answer, llm)
        
        # Store follow-up and move to next question
        interview_state["questions"].insert(interview_state["current_index"] + 1, follow_up)
    except Exception as e:
        print(f"Error generating follow-up: {e}")
    
    # Move to next question
    interview_state["current_index"] += 1
    
    return jsonify({
        "status": "success",
        "message": "Answer received"
    })

if __name__ == '__main__':
    app.run(debug=True)