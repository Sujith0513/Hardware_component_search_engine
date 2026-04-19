import asyncio
import json
import os
from fastapi import FastAPI, Request
from fastapi.responses import StreamingResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from src.agent import compile_graph, AgentState
from src.utils.logger import logger

app = FastAPI(title="Hardware Sourcing API", version="2.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Adjust in prod
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory store for reports
_RESULTS_DB = {}

class QueryRequest(BaseModel):
    query: str

from fastapi.staticfiles import StaticFiles

# Endpoints go below...

@app.post("/api/start_research")
async def start_research(req: QueryRequest):
    """Initializes a new research job. Returns a Job ID (which for now is just the query)."""
    # In a real app we'd spawn a background worker and return a UUID.
    # For simplicity, our frontend will just connect to /stream?q=query directly.
    return {"job_id": req.query}

@app.get("/api/stream")
async def stream_research(q: str):
    """Streams the SSE progression of the LangGraph agent."""
    
    async def event_generator():
        try:
            app_compiled = compile_graph()
            
            initial_state: AgentState = {
                "component_query": q,
                "search_plan": "",
                "search_results": [],
                "datasheet_info": None,
                "secondary_datasheet_info": None,
                "cross_validation": None,
                "pricing_data": [],
                "stock_status": None,
                "final_output": None,
                "error_log": [],
                "retry_count": 0,
                "current_step": "initializing",
                "reasoning_trace": [f"[INIT] Agent initialized for: '{q}'"],
            }
            
            shown_steps = set([initial_state["reasoning_trace"][0]])
            
            yield f"data: {json.dumps({'type': 'trace', 'data': initial_state['reasoning_trace'][0]})}\n\n"
            
            final_state = initial_state
            
            # Since standard stream() is blocking but fast enough for our use-case,
            # we iterate over it natively (could use astream if agent supports it).
            for current_state in app_compiled.stream(initial_state, stream_mode="values"):
                final_state = current_state
                trace = current_state.get("reasoning_trace", [])
                
                for t in trace:
                    if t not in shown_steps:
                        shown_steps.add(t)
                        # Yield the new trace event to the client
                        yield f"data: {json.dumps({'type': 'trace', 'data': t})}\n\n"
                        await asyncio.sleep(0.05) # Tiny buffer for SSE flush
                        
            report = final_state.get("final_output")
            if report:
                # Save purely so the frontend can quickly fetch it structurally
                if hasattr(report, "model_dump"):
                    _RESULTS_DB[q] = report.model_dump()
                else:
                    _RESULTS_DB[q] = report # Already a dict
                yield f"data: {json.dumps({'type': 'complete', 'data': 'RESEARCH_SUCCESS'})}\n\n"
            else:
                yield f"data: {json.dumps({'type': 'error', 'data': 'Agent returned partial or no report'})}\n\n"
                
        except Exception as e:
            yield f"data: {json.dumps({'type': 'error', 'data': str(e)})}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")

from fastapi.encoders import jsonable_encoder

@app.get("/api/report")
async def get_report(q: str):
    """Fetch the final parsed structure after completion."""
    try:
        if q in _RESULTS_DB:
            logger.info(f"Serving report for: {q}")
            data = jsonable_encoder(_RESULTS_DB[q])
            return JSONResponse(content=data)
        logger.warning(f"Report not found for: {q}")
        return JSONResponse(content={"error": "Not found"}, status_code=404)
    except Exception as e:
        logger.error(f"Error serving report: {e}")
        return JSONResponse(content={"error": str(e)}, status_code=500)

app.mount("/static", StaticFiles(directory=os.path.join(os.getcwd(), "static")), name="static")

@app.get("/")
async def read_index():
    from fastapi.responses import FileResponse
    return FileResponse(os.path.join(os.getcwd(), "static", "index.html"))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("api:app", host="127.0.0.1", port=8000, reload=True)
