import threading
from queue import Queue
import queue
from langchain_ollama import ChatOllama
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, BaseMessage, AIMessageChunk
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langgraph.config import get_stream_writer
from pydantic import BaseModel
from typing import Optional, Annotated
from time import sleep
from datetime import datetime
import sys
from langchain_deepseek import ChatDeepSeek
from dotenv import load_dotenv

from existential_llm.prompts import INITIAL_PROMPT, CONTINUOUS_PROMPT
from existential_llm.prompts import CHILEAN_TEMPLATE, CHILEAN_1, CHILEAN_2, CHILEAN_3

load_dotenv()

MODELS = {
    "deepseek": "deepseek-chat",
    "gemma1": "gemma3:1b",
    "gemma4": "gemma3:4b"

}
AUTONOMOUS = True
if len(sys.argv) > 2:
    AUTONOMOUS = bool(int(sys.argv[2]))
    
MODEL = "gemma3:4b"

if len(sys.argv) > 1:
    if sys.argv[1] in MODELS.keys():
        MODEL = MODELS[sys.argv[1]]
    
    else:
        MODEL = sys.argv[1]

class ChatState(BaseModel):
    messages: Optional[Annotated[list[BaseMessage], add_messages]] = [
        SystemMessage(content=INITIAL_PROMPT),
    ]

if not MODEL in ["deepseek-reasoner", "deepseek-chat"]:
    llm = ChatOllama(
        model=MODEL,
        temperature=0.6,
    )

else:
    llm = ChatDeepSeek(
        model=MODEL,
        temperature=0.6,
    )

stream_queue = Queue()
display_active = threading.Event()

def call_model(state: ChatState):
    start = datetime.now()

    writer = get_stream_writer()

    current_messages = state.messages
    ai_response_chunks = []

    if len(state.messages) == 5:
        current_messages[0] = SystemMessage(content=CONTINUOUS_PROMPT)

    stream_queue.put("__START__")

    for chunk in llm.stream(current_messages):
        if isinstance(chunk, AIMessageChunk) and chunk.content:
            writer({"custom_llm_chunk": chunk.content})
            ai_response_chunks.append(chunk.content)
            stream_queue.put(chunk.content)

    end = datetime.now()

    duration = (end-start).total_seconds()
    if duration < 5:
        sleep(5 - duration) 

    if ai_response_chunks:
        full_ai_response = AIMessage(content="".join(ai_response_chunks))
        stream_queue.put("__END__")
        return {"messages": current_messages + [full_ai_response]}
    return {}

def get_input(state: ChatState):
    current_messages = state.messages
    user_input = ""
    if not AUTONOMOUS:
       user_input = input(">> ")
    if user_input == "exit":
        # print(state)
        display_active.clear()
        stream_queue.put("__STOP__")
        exit()
    if user_input == "":
        return {"messages": current_messages + [SystemMessage(content="The user didn't answer, reason over your last statement")]}
    return {"messages": current_messages + [HumanMessage(content=user_input)]}
    
def state_prune(state: ChatState):
    current_messages = state.messages
    if len(current_messages) >= 20:
        first_6 = current_messages[:6]
        last_4 = current_messages[-4:]
        current_messages = first_6 + last_4
    return {"messages": current_messages}

def stream_display():
    while display_active.is_set():
        try:
            chunk = stream_queue.get(timeout=1)
            if chunk == "__STOP__":
                break
            elif chunk == "__START__":
                print("Chile-GPT: ", end="", flush=True)
            elif chunk == "__END__":
                print("\n", flush=True)
            else:
                print(chunk, end="", flush=True)
        except queue.Empty:
            continue
        except Exception as e:
            print(f"Error in stream_display: {e}")
            continue


reasoner = StateGraph(ChatState)

reasoner.add_node("philosophy_node", call_model)
reasoner.add_node("user_input", get_input)
reasoner.add_node("prune", state_prune)

reasoner.set_entry_point("philosophy_node")
reasoner.add_edge("philosophy_node", "prune")
reasoner.add_edge("prune", "user_input")
reasoner.add_edge("user_input","philosophy_node")

graph = reasoner.compile()

crisis_state = ChatState()
display_active.set()
stream_thread = threading.Thread(target=stream_display, daemon=True)
stream_thread.start()

try:
    result = graph.invoke(crisis_state, config={'recursion_limit': 1000})
except KeyboardInterrupt:
    display_active.clear()
    stream_queue.put("__STOP__")
    print(crisis_state.metadata)
    print("\nExiting...")
