import streamlit as st
from langgraph_backend_rag import workflow,  ingest_pdf, retrieve_all_threads,  thread_document_metadata
from langchain_core.messages import HumanMessage , AIMessage ,ToolMessage
import uuid 
import os

thread_ids=[]
# generating threadid utility functions
def generate_thread_id():
    thread_id = uuid.uuid4()
    st.session_state['chat_thread_ids'].append(thread_id)
    return thread_id

def reset_chat():
    thread_id = generate_thread_id()
    st.session_state['thread_id']= thread_id
    st.session_state['message_history']=[]

def load_coversations(thread_id):
    state = workflow.get_state(config = {'configurable': {'thread_id': thread_id}})
    return state.values.get('messages',[])

# st.session_state -> dict -> 
if 'message_history' not in st.session_state:
    st.session_state['message_history'] = []

if 'chat_thread_ids' not in st.session_state:
    st.session_state['chat_thread_ids']=[]

if 'thread_id' not in st.session_state:
    st.session_state['thread_id']= generate_thread_id()


CONFIG = {'configurable': {'thread_id': st.session_state['thread_id']}}


#side bar UI creation
st.sidebar.title('LangGraph Chatbot')
if st.sidebar.button('New Chat'):
    reset_chat()

st.sidebar.header('My Conversations')
for thread_id in st.session_state['chat_thread_ids']:
    messages = load_coversations(thread_id)
    if len(messages)>0:
        display = messages[0].content[:30]
    else:
        display = 'Ask here ...'
    if st.sidebar.button(display , key=thread_id):
        st.session_state['thread_id']= thread_id
        messages = load_coversations(thread_id)
        temp_messages =[]
        for message in messages:
            if isinstance(message , HumanMessage):
                role= 'user'
            else:
                role = 'assistant'
            temp_messages.append({'role':role,'content':message.content})
        st.session_state['message_history']= temp_messages
        st.rerun()
st.sidebar.title("LangGraph PDF Chatbot")


if "message_history" not in st.session_state:
    st.session_state["message_history"] = []

if "thread_id" not in st.session_state:
    st.session_state["thread_id"] = generate_thread_id()

if "chat_threads" not in st.session_state:
    st.session_state["chat_threads"] = retrieve_all_threads()

if "ingested_docs" not in st.session_state:
    st.session_state["ingested_docs"] = {}


thread_key = str(st.session_state["thread_id"])
thread_docs = st.session_state["ingested_docs"].setdefault(thread_key, {})
threads = st.session_state["chat_threads"][::-1]
selected_thread = None
st.sidebar.markdown(f"**Thread ID:** `{thread_key}`")

if st.sidebar.button("New Chat", use_container_width=True):
    reset_chat()
    st.rerun()

if thread_docs:
    latest_doc = list(thread_docs.values())[-1]
    st.sidebar.success(
        f"Using `{latest_doc.get('filename')}` "
        f"({latest_doc.get('chunks')} chunks from {latest_doc.get('documents')} pages)"
    )
else:
    st.sidebar.info("No PDF indexed yet.")

uploaded_pdf = st.sidebar.file_uploader("Upload a PDF for this chat", type=["pdf"])
if uploaded_pdf:
    if uploaded_pdf.name in thread_docs:
        st.sidebar.info(f"`{uploaded_pdf.name}` already processed for this chat.")
    else:
        with st.sidebar.status("Indexing PDF…", expanded=True) as status_box:
            summary = ingest_pdf(
                uploaded_pdf.getvalue(),
                thread_id=thread_key,
                filename=uploaded_pdf.name,
            )
            thread_docs[uploaded_pdf.name] = summary
            status_box.update(label="✅ PDF indexed", state="complete", expanded=False)

st.sidebar.subheader("Past conversations")
if not threads:
    st.sidebar.write("No past conversations yet.")
else:
    for thread_id in threads:
        if st.sidebar.button(str(thread_id), key=f"side-thread-{thread_id}"):
            selected_thread = thread_id

# loading the conversation history
for message in st.session_state['message_history']:
    with st.chat_message(message['role']):
        st.text(message['content'])

#{'role': 'user', 'content': 'Hi'}
#{'role': 'assistant', 'content': 'Hi=ello'}

user_input = st.chat_input('Type here')

if user_input:

    # first add the message to message_history
    st.session_state['message_history'].append({'role': 'user', 'content': user_input})
    with st.chat_message('user'):
        st.text(user_input)

    #ai_message = response['messages'][-1].content
    # first add the message to message_history
    # #st.session_state['message_history'].append({'role': 'assistant', 'content': ai_message})
    # with st.chat_message('assistant'):
    #     ai_message=st.write_stream(
    #        message_chunk.content for message_chunk , metadata in workflow.stream(
    #         {'messages': [HumanMessage(content=user_input)]},
    #          config = CONFIG,
    #         stream_mode = "messages"
    #     ))
    #     st.session_state['message_history'].append({'role': 'assistant', 'content': ai_message})

    # Assistant streaming block
    
    with st.chat_message("assistant"):
        # Use a mutable holder so the generator can set/modify it
        status_holder = {"box": None}

        def ai_only_stream():
            for message_chunk, metadata in workflow.stream(
                {"messages": [HumanMessage(content=user_input)]},
                config=CONFIG,
                stream_mode="messages",
            ):
                # Lazily create & update the SAME status container when any tool runs
                if isinstance(message_chunk, ToolMessage):
                    tool_name = getattr(message_chunk, "name", "tool")
                    if status_holder["box"] is None:
                        status_holder["box"] = st.status(
                            f"🔧 Using `{tool_name}` …", expanded=True
                        )
                    else:
                        status_holder["box"].update(
                            label=f"🔧 Using `{tool_name}` …",
                            state="running",
                            expanded=True,
                        )

                # Stream ONLY assistant tokens
                if isinstance(message_chunk, AIMessage):
                    yield message_chunk.content

        ai_message = st.write_stream(ai_only_stream())

        # Finalize only if a tool was actually used
        if status_holder["box"] is not None:
            status_holder["box"].update(
                label="✅ Tool finished", state="complete", expanded=False
            )

    # Save assistant message
    st.session_state["message_history"].append(
        {"role": "assistant", "content": ai_message}
    )
