from fastapi import FastAPI
from fastapi.responses import JSONResponse

app = FastAPI()


@app.get("/project/")
def who_i_am():
    return {"message": "I am project service!"}
    
@app.get("/health")
async def health_check():
    return JSONResponse({"status": "healthy"})
