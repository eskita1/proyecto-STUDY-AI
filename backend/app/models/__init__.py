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
    "Career",
    "Course",
    "CourseEnrollment",
    "CourseOffering",
    "Faculty",
    "StudyPlan",
    "StudyPlanCourse",
    "University",
    "User",
    "UserCareer",
    "UserCourse",
]
