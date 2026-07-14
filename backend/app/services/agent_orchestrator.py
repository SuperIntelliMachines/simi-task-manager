from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.domain_classifier import DomainClassifier
from app.ai.fake_llm_provider import FakeLLMProvider
from app.ai.registry import AgentRegistry
from app.ai.validator import StructuredOutputValidator
from app.schemas.atm012 import AgentCommandInput, AgentExecutionResult
from app.services.approval_service import ApprovalService
from app.services.agent_invocation_service import AgentInvocationService
from app.services.general_task_agent_service import GeneralTaskAgentService
from app.services.insurance_agent_service import InsuranceAgentService


class AgentOrchestrator:
    def __init__(
        self,
        session: AsyncSession,
        registry: AgentRegistry,
        classifier: DomainClassifier,
        llm_provider: FakeLLMProvider,
        validator: StructuredOutputValidator,
    ):
        self.session = session
        self.registry = registry
        self.classifier = classifier
        self.llm_provider = llm_provider
        self.validator = validator
        self.invocation_service = AgentInvocationService(session)
        self.general_task_agent_service = GeneralTaskAgentService(session)
        self.insurance_agent_service = InsuranceAgentService(session)
        self.approval_service = ApprovalService(session)

    async def process_command(self, command: AgentCommandInput) -> AgentExecutionResult:
        classification = self.classifier.classify(command.command_text)

        if classification.needs_clarification or classification.domain is None:
            result = AgentExecutionResult(
                status="needs_clarification",
                agent_key="general_task_agent",
                domain="general",
                intent="follow_up",
                confidence=classification.confidence,
                summary=None,
                created_entities=[],
                missing_fields=classification.clarification.missing_fields if classification.clarification else [],
                approval_request_id=None,
                user_message=None,
                structured_response=None,
                clarification=classification.clarification,
                approval_required=None,
            )
            await self.invocation_service.record_invocation(
                organization_id=command.organization_id,
                actor_user_id=command.actor_user_id,
                agent=result.agent_key,
                domain=result.domain,
                intent=result.intent,
                confidence=result.confidence,
                input_summary=command.command_text,
                output_summary=result.clarification.question if result.clarification else "clarification",
                guardrail_result="clarification",
                tool_calls=[],
                token_usage=None,
            )
            return result

        await self.registry.load_persisted_definitions(
            session=self.session,
            organization_id=command.organization_id,
        )
        agent_key = self.registry.resolve_agent_for_domain(
            classification.domain,
            organization_id=command.organization_id,
        )

        payload = self.llm_provider.generate_structured_response(agent_key, command)
        structured = self.validator.validate(payload)
        execution_result = self.validator.to_execution_result(agent_key=agent_key, response=structured)

        if agent_key == "general_task_agent" and execution_result.status == "executed":
            execution_result = await self.general_task_agent_service.execute(
                command=command,
                response=structured,
                result=execution_result,
            )
        elif agent_key == "insurance_agent" and execution_result.status == "executed":
            execution_result = await self.insurance_agent_service.execute(
                command=command,
                response=structured,
                result=execution_result,
            )
        elif execution_result.status == "needs_approval":
            approval = await self.approval_service.create_request(
                organization_id=command.organization_id,
                requested_by_user_id=command.actor_user_id,
                proposed_action={
                    "action_type": structured.intent,
                    "payload": {
                        "command_text": command.command_text,
                        "proposed_actions": [action.model_dump() for action in structured.proposed_actions],
                    },
                },
                reason=structured.approval_reason or (execution_result.approval_required.reason if execution_result.approval_required else None),
            )
            execution_result = execution_result.model_copy(update={"approval_request_id": str(approval.id)})

        guardrail_result = "passed"
        if execution_result.status == "needs_approval":
            guardrail_result = "approval_required"
        if execution_result.status == "needs_clarification":
            guardrail_result = "clarification"

        await self.invocation_service.record_invocation(
            organization_id=command.organization_id,
            actor_user_id=command.actor_user_id,
            agent=execution_result.agent_key,
            domain=execution_result.domain,
            intent=execution_result.intent,
            confidence=execution_result.confidence,
            input_summary=command.command_text,
            output_summary=execution_result.summary or "",
            guardrail_result=guardrail_result,
            tool_calls=[action.tool_name for action in (structured.proposed_actions if structured else [])],
            token_usage=None,
        )
        return execution_result
