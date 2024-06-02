import streamlit as st
import requests

def get_response(user_query, chat_history):
    url = "http://localhost:8000/ask"
    data = {
        "question": user_query,
        "chat_history": str(chat_history)
        }
    headers = {"Content-Type": "application/json"}
    response = requests.post(url, json=data, headers=headers)
    if response.status_code == 200:
        decoded_message = response.json().get("reply")
        return decoded_message            
    else:
        return "Error: " + str(response.status_code)

st.set_page_config(page_title="AI_Fresh Assistat")
st.title("🧑‍💻 AI Network Engineer")

if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

print(st.session_state.chat_history)

for message in st.session_state.chat_history:
    if message.get("type") == "AI":
        with st.chat_message("AI"):
            st.write(message.get("content"))
    elif message.get("type") == "Human":
        with st.chat_message("Human"):
            st.write(message.get("content"))

user_query = st.chat_input("Type your message here...")
if user_query:
    st.session_state.chat_history.append(({"type": "Human", "content": user_query}))
    with st.chat_message("Human"):
        st.markdown(user_query)
    response = get_response(user_query, st.session_state.chat_history)
    with st.chat_message("AI"):
        print(response)
        st.write(response)
        st.session_state.chat_history.append(({"type": "AI", "content": response}))
