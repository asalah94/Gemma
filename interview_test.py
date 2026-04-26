from fastapi import FastAPI
from pydantic import BaseModel
import asyncio
from interview_simulator import stream_interview  # import your functions

app = FastAPI()

class InterviewRequest(BaseModel):
    patient_name: str
    condition_name: str

@app.post("/start-interview")
async def start_interview(req: InterviewRequest):
    results = []
    async for event in stream_interview(req.patient_name, req.condition_name):
        results.append(event)
    return results
