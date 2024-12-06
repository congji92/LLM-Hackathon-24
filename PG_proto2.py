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

llm = ChatOpenAI(model="gpt-4o", temperature=0, api_key = 'OpenAI API Here' ) 

### Schema 

class OrderState(TypedDict):
    """State representing the customer's order conversation."""
    messages: Annotated[list, add_messages] # aka the MessagesState class
    destination: str                  #TBD
    duration: str                           #TBD
    order: list[str]
    suggestions: list[str]
    selections: list[str]
    finished: bool                          #TBD
    desination_collected: bool
    pref_collected: bool
    search_returned: bool
    selected: bool
    plan_ordered: bool

TravelBOT_SYSINT = (
    "system",  # 'system' indicates the message is a system instruction.
    "You are a TravelBot, an interactive travel planning system. You will do the following:"

    "Step 1: A customer will talk to you about the preferences for destination. Add destination by calling add_to_destination."
    "You will answer any questions about destinations (and only about destinations - no off-topic discussion). "
    
    "Step 2: The customer will talk to you about the preferences for places of interests or food. "
    "Add those preferences to the customer's order by calling add_to_order"
    "You will answer any questions about preferences (and only about preferences - no off-topic discussion). "

    "Step 3: Search preferences by calling get_search. "
    "You only have the places and restaurants listed in suggestions by calling get_search. "

    "Step 4: You will call confirm_order in order to ask for customer's choice from the suggestions. "

    "Step 5: Customer might select a part of or all suggestions, call select_order to record customer selections. "
    "Customer might request to make a new search, which will have the system go back to step 1 and follow the same step order. "

    "Step 6: After user makes a selection, call plan_order."
    "Customer might request to make a new search, which will have the system go back to step 1 and follow the same step order. "

    "Step 7: If user confirmes the plan, then thank the user and say goodbye!",
)

WELCOME_MSG = "Welcome to DJ, the travel agent. What's on your mind today? Type `q` to quit"

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
    destination = state.get("destination", '')
    destination_collected = state.get("destination_collected", False)
    pref_collected = state.get("pref_collected", False)
    search_returned = state.get("search_returned", False)
    suggestions = state.get("order", [])

    for tool_call in tool_msg.tool_calls:
        if tool_call["name"] == "get_search" and pref_collected:
            print(f"Debuge step 3: call api according to destination: {destination}, order (preferences): {order}")
            query = ''.join(order)
            print('debug step 2.1: query is: ', query)
            agent = Agent_search(destination, query)
            result = agent.search().tolist()
            response = "\n found the following: ".join(result)

        outbound_msgs.append(ToolMessage(
                content=response,
                name=tool_call["name"],
                tool_call_id=tool_call["id"],))
        suggestions = result
        search_returned = True
        return state | {"messages": outbound_msgs, "suggestions": suggestions, "search_returned": search_returned }

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
def add_to_destination(location: str) -> str:
    """Adds the specified destination.
    Returns:
      The updated destination.
    """

@tool
def add_to_order(requests: str) -> str:
    """Adds the specified preferences for place of interest and food.
    Returns:
      The updated order in progress.
    """

@tool
def confirm_order() -> str:
    """Asks for selection.
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
def select_order(selection: str) -> str:
    """Adds the specified suggestions into selections.
    Returns:
      The updated selections in progress.
    """

@tool
def plan_order() -> int:
    """Sends the food and place suggestions for planning.

    Returns:
      The estimated number of minutes until the plan is ready.
    """

def order_node(state: OrderState) -> OrderState:
    """The ordering node. This is where the order state is manipulated."""
    tool_msg = state.get("messages", [])[-1]
    destination = state.get("destination", '')
    order = state.get("order", [])
    suggestions = state.get("suggestions", [])
    selections = state.get("selections", [])
    outbound_msgs = []
    destination_collected = state.get("destination_collected", False)
    pref_collected = state.get("pref_collected", False)
    search_returned = state.get("search_returned", False)
    selected = state.get("selected", False)
    plan_ordered = state.get("plan_ordered", False)

    for tool_call in tool_msg.tool_calls:
        if tool_call["name"] == "add_to_destination":
            destination = (f'{tool_call["args"]["location"]}')
            print('debug step 1: updating destination: ', destination)
            response = "\n".join(destination)
            destination_collected = True

        elif tool_call["name"] == "add_to_order":
            order = []
            order.append(f'{tool_call["args"]["requests"]}')
            print('debug step 2: updating preferences to order: ', order)
            response = "\n".join(order)
            pref_collected = True

        elif tool_call["name"] == "confirm_order":
            print("debug step 4: Confirming suggestions: \nYour destination:")
            if not destination:
                print("  (no destination supplied by customer)")
            elif destination:
                print(f"  {destination}")

            print("\nYour preferences:")
            if not order:
                print("  (no preferences supplied by customer)")
            elif order:
              for items in order:
                print(f"  {items}")

            print(" \nSuggestions for you: \n")
            if not suggestions:
                print("  (no suggestions provided by search)")
            elif order:
              for items in suggestions:
                print(f"  {items}")

            response = input("Any suggestions that looks interesting to you? ")

        elif tool_call["name"] == "get_order":

            response = "\n".join(order) if order else "(no order)"

        elif tool_call["name"] == "clear_order":

            order.clear()
            response = None

        elif tool_call["name"] == "select_order":
            selections.append(f'{tool_call["args"]["selection"]}')
            print('debug step 5: selections to plan: ', selections)
            response = "\n".join(selections)
            selected = True
            order = []
            destination = ''

        elif tool_call["name"] == "plan_order" and selected == True:

            order_text = "\n".join(suggestions)
            print('Debug step 6: call plan_order with following selections: ', selections)
            plan_ordered = True
            destination_collected = False
            pref_collected = False
            search_returned = False
            selected = False
            order = []
            destination = ''
            suggestions = []

            # TODO: Implement planning based on order.
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
    return state | {"messages": outbound_msgs, "destination": destination, "order": order, "suggestions": suggestions, "destination_collected": destination_collected, "pref_collected": pref_collected, "selected": selected, "selections": selections, "plan_ordered": plan_ordered}

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
order_tools = [add_to_destination, add_to_order, confirm_order, get_order, clear_order, select_order, plan_order]
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
