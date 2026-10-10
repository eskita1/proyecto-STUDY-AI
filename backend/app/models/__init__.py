from app.models.academic import (
    AcademicSource,
    ExtractionProposal,
    Subtopic,
    Topic,
    Unit,
)
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
from app.models.planning import Assessment, AssessmentTopic, CourseScheduleItem
from app.models.practice import PracticeExercise, PracticeSession, PracticeSessionTopic
from app.models.study import StudySession, StudySessionTopic
from app.models.tracking import EnrollmentTopic
from app.models.university import University

__all__ = [
    "AcademicSource",
    "Assessment",
    "AssessmentTopic",
    "Career",
    "Course",
    "CourseEnrollment",
    "CourseOffering",
    "CourseScheduleItem",
    "EnrollmentTopic",
    "ExtractionProposal",
    "Faculty",
    "PracticeExercise",
    "PracticeSession",
    "PracticeSessionTopic",
    "StudyPlan",
    "StudyPlanCourse",
    "StudySession",
    "StudySessionTopic",
    "Subtopic",
    "Topic",
    "Unit",
    "University",
    "User",
    "UserCareer",
    "UserCourse",
]
