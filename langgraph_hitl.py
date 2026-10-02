from langgraph.graph import StateGraph, START, END
from typing import TypedDict, Annotated
from langchain_core.messages import BaseMessage, HumanMessage , AIMessage
from langchain_openai import ChatOpenAI
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph.message import add_messages
from dotenv import load_dotenv
from langgraph.types import interrupt, Command

load_dotenv()

base_url = "http://103.42.50.41:443/api1"
api_key = f'{("sk-Qp7f5gy8WRqJW2KRbhOrZVD280JJWdSo")}'

model = ChatOpenAI(model = 'Qwen/Qwen2.5-7B-Instruct-AWQ',
 openai_api_base=base_url, openai_api_key=api_key, streaming=False)

class ChatState(TypedDict):
    messages: Annotated[list[BaseMessage], add_messages]

def chat_node(state: ChatState):
    decision = interrupt({
        "type":"approval",
        "reason":"Model is about to answer your question please verify the question and respond",
        "question": state['messages'][-1].content,
        "instruction":"Approve this question Yes /No ?"
    })

    if decision["approved"]== 'No':
        return {"messages": [AIMessage(content="Not Approved")]}
    
    else:
        response = model.invoke(state["messages"])
        return {"messages": [response]}

    # messages = state['messages']
    # response = model.invoke(messages)
    # return {"messages": [response]}

# Checkpointer
checkpointer = InMemorySaver()

graph = StateGraph(ChatState)
graph.add_node("chat_node", chat_node)
graph.add_edge(START, "chat_node")
graph.add_edge("chat_node", END)

CONFIG = {"configurable": {"thread_id": "thread_1"}}
workflow = graph.compile(checkpointer=checkpointer)

response = workflow.invoke(
   {"messages": [HumanMessage("Tell me about Prabhas")]},
   config=CONFIG
)

message = response['__interrupt__'][0].value 
user_input = "No"
final_response = workflow.invoke(
    Command(resume={"approved": user_input}),
    config = CONFIG
)
print(final_response)


# print(workflow.get_state(CONFIG))

# # print(response)
# for message_chunk , metadata in workflow.stream(
#     {'messages': [HumanMessage("Tell me about Prabhas")]},
#     config = {'configurable': {'thread_id': 'thread_2'}},
#     stream_mode = "messages"):
#     if message_chunk.content:
#         print(message_chunk.content,end=" ",flush= True)
    



