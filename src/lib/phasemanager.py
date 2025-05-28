from .phase import Phase
from ..message_event import MessageBroker, MessageType
from ..async_event import AsyncBroker, AsyncMessageType


class PhaseManager:
    def __init__(self, name: str, description: str):
        self.phase_dict = {}  # : dict[str, Phase]
        self.start_phase = None  # : Phase
        self.current_phase = None  # : Phase
        self.topics = {}  # : dict[str, str]
        self.bot_name = name
        self.bot_desc = description

    def addNewPhase(self, phase: Phase) -> str:
        if phase.name in self.phase_dict:
            raise ValueError(f"Phase named {phase.name} is already added")
        else:
            self.phase_dict[phase.name] = phase

        return f"Phase {phase.name} added successfully."

    def setStartPhase(self, name: str) -> str:
        if name in self.phase_dict:
            self.start_phase = self.phase_dict[name]
            return f"Phase {name} is set to start phase."
        else:
            raise ValueError(f"Phase named {name} is not added.")

    def getStartPhase(self) -> Phase:

        return self.start_phase

    def setCurrPhase(self, name: str) -> str:
        if name in self.phase_dict:
            self.current_phase = self.phase_dict[name]
            return f"Phase {name} is set to current phase."
        else:
            raise ValueError(f"Phase named {name} is not added.")

    def getCurrPhase(self) -> Phase:

        return self.current_phase
    
    def goNextPhase(self, next_phase: str | None) -> bool:
        if next_phase == None:
            # print(f"There is no phase result, keep track on current phase.")
            pass
        else:
            if next_phase in self.phase_dict:
                self.current_phase = self.phase_dict[next_phase]
                
                if next_phase == "FINISH":
                    print("Starting a new conversation. Initializing Greeting phase.")
                    self.setStartPhase("Greeting")  # 'Greeting'으로 돌아가서 대화 초기화
                    self.setCurrPhase("Greeting")  # 새로운 대화 흐름 시작
                    AsyncBroker().emit(("wait_chat_finish", None))
                return True
            else:
                print(f"There is no such phase named '{next_phase}'")

        return False

    def updateTopics(self, topics: dict[str, str]) -> str:
        self.topics = topics
        names = list(topics.keys())

        return f"Topics {names} are updated to the phase manager."

    def getTopics(self) -> dict[str, str]:
        available_topics = {}
        for topic_name in self.current_phase.topic_list:
            available_topics[topic_name] = self.topics[topic_name]

        return available_topics

    def getBotInfo(self) -> tuple[str, str]:

        return self.bot_name, self.bot_desc
