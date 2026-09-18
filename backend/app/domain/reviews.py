from enum import StrEnum


class AdminStatus(StrEnum):
    UNREVIEWED = "UNREVIEWED"
    VERIFIED = "VERIFIED"
    REJECTED = "REJECTED"
    ESCALATED = "ESCALATED"


class ReviewAction(StrEnum):
    VERIFY = "VERIFY"
    REJECT = "REJECT"
    ESCALATE = "ESCALATE"
