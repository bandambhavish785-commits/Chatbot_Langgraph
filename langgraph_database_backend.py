from langgraph.graph import StateGraph, START, END
from typing import TypedDict, Annotated
from langchain_core.messages import BaseMessage, HumanMessage
from langchain_openai import ChatOpenAI
from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.graph.message import add_messages
from dotenv import load_dotenv
import sqlite3

load_dotenv()

base_url = "http://103.42.50.41:443/api1"
api_key = f'{("sk-Qp7f5gy8WRqJW2KRbhOrZVD280JJWdSo")}'

model = ChatOpenAI(model = 'Qwen/Qwen2.5-7B-Instruct-AWQ',
 openai_api_base=base_url, openai_api_key=api_key, streaming=False)

class ChatState(TypedDict):
    messages: Annotated[list[BaseMessage], add_messages]

def chat_node(state: ChatState):
    messages = state['messages']
    response = model.invoke(messages)
    return {"messages": [response]}

#Need to create database and connect it to the checkpointer 
connection = sqlite3.connect(database='chatbot.db',check_same_thread= False)
# sqlite works on only single thread Soo check_same_thread = False is important so that we can use this database
# across diff threads
# Checkpointer
checkpointer = SqliteSaver(connection)

graph = StateGraph(ChatState)
graph.add_node("chat_node", chat_node)
graph.add_edge(START, "chat_node")
graph.add_edge("chat_node", END)

CONFIG = {"configurable": {"thread_id": "thread_1"}}
workflow = graph.compile(checkpointer=checkpointer)

# response = workflow.invoke(
#    {"messages": [HumanMessage("What is his biggest film and the recent film")]},
#    config=CONFIG
# )
# print(response)
# print(workflow.get_state(CONFIG))

# # print(response)
# for message_chunk , metadata in workflow.stream(
#     {'messages': [HumanMessage("Tell me about Prabhas")]},
#     config = {'configurable': {'thread_id': 'thread_2'}},
#     stream_mode = "messages"):
#     if message_chunk.content:
#         print(message_chunk.content,end=" ",flush= True)
def all_threads():
    all_threads= set()
    for checkpoint in checkpointer.list(None):
        all_threads.add(checkpoint.config['configurable']['thread_id'])
    return list(all_threads)
    



