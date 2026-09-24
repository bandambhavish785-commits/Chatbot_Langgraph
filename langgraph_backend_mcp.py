from langgraph.graph import StateGraph, START, END
from typing import TypedDict, Annotated
from langchain_core.messages import BaseMessage, HumanMessage
from langchain_openai import ChatOpenAI
from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode , tools_condition
from langchain_community.tools import DuckDuckGoSearchRun
from langchain_core.tools import tool
from langchain_mcp_adapters.client import MultiServerMCPClient
import asyncio

from dotenv import load_dotenv
import sqlite3

load_dotenv()

base_url = "http://103.42.50.41:443/api1"
api_key = f'{("sk-Qp7f5gy8WRqJW2KRbhOrZVD280JJWdSo")}'

model = ChatOpenAI(model = 'Qwen/Qwen2.5-7B-Instruct-AWQ',
 openai_api_base=base_url, openai_api_key=api_key, streaming=False)

#Tools
search_tool = DuckDuckGoSearchRun(region="us-en")

client = MultiServerMCPClient(
    {
        "arith": {
            "transport": "stdio", # local server
            "command": "python3",          
            "args": ["file_path"],
        },
        "expense": {
            "transport": "streamable_http",  # if this fails, try "sse"
            "url": "https://splendid-gold-dingo.fastmcp.app/mcp"
        }
    }
)

# @tool
# def calculator(first_num: float, second_num: float, operation: str) -> dict:
#     # Definitely need to add this so that llm can understand when to use this 
#     """
#     Perform a basic arithmetic operation on two numbers.
#     Supported operations: add, sub, mul, div
#     """
#     try:
#         if operation == "add":
#             result = first_num + second_num
#         elif operation == "sub":
#             result = first_num - second_num
#         elif operation == "mul":
#             result = first_num * second_num
#         elif operation == "div":
#             if second_num == 0:
#                 return {"error": "Division by zero is not allowed"}
#             result = first_num / second_num
#         else:
#             return {"error": f"Unsupported operation '{operation}'"}
        
#         return {"first_num": first_num, "second_num": second_num, "operation": operation, "result": result}
#     except Exception as e:
#         return {"error": str(e)}

@tool
def get_stock_price(symbol: str) -> dict:
    """
    Fetch latest stock price for a given symbol (e.g. 'AAPL', 'TSLA') 
    using Alpha Vantage with API key in the URL.
    """
    url = f"https://www.alphavantage.co/query?function=GLOBAL_QUOTE&symbol={symbol}&apikey=FII1JJLG16NX8ZK7"
    r = requests.get(url)
    return r.json()

def load_mcp_tools() -> List[BaseTool]:
    try:
        return run_async(client.get_tools())
    except Exception:
        return []

mcp_tools = load_mcp_tools()
tools = [search_tool,get_stock_price,*mcp_tools]

model_with_tools = model.bind_tools(tools) if tools else llm 

tool_node = ToolNode(tools)

class ChatState(TypedDict):
    messages: Annotated[list[BaseMessage], add_messages]


async def build_graph():

    # tools = await client.get_tools()
    # print(tools)
    async def chat_node(state: ChatState):
        messages = state['messages']
        response = await  model_with_tools.ainvoke(messages)
        return {"messages": [response]}

    #Need to create database and connect it to the checkpointer 
    #connection = sqlite3.connect(database='chatbot.db',check_same_thread= False)
    async def __init__checkpointer():
        conn = await aiosqlite.connect(database = 'chatbot.db')
        return AsyncSqliteSaver(conn)
    checkpointer = run_async(__init__checkpointer())
    # sqlite works on only single thread Soo check_same_thread = False is important so that we can use this database
    # across diff threads
    # Checkpointer
    # checkpointer = SqliteSaver(connection)

    graph = StateGraph(ChatState)
    graph.add_node("chat_node", chat_node)
    graph.add_node("tools",tool_node)
    graph.add_edge(START, "chat_node")
    graph.add_conditional_edges("chat_node",tools_condition)
    graph.add_edge('tools', 'chat_node')

    #graph.add_edge("chat_node", END)

    CONFIG = {"configurable": {"thread_id": "thread_2"}}
    #workflow = graph.compile(checkpointer=checkpointer)
    workflow=graph.compile()
    return workflow


async def main():
    workflow= build_graph()
    CONFIG = {"configurable": {"thread_id": "thread_2"}}
    # print(workflow)
    response = await workflow.ainvoke(
    {"messages": [HumanMessage("What is 2+4")]},
    config=CONFIG
    )
    print(response)
    #print(workflow.get_state(CONFIG))


if __name__=='__main__':
    asyncio.run(main())


# # print(response)
# for message_chunk , metadata in workflow.stream(
#     {'messages': [HumanMessage("Tell me about Prabhas")]},
#     config = {'configurable': {'thread_id': 'thread_2'}},
#     stream_mode = "messages"):
#     if message_chunk.content:
#         print(message_chunk.content,end=" ",flush= True)


# def all_threads():
#     all_threads= set()
#     for checkpoint in checkpointer.list(None):
#         all_threads.add(checkpoint.config['configurable']['thread_id'])
#     return list(all_threads)
    



