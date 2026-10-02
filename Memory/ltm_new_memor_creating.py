from langgraph.graph import StateGraph, START, END ,MessagesState
from typing import TypedDict, Annotated
from langchain_core.messages import BaseMessage, HumanMessage , SystemMessage
from langchain_openai import ChatOpenAI
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph.message import add_messages
from langchain_core.runnables import RunnableConfig
from langgraph.store.memory import InMemoryStore
from langgraph.store.base import BaseStore
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from dotenv import load_dotenv
from typing import List
import uuid
from pydantic import BaseModel , Field

load_dotenv()

base_url = "http://103.42.50.41:443/api1"
api_key = f'{("sk-Qp7f5gy8WRqJW2KRbhOrZVD280JJWdSo")}'

model = ChatOpenAI(model = 'Qwen/Qwen2.5-7B-Instruct-AWQ',
 openai_api_base=base_url, openai_api_key=api_key, streaming=False)

store = InMemoryStore()

class MemoryDecision(BaseModel):
    should_write: bool = Field(description= "whether to store any memory")
    memories : List[str] = Field(default_factory = list ,description = "Atomic user memories to store")

memory_extraction = model.with_structured_output(MemoryDecision)

def remember_only(state:MessagesState, config: RunnableConfig , store: BaseStore):
    user_id = config["configurable"]["user_id"]
    namespace = ("user", user_id , "details")
    last_msg = state["messages"][-1].content
    decision: MemoryDecision = memory_extraction.invoke(
        [
            SystemMessage(
                content=(
                    "Extract LONG-TERM memories from the user's message.\n"
                    "Only store stable, user-specific info (identity, preferences, ongoing projects).\n"
                    "Do NOT store transient info.\n"
                    "Return should_write=false if nothing is worth storing.\n"
                    "Each memory should be a short atomic sentence."
                )
            ),
            {"role": "user", "content": last_msg},
        ]
    )
    print(decision)
    if decision.should_write:
        for mem in decision.memories:
            store.put(namespace,str(uuid.uuid4()),{"data":mem})

    return {"messages": [{"role": "assistant", "content": "Noted."}]}

graph = StateGraph(MessagesState)
graph.add_node("remember_only",remember_only)
graph.add_edge(START , "remember_only")
graph.add_edge("remember_only", END)
workflow = graph.compile(store= store)


config = {"configurable": {"user_id": "u1"}}

res = workflow.invoke({"messages": [{"role": "user", "content": "Hi my name is Bhavish"}]},config)
print("Assistant:", res["messages"][-1].content)

res = workflow.invoke({"messages": [{"role": "user", "content": "I work as a data analyst and curious about AI"}]},config)
print("Assistant:", res["messages"][-1].content)

res = workflow.invoke({"messages": [{"role": "user", "content": "My favorite programming language is Python"}]},config)
print("Assistant:", res["messages"][-1].content)

items = store.search(("user", "u1", "details"))
print(items)
for item in items:
    print(item.value['data'])

# Need to solve redundancy in code

class MemoryItem(BaseModel):
    text : str =Field(description = "Action User memeory as a short sentence")
    is_new : bool = Field(description = "True if this memory is NEW and should be stored. False if duplicate/already known.")

class MemoryDecision_1(BaseModel):
    should_write: bool = Field(description= "whether to store any memory")
    memories : List[MemoryItem] = Field(default_factory = list ,description = "Atomic user memories to store")

memory_extraction_2 = model.with_structured_output(MemoryDecision)

MEMORY_PROMPT = """You are responsible for updating and maintaining accurate user memory.

CURRENT USER DETAILS (existing memories):
{user_details_content}

TASK:
- Review the user's latest message.
- Extract user-specific info worth storing long-term (identity, stable preferences, ongoing projects/goals).
- For each extracted item, set is_new=true ONLY if it adds NEW information compared to CURRENT USER DETAILS.
- If it is basically the same meaning as something already present, set is_new=false.
- Keep each memory as a short atomic sentence.
- No speculation; only facts stated by the user.
- If there is nothing memory-worthy, return an empty list.
"""

def remember_only_2(state:MessagesState, config: RunnableConfig , store: BaseStore):

    user_id = config["configurable"]["user_id"]

    namespace = ("user", user_id, "details")

    # A) Load existing memories
    existing_items = store.search(namespace)
    existing_texts = [it.value.get("data", "") for it in existing_items if it.value.get("data")]
    user_details_content = "\n".join(f"- {t}" for t in existing_texts) if existing_texts else "(empty)"

    # B) Latest user message
    last_text = state["messages"][-1]

    # C) LLM extracts memories + marks new vs duplicate
    decision: MemoryDecision = memory_extraction_2.invoke(
        [
            SystemMessage(content=MEMORY_PROMPT.format(user_details_content=user_details_content)),
            {"role": "user", "content": f"USER MESSAGE:\n{last_text}"},
        ]
    )

    # D) Store ONLY new memories
    if decision.should_write:
        for mem in decision.memories:
            if mem.is_new:
                store.put(namespace, str(uuid.uuid4()), {"data": mem.text})

    return {"messages": [{"role": "assistant", "content": "Noted."}]}

graph = StateGraph(MessagesState)
graph.add_node("remember_only_2",remember_only_2)
graph.add_edge(START , "remember_only_2")
graph.add_edge("remember_only_2", END)
workflow = graph.compile(store= store)


config = {"configurable": {"user_id": "u1"}}

res = workflow.invoke({"messages": [{"role": "user", "content": "Hi my name is Bhavish"}]},config)
print("Assistant:", res["messages"][-1].content)

res = workflow.invoke({"messages": [{"role": "user", "content": "I work as a data analyst and curious about AI"}]},config)
print("Assistant:", res["messages"][-1].content)

res = workflow.invoke({"messages": [{"role": "user", "content": "My favorite programming language is Python"}]},config)
print("Assistant:", res["messages"][-1].content)

items = store.search(("user", "u1", "details"))
print(items)
for item in items:
    print(item.value['data'])




