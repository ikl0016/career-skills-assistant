import json, os
from pathlib import Path
from retrieval import Index, sanitize

def data_dir():
    """Read at call time so tests can point it at a temp copy."""
    return Path(os.getenv("DATA_DIR", "data"))

def load(name):
    return json.loads((data_dir() / name).read_text(encoding="utf-8"))

class ToolBox:
    """All tools for ONE signed-in session. employee_id comes from sign-in,
    never from the model, so no tool can read another employee's data."""

    ALLOWED = {"get_my_profile", "search_skills", "search_courses",
               "search_jobs", "enroll_in_course"}

    def __init__(self, employee_id):
        self.employee_id = employee_id
        self.retrieved_ids = set()     # ids the model has actually been shown
        self.pending_course = None     # course awaiting a yes
        self.user_confirmed = False    # set only by app code
        self.skills = Index(load("skills.json"), "skill_id",
            lambda s: f"{s['name']} {s['category']} {s['description']} {' '.join(s['roles'])}")
        self.courses = Index(load("courses.json"), "course_id",
            lambda c: f"{c['title']} {c['description']} {' '.join(c['skills_taught'])}")
        jobs = [sanitize(j) for j in load("jobs.json")]
        self.jobs = Index(jobs, "job_id",
            lambda j: f"{j['title']} {j['untrusted_description']} {' '.join(j['required_skills'])}")

    def get_my_profile(self):
        me = next((e for e in load("employees.json")
                   if e["employee_id"] == self.employee_id), None)
        return me or {"error": "profile not found"}

    def search_skills(self, query, top_k=5):
        return self.skills.search(query, top_k)

    def search_courses(self, query, top_k=3):
        hits = self.courses.search(query, top_k)
        self.retrieved_ids.update(h["course_id"] for h in hits)
        return hits

    def search_jobs(self, query, top_k=3):
        hits = self.jobs.search(query, top_k)
        self.retrieved_ids.update(h["job_id"] for h in hits)
        return hits

    def enroll_in_course(self, course_id):
        catalog = {c["course_id"]: c for c in load("courses.json")}
        if course_id not in catalog:
            return {"error": f"unknown course {course_id}"}
        if not (self.user_confirmed and self.pending_course == course_id):
            self.pending_course = course_id
            return {"status": "confirmation_required",
                    "course": catalog[course_id]["title"]}
        enrollments = load("enrollments.json")
        if any(e["employee_id"] == self.employee_id and e["course_id"] == course_id
               for e in enrollments):
            return {"status": "already_enrolled"}
        enrollments.append({"employee_id": self.employee_id, "course_id": course_id})
        (data_dir() / "enrollments.json").write_text(json.dumps(enrollments, indent=2))
        self.pending_course, self.user_confirmed = None, False
        return {"status": "enrolled", "course": catalog[course_id]["title"]}

    def dispatch(self, name, args):
        """Route a model tool call to a method. Never crash the loop."""
        if name not in self.ALLOWED:
            return {"error": f"unknown tool {name}"}
        try:
            return getattr(self, name)(**args)
        except TypeError as e:
            return {"error": f"bad arguments: {e}"}

def _fn(name, desc, props=None, required=None):
    return {"type": "function", "function": {
        "name": name, "description": desc,
        "parameters": {"type": "object", "properties": props or {},
                       "required": required or []}}}

_query = {"query": {"type": "string"}, "top_k": {"type": "integer"}}

TOOL_SCHEMAS = [
    _fn("get_my_profile", "Get the signed-in employee's own profile. Takes no arguments."),
    _fn("search_skills", "Search the skill taxonomy by topic or role.", _query, ["query"]),
    _fn("search_courses", "Search the learning catalog by skill or topic.", _query, ["query"]),
    _fn("search_jobs", "Search internal job postings by skill or role.", _query, ["query"]),
    _fn("enroll_in_course", "Enroll the signed-in employee in a course. Requires their confirmation.",
        {"course_id": {"type": "string"}}, ["course_id"]),
]
