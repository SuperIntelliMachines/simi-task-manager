from pydantic import BaseModel, Field


class SchedulerJobCountResponse(BaseModel):
    success: bool = True
    processed: int = Field(..., ge=0, description="Reminders successfully sent (SENT status)")
    fetched: int = Field(0, ge=0, description="Due PENDING reminders fetched for processing")
    failed: int = Field(0, ge=0, description="Reminders that failed to send and remain PENDING")
    due_total: int = Field(0, ge=0, description="Due PENDING reminders matching fetch filters before locking")


class RenewalEscalationJobResponse(BaseModel):
    success: bool = True
    processed: int = Field(..., ge=0, description="Expired policies evaluated for escalation")
    escalated: int = Field(..., ge=0, description="Policies newly escalated in this run")
    skipped: int = Field(..., ge=0, description="Policies skipped (already escalated or renewed)")


class SchedulerSuccessResponse(BaseModel):
    success: bool = True


class RepairPolicyRemindersResponse(BaseModel):
    success: bool = True
    policies_repaired: int = Field(..., ge=0)
    deleted: int = Field(..., ge=0, description="Stale PENDING reminder rows removed")
    created: int = Field(..., ge=0, description="Correct schedule rows created")
