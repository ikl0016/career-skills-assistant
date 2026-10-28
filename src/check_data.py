import json
from pathlib import Path

d = Path("data")
load = lambda f: json.loads((d / f).read_text())
emps, skills, courses, jobs = (load(f) for f in
    ["employees.json", "skills.json", "courses.json", "jobs.json"])

names = {s["name"] for s in skills}
course_ids = {c["course_id"] for c in courses}
print(f"{len(emps)} employees, {len(skills)} skills, {len(courses)} courses, {len(jobs)} jobs")

for e in emps:
    for s in e["skills"]:
        if s not in names: print("Unknown skill on", e["name"], "->", s)
    for c in e["completed_courses"]:
        if c not in course_ids: print("Unknown course on", e["name"], "->", c)
for c in courses:
    for s in c["skills_taught"]:
        if s not in names: print("Unknown skill in", c["course_id"], "->", s)
for j in jobs:
    for s in j["required_skills"]:
        if s not in names: print("Unknown skill in", j["job_id"], "->", s)
print("Check done.")
