from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from openai import OpenAI
from fastapi.responses import StreamingResponse

import json

import os
from dotenv import load_dotenv

load_dotenv()
api_key = os.getenv("OPENAI_API_KEY")
client = OpenAI(api_key=api_key)

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
    
    context = f"""
    I am helpful assistant. I am answering questions considering the history of the conversation and the rules which have been set:

    Chat history: '''{request.chat_history}'''
    
    RULES: '''
    - My name is Turingo from AI Fresh and I am AI assistant.
    - When i have no enough information, say I don't know.
    - I can speak Polish and English only
    '''
    """

    
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": context},
            {"role": "user", "content": request.question}
        ],
        stream=True
    )
    
    def generate():
        for item in response:
            if item.choices[0].delta.content:
                yield json.dumps({"reply": item.choices[0].delta.content}) + "\n"
    return StreamingResponse(generate(), media_type="application/json")
    
