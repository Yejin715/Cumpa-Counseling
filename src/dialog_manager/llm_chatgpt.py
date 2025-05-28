from pydantic import BaseModel, ValidationError
import yaml
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import asyncio

from ..lib.time_stamp import get_current_timestamp
from ..lib.loggable import Loggable
from ..lib.phasemanager import PhaseManager
from ..lib.phase import Phase
from ..lib.DB import initialize, addMessage, getHistory, reset, saveConversation
from ..graphics.chat_window import ChatWindow
from langchain_core.prompts import PromptTemplate
from langchain_openai import ChatOpenAI
from typing import Any

import threading
from ..async_event import AsyncBroker, AsyncMessageType
from .hugging_face_transformers_emotion import EmotionAnalyzer

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize DB
    initialize()

    # reset DB
    reset()

    yield


# Set FastAPI app
app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class routerData(BaseModel):
    criteria: str
    next_phase: str


class phaseData(BaseModel):
    name: str
    goal: str
    action_list: list[str]
    instruction: str
    router_list: list[routerData]


class actionData(BaseModel):
    action_name: str
    action_explanation: str


class chatbotSettingData(BaseModel):
    bot_name: str
    bot_desc: str
    start_phase: str
    finish_phases: list[str]
    phases: list[phaseData]
    actions: list[actionData]


class userInputData(BaseModel):
    input: str

# get setting data from yaml file
def getTestSettingData() -> chatbotSettingData:
    try:
        with open("./src/lib/LLM_Specification.yaml", "r", encoding="utf-8") as file:
            yaml_data = yaml.safe_load(file)

        data = chatbotSettingData.model_validate(yaml_data)

    except FileNotFoundError:
        print("file not found")

    except ValidationError as e:
        print(f"setting data validation failed: {e}")

    return data

# save chatbot setting for test
def saveTestSetting(data: chatbotSettingData) -> PhaseManager:
    phase_manager = PhaseManager(data.bot_name, data.bot_desc)

    for phase in data.phases:
        # print(f"{phase.name} adding...")
        dict_router_list = [router.model_dump() for router in phase.router_list]
        new_phase = Phase(
            phase.name,
            phase.goal,
            phase.action_list,
            phase.instruction,
            dict_router_list,
        )
        phase_manager.addNewPhase(new_phase)

    phase_manager.addNewPhase(Phase("FINISH", "", [], "", []))
    phase_manager.setStartPhase(data.start_phase)
    phase_manager.setCurrPhase(data.start_phase)
    # print(f"current phase: {data.start_phase}")
    # reset DB for new chatbot
    reset()
    PHASE_end_time = get_current_timestamp()
    addMessage("PHASE", data.start_phase, PHASE_end_time, PHASE_end_time)


    action_dict = {}
    for action in data.actions:
        action_dict[action.action_name] = action.action_explanation
    # print(phase_manager.updateTopics(action_dict))
    phase_manager.updateTopics(action_dict)

    return phase_manager

async def selectTopic(phase_manager: PhaseManager, conversation_history: str) -> Any:
    bot_name, bot_desc = phase_manager.getBotInfo()
    actions = phase_manager.getTopics()
    phase_info = phase_manager.getCurrPhase().getInfo()
    response_format = phase_manager.getCurrPhase().getResponseFormat()

    llm = ChatOpenAI(model="gpt-4o", temperature=1)
    llm = llm.with_structured_output(response_format)

    prompt_template = PromptTemplate.from_template(
        """
    [Task]
    You are an action selector of the {bot_name}, which is {bot_desc}. 
    Your role is to do two things with reference to the "Context".
    1. Decide whether the main goal of the current phase is achieved. And if it is achieved, select which phase to go next.
    2. Decide which action to use for the current conversation turn. You can only select one action from the available actions below.
    
    [Context]
    - current phase name: {phase_name}
    - current phase goal: {phase_goal}
    - available actions: {phase_actions}
    - current phase instruction: {phase_instruction}
    - conversation history: {conversation_history}
    """
    )

    chain = prompt_template | llm
    response = await chain.ainvoke(
        {
            "bot_name": bot_name,
            "bot_desc": bot_desc,
            "phase_name": phase_info["name"],
            "phase_goal": phase_info["goal"],
            "phase_actions": actions,
            "phase_instruction": phase_info["instruction"],
            "conversation_history": conversation_history,
        }
    )

    return response

async def generateResponse(
    phase_manager: PhaseManager,
    conversation_history: str,
    action: str,
    action_reason: str,
) -> str:
    bot_name, bot_desc = phase_manager.getBotInfo()
    phase_info = phase_manager.getCurrPhase().getInfo()
    
    llm = ChatOpenAI(model="gpt-4o", temperature=1)

    prompt_template = PromptTemplate.from_template(
        """
    [Task]
    You are a response generator of the {bot_name}, which is {bot_desc}.
    To achieve the "phase goal" within the total conversation, one "action" is selected for the current conversation turn.
    Your role is to make a chatbot response for this turn according to the "Context".
    You MUST ask or respond about one subject at a time.
    The response MUST be in KOREAN.
    
    [Context]
    - current phase name: {phase_name}
    - current phase goal: {phase_goal}
    - selected action: {action}
    - reason for the action selection: {action_reason}
    - conversation history: {conversation_history}
    """
    )

    chain = prompt_template | llm
    response = await chain.ainvoke(
        {
            "bot_name": bot_name,
            "bot_desc": bot_desc,
            "phase_name": phase_info["name"],
            "phase_goal": phase_info["goal"],
            "action": action,
            "action_reason": action_reason,
            "conversation_history": conversation_history + "\nCUMPAR: ",
        }
    )

    return response


async def executeChatbot(
    phase_manager: PhaseManager, conversation_history: str
) -> tuple[str, bool]:
    selector_response = await selectTopic(phase_manager, conversation_history)
    
    # next_phase_info = ""
    # if selector_response.next_phase:
    #     next_phase_info += f"\n- next phase name: {selector_response.next_phase}"
    #     next_phase_info += f"\n- next phase reason: {selector_response.next_phase_reason}"
        
    chatbot_response = await generateResponse(
        phase_manager,
        conversation_history,
        phase_manager.getTopics()[selector_response.action],
        selector_response.action_reason,
        # next_phase_info,
    )
    changed = phase_manager.goNextPhase(selector_response.next_phase)

    return chatbot_response.content, changed

class LLMChatManager(threading.Thread, Loggable):
    def __init__(self):
        threading.Thread.__init__(self)
        Loggable.__init__(self)
        self.set_tag("llm_chat")
        self.emotion_analyzer = EmotionAnalyzer()

        self.phase_manager = None
        self._loop = None
        self._input_queue = asyncio.Queue()
        self._cycle_time_queue = asyncio.Queue()
        self._stop_event = threading.Event()

        AsyncBroker().subscribe("chat_cycle_time", self._on_cycle_time)
        AsyncBroker().subscribe("chat_user_input", self._on_user_input)
        AsyncBroker().subscribe("wake_up", self._on_wake_up)
    
    async def _on_wake_up(self, _: tuple[str, None]):
        await self._handle_first_input()

    def _on_cycle_time(self, msg: dict):
        if self._loop and not self._loop.is_closed():
            asyncio.run_coroutine_threadsafe(self._cycle_time_queue.put(msg), self._loop)

    def _on_user_input(self, msg: dict):
        self.submit_input(msg)        

    def run(self):
        self._loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self._loop)
        self._loop.run_until_complete(self._start_chat_loop())

    def stop(self):
        self._stop_event.set()
        if self._loop:
            self._loop.call_soon_threadsafe(self._loop.stop)

    async def _start_chat_loop(self):
        initialize()
        # phase_manager 초기화
        data = getTestSettingData()
        self.phase_manager = saveTestSetting(data)
        await self._handle_first_input()

        print("[LLMChat] Started. Waiting for user input...")
        while not self._stop_event.is_set():
            try:
                cycle_time = await asyncio.wait_for(self._cycle_time_queue.get(), timeout=0.1)
                user_input = await asyncio.wait_for(self._input_queue.get(), timeout=0.1)
                await self._handle_cycle_time(cycle_time)
                await self._handle_user_input(user_input)
            except asyncio.TimeoutError:
                continue

    async def _handle_cycle_time(self, msg: dict):
        cycle_time_text, start_time, end_time = msg
        cycle_time_text = msg["content"]
        cycle_start_time = msg["start_time"]
        cycle_end_time = msg["end_time"]
        addMessage("MODE_TURN", cycle_time_text, cycle_start_time, cycle_end_time)


    async def _handle_first_input(self):
        response_start_time = get_current_timestamp()
        response, changed = await executeChatbot(self.phase_manager, getHistory())
        response_end_time = get_current_timestamp()
        addMessage("CUMPAR", response, response_start_time, response_end_time)
        if changed:
            PHASE_end_time = get_current_timestamp()
            addMessage("PHASE", self.phase_manager.getCurrPhase().getName(), PHASE_end_time, PHASE_end_time)

        print(f"[LLMChat] CUMPAR: {response}")
        AsyncBroker().emit(("chat_response", {"msg": response, "type": "text", "emotion": "중립"}))

    async def _handle_user_input(self, msg: dict):
        user_input = msg["content"]
        user_start_time = msg["start_time"]
        user_end_time = msg["end_time"]
        
        if ChatWindow.use_whisper:
            addMessage("USER_WHISPER", user_input, user_start_time, user_end_time)
        else:
            addMessage("USER_KEYBOARD", user_input, user_start_time, user_end_time)
        
        if user_input and self.emotion_analyzer:
            emotion_result = self.emotion_analyzer.analyze_emotion(user_input)
            self.log(f"Emotion analysis user_input: {user_input}")
            self.log(f"Emotion analysis result: {emotion_result}")

        response_start_time = get_current_timestamp()
        response, changed = await executeChatbot(self.phase_manager, getHistory())
        response_end_time = get_current_timestamp()
        addMessage("CUMPAR", response, response_start_time, response_end_time)
        if changed:
            PHASE_end_time = get_current_timestamp()
            addMessage("PHASE", self.phase_manager.getCurrPhase().getName(), PHASE_end_time, PHASE_end_time)

        print(f"[LLMChat] CUMPAR: {response}")
        AsyncBroker().emit(("chat_response", {"msg": response, "type": "text", "emotion": emotion_result}))

    def submit_input(self, msg: dict):
        if self._loop and not self._loop.is_closed():
            asyncio.run_coroutine_threadsafe(self._input_queue.put(msg), self._loop)
