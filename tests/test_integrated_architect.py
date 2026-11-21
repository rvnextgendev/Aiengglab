from uuid import uuid4
import pytest
from app.ai_workflows import feedback
from app.ai_workflows.integrated import approval_preview

def test_feedback_tenant_isolation(tmp_path, monkeypatch):
    monkeypatch.setenv("WORKFLOW_FEEDBACK_SQLITE_PATH",str(tmp_path/"f.sqlite"))
    thread = uuid4().hex
    feedback.submit(thread,"tenant-a","user",5,"Good")
    assert feedback.list_for_workflow(thread,"tenant-b")==[]
    assert feedback.list_for_workflow(thread,"tenant-a")[0]["rating"]==5

def test_feedback_upsert_and_validation(tmp_path,monkeypatch):
    monkeypatch.setenv("WORKFLOW_FEEDBACK_SQLITE_PATH",str(tmp_path/"f.sqlite"))
    thread = uuid4().hex
    feedback.submit(thread,"tenant-a","user",4,"OK")
    feedback.submit(thread,"tenant-a","user",2,"Needs work")
    assert len(feedback.list_for_workflow(thread,"tenant-a"))==1
    with pytest.raises(ValueError):
        feedback.submit(thread,"tenant-a","user",7)

def test_approval_preview_masks_email():
    result = approval_preview({"sources":[{"source":"doc:1",
        "text":"Email learner@example.com for help"}]})
    assert "[EMAIL]" in result[0]["excerpt"]
    assert "learner@example.com" not in result[0]["excerpt"]
