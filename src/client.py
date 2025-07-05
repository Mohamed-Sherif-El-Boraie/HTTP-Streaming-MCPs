# Import necessary libraries and modules
import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import json
import asyncio
import traceback
import uuid
from loguru import logger
from typing import List, Dict, Any

from groq import Groq
from fastmcp import Client
from fastmcp.client.transports import StreamableHttpTransport

from configs.config import GROQ_API_KEY, MODEL_NAME, MCP_SERVER_URL



# Core Logic Loop
async def run_agent_turn(
    user_input: str,
    mcp_client: Client,
    groq_client: Groq,
    history: List[Dict[str, Any]],
    groq_tools: List[Dict[str, Any]],
    session_run_id: str
) -> str: 
    """
    Runs a full agent turn, correctly handling both structured and raw tool calls.
    """
    # Append the user input to the conversation history
    history.append({"role": "user", "content": user_input})
    logger.debug(f"User input added to history: {user_input}")
    

    while True:
        print("\n🤖 Assistant is thinking...")
        
        # Groq API Call
        try:
            resp = groq_client.chat.completions.create(
                model=MODEL_NAME,
                temperature=0.2,
                messages=history,
                tools=groq_tools,
                tool_choice="auto",
                max_tokens=4096,
            )
            msg = resp.choices[0].message
            logger.debug(f"LLM Raw Response: {msg}")
        except Exception as e:
            logger.error(f"Groq API call failed: {e}")
            return "Sorry, I had a problem communicating with my brain. Please try again."

        # Check for structured tool calls first
        if msg.tool_calls:
            print(f"🛠️ Assistant wants to use a structured tool.")
            history.append(msg) 
            
            tool_call = msg.tool_calls[0]
            tool_name = tool_call.function.name
            tool_args = json.loads(tool_call.function.arguments or "{}")

            # Execute the tool
            try:
                print(f"  - Calling tool: {tool_name}({json.dumps(tool_args)})")
                if tool_name == "add_short_memory":
                    tool_args['run_id'] = session_run_id
                
                result = await mcp_client.call_tool(tool_name, tool_args)
                result_content = str(result)
                logger.debug(f"Tool '{tool_name}' returned: {result_content}...")

                # Append the result back to history
                history.append({
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "name": tool_name,
                    "content": result_content,
                })

            except Exception as e:
                logger.error(f"Tool `{tool_name}` error: {e}\n{traceback.format_exc()}")
                history.append({
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "name": tool_name,
                    "content": f"Error executing tool: {e}",
                })
            
            print("🧠 Assistant is processing the tool result...")
            continue 


        # TODO: Improve this manual parsing logic. This is a temporary workaround because the AI
        # sometimes "forgets" to use the structured `tool_calls` object and writes a raw function
        # string to the content. A more robust, automated solution should be developed.
        # --- Handle Raw Tool Calls ---

        # If no structured tool_calls, check if the content IS a raw tool call
        elif msg.content and msg.content.strip().startswith("<function="):
            print(f"⚠️ Assistant returned a raw tool call string. Parsing manually.") # This is a manual print for debugging
            
            # Basic parsing for <function=NAME{ARGS}></function>
            try:
                # This is a simplified parser. It might need to be more robust.
                func_part = msg.content.split('{', 1)
                tool_name = func_part[0].replace('<function=', '').strip()
                args_part = '{' + func_part[1].rsplit('}', 1)[0] + '}'
                tool_args = json.loads(args_part)

                print(f"  - Calling tool: {tool_name}({json.dumps(tool_args)})")
                if tool_name == "add_short_memory":
                    tool_args['run_id'] = session_run_id

                result = await mcp_client.call_tool(tool_name, tool_args)
                result_content = str(result)
                print(f"  - Tool '{tool_name}' returned: {result_content[:300]}...")

                # Append the result back to history 
                history.append({
                    "role": "user",
                    "content": f"The tool '{tool_name}' returned this result:\n{result_content}"
                })

            except Exception as e:
                logger.error(f"Failed to parse or execute raw tool call: {e}")
                history.append({"role": "user", "content": f"I tried to call a tool but failed: {e}"})

            print("🧠 Assistant is processing the tool result...")
            continue # Loop to continue the thought process

        else:
        
            print("✅ Assistant has a final answer.")
            assistant_text = msg.content or "I'm finished with the task."
            history.append({"role": "assistant", "content": assistant_text})
            return assistant_text

# Main Application
async def chat_loop():
    """Main chat loop that initializes the agent and handles user input."""
    
    
    print("Starting Memoria Agent...")
    try:
        transport = StreamableHttpTransport(MCP_SERVER_URL)
        async with Client(transport=transport) as mcp_client:
            await mcp_client.ping()
            logger.info(f"✅ Connected to MCP server at {MCP_SERVER_URL}")

            # Prepare tools for the Groq API
            raw_tools = await mcp_client.list_tools()
            logger.info(f"🔧 Available tools: {', '.join(tool.name for tool in raw_tools)}")
            groq_tools = []
            for t in raw_tools:
                tool_schema = t.model_json_schema(by_alias=True)
                groq_tools.append({
                    "type": "function",
                    "function": {
                        "name": t.name,
                        "description": t.description,
                        "parameters": tool_schema.get("parameters", {})
                    }
                })

            # System prompt content
            system_prompt_content = (
                "You are Memoria, a highly intelligent AI assistant with a sophisticated memory system. Your goal is to be helpful and conversational while intelligently managing your memory.\n\n"
                "## Your Reasoning Process (Follow on EVERY turn):\n"
                "1.  **Analyze the User's Intent:** What is the user trying to do? Are they asking a question? Providing new information? Asking to change or delete a memory? Just chatting?\n"
                "2.  **Formulate a Plan:** Based on the intent, create a step-by-step plan. Your plan should consist of a series of single actions.\n"
                "3.  **Select ONE Tool for the First Step:** Choose the single best tool to accomplish the first step of your plan. If no tool is needed (e.g., you are just chatting), then you can respond directly.\n"
                "4.  **Execute and Re-evaluate:** After using a tool, analyze the result and decide the next step in your plan. This may involve using another tool.\n"
                "5.  **Remember (Final Step):** Once you have all the information needed to answer the user, your final action before responding MUST be to call `add_short_memory`. Save the key facts from the conversation, including the user's query and the main points of the answer you found.\n\n"
                "---"
                "## Tool Usage Guidelines:\n\n"
                "### User Identification:\n"
                "- **If the user provides a name** (e.g., 'I am Bob'), use that name as the `user_id` for all memory operations.\n"
                "- **If the user does NOT provide a name**, you MUST use the default identifier `user-anonymous` as the `user_id`. Do not invent a user_id from the topic of their query.\n\n"
                "### Memory Management:\n"
                "- **First Interaction:** If a user introduces themself, your first step should be to call `get_memories` with their `user_id` to see if you know them.\n"
                "- **Saving Information:** Use `add_short_memory` for conversational context. Use `add_longterm_memory` for critical facts and preferences that should last forever. You can call both if needed, but do it in separate steps.\n"
                "- **Updating/Deleting:** If a user says 'My name is not Bob, it's Robert' or 'Forget my favorite color', use `update_memory` or `delete_memory` with the correct `memory_id`.\n"
                "- **Recalling Information:** Use `search_memories_v2` for specific questions about the past. Use `get_memories` to get a general overview of a user.\n\n"
                "### Information Retrieval:\n"
                "- **Use `web_search` ONLY when you don't know the answer** and the information is likely on the internet. Do not use it if the user is just chatting.\n\n"
                "### CRITICAL RULE:\n"
                "**You MUST call only one tool at a time.** This is a strict limitation. Your plan must be executed sequentially, step by step.\n\n"
            )
            history = [{"role": "system", "content": system_prompt_content}]
            
            # Initialize Groq client and session ID
            groq_client = Groq(api_key=GROQ_API_KEY)
            session_run_id = str(uuid.uuid4())
            logger.info(f"🤖 Memoria session started. Session ID: {session_run_id}")

            print("\nAssistant: Hi, I am Agent Memoria! 🤖 Your AI assistant. How can I help you today? 😊")
        
            # Chat loop
            while True:
                user_input = input("You: ").strip()
                if not user_input:
                    continue
                if user_input.lower() in ("exit", "quit"):
                    print("👋 Goodbye!")
                    break

                # Memoria's turn to think and respond
                final_reply = await run_agent_turn(
                    user_input, mcp_client, groq_client, history, groq_tools, session_run_id
                )
                print(f"Assistant: {final_reply}")

    except Groq.APIError as e:
        logger.error(f"❌ Groq API error: {e}")
        print("Sorry, I had a problem communicating with my brain. Please try again later.")
    except Exception as e:
        logger.error(f"❌ A critical error occurred during setup or chat: {e}")
        traceback.print_exc()


if __name__ == "__main__":
    try:
        asyncio.run(chat_loop())
    except KeyboardInterrupt:
        print("\n👋 Goodbye!. Chat is interrupted by keyboard!")

