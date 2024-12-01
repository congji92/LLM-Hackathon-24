import operator
from pydantic import BaseModel, Field
from typing import Annotated, List
from typing_extensions import TypedDict

from langchain_community.document_loaders import WikipediaLoader
from langchain_community.tools.tavily_search import TavilySearchResults
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, get_buffer_string
from langchain_openai import ChatOpenAI

from langgraph.constants import Send
from langgraph.graph import END, MessagesState, START, StateGraph
from langgraph.graph.message import add_messages
from maps_text_search import Agent_search

### LLM

llm = ChatOpenAI(model="gpt-4o", temperature=0, api_key = 'type_your_own' ) 

### Schema 

class OrderState(TypedDict):
    """State representing the customer's order conversation."""
    messages: Annotated[list, add_messages] # aka the MessagesState class
    destination: str
    duration: str
    order: list[str]
    suggestions: list[str]
    finished: bool
    ready_to_search: bool

TravelBOT_SYSINT = (
    "system",  # 'system' indicates the message is a system instruction.
    "You are a TravelBot, an interactive travel planning system. You will do the following:"
    
    "Step 1: A customer will talk to you about the preferences for destination, places of interests, food, and etc, "
    "you will gather preferences, usually at lease one destination,"
    "and you will answer any questions about travel preferences (and only about travel preferences - no off-topic discussion). "
    "Add destination, places of interest and food preferences to the customer's order by calling add_to_order"
    "To see the contents of the order so far, call get_order (this is shown to you, not the user) "
    "Customer may request to reset the order by calling clear_order. "
    "The customer will confirm the collected preferences, which you will structure."
    
    "Step 2: Search preferences by calling get_search. "
    "Always verify and respond with places of interest and restaurant from the get_search before adding them to the suggestions. "
    "You only have the places and restaurants listed by calling get_search. "

    "Step 3: Once having called get_search, call confirm_order to ensure it is correct, then make "
    "any necessary updates and then call plan_order. "
    "Always confirm_order with the user (double-check) before calling plan_order. Calling confirm_order will "
    "display the preferences and suggestions to the user and returns their response to seeing the list. Their response may contain modifications. "

    "Step 4: If user confirmes, thank the user and say goodbye!",
)

WELCOME_MSG = "Welcome to DJ (Dr.J), the travel agent. Type `q` to quit. What's on your mind for travel today?"

def human_node(state: OrderState) -> OrderState:
    print("Model:", state["messages"][-1].content)

    user_input = input("User: ")
    if user_input in {"q", "quit", "exit", "goodbye", "That's all", "I am good"}:
        state["finished"] = True      # OrderState.finished = True -> maybe_exit_human_node -> END

    return state | {"messages": [("user", user_input)]}

from typing import Literal
def maybe_exit_human_node(state: OrderState) -> Literal["chatbot", "__end__"]:
    """Route to the chatbot, unless it looks like the user is exiting."""
    if state.get("finished", False):
        return END
    else:
        return "chatbot"
    
from langchain_core.tools import tool

@tool
def get_search() -> str:
    """Provide the latest up-to-date places of insterests and food suggestions. 
    """

def search_node(state: OrderState) -> OrderState:
    """The search node. This is where the suggestion state is manipulated."""
    tool_msg = state.get("messages", [])[-1]
    order = state.get("order", [])
    outbound_msgs = []
    order_placed = False

    for tool_call in tool_msg.tool_calls:
        if tool_call["name"] == "get_search":
            print('debug step 1: ', order)
            query = order[0]
            agent = Agent_search(query, 37.802516, -122.399833, 37.775271, -122.431116)
            result = agent.search().tolist()
            response = "\n found the following: ".join(result)

        outbound_msgs.append(ToolMessage(
                content=response,
                name=tool_call["name"],
                tool_call_id=tool_call["id"],))
        suggestion = result
        return state | {"messages": outbound_msgs, "suggestions": suggestion }


from langgraph.prebuilt import ToolNode
from typing import Literal

def chatbot_with_tools(state: OrderState) -> OrderState: #should this be defined after llm_with_tools definition?
    defaults = {"order": [], "finished": False}
    if state["messages"]:
        new_output = llm_with_tools.invoke([TravelBOT_SYSINT] + state["messages"])
    else:
        new_output = AIMessage(content=WELCOME_MSG)
    return defaults | state | {"messages": [new_output]}

from collections.abc import Iterable
from random import randint
from langgraph.prebuilt import InjectedState
from langchain_core.messages.tool import ToolMessage
@tool
def add_to_order(requests: str) -> str:
    """Adds the specified preferences for place of interest and food.
    Returns:
      The updated order in progress.
    """

@tool
def confirm_order() -> str:
    """Asks the customer if the preference is correct.
    Returns:
      The user's free-text response.
    """

@tool
def get_order() -> str:
    """Returns the user's preference so far. One item per line."""

@tool
def clear_order():
    """Removes all items from the user's order."""

@tool
def plan_order() -> int:
    """Sends the food and place suggestions for planning.

    Returns:
      The estimated number of minutes until the plan is ready.
    """

def order_node(state: OrderState) -> OrderState:
    """The ordering node. This is where the order state is manipulated."""
    tool_msg = state.get("messages", [])[-1]
    order = state.get("order", [])
    suggestions = state.get("suggestions", [])
    outbound_msgs = []
    order_placed = False

    for tool_call in tool_msg.tool_calls:
        if tool_call["name"] == "add_to_order":
            order.append(f'{tool_call["args"]["requests"]}')
            print('debug step 1: updating preferences to order: ', order)
            response = "\n".join(order)

        elif tool_call["name"] == "confirm_order":
            print("Confirming tool_call: \nYour preferences:")
            if not order:
                print("  (no preferences)")
            elif order:
              for items in order:
                print(f"  {items}")
            if not suggestions:
                print("  (no suggestions)")
            elif order:
              for items in suggestions:
                print(f"  {items}")

            response = input("Is this correct? ")

        elif tool_call["name"] == "get_order":

            response = "\n".join(order) if order else "(no order)"

        elif tool_call["name"] == "clear_order":

            order.clear()
            response = None

        elif tool_call["name"] == "plan_order":

            order_text = "\n".join(suggestions)
            print("\n Sending place and food suggestions to planner!\n")
            print('Debug step 3: call plan_order to send to planning: ', order_text)

            # TODO: Implement planning based on order.
            order_placed = True
            response = randint(1, 5)  # ETA in minutes

        else:
            raise NotImplementedError(f'Unknown tool call: {tool_call["name"]}')

        # Record the tool results as tool messages.
        outbound_msgs.append(
            ToolMessage(
                content=response,
                name=tool_call["name"],
                tool_call_id=tool_call["id"],
            )
        )
    return state | {"messages": outbound_msgs, "order": order, "ready_to_search": order_placed}

def maybe_route_to_tools(state: OrderState) -> str:
    if not (msgs := state.get("messages", [])):
        raise ValueError(f"No messages found when parsing state: {state}")
    msg = msgs[-1]
    if state.get("finished", False):
        return END

    elif hasattr(msg, "tool_calls") and len(msg.tool_calls) > 0:
        if any(tool["name"] in ["get_search"] for tool in msg.tool_calls):
            return "search"
        else:return "ordering"
    else:return "human"

auto_tools = [get_search]
order_tools = [add_to_order, confirm_order, get_order, clear_order, plan_order]
llm_with_tools = llm.bind_tools(auto_tools + order_tools)

graph_builder = StateGraph(OrderState)

graph_builder.add_node("chatbot", chatbot_with_tools)
graph_builder.add_node("human", human_node)
graph_builder.add_node("search", search_node)
graph_builder.add_node("ordering", order_node)

graph_builder.add_conditional_edges("chatbot", maybe_route_to_tools)
graph_builder.add_conditional_edges("human", maybe_exit_human_node)

graph_builder.add_edge("search", "chatbot")
graph_builder.add_edge("ordering", "chatbot")

graph_builder.add_edge(START, "chatbot")

#from langgraph.checkpoint.memory import MemorySaver
#memory = MemorySaver()
#graph = graph_builder.compile(interrupt_before=['human'], checkpointer=memory)

graph = graph_builder.compile()

config = {"recursion_limit": 100}
state = graph.invoke({"messages": []}, config)