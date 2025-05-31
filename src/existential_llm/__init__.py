from langchain_ollama import ChatOllama
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, BaseMessage
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langgraph.config import get_stream_writer
from pydantic import BaseModel
from typing import Optional, Annotated

from existential_llm.prompts import INITIAL_PROMPT


class ChatState(BaseModel)
    base_prompt: List[SystemMessage]
    messages: Annotated[List[BaseMessage], add_messages]

llm = ChatOllama(
    model="gemma3:4b-it-qat",
    temperature=0.7,
)

def call_model(state: ChatState):
    writer = get_stream_writer()

    current_messages = state.messages
    ai_response_chunks = []

    full_response_content = ""
    for chunk in llm.stream(state.base_prompt + current_messages):
        if isinstance(chunk, AIMessageChunk) and chunk.content:
            writer("custom_llm_chunk": chunk.content)
            ai_response_chunks.append(chunk.content)

    if ai_response_chunks:
        full_ai_response = AIMessage(content="".join(ai_response_chunks))
        return {"messages": [full_ai_response]}
    return {}

reasoner = StateGraph(ChatState)
reasoner.add_node("philosophy_node", call_model)

reasoner.set_entry_point("philosophy_node")
reasoner.add_edge("philosophy_node", "philosophy_node")

app = workflow.compile()

initial_input = ChatState(
    base_prompt = INITIAL_PROMPT
    messages = []
)


