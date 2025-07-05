# MCP-HTTP Streaming Agent

This project implements an AI agent capable of engaging in conversational interactions, performing web searches, and managing its memory using the Mem0 platform. The agent communicates with a custom server via HTTP streaming for tool execution and leverages the Groq API for its language model capabilities.




## Project Overview

The core of this project is an AI assistant named **Memoria**. It is designed to:
- Understand user queries and intent.
- Utilize external tools (like web search and memory management) to fulfill requests.
- Maintain conversational context and user-specific information across turns and sessions.
- Operate in a step-by-step, autonomous manner, deciding its own actions based on the conversation.




## `server.py` (MCP Tool Server)

This file acts as the backend server for the agent, exposing various tools via the MCP (Multi-Agent Communication Protocol) framework. It handles requests from the `client.py` to execute specific functionalities.

### Key Tools Provided:
- **`web_search`**: Performs web searches using the Tavily API to retrieve information.
- **`add_short_memory`**: Stores conversational context and ephemeral facts for the current session using Mem0.
- **`add_longterm_memory`**: Stores critical, long-lasting facts and user preferences using Mem0.
- **`get_memories`**: Retrieves memories associated with a specific user ID from Mem0.
- **`search_memories_v2`**: Advanced search functionality for memories.
- **`memory_history`**: Retrieves the history of memory operations.
- **`get_memory`**: Retrieves a specific memory by ID.
- **`update_memory`**: Modifies existing memories in Mem0.
- **`delete_memory`**: Removes memories from Mem0.




## `client.py` (Memoria AI Agent)

This is the main client-side application that runs the Memoria AI agent. It orchestrates the conversation flow, interacts with the Groq API for AI reasoning, and calls tools exposed by the `server.py`.

### Key Components:
- **`chat_loop()`**: The main asynchronous function that initializes the MCP client, fetches available tools, sets up the Groq client, and manages the interactive chat session. It continuously takes user input and passes it to `run_agent_turn`.
- **`run_agent_turn()`**: The core agent logic. This function handles a single 


turn of the agent's reasoning. It iteratively communicates with the Groq AI model, executes tools (via `mcp_client.call_tool`), and feeds the results back to the AI until a final natural language response is generated. It includes robust error handling and a safeguard for injecting `session_run_id` into memory operations.

### Agent's Reasoning Process (System Prompt):
Memoria operates based on a sophisticated system prompt that guides its behavior:
1.  **Analyze User Intent:** Understands what the user wants.
2.  **Formulate a Plan:** Creates a step-by-step plan of single actions.
3.  **Select One Tool:** Chooses the best tool for the current step.
4.  **Execute & Re-evaluate:** Runs the tool, processes results, and decides the next action.
5.  **Remember (Final Step):** Calls `add_short_memory` to save conversational context before responding.

### User Identification & Memory Strategy:
-   Uses provided `user_id` if available.
-   Defaults to `user-anonymous` for unnamed users.
-   Utilizes `add_short_memory` for session context and `add_longterm_memory` for critical, persistent facts.




## Setup and Installation

To set up and run this project, follow these steps:

1.  **Clone the repository:**
    ```bash
    git clone <repository_url>
    cd MCP-HTTP_Streaming
    ```

2.  **Create a virtual environment (recommended):**
    ```bash
    python -m venv .venv
    # On Windows:
    .venv\Scripts\activate
    # On macOS/Linux:
    source .venv/bin/activate
    ```

3.  **Install dependencies:**
    ```bash
    pip install -r requirements.txt
    ```
    *(Note: You will need to create a `requirements.txt` file containing `fastmcp`, `groq`, `loguru`, `mem0`, `tavily-python`)*

4.  **Configure API Keys and Environment Variables:**
    Create a `configs` directory in the root of your project, and inside it, create a `config.py` file. This file should contain your API keys and server URLs:
    ```python
    # configs/config.py
    GROQ_API_KEY = "your_groq_api_key_here"
    MODEL_NAME = "llama3-8b-8192" # Or your preferred Groq model
    MCP_SERVER_URL = "http://127.0.0.1:8000/mcp/"
    MEM0_API_KEY = "your_mem0_api_key_here"
    TAVILY_API_KEY = "your_tavily_api_key_here"
    ```




## How to Run

1.  **Start the MCP Server:**
    Open a new terminal, activate your virtual environment, and run the `server.py`:
    ```bash
    python server.py
    ```
    Ensure the server starts successfully and is listening on `http://127.0.0.1:8000/mcp/`.

2.  **Start the Memoria AI Agent:**
    Open another terminal, activate your virtual environment, and run the `client.py`:
    ```bash
    python client.py
    ```

3.  **Interact with the Agent:**
    You can now type your queries in the client terminal. The agent will use its reasoning process and available tools to respond.



