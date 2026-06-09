import pytest
from app.schemas.jobs import JobCreate

def test_apply_url_whatsapp_channel_dropped():
    job = JobCreate(
        title="Software Engineer",
        description="Must have 5 years of Python experience, Django, FastAPI.",
        source="scraper",
        apply_url="https://whatsapp.com/channel/X"
    )
    assert job.apply_url is None

def test_apply_url_case_insensitive():
    job = JobCreate(
        title="Software Engineer",
        description="Must have 5 years of Python experience, Django, FastAPI.",
        source="scraper",
        apply_url="https://WHATSAPP.COM/channel/X"
    )
    assert job.apply_url is None

def test_contact_phone_aggregator_dropped():
    job = JobCreate(
        title="Software Engineer",
        description="Must have 5 years of Python experience, Django, FastAPI.",
        source="scraper",
        contact_phone="+260813252760"
    )
    assert job.contact_phone is None
