import json
from schemas import Reply

def parse(raw: str) -> Reply:
    """Pull the JSON object out of the model's text and check its shape."""
    start, end = raw.find("{"), raw.rfind("}")
    if start == -1 or end == -1:
        raise json.JSONDecodeError("no JSON object found", raw, 0)
    return Reply.model_validate(json.loads(raw[start:end + 1]))

def semantic_errors(reply: Reply, tools) -> list[str]:
    """Shape can be right but content wrong. Check ids are real and allowed."""
    if not reply.recommendations:
        return []
    errs = []
    done = set(tools.get_my_profile().get("completed_courses", []))
    for c in reply.recommendations.courses:
        if c.course_id not in tools.retrieved_ids:
            errs.append(f"{c.course_id} was not returned by search_courses")
        if c.course_id in done:
            errs.append(f"{c.course_id} is already completed")
    for r in reply.recommendations.roles:
        if r.job_id not in tools.retrieved_ids:
            errs.append(f"{r.job_id} was not returned by search_jobs")
    return errs
