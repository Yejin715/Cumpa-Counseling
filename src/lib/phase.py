from typing import Literal
from pydantic import BaseModel, create_model, Field


class Phase:
    def __init__(
        self,
        name: str,
        goal: str,
        topic_list: list[str],
        instruction: str,
        router_list: list[dict[str, str]],
    ):
        self.name = name
        self.goal = goal
        self.topic_list = topic_list
        self.instruction = instruction
        self.router_list = router_list

    def getInfo(self) -> dict:

        return {
            "name": self.name,
            "goal": self.goal,
            "topic_list": self.topic_list,
            "instruction": self.instruction,
        }

    def getResponseFormat(self) -> BaseModel:
        options = [router["next_phase"] for router in self.router_list]
        explanations = "\n".join(
            [
                f"{router["next_phase"]}: {router["criteria"]}"
                for router in self.router_list
            ]
        )

        format = create_model(
            "ResponseFormat",
            action=(
                str,
                Field(
                    description="An action for generating current response. You should select one action from the available actions."
                ),
            ),
            action_reason=(
                str,
                Field(
                    description="A detailed reason for the action selection. If you need further clarification on the action, you can add it here."
                ),
            ),
            next_phase=(
                Literal[tuple(options)] | None,
                Field(
                    description=f"Select next phase to go if the main goal of the phase is achieved. If not, just remain it None. Explanation for each option is shown below.\n\n{explanations}"
                ),
            ),
            next_phase_reason=(
                str | None,
                Field(
                    description="A detailed reason for the next phase selection. If you didn't select the next phase, just remain it None."
                ),
            ),
        )

        return format

    def getName(self) -> str:

        return self.name
