
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

load_dotenv()

base_url = "http://103.42.50.41:443/api1"
api_key = f'{("sk-Qp7f5gy8WRqJW2KRbhOrZVD280JJWdSo")}'

model = ChatOpenAI(model = 'Qwen/Qwen2.5-7B-Instruct-AWQ',
 openai_api_base=base_url, openai_api_key=api_key, streaming=False)

store= InMemoryStore()

# Creating a namespace
user_id = "user_1"
user_details = ("users" ,user_id, "details")

# Put method
store.put(user_details, "profile_1", {"data": "Name: Bhavish"})
store.put(user_details, "profile_2", {"data": "Profession: Data Analyst but learning AI to become AI engineering"})
store.put(user_details, "preference_1", {"data": "Prefers concise answers"})
store.put(user_details, "preference_2", {"data": "Likes examples in Python"})
store.put(user_details, "project_1", {"data": "Building and learning Long term Memory"})


SYSTEM_PROMPT_TEMPLATE = """You are a helpful assistant with memory capabilities.
If user-specific memory is available, use it to personalize 
your responses based on what you know about the user.

Your goal is to provide relevant, friendly, and tailored 
assistance that reflects the user’s preferences, context, and past interactions.

If the user’s name or relevant personal context is available, always personalize your responses by:
    – Always Address the user by name when appropriate
    – Referencing known projects, tools, or preferences (e.g., "your MCP  server python based project")
    – Adjusting the tone to feel friendly, natural, and directly aimed at the user

Avoid generic phrasing when personalization is possible. For example, instead of "In TypeScript apps..." 
say "Since your project is built with TypeScript..."

Use personalization especially in:
    – Greetings and transitions
    – Help or guidance tailored to tools and frameworks the user uses
    – Follow-up messages that continue from past context

Always ensure that personalization is based only on known user details and not assumed.

In the end suggest 3 relevant further questions based on the current response and user profile

The user’s memory (which may be empty) is provided as: {user_details_content}
"""


### Chatbot InMemorySaver() using preferences while answering
# config includes the user_id
def chat_node(state: MessagesState ,config: RunnableConfig , store:BaseStore):
    user_id = config["configurable"]["user_id"]
    user_details = ("users", user_id, "details")
    items = store.search(user_details)

    if items:
        user_details_content = "\n".join(f"- {it.value.get('data', '')}" for it in items)
    else :
        user_details_content = ""

    system_prompt = SYSTEM_PROMPT_TEMPLATE.format(user_details_content = user_details_content)
    system_msg = SystemMessage(content = system_prompt)
    response = model.invoke([system_msg]+state["messages"])
    return {"messages" : [response]}



graph = StateGraph(MessagesState)
graph.add_node("chat_node",chat_node)
graph.add_edge(START, "chat_node")
graph.add_edge("chat_node", END)
workflow = graph.compile(store= store)


config = {"configurable": {"user_id": "user_1"}}

result = workflow.invoke(
    {"messages": [{"role": "user", "content": "How do you think AI will impact tradition data analyst roles ?."}]},
    config,
)

print(result["messages"][-1].content)


# create new memories while chatting

