from langgraph.graph import StateGraph, START, END
from typing import TypedDict, Annotated
from langchain_core.messages import BaseMessage, HumanMessage
from langchain_openai import ChatOpenAI
from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode , tools_condition
from langchain_community.tools import DuckDuckGoSearchRun
from langchain_core.tools import tool

from dotenv import load_dotenv
import sqlite3

load_dotenv()

base_url = "http://103.42.50.41:443/api1"
api_key = f'{("sk-Qp7f5gy8WRqJW2KRbhOrZVD280JJWdSo")}'

model = ChatOpenAI(model = 'Qwen/Qwen2.5-7B-Instruct-AWQ',
 openai_api_base=base_url, openai_api_key=api_key, streaming=False)

#Tools
search_tool = DuckDuckGoSearchRun(region="us-en")

@tool
def calculator(first_num: float, second_num: float, operation: str) -> dict:
    # Definitely need to add this so that llm can understand when to use this 
    """
    Perform a basic arithmetic operation on two numbers.
    Supported operations: add, sub, mul, div
    """
    try:
        if operation == "add":
            result = first_num + second_num
        elif operation == "sub":
            result = first_num - second_num
        elif operation == "mul":
            result = first_num * second_num
        elif operation == "div":
            if second_num == 0:
                return {"error": "Division by zero is not allowed"}
            result = first_num / second_num
        else:
            return {"error": f"Unsupported operation '{operation}'"}
        
        return {"first_num": first_num, "second_num": second_num, "operation": operation, "result": result}
    except Exception as e:
        return {"error": str(e)}

@tool
def get_stock_price(symbol: str) -> dict:
    """
    Fetch latest stock price for a given symbol (e.g. 'AAPL', 'TSLA') 
    using Alpha Vantage with API key in the URL.
    """
    url = f"https://www.alphavantage.co/query?function=GLOBAL_QUOTE&symbol={symbol}&apikey=FII1JJLG16NX8ZK7"
    r = requests.get(url)
    return r.json()

tools = [search_tool,get_stock_price,calculator]

model_with_tools = model.bind_tools(tools)

tool_node = ToolNode(tools)

class ChatState(TypedDict):
    messages: Annotated[list[BaseMessage], add_messages]

def chat_node(state: ChatState):
    messages = state['messages']
    response = model_with_tools.invoke(messages)
    return {"messages": [response]}

#Need to create database and connect it to the checkpointer 
connection = sqlite3.connect(database='chatbot.db',check_same_thread= False)
# sqlite works on only single thread Soo check_same_thread = False is important so that we can use this database
# across diff threads
# Checkpointer
checkpointer = SqliteSaver(connection)

graph = StateGraph(ChatState)
graph.add_node("chat_node", chat_node)
graph.add_node("tools",tool_node)
graph.add_edge(START, "chat_node")
graph.add_conditional_edges("chat_node",tools_condition)
graph.add_edge('tools', 'chat_node')

#graph.add_edge("chat_node", END)

CONFIG = {"configurable": {"thread_id": "thread_2"}}
workflow = graph.compile(checkpointer=checkpointer)

# print(workflow)

# response = workflow.invoke(
#    {"messages": [HumanMessage("What is 2+4")]},
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
    



