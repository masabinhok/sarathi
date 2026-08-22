"""A terminal REPL against the same graph the API serves, for poking at answers."""

import asyncio

from langchain_core.messages import HumanMessage

from ioe.graph import get_chatbot

config = {"configurable": {"thread_id": "cli"}}


async def run() -> None:
    # Async because the checkpointer is: conversations are written to SQLite, and this
    # shares that store with the API rather than keeping a second one.
    chatbot = await get_chatbot()
    while True:
        user_input = input("You: ")
        if user_input.strip().lower() in ["exit", "bye", "quit"]:
            break

        result = await chatbot.ainvoke(
            {"messages": [HumanMessage(content=user_input)]}, config
        )
        print("Bot:", result["messages"][-1].content)


def main() -> None:
    asyncio.run(run())


if __name__ == "__main__":
    main()
