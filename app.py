from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from src.environment import SupportTriageEnv
from src.models import Action

app = FastAPI(
    title="OpenEnv Support Triage",
    description="Customer Support Ticket Triage AI Agent Environment",
    version="0.1.0",
)

env = SupportTriageEnv()


@app.get("/")
def root():
    return {"name": "OpenEnv Support Triage", "docs": "/docs", "health": "/health"}


class ResetRequest(BaseModel):
    task_id: str


class StepResponse(BaseModel):
    observation: dict | None
    reward: dict
    done: bool
    info: dict


@app.post("/reset")
async def reset(request: ResetRequest):
    try:
        obs = env.reset(request.task_id)
        return obs.model_dump()
    except (FileNotFoundError, ValueError) as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/step")
async def step(action: Action):
    try:
        next_obs, reward, done, info = env.step(action)
        return StepResponse(
            observation=next_obs.model_dump() if next_obs else None,
            reward=reward.model_dump(),
            done=done,
            info=info,
        )
    except RuntimeError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/state")
async def state():
    return env.state().model_dump()


@app.get("/health")
async def health():
    return {"status": "ok"}
