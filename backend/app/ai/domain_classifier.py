from app.ai.fake_llm_provider import FakeLLMProvider
from app.schemas.atm012 import ClarificationRequest, DomainClassificationResult


class DomainClassifier:
    def __init__(self, llm_provider: FakeLLMProvider):
        self.llm_provider = llm_provider
        # Expanded keyword sets: Specialized Agents Implementation Guide + legacy domains
        self.keyword_scores = {
            "calendar": ["calendar", "meeting", "schedule", "appointment", "event", "invite", "reschedule", "cancel meeting", "book room"],
            "email": ["email", "mail", "inbox", "send email", "compose", "forward", "reply", "draft", "subject", "attachment"],
            "tasks": ["task", "todo", "reminder", "assign", "complete", "due date", "checklist", "mark done", "task list"],
            "notes": ["note", "notebook", "jot", "write note", "record note", "save note", "edit note", "delete note"],
            "general": ["remind", "call", "todo", "task", "follow up", "reminder", "snooze", "complete", "summary", "overdue"],
            "insurance": ["policy", "renewal", "premium", "claim", "insurer", "insurance", "coverage", "quote", "lead", "demo"],
            "construction": ["wiring", "site", "contractor", "concrete", "project", "construction", "blueprint", "permit", "inspection", "owner update"],
            "doctors_office": ["patient", "clinic", "appointment", "medical", "doctor", "insurance verification", "verify patient insurance", "patient insurance", "referral", "billing", "staff", "office task"],
        }

    def classify(self, command_text: str) -> DomainClassificationResult:
        text = command_text.lower()
        scores = {
            domain: sum(1 for keyword in keywords if keyword in text)
            for domain, keywords in self.keyword_scores.items()
        }

        non_general_scores = {domain: score for domain, score in scores.items() if domain != "general"}
        if "follow up" in text and max(non_general_scores.values(), default=0) == 0:
            return DomainClassificationResult(
                domain=None,
                confidence=0.5,
                needs_clarification=True,
                clarification=ClarificationRequest(
                    question="Please clarify which domain this follow-up belongs to.",
                    missing_fields=["domain"],
                ),
            )

        doctors_office_cues = [
            "patient",
            "clinic",
            "doctor",
            "medical",
            "insurance verification",
            "verify patient insurance",
            "patient insurance",
            "referral",
            "billing",
            "staff",
            "office task",
        ]
        if scores.get("doctors_office", 0) > 0 and any(cue in text for cue in doctors_office_cues):
            confidence = min(0.99, 0.7 + 0.08 * scores["doctors_office"])
            return DomainClassificationResult(
                domain="doctors_office",
                confidence=confidence,
                needs_clarification=False,
                clarification=None,
            )

        insurance_cues = [
            "policy",
            "renewal",
            "premium",
            "claim",
            "insurance",
            "coverage",
            "quote",
            "lead",
            "demo",
            "expiring customer",
            "expiring customers",
        ]
        if scores.get("insurance", 0) > 0 and any(cue in text for cue in insurance_cues):
            confidence = min(0.99, 0.7 + 0.08 * scores["insurance"])
            return DomainClassificationResult(
                domain="insurance",
                confidence=confidence,
                needs_clarification=False,
                clarification=None,
            )

        if (
            scores.get("general", 0) > 0
            and scores.get("insurance", 0) == 0
            and scores.get("construction", 0) == 0
            and scores.get("doctors_office", 0) == 0
            and scores.get("calendar", 0) == 0
            and scores.get("email", 0) == 0
            and scores.get("notes", 0) == 0
        ):
            confidence = min(0.99, 0.6 + 0.1 * scores["general"])
            return DomainClassificationResult(
                domain="general",
                confidence=confidence,
                needs_clarification=False,
                clarification=None,
            )

        ranked = sorted(scores.items(), key=lambda kv: kv[1], reverse=True)
        top_domain, top_score = ranked[0]
        second_score = ranked[1][1] if len(ranked) > 1 else 0

        # Ambiguity logic: no match or multiple matches triggers clarification
        if top_score == 0:
            return DomainClassificationResult(
                domain=None,
                confidence=0.0,
                needs_clarification=True,
                clarification=ClarificationRequest(
                    question="Could not determine the domain. Please clarify your intent.",
                    missing_fields=["domain"],
                ),
            )
        if top_score == second_score:
            return DomainClassificationResult(
                domain=None,
                confidence=0.5,
                needs_clarification=True,
                clarification=ClarificationRequest(
                    question="Your request matches multiple domains. Please clarify.",
                    missing_fields=["domain"],
                ),
            )
        confidence = min(0.99, 0.6 + 0.1 * top_score)
        return DomainClassificationResult(
            domain=top_domain,
            confidence=confidence,
            needs_clarification=False,
            clarification=None,
        )
