"""What the model is shown of a conversation, and what it is told about the rest.

Two mechanisms, and the distinction between them is the point.

Short term is a *view*: the last few turns, verbatim, taken as a slice at prompt-assembly
time. The `messages` channel itself is never trimmed. It is the checkpointed transcript
that /api/history replays into the sidebar, so trimming it would not be managing a
context window, it would be deleting the student's own conversation.

Long term is a rolling summary, kept in state and updated every few turns. It is what
lets a bare follow-up work after the raw turns have scrolled out of the view -- "foreign?"
lands with three turns of transcript and a note saying the student has been asking about
fee categories.

Neither is a general memory across conversations. A student who comes back tomorrow with
a new thread starts clean, which for a public assistant answering questions that name
real people is the right default.
"""

from langchain_core.messages import AIMessage, AnyMessage, HumanMessage
from langchain_core.messages.utils import count_tokens_approximately
from langchain_ollama import ChatOllama

from ioe.prompts import SUMMARY_PROMPT
from ioe.rag import NUM_CTX, OLLAMA_URL

TEXT_MODEL = "qwen2.5:7b"

# Three exchanges. Enough that a follow-up to a follow-up still has its subject in view,
# short enough that a long fee answer does not push the documents out of the window.
KEEP_TURNS = 3

# Summarise once there are this many messages the summary has not seen, AND they are
# substantial. Both conditions, because three turns of "thanks" / "ok" / "got it" are
# three turns and are worth nothing to a summary -- and a summarisation call is a second
# pass over the conversation by a model that is already the slow part of the turn.
SUMMARY_EVERY_MESSAGES = KEEP_TURNS * 2
SUMMARY_MIN_TOKENS = 900

# Same model and the same num_ctx as everything else, so Ollama serves it from the runner
# already resident. See rag.NUM_CTX.
summary_model = ChatOllama(
    model=TEXT_MODEL,
    base_url=OLLAMA_URL,
    num_ctx=NUM_CTX,
    num_predict=200,
    temperature=0.2,
)


def recent_messages(
    messages: list[AnyMessage], keep: int = KEEP_TURNS * 2
) -> list[AnyMessage]:
    """The tail of the transcript the model is shown. Never mutates `messages`."""
    return messages[-keep:] if keep else []


def unseen(messages: list[AnyMessage], summarized_upto: int) -> list[AnyMessage]:
    """The messages the running summary does not yet account for."""
    return messages[summarized_upto:]


def should_summarize(messages: list[AnyMessage], summarized_upto: int) -> bool:
    """Whether enough has happened since the last summary to be worth a model call."""
    fresh = unseen(messages, summarized_upto)
    return (
        len(fresh) >= SUMMARY_EVERY_MESSAGES
        and count_tokens_approximately(fresh) >= SUMMARY_MIN_TOKENS
    )


def transcript(messages: list[AnyMessage], cap: int = 600) -> str:
    """Messages as speaker-labelled lines, for a prompt that reads rather than replays."""
    lines = []
    for message in messages:
        if isinstance(message, HumanMessage):
            speaker = "Student"
        elif isinstance(message, AIMessage):
            speaker = "Sarathi"
        else:
            continue
        said = " ".join((message.content or "").split())
        if said:
            lines.append(f"{speaker}: {said[:cap]}")
    return "\n".join(lines)


def summarize(summary: str, fresh: list[AnyMessage]) -> str:
    """The updated running summary, or the old one if the call fails.

    A failed summarisation must never cost the student their answer -- it runs after the
    answer has already been streamed, and the worst case is that the next turn has a
    slightly staler note than it might have had.
    """
    try:
        written = summary_model.invoke(
            SUMMARY_PROMPT.format(
                summary=summary or "(nothing yet)", new=transcript(fresh)
            )
        )
    except Exception:  # noqa: BLE001 - a summary is a convenience, never a requirement
        return summary
    return (written.content or "").strip() or summary


# How many earlier turns a detector may look back over. Three, to match the short-term
# memory window the model itself is shown -- a detector reading further back than the
# model can see would ground an answer in something the model cannot account for.
CARRY_TURNS = 3


def previous_question(messages: list) -> str:
    """The student's recent earlier messages, newest first, as one string.

    For detectors that a bare follow-up starves: "for regular" is a fee question only in
    the light of an earlier turn, and which figure it wants -- the admission-day total or
    the whole-degree total -- was stated there and nowhere else.

    Deliberately several turns rather than only the last one. Taking exactly the previous
    message was wrong in the case that prompted this: asked the degree cost, told "you are
    so wrong", then "for regular", the intent-carrying turn is two back and the one in
    between carries nothing at all.
    """
    asked = [
        message.content
        for message in messages or []
        if isinstance(message, HumanMessage) and isinstance(message.content, str)
    ]
    return "\n".join(reversed(asked[:-1][-CARRY_TURNS:]))
