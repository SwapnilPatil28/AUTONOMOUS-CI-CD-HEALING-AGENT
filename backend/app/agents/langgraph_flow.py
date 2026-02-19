from __future__ import annotations

from typing import TypedDict

from langgraph.graph import END, StateGraph

from app.agents.pipeline import FailureClassifierAgent, PatchGeneratorAgent, VerifierAgent


class AgentState(TypedDict):
    raw_failures: list[dict]
    classified_failures: list
    fix_plans: list
    fix_results: list


class LangGraphOrchestrator:
    def __init__(self) -> None:
        self.classifier = FailureClassifierAgent()
        self.patcher = PatchGeneratorAgent()
        self.verifier = VerifierAgent()
        self.graph = self._build_graph()

    def _build_graph(self):
        workflow = StateGraph(AgentState)
        workflow.add_node("classify", self._classify)
        workflow.add_node("generate", self._generate)
        workflow.add_node("verify", self._verify)

        workflow.set_entry_point("classify")
        workflow.add_edge("classify", "generate")
        workflow.add_edge("generate", "verify")
        workflow.add_edge("verify", END)

        return workflow.compile()

    def _classify(self, state: AgentState):
        classified = self.classifier.classify(state["raw_failures"])
        return {"classified_failures": classified}

    def _generate(self, state: AgentState):
        plans = [self.patcher.generate(item) for item in state["classified_failures"]]
        return {"fix_plans": plans}

    def _verify(self, state: AgentState):
        results = []
        for plan in state["fix_plans"]:
            results.append(
                {
                    "plan": plan,
                    "local_ok": self.verifier.local_verify(plan),
                }
            )
        return {"fix_results": results}

    def run(self, raw_failures: list[dict]) -> AgentState:
        initial: AgentState = {
            "raw_failures": raw_failures,
            "classified_failures": [],
            "fix_plans": [],
            "fix_results": [],
        }
        return self.graph.invoke(initial)
