from pydantic import BaseModel, Field

class SkillRec(BaseModel):
    skill: str
    reason: str

class CourseRec(BaseModel):
    course_id: str
    title: str
    reason: str

class RoleRec(BaseModel):
    job_id: str
    title: str
    reason: str

class Recommendations(BaseModel):
    skills: list[SkillRec] = Field(min_length=3, max_length=3)
    courses: list[CourseRec] = Field(min_length=2, max_length=3)
    roles: list[RoleRec] = Field(min_length=1, max_length=2)

class Reply(BaseModel):
    message: str
    recommendations: Recommendations | None = None
