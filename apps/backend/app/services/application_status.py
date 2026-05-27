"""Application status transition rules for saved jobs."""

from app.schemas.application_status import ApplicationStatus

PIPELINE: tuple[ApplicationStatus, ...] = (
    ApplicationStatus.saved,
    ApplicationStatus.applied,
    ApplicationStatus.interviewing,
    ApplicationStatus.offered,
)

CLOSED_STATUSES: frozenset[ApplicationStatus] = frozenset(
    {ApplicationStatus.closed_won, ApplicationStatus.closed_lost}
)


def _stage_index(status: ApplicationStatus) -> int | None:
    if status in CLOSED_STATUSES:
        return len(PIPELINE)
    try:
        return PIPELINE.index(status)
    except ValueError:
        return None


def validate_status_transition(
    from_status: ApplicationStatus,
    to_status: ApplicationStatus,
) -> None:
    """Allow same-status updates and moves along the pipeline (incl. closed)."""
    if from_status == to_status:
        return

    from_idx = _stage_index(from_status)
    to_idx = _stage_index(to_status)
    if from_idx is None or to_idx is None:
        raise ValueError("Invalid application status")

    # Forward moves along saved → applied → interviewing → offered → closed.
    if to_idx >= from_idx:
        return

    # Allow moving back one pipeline stage (e.g. applied → saved).
    if from_idx - to_idx == 1:
        return

    # Allow switching between closed outcomes.
    if from_status in CLOSED_STATUSES and to_status in CLOSED_STATUSES:
        return

    raise ValueError(
        f"Cannot move from {from_status.value} to {to_status.value}"
    )
