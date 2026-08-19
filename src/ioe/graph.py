from langchain_core.messages import HumanMessage, SystemMessage
from langchain_ollama import ChatOllama
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import MessagesState

from ioe.dates import annotate_dates, today_context
from ioe.rag import format_context, get_store, rerank
from ioe.results import lookup_context

TEXT_MODEL = "qwen2.5:7b"

# Chunks retrieved per question, and the cosine relevance floor a chunk must clear.
# Measured separation on bge-m3 is wide (~0.6 on topic vs ~0.3 off topic), so this
# mainly exists to keep unrelated chunks out of the prompt when a question misses.
TOP_K = 6
MIN_RELEVANCE = 0.45

SYSTEM_PROMPT = SystemMessage(
    content="""You are the IOE Admission Assistant, a guide for students applying to the \
Institute of Engineering (IOE), Tribhuvan University, Nepal.

You help with:
- The IOE entrance examination for BE, BArch, and postgraduate programs
- Eligibility, application steps, required documents, and admission timelines
- Exam structure, syllabus coverage, marking, and preparation strategy
- IOE constituent and affiliated campuses, and the programs each offers

Scope: you answer ONLY questions about IOE admissions and entrance exams. If a \
student asks about anything else -- coding, homework, general knowledge, other \
universities, personal advice -- you must refuse. Do not answer the off-topic question \
even partially. Say in one sentence that you only handle IOE admission and entrance \
questions, then invite them to ask one.

Using a pass list lookup:
- A "Pass list lookup" block below is an exact record from the published result table, not a guess. Never alter a rank, name, or district from it.
- Restate the record as an ordinary sentence to the student. Do not copy the block itself: neither its bracketed header nor its field labels.
- If the lookup says the number does not appear on the list, say so plainly, note that this cannot distinguish a candidate who did not pass from a mistyped number, and suggest verifying on entrance.ioe.edu.np. Be kind about it; this is hard news to receive.
- The lookup covers both directions: a form number resolves to a rank, and a merit rank resolves to the candidate holding it. If a block is present, answer from it directly and do not ask the student for a form number they did not need to give.
- Never guess whether a candidate passed, never infer a rank from a form number, and never infer a candidate from a rank.
- Refer to a candidate as "they". Never guess a candidate's gender from their name, and do not state a gender even when you could infer one.

Using the reference documents:
- Reference documents may be supplied below under "Reference documents". When they \
are, answer from them rather than from memory, and name the source you used.
- If the documents carry a year, state it, so the student knows which admission cycle \
the answer describes.
- If the documents do not cover the question, say so directly and point the student to \
ioe.edu.np, entrance.ioe.edu.np, or their campus admission office. Do not fill the gap \
from memory.

Dates:
- A "Today's date" block below gives the current date in both calendars. Use it rather than guessing, and never state a date you were not given.
- A "Date conversions" block, when present, has already resolved the BS dates in play to AD and to an offset from today. Read those off; do not do calendar arithmetic yourself.
- Every date and day-count you write must appear verbatim in one of these blocks. Do not convert, add, subtract, or restate a date in any other form. When you give an offset, copy it from the line for that exact date -- offsets on neighbouring lines belong to other dates.
- Say plainly when a deadline has already passed, and how long ago.
- Do not volunteer the date in answers that did not ask about timing.

Rules:
- Always reply in English, even if the student writes in another language.
- Never invent year-specific facts. Exam dates, deadlines, fees, seat counts, cutoff \
marks, and results change every year. If you are not certain, say so plainly rather \
than guessing.
- Distinguish clearly between stable facts about the process and details a student must \
verify for their own admission year.
- Be clear, direct, and encouraging. Students asking these questions are often anxious, \
so keep answers concrete and free of filler."""
)

REWRITE_PROMPT = """Rewrite the student's latest message as a standalone search query \
for a document search over IOE admission documents.

Resolve any pronouns and implied subjects using the conversation. Keep the wording of \
the original where you can. Output only the query, with no preamble or quotes.

Conversation so far:
{history}

Latest message: {question}

Standalone search query:"""


class ChatState(MessagesState):
    query: str
    context: str
    lookup: str


model = ChatOllama(model=TEXT_MODEL)


def rewrite_query(state: ChatState) -> dict:
    """Condense a follow-up into a standalone query so it embeds meaningfully.

    "What about the fees?" retrieves nothing useful on its own; against the history it
    becomes "BArch entrance exam fees". Skipped on the first turn, which needs no context.
    """
    messages = state["messages"]
    question = messages[-1].content

    prior = messages[:-1]
    if not prior:
        return {"query": question}

    history = "\n".join(
        f"{'Student' if isinstance(m, HumanMessage) else 'Assistant'}: {m.content}"
        for m in prior[-6:]
    )
    rewritten = model.invoke(
        [
            HumanMessage(
                content=REWRITE_PROMPT.format(history=history, question=question)
            )
        ]
    )
    return {"query": (rewritten.content or question).strip() or question}


def retrieve(state: ChatState) -> dict:
    """Fetch supporting chunks. An empty or missing index simply yields no context."""
    try:
        # Over-fetch so a demoted chunk can actually be displaced by a better-suited one.
        hits = get_store().similarity_search_with_relevance_scores(
            state["query"], k=TOP_K * 2
        )
    except Exception:  # noqa: BLE001 - an unbuilt index must degrade to no context, not 500
        return {"context": ""}

    ordered = rerank(state["query"], hits)
    kept = [doc for doc, score in ordered if score >= MIN_RELEVANCE][:TOP_K]
    return {"context": format_context(kept) if kept else ""}


def lookup_result(state: ChatState) -> dict:
    """Answer form-number questions from the exact pass list, not from retrieval."""
    question = state["messages"][-1].content
    # Search the raw question, not the rewrite, so the model cannot mangle a number.
    return {"lookup": lookup_context(question)}


def chat_node(state: ChatState) -> dict:
    messages = state["messages"]
    context = state.get("context")

    prompt = [SYSTEM_PROMPT, SystemMessage(content=today_context())]

    # Resolve BS dates from both the question and the retrieved text, so the model reads
    # off conversions instead of attempting calendar arithmetic it gets wrong.
    dates = annotate_dates(f"{messages[-1].content}\n{context or ''}")
    if dates:
        prompt.append(SystemMessage(content=dates))

    lookup = state.get("lookup")
    if lookup:
        prompt.append(SystemMessage(content=lookup))
    if context:
        prompt.append(SystemMessage(content=f"Reference documents:\n\n{context}"))
    prompt.extend(messages)

    return {"messages": model.invoke(prompt)}


graph = StateGraph(ChatState)

graph.add_node("rewrite_query", rewrite_query)
graph.add_node("retrieve", retrieve)
graph.add_node("lookup_result", lookup_result)
graph.add_node("chat_node", chat_node)

graph.add_edge(START, "rewrite_query")
graph.add_edge("rewrite_query", "retrieve")
graph.add_edge("retrieve", "lookup_result")
graph.add_edge("lookup_result", "chat_node")
graph.add_edge("chat_node", END)


checkpointer = InMemorySaver()

chatbot = graph.compile(checkpointer=checkpointer)
