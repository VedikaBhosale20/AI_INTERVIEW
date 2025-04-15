# app.py (Updated with WebSockets and Interactive Interview)

from flask import Flask, jsonify, request
from flask_cors import CORS
from flask_socketio import SocketIO, emit
import threading
import json
import os
import base64
import time
import io
import tempfile

app = Flask(__name__)
CORS(app)
socketio = SocketIO(app, cors_allowed_origins="*")

# Shared state between routes
interview_state = {
    "active": False,
    "questions": [],
    "current_index": 0,
    "interview_data": {},
    "analysis": "",
    "completed": False,
    "updated_portfolio": None
}

# Track active interview sessions
active_sessions = {}


def run_interview(session_id, job_description, resume_data, num_questions=5):
    """Background thread to run the interview process with dynamic inputs"""
    global active_sessions

    try:
        # Save job description to temporary file
        jd_file = tempfile.NamedTemporaryFile(delete=False, mode='w', suffix='.txt')
        jd_file.write(job_description)
        jd_path = jd_file.name
        jd_file.close()

        # Save resume data to temporary file
        resume_file = tempfile.NamedTemporaryFile(delete=False, mode='w', suffix='.json')
        json.dump(resume_data, resume_file)
        resume_path = resume_file.name
        resume_file.close()

        # Import necessary modules
        from question_gen import generate_custom_questions
        from langchain_community.llms import Ollama
        from analyzeSW import analyze_strengths_and_weaknesses
        from extract_SW import add_strengths_and_weaknesses_to_portfolio

        # Initialize Ollama
        llm = Ollama(model="llama3")

        # Load whisper model once
        import whisper
        whisper_model = whisper.load_model("base")

        # Initialize the session state
        session = {
            "active": True,
            "questions": [],
            "current_index": 0,
            "interview_data": {},
            "analysis": "",
            "completed": False
        }
        active_sessions[session_id] = session

        # Generate questions using the provided job description and resume
        socketio.emit('interview_status', {'status': 'generating_questions'}, room=session_id)
        questions = generate_custom_questions(
            num_questions,
            job_description,
            resume_data,
            llm
        )

        # Store questions in session state
        session["questions"] = questions

        # Process each question in sequence
        for idx, question in enumerate(questions):
            # Update status
            session["current_index"] = idx
            socketio.emit('new_question', {
                'question': question,
                'question_number': idx + 1,
                'total_questions': len(questions)
            }, room=session_id)

            # Speak the question using TTS
            try:
                import pyttsx3
                engine = pyttsx3.init()
                engine.setProperty('rate', 160)
                voices = engine.getProperty('voices')
                engine.setProperty('voice', voices[1].id)
                engine.say(question)
                engine.runAndWait()
            except Exception as e:
                print(f"Error with TTS: {e}")
                socketio.emit('tts_error', {'error': str(e)}, room=session_id)

            # Wait for answer (this will be triggered by client-side events)
            # The actual handling is in the WebSocket event handlers below

            # We'll proceed once the answer is received in the WebSocket handler
            while session["current_index"] == idx and session["active"]:
                time.sleep(0.5)

            if not session["active"]:
                # Interview was cancelled
                break

            # After answer is received, we could generate a follow-up
            if idx < len(questions) - 1 and "generate_followup" in session and session["generate_followup"]:
                current_question = session["questions"][idx]
                answer = session["interview_data"].get(current_question, "")

                try:
                    follow_up = generate_follow_up(current_question, answer, llm)

                    # Add follow-up question
                    session["questions"].insert(idx + 1, follow_up)
                    questions = session["questions"]  # Update local questions list
                except Exception as e:
                    print(f"Error generating follow-up: {e}")

        # After all questions are answered, analyze strengths and weaknesses
        socketio.emit('interview_status', {'status': 'analyzing_responses'}, room=session_id)
        strengths_weaknesses_analysis = analyze_strengths_and_weaknesses(
            session["interview_data"],
            llm
        )

        # Store analysis in session state
        session["analysis"] = strengths_weaknesses_analysis
        session["completed"] = True

        # Update portfolio with analysis
        updated_portfolio = resume_data.copy()

        # Check if the portfolio already has a strengths_weaknesses field
        if "strengths_weaknesses" not in updated_portfolio:
            updated_portfolio["strengths_weaknesses"] = {}

        # Update with new analysis
        updated_portfolio["strengths_weaknesses"] = strengths_weaknesses_analysis

        # Store updated portfolio
        session["updated_portfolio"] = updated_portfolio

        # Send completion notification
        socketio.emit('interview_complete', {
            'analysis': strengths_weaknesses_analysis,
            'updated_portfolio': updated_portfolio
        }, room=session_id)

        # Clean up temporary files
        try:
            os.unlink(jd_path)
            os.unlink(resume_path)
        except:
            pass

    except Exception as e:
        print(f"Error in interview thread: {e}")
        socketio.emit('interview_error', {'error': str(e)}, room=session_id)

        # Clean up session
        if session_id in active_sessions:
            active_sessions[session_id]["active"] = False


@app.route('/api/start-interview', methods=['POST'])
def start_interview():
    # Generate a session ID
    session_id = request.sid if hasattr(request, 'sid') else f"session_{int(time.time())}"

    # Get job description from form text field
    job_description = request.form.get("jobDescription", "")

    # Get resume data from uploaded JSON file
    resume_data = {}
    if 'resumeFile' in request.files:
        resume_file = request.files['resumeFile']
        if resume_file.filename != '' and resume_file.filename.endswith('.json'):
            try:
                resume_data = json.loads(resume_file.read().decode('utf-8'))
            except json.JSONDecodeError:
                return jsonify({
                    "status": "error",
                    "message": "Invalid JSON file format for resume data"
                }), 400

    # Get number of questions (default to 5)
    try:
        num_questions = int(request.form.get("numQuestions", "5"))
    except ValueError:
        num_questions = 5

    # Validate inputs
    if not job_description:
        return jsonify({
            "status": "error",
            "message": "Job description is required"
        }), 400

    if not resume_data:
        return jsonify({
            "status": "error",
            "message": "Resume data file is required"
        }), 400

    # Start interview process in background thread
    thread = threading.Thread(
        target=run_interview,
        args=(session_id, job_description, resume_data, num_questions)
    )
    thread.daemon = True
    thread.start()

    return jsonify({
        "status": "success",
        "message": "Interview started successfully",
        "session_id": session_id
    })


@socketio.on('connect')
def handle_connect():
    print(f"Client connected: {request.sid}")


@socketio.on('join_session')
def handle_join(data):
    session_id = data.get('session_id')
    if not session_id:
        emit('error', {'message': 'No session ID provided'})
        return

    # Join the room corresponding to this session
    from flask_socketio import join_room
    join_room(session_id)
    emit('joined_session', {'session_id': session_id})


@socketio.on('submit_answer')
def handle_answer(data):
    session_id = data.get('session_id')
    if not session_id or session_id not in active_sessions:
        emit('error', {'message': 'Invalid session ID'})
        return

    session = active_sessions[session_id]
    if not session["active"] or session["current_index"] >= len(session["questions"]):
        emit('error', {'message': 'No active question'})
        return

    current_question = session["questions"][session["current_index"]]
    answer_text = data.get('text')
    audio_data = data.get('audio')  # Base64 encoded audio if available

    # Process the answer based on what was provided
    if audio_data:
        # If audio was provided, convert it to text
        try:
            # Decode base64 audio
            audio_bytes = base64.b64decode(audio_data)

            # Save to temporary file
            with tempfile.NamedTemporaryFile(delete=False, suffix='.wav') as temp_audio_file:
                temp_audio_path = temp_audio_file.name
                temp_audio_file.write(audio_bytes)

            # Use whisper to transcribe
            import whisper
            model = whisper.load_model("base")
            result = model.transcribe(temp_audio_path)
            answer = result["text"]

            # Clean up temp file
            os.unlink(temp_audio_path)

        except Exception as e:
            print(f"Error processing audio: {e}")
            emit('transcription_error', {'error': str(e)})
            # Fall back to text answer if provided
            answer = answer_text or "Unable to process audio response"
    else:
        # Use provided text answer
        answer = answer_text or "No answer provided"

    # Store in interview data
    session["interview_data"][current_question] = answer

    # Save whether to generate a follow-up
    session["generate_followup"] = data.get("generateFollowUp", True)

    # Move to next question (the main thread will handle the follow-up)
    session["current_index"] += 1

    emit('answer_received', {
        'question': current_question,
        'answer': answer,
        'transcription': answer if audio_data else None
    })


@socketio.on('cancel_interview')
def handle_cancel(data):
    session_id = data.get('session_id')
    if session_id and session_id in active_sessions:
        active_sessions[session_id]["active"] = False
        emit('interview_cancelled', {}, room=session_id)


@app.route('/api/get-analysis', methods=['GET'])
def get_analysis():
    session_id = request.args.get('session_id')
    if not session_id or session_id not in active_sessions:
        return jsonify({
            "status": "error",
            "message": "Invalid session ID"
        }), 400

    session = active_sessions[session_id]

    if not session["completed"]:
        return jsonify({
            "status": "waiting",
            "message": "Analysis not yet complete"
        })

    return jsonify({
        "status": "success",
        "analysis": session["analysis"],
        "updated_portfolio": session["updated_portfolio"]
    })


# Add this import if not at the top
from follow_up_gen import generate_follow_up

if __name__ == '__main__':
    socketio.run(app, debug=True)