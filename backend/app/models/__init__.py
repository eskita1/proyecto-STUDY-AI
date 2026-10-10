from app.models.enrollment import CourseEnrollment, CourseOffering, UserCourse
from app.models.faculty import Faculty
from app.models.institutional import (
    Career,
    Course,
    StudyPlan,
    StudyPlanCourse,
    User,
    UserCareer,
)
from app.models.university import University

__all__ = [
    "AcademicSource",
    "Career",
    "Course",
    "CourseEnrollment",
    "CourseOffering",
    "ExtractionProposal",
    "Faculty",
    "StudyPlan",
    "StudyPlanCourse",
    "Subtopic",
    "Topic",
    "Unit",
    "University",
    "User",
    "UserCareer",
    "UserCourse",
]
from app.models.academic import (
    AcademicSource,
    ExtractionProposal,
    Subtopic,
    Topic,
    Unit,
)
