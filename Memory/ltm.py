from langgraph.graph import StateGraph, START, END ,MessagesState
from typing import TypedDict, Annotated
from langchain_core.messages import BaseMessage, HumanMessage
from langchain_openai import ChatOpenAI
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph.message import add_messages
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from dotenv import load_dotenv

load_dotenv()

base_url = "http://103.42.50.41:443/api1"
api_key = f'{("sk-Qp7f5gy8WRqJW2KRbhOrZVD280JJWdSo")}'

model = ChatOpenAI(model = 'Qwen/Qwen2.5-7B-Instruct-AWQ',
 openai_api_base=base_url, openai_api_key=api_key, streaming=False)

store= InMemorySaver()

# Creating a namespace
namespace = ("users" , "u1")

# Put method
store.put(namespace ,"1" ,{"data": "Users like movies"})

# Retriveing
store.get(namespace, "1")
# retrieving all the memories
items = store.seacrh(namespace)
for item in items :
    print(item.value)

# for semantic seacrh we need to have embedding model in the store creation
embeddings = OpenAIEmbeddings(model="text-embedding-3-small")
emb_vector_store = InMemorySaver(index={'embed':embeddings , "dims":1356})

