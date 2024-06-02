import os
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from assistant import NetworkAssistant  

load_dotenv()
app = FastAPI()

class QuestionRequest(BaseModel):
    question: str
    chat_history: str

class AnswerResponse(BaseModel):
    reply: str

@app.post("/ask/", response_model=AnswerResponse)
async def ask(request: QuestionRequest):
    if not request.question:
        raise HTTPException(status_code=400, detail="Question content is empty")
    
    api_key = os.getenv("OPENAI_API_KEY")
    assistant_ai = NetworkAssistant(api_key=api_key)
    print(request.chat_history)
    answer = assistant_ai.make_decision(request.question, request.chat_history)
    print("answer: ", answer)
    
    if not answer:
        raise HTTPException(status_code=500, detail="Failed to get a response from the assistant")
    
    return AnswerResponse(reply=answer)
