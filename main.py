from typing import TypedDict, Annotated

from dotenv import load_dotenv

from langgraph.graph.message import add_messages
from langgraph.graph import StateGraph, START, END
from langgraph.prebuilt import ToolNode

from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_groq import ChatGroq
from langchain_tavily import TavilySearch


# ============================================================
# ENVIRONMENT
# ============================================================

load_dotenv()


# ============================================================
# TOOLS
# ============================================================

search_tool = TavilySearch(
    max_results=3
)

tools = [search_tool]


# ============================================================
# LLMs
# ============================================================

# Writer
writer_llm = ChatGoogleGenerativeAI(
    model="gemini-3.8-flash",
    temperature=0.7
)

writer_llm_with_tools = writer_llm.bind_tools(tools)


# Reviewer
reviewer_llm = ChatGroq(
    model="openai/gpt-oss-120b",
    temperature=0.2
)


# ============================================================
# STATE
# ============================================================

class State(TypedDict):
    topic: str
    messages: Annotated[list, add_messages]
    draft: str
    review_feedback: str
    is_approved: bool
    attempt: int


# ============================================================
# WRITER PROMPT
# ============================================================

WRITER_SYSTEM_PROMPT = (
    "You are an expert LinkedIn content writer. Your job is to write "
    "engaging, professional LinkedIn posts about the given topic. "

    "If the topic requires up-to-date information, statistics, or "
    "current trends, use the web search tool to gather fresh context "
    "before writing. "

    "If you have already received feedback on a previous draft, "
    "carefully address every point in the new draft. "

    "Rules for good LinkedIn posts: "
    "strong hook in the first line, "
    "1 clear takeaway, "
    "easy to skim with short paragraphs, "
    "around 150-200 words, "
    "ends with a question or call-to-action to invite engagement. "

    "Do not use hashtags."
)


# ============================================================
# WRITER NODE
# ============================================================

def writer_node(state: State) -> dict:
    """
    Writes or rewrites the LinkedIn post.

    Important:
    If Gemini previously made a tool call, we preserve the
    existing conversation so the ToolMessage immediately follows
    the AI tool call. This prevents Gemini's INVALID_ARGUMENT error.
    """

    attempt = state.get("attempt", 0) + 1

    topic = state["topic"]

    previous_feedback = state.get(
        "review_feedback",
        ""
    )

    messages = state.get(
        "messages",
        []
    )

    # --------------------------------------------------------
    # CASE 1:
    # Continuing after a tool call
    # --------------------------------------------------------

    if messages:

        last_message = messages[-1]

        # If the previous message is a ToolMessage,
        # send the complete conversation back to Gemini.
        if getattr(last_message, "type", None) == "tool":

            response = writer_llm_with_tools.invoke(
                [
                    ("system", WRITER_SYSTEM_PROMPT),
                    *messages
                ]
            )

            return {
                "messages": [response],
                "attempt": attempt
            }

    # --------------------------------------------------------
    # CASE 2:
    # First attempt
    # --------------------------------------------------------

    if attempt == 1:

        user_message = (
            f"Write a LinkedIn post on this topic:\n\n"
            f"{topic}\n\n"
            f"If you need current information, search the web first."
        )

    # --------------------------------------------------------
    # CASE 3:
    # Reviewer rejected previous draft
    # --------------------------------------------------------

    else:

        user_message = (
            f"Your previous draft on '{topic}' was rejected.\n\n"

            f"Here is the reviewer's feedback:\n\n"
            f"{previous_feedback}\n\n"

            f"Write a new, improved draft that fixes every issue "
            f"mentioned in the feedback. "

            f"Do not repeat the same mistakes."
        )

    response = writer_llm_with_tools.invoke(
        [
            ("system", WRITER_SYSTEM_PROMPT),
            ("human", user_message)
        ]
    )

    return {
        "messages": [
            ("human", user_message),
            response
        ],
        "attempt": attempt
    }


# ============================================================
# TOOL NODE
# ============================================================

tool_node = ToolNode(
    tools
)


# ============================================================
# EXTRACT DRAFT NODE
# ============================================================

def extract_draft_node(state: State) -> dict:
    """
    Gets the final AI response and saves it as the draft.
    """

    last_message = state["messages"][-1]

    draft = last_message.content

    print("\n")
    print("=" * 60)
    print("GENERATED LINKEDIN POST")
    print("=" * 60)
    print(draft)
    print("=" * 60)
    print()

    return {
        "draft": draft
    }


# ============================================================
# REVIEWER PROMPT
# ============================================================

REVIEWER_SYSTEM_PROMPT = (
    "You are a strict LinkedIn content reviewer. "
    "You judge whether a post is publish-ready. "

    "Evaluate against these criteria:\n"

    "1. Strong hook in the first line\n"
    "2. One clear, valuable takeaway\n"
    "3. Easy to skim — uses short paragraphs\n"
    "4. Roughly 150-200 words\n"
    "5. Ends with an engaging question or CTA\n"
    "6. Professional but human tone (not corporate-robotic)\n"
    "7. No hashtags\n\n"

    "Respond in exactly this format:\n"

    "VERDICT: APPROVED or REJECTED\n"
    "FEEDBACK: <one short paragraph explaining why>\n\n"

    "Be strict but fair. "
    "Approve only if the post genuinely meets all criteria. "
    "Reject if even one criterion is clearly missing."
)


# ============================================================
# REVIEWER NODE
# ============================================================

def reviewer_node(state: State) -> dict:
    """
    Reviews the generated LinkedIn post.
    """

    draft = state["draft"]

    prompt = (
        f"Review this LinkedIn post draft:\n\n"
        f"{draft}\n\n"
        f"Give your review using the required format."
    )

    response = reviewer_llm.invoke(
        [
            ("system", REVIEWER_SYSTEM_PROMPT),
            ("human", prompt)
        ]
    )

    review_text = response.content.strip()

    # --------------------------------------------------------
    # Extract verdict
    # --------------------------------------------------------

    first_part = review_text.upper().split(
        "FEEDBACK",
        1
    )[0]

    is_approved = (
        "VERDICT: APPROVED" in first_part
    )

    # --------------------------------------------------------
    # Extract feedback
    # --------------------------------------------------------

    if "FEEDBACK:" in review_text:

        feedback = review_text.split(
            "FEEDBACK:",
            1
        )[1].strip()

    else:

        feedback = review_text

    verdict = (
        "APPROVED"
        if is_approved
        else "REJECTED"
    )

    print(
        f"[Verdict: {verdict}]"
    )

    print(
        f"[Feedback: {feedback}]"
    )

    return {
        "review_feedback": feedback,
        "is_approved": is_approved
    }


# ============================================================
# ROUTER 1
# ============================================================

def should_use_tool(state: State):

    last_message = state["messages"][-1]

    if getattr(
        last_message,
        "tool_calls",
        None
    ):

        return "tools"

    return "extract_draft"


# ============================================================
# ROUTER 2
# ============================================================

def should_stop_looping(state: State):

    if state["is_approved"]:

        print(
            "Post has been approved."
        )

        return END

    if state["attempt"] >= 3:

        print(
            "Reached maximum attempts."
        )

        return END

    return "writer"


# ============================================================
# BUILD GRAPH
# ============================================================

graph = StateGraph(State)


graph.add_node(
    "writer",
    writer_node
)

graph.add_node(
    "tools",
    tool_node
)

graph.add_node(
    "extract_draft",
    extract_draft_node
)

graph.add_node(
    "reviewer",
    reviewer_node
)


# ============================================================
# GRAPH EDGES
# ============================================================

graph.add_edge(
    START,
    "writer"
)


# Writer decides whether a tool is required
graph.add_conditional_edges(
    "writer",
    should_use_tool
)


# IMPORTANT:
# Tool result goes BACK to writer.
#
# Do NOT use:
#
# graph.add_edge("tools", "reviewer")
#
# because the reviewer would receive the tool result
# instead of the final LinkedIn post.

graph.add_edge(
    "tools",
    "writer"
)


# Final writer response → draft
graph.add_edge(
    "extract_draft",
    "reviewer"
)


# Reviewer → END or another writer attempt
graph.add_conditional_edges(
    "reviewer",
    should_stop_looping
)


# ============================================================
# COMPILE
# ============================================================

app = graph.compile()


# ============================================================
# PUBLIC FUNCTION USED BY FASTAPI
# ============================================================

def generate_post(topic: str):

    initial_state = {
        "topic": topic,
        "messages": [],
        "draft": "",
        "review_feedback": "",
        "is_approved": False,
        "attempt": 0,
    }

    final_state = app.invoke(
        initial_state
    )

    return {
        "draft": final_state["draft"],
        "approved": final_state["is_approved"],
        "attempts": final_state["attempt"],
        "feedback": final_state["review_feedback"],
    }
