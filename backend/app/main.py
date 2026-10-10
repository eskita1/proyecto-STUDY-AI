from fastapi import FastAPI

from app.routes.academic import router as academic_router
from app.routes.enrollment import router as enrollment_router
from app.routes.faculty import router as faculty_router
from app.routes.institutional import router as institutional_router
from app.routes.planning import router as planning_router
from app.routes.tracking import router as tracking_router
from app.routes.university import router as university_router

app = FastAPI()
app.include_router(academic_router)
app.include_router(faculty_router)
app.include_router(enrollment_router)
app.include_router(institutional_router)
app.include_router(planning_router)
app.include_router(tracking_router)
app.include_router(university_router)


@app.get("/health")
async def health():
    return {"status": "ok"}
