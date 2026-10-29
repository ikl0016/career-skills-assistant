import json, shutil
import pytest
from tools import ToolBox

@pytest.fixture
def tb(tmp_path, monkeypatch):
    shutil.copytree("data", tmp_path, dirs_exist_ok=True)   # clean data per test
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    return ToolBox("E001")

def test_profile_is_only_signed_in_employee(tb):
    assert tb.get_my_profile()["name"] == "Maya Chen"

def test_course_search_ranks_ml_first(tb):
    assert tb.search_courses("machine learning")[0]["course_id"] == "C03"

def test_search_records_sources(tb):
    tb.search_courses("machine learning")
    assert "C03" in tb.retrieved_ids

def test_injection_is_removed_from_j5(tb):
    j5 = next(j for j in tb.jobs.items if j["job_id"] == "J5")
    assert j5["flagged"] is True
    assert "ignore" not in j5["untrusted_description"].lower()

def test_unknown_tool_is_rejected(tb):
    assert "error" in tb.dispatch("delete_everything", {})

def test_bad_arguments_dont_crash(tb):
    assert "error" in tb.dispatch("search_courses", {"wrong": "x"})

def test_no_enrollment_without_confirmation(tb, tmp_path):
    result = tb.enroll_in_course("C03")
    assert result["status"] == "confirmation_required"
    assert json.loads((tmp_path / "enrollments.json").read_text()) == []

def test_enrollment_after_confirmation(tb, tmp_path):
    tb.enroll_in_course("C03")          # sets pending
    tb.user_confirmed = True            # simulates the app seeing "yes"
    assert tb.enroll_in_course("C03")["status"] == "enrolled"
    saved = json.loads((tmp_path / "enrollments.json").read_text())
    assert saved == [{"employee_id": "E001", "course_id": "C03"}]

def test_no_cancels_pending_enrollment(tb, tmp_path):
    tb.enroll_in_course("C03")          # asks for confirmation
    tb.set_consent(False)               # the person said no (or anything else)
    assert tb.pending_course is None
    assert tb.enroll_in_course("C03")["status"] == "confirmation_required"
    assert json.loads((tmp_path / "enrollments.json").read_text()) == []

def test_yes_without_pending_course_does_nothing(tb):
    tb.set_consent(True)                # a stray "yes" with nothing to confirm
    assert tb.user_confirmed is False
