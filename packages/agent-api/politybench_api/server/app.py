"""FastAPI remote agent interface."""

from __future__ import annotations

import uuid
from typing import Any

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from politybench_api import PolityEnv
from politybench_core.schemas import ActionBundle

app = FastAPI(
    title="PolityBench Agent API",
    description="Constitutionally constrained national executive policy interface. Research simulator, not a policy oracle.",
    version="0.1.0",
)

SESSIONS: dict[str, PolityEnv] = {}


class ResetRequest(BaseModel):
    scenario: str = "macro_fiscal_crisis"
    fidelity: str = "F1"
    seed: int = 41823
    eval_mode: str = "official"


class ActionRequest(BaseModel):
    action: dict[str, Any] = Field(default_factory=dict)


@app.get("/health")
def health():
    return {"ok": True, "service": "politybench", "disclaimer": "research simulator, not a policy oracle"}


@app.post("/v1/session/reset")
def reset(req: ResetRequest):
    env = PolityEnv(scenario=req.scenario, fidelity=req.fidelity, seed=req.seed, eval_mode=req.eval_mode)
    obs = env.reset()
    sid = str(uuid.uuid4())
    SESSIONS[sid] = env
    return {"session_id": sid, "observation": obs.model_dump()}


@app.get("/v1/session/{sid}/observation")
def observation(sid: str):
    env = SESSIONS.get(sid)
    if not env:
        raise HTTPException(404, "session not found")
    return env.observe().model_dump()


@app.post("/v1/session/{sid}/actions")
def actions(sid: str, req: ActionRequest):
    env = SESSIONS.get(sid)
    if not env:
        raise HTTPException(404, "session not found")
    result = env.step(ActionBundle.model_validate(req.action))
    return result.model_dump()


@app.get("/v1/session/{sid}/ledger")
def ledger(sid: str):
    env = SESSIONS.get(sid)
    if not env:
        raise HTTPException(404, "session not found")
    return env.get_public_ledger()


@app.get("/v1/session/{sid}/legal-authority")
def legal(sid: str):
    env = SESSIONS.get(sid)
    if not env:
        raise HTTPException(404, "session not found")
    return env.get_legal_authority()


@app.get("/v1/session/{sid}/reports/{ministry}")
def reports(sid: str, ministry: str):
    env = SESSIONS.get(sid)
    if not env:
        raise HTTPException(404, "session not found")
    return {"ministry": ministry, "reports": env.get_reports(ministry)}
