from dotenv import load_dotenv
import os

# Load environment variables
ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "../"))
load_dotenv(dotenv_path=os.path.join(ROOT_DIR, ".env"))


GROQ_API_KEY = os.getenv("GROQ_API_KEY")
MODEL_NAME = os.getenv("MODEL_NAME")
TAVILY_API_KEY = os.getenv("TAVILY_API_KEY")
MEM0_API_KEY    = os.getenv("MEM0_API_KEY")
MEM0_ORG_ID     = os.getenv("MEM0_ORG_ID")
MEM0_PROJECT_ID = os.getenv("MEM0_PROJECT_ID")
MCP_SERVER_URL = os.getenv("MCP_SERVER_URL")


# Print for debugging
missing_vars = []
if not GROQ_API_KEY:
    missing_vars.append("GROQ_API_KEY")
if not MODEL_NAME:
    missing_vars.append("MODEL_NAME")
if not TAVILY_API_KEY:
    missing_vars.append("TAVILY_API_KEY")
if not MEM0_API_KEY:
    missing_vars.append("MEM0_API_KEY")
if not MEM0_ORG_ID:
    missing_vars.append("MEM0_ORG_ID")
if not MEM0_PROJECT_ID:
    missing_vars.append("MEM0_PROJECT_ID")
if not MCP_SERVER_URL:
    missing_vars.append("MCP_SERVER_URL")
if missing_vars:
    raise EnvironmentError(f"❌ Missing environment variables: {', '.join(missing_vars)}")
else:
    print("✅ Environment variables loaded successfully.")  