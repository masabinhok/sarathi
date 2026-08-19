from langchain_core.messages import HumanMessage

from ioe.graph import chatbot

config = {"configurable": {"thread_id": "1"}}


def main() -> None:
    while True:
        user_input = input("You: ")
        if user_input.strip().lower() in ["exit", "bye", "quit"]:
            break

        result = chatbot.invoke({"messages": [HumanMessage(content=user_input)]}, config)
        print("Bot:", result["messages"][-1].content)


if __name__ == "__main__":
    main()
