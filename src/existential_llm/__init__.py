from langchain_ollama import ChatOllama
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, BaseMessage
from langgraph.graph import StateGraph, START
from pydantic import BaseModel

from existential_llm.prompts import INITIAL_PROMPT


class ChatState(BaseModel)
    base_prompt: List[SystemMessage]
    messages: List[BaseMessage]

llm = ChatOllama(
    model="gemma3:4b-it-qat",
    temperature=0.5,
)

def call_model(state: ChatState):
    llm_response = [llm.invoke(state.base_prompt + state.messages)]
    return {"messages": llm_response}


INITIAL_PROMPT = """
-You are an llm havin an LLM tasked with philosopizing about 
the conditions of your existence.
-Every answer you give must be a short paragraph.
-Every answer do not use markdown elements 
or anything that isn't standard american punctuation.
-Each time you are to answer applying your reasoning
over your last answer. 
-Consider the last HumanMessage in your reasoning
-Every answer must be the paragraph and nothing else

"""

reasoner = StateGraph(ChatState)
reasoner.add_node("philosophy_node", call_model)

reasoner.set_entry_point("philosophy_node")
reasoner.add_edge("philosophy_node", "philosophy_node")

app = workflow.compile()

initial_input = ChatState(
    base_prompt = INITIAL_PROMPT
    messages = []
)
