from langchain_core.messages import HumanMessage
from langchain_ollama import ChatOllama, OllamaEmbeddings
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import MessagesState

TEXT_MODEL = "qwen2.5:7b"
EMB_MODEL = "bge-m3:latest"


class ChatState(MessagesState):
    pass


model = ChatOllama(model=TEXT_MODEL)
emb_model = OllamaEmbeddings(model=EMB_MODEL)


def chat_node(state: ChatState) -> ChatState:

    messages = state["messages"]

    response = model.invoke(messages)

    return {"messages": response}


graph = StateGraph(MessagesState)

graph.add_node("chat_node", chat_node)
graph.add_edge(START, "chat_node")
graph.add_edge("chat_node", END)

checkpointer = InMemorySaver()

chatbot = graph.compile(checkpointer=checkpointer)
config = {"configurable": {"thread_id": "1"}}

while True:
    user_input = input("You: ")
    if user_input.strip().lower() in ["exit", "bye", "quit"]:
        break

    result = chatbot.invoke({"messages": [HumanMessage(content=user_input)]}, config)
    print("Bot:", result["messages"][-1].content)
