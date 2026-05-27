"""Application status transition rules."""

import pytest

from app.schemas.application_status import ApplicationStatus
from app.services.application_status import validate_status_transition


class TestValidateStatusTransition:
    def test_same_status_allowed(self):
        validate_status_transition(ApplicationStatus.saved, ApplicationStatus.saved)

    def test_forward_pipeline_allowed(self):
        validate_status_transition(ApplicationStatus.saved, ApplicationStatus.applied)
        validate_status_transition(ApplicationStatus.applied, ApplicationStatus.interviewing)
        validate_status_transition(ApplicationStatus.interviewing, ApplicationStatus.offered)
        validate_status_transition(ApplicationStatus.offered, ApplicationStatus.closed_won)

    def test_one_step_back_allowed(self):
        validate_status_transition(ApplicationStatus.applied, ApplicationStatus.saved)

    def test_skip_back_multiple_rejected(self):
        with pytest.raises(ValueError, match="Cannot move"):
            validate_status_transition(ApplicationStatus.offered, ApplicationStatus.saved)

    def test_closed_outcome_switch_allowed(self):
        validate_status_transition(ApplicationStatus.closed_won, ApplicationStatus.closed_lost)
