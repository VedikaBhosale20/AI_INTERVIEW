import re

def generate_custom_questions(number_of_questions, job_description, candidate_resume, llm_model):
    """Generate custom questions based on job description and candidate resume."""
    prompt = (
        f"Only Generate {number_of_questions} interview questions based on the following job description requirements and my resume in points separated by new lines. Check if the candidate is the right fit for the job. strictly follow the format of just giving questions.\n"
        f"Job Description: {job_description}\n"
        f"Candidate Resume: {candidate_resume}\n"
    )
    questions = llm_model.invoke(prompt)
    question_list = re.findall(r'\d+\.\s.*', questions)
    
    # Strip leading/trailing whitespace from each question
    question_list = [q.strip() for q in question_list]
    return question_list

