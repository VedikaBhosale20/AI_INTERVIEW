// src/App.js
import React, { useState, useRef, useEffect } from 'react';
import './App.css';

function App() {
  const [name, setName] = useState('');
  const [skills, setSkills] = useState('');
  const [isInterviewStarted, setIsInterviewStarted] = useState(false);
  const [isInterviewCompleted, setIsInterviewCompleted] = useState(false);
  const [currentQuestion, setCurrentQuestion] = useState('');
  const [isListening, setIsListening] = useState(false);
  const [interviewResults, setInterviewResults] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  
  const videoRef = useRef(null);
  const mediaStreamRef = useRef(null);

  // Start camera when interview begins
  useEffect(() => {
    if (isInterviewStarted && !isInterviewCompleted) {
      startCamera();
    }
    return () => {
      if (mediaStreamRef.current) {
        mediaStreamRef.current.getTracks().forEach(track => track.stop());
      }
    };
  }, [isInterviewStarted, isInterviewCompleted]);

  const startCamera = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ 
        video: true,
        audio: true 
      });
      mediaStreamRef.current = stream;
      if (videoRef.current) {
        videoRef.current.srcObject = stream;
      }
    } catch (err) {
      console.error("Error accessing camera:", err);
      setError("Cannot access camera. Please check permissions.");
    }
  };

  const stopCamera = () => {
    if (mediaStreamRef.current) {
      mediaStreamRef.current.getTracks().forEach(track => track.stop());
      mediaStreamRef.current = null;
      if (videoRef.current) {
        videoRef.current.srcObject = null;
      }
    }
  };

  const startInterview = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError('');
    
    try {
      const response = await fetch('http://127.0.0.1:5000/api/start-interview', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ name, skills: skills.split(',').map(s => s.trim()) }),
      });

      if (!response.ok) {
        throw new Error('Failed to start interview');
      }

      setIsInterviewStarted(true);
      fetchNextQuestion();
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const fetchNextQuestion = async () => {
    try {
      const response = await fetch('http://127.0.0.1:5000/api/get-question');
      
      if (!response.ok) {
        throw new Error('Failed to get next question');
      }

      const data = await response.json();
      
      if (data.status === 'complete') {
        // Interview is complete
        setIsInterviewCompleted(true);
        setInterviewResults(data.analysis);
        stopCamera();
      } else {
        // Set next question
        setCurrentQuestion(data.question);
        setIsListening(true);
        
        // Wait for answer duration
        setTimeout(() => {
          setIsListening(false);
          submitAnswer();
        }, 60000); // 60 seconds to answer
      }
    } catch (err) {
      setError(err.message);
    }
  };

  const submitAnswer = async () => {
    try {
      const response = await fetch('http://127.0.0.1:5000/api/submit-answer', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ answered: true }),
      });

      if (!response.ok) {
        throw new Error('Failed to submit answer');
      }
      
      // After submission, get next question or finish
      fetchNextQuestion();
    } catch (err) {
      setError(err.message);
    }
  };

  return (
    <div className="app-container">
      <h1>AI Interview Assistant</h1>
      
      {error && <div className="error-message">{error}</div>}
      
      {!isInterviewStarted ? (
        <div className="start-form">
          <h2>Start Your Interview</h2>
          <form onSubmit={startInterview}>
            <div className="form-group">
              <label htmlFor="name">Full Name:</label>
              <input
                type="text"
                id="name"
                value={name}
                onChange={(e) => setName(e.target.value)}
                required
              />
            </div>
            <div className="form-group">
              <label htmlFor="skills">Skills (comma separated):</label>
              <input
                type="text"
                id="skills"
                value={skills}
                onChange={(e) => setSkills(e.target.value)}
                required
                placeholder="React, Python, Machine Learning"
              />
            </div>
            <button type="submit" disabled={loading}>
              {loading ? 'Starting...' : 'Start Interview'}
            </button>
          </form>
        </div>
      ) : isInterviewCompleted ? (
        <div className="results-container">
          <h2>Interview Completed!</h2>
          <div className="analysis">
            <h3>Strengths and Weaknesses Analysis</h3>
            <pre>{interviewResults}</pre>
          </div>
          <button onClick={() => {
            setIsInterviewStarted(false);
            setIsInterviewCompleted(false);
            setCurrentQuestion('');
          }}>
            Start New Interview
          </button>
        </div>
      ) : (
        <div className="interview-container">
          <div className="video-section">
            <video
              ref={videoRef}
              autoPlay
              playsInline
              muted={false}
              className="webcam-feed"
            />
          </div>
          
          <div className="question-section">
            <h2>Current Question:</h2>
            <div className="question-box">
              {currentQuestion || "Loading question..."}
            </div>
            
            <div className="status-indicator">
              {isListening ? (
                <div className="listening">
                  <div className="pulse-animation"></div>
                  Listening to your answer...
                </div>
              ) : (
                <div className="processing">Processing your answer...</div>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export default App;