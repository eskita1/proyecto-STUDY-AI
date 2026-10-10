from fastapi import FastAPI

from app.routes.university import router as university_router

app = FastAPI()
app.include_router(university_router)


@app.get("/health")
async def health():
    return {"status": "ok"}
