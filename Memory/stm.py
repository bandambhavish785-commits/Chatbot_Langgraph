from langgraph.graph import StateGraph, START, END ,MessagesState
from typing import TypedDict, Annotated
from langchain_core.messages import BaseMessage, HumanMessage
from langchain_openai import ChatOpenAI
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph.message import add_messages
from dotenv import load_dotenv

load_dotenv()

base_url = "http://103.42.50.41:443/api1"
api_key = f'{("sk-Qp7f5gy8WRqJW2KRbhOrZVD280JJWdSo")}'

model = ChatOpenAI(model = 'Qwen/Qwen2.5-7B-Instruct-AWQ',
 openai_api_base=base_url, openai_api_key=api_key, streaming=False)

def call_mode(state: MessagesState):
    response = model.invoke(state['messages'])
    return {"messages": response}

from langgraph.checkpoint.memory import InMemorySaver

graph = StateGraph(MessagesState)
graph.add_node("call_mode",call_mode)
graph.add_edge(START,"call_mode")
graph.add_edge("call_mode",END)

checkpointer = InMemorySaver()
workflow = graph.compile(checkpointer=checkpointer)
config = {"configurable":{"thread_id":"thread_1"}}
          
print(workflow.invoke({"messages":[{"role":"user" , "content": "Hi My name is bhavish"}]}, config = config))
print(workflow.invoke({"messages":[{"role":"user" , "content": "What is my name"}]}, config = config))

# Trimming
from langchain_core.messages.utils import trim_messages, count_tokens_approximately

max_tokens = 150

def call_mode(state: MessagesState):
    # trimming messages and then sharing it with the model
    messages = trim_messages(
        state["messages"],
        strategy="last",
        token_counter=count_tokens_approximately,
        max_tokens=max_tokens
    )
    response = model.invoke(state['messages'])
    return {"messages": response}


