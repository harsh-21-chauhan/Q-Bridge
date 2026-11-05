"""Local assistant endpoints. The browser cannot enable live mode."""
from fastapi import APIRouter, Request
from ..services.assistant_service import AssistantRequest, LocalExplanationRequest

router = APIRouter(prefix='/api/assistant', tags=['Research assistant'])

@router.get('/status')
def status(request: Request):
    return request.app.state.assistant_service.status()

@router.post('/disable')
def disable(request: Request):
    return request.app.state.assistant_service.disable()

@router.post('/ask')
def ask(body: AssistantRequest, request: Request):
    return request.app.state.assistant_service.ask(body)

@router.post('/resume')
def resume(request: Request):
    return request.app.state.assistant_service.resume()

@router.post('/explain')
def explain(body: LocalExplanationRequest, request: Request):
    return request.app.state.assistant_service.local_explanation(body.experiment_id)
