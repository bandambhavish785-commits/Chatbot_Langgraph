import streamlit as st
from langgraph_backend_tools import workflow
from langchain_core.messages import HumanMessage , AIMessage ,ToolMessage
import uuid 

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
  
