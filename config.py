import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Google AI Configuration
# Try Streamlit secrets first (for cloud deployment), then fall back to env vars
try:
    import streamlit as st
    GOOGLE_API_KEY = st.secrets.get("GOOGLE_API_KEY", os.getenv("GOOGLE_API_KEY"))
except (ImportError, FileNotFoundError):
    # Not running in Streamlit or secrets not configured
    GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
GOOGLE_MODEL = "gemini-2.5-flash"  # Updated to latest available model
EMBEDDING_MODEL = "models/text-embedding-004"  # Updated embedding model

# Vector Database Configuration
CHROMA_DB_DIR = "./chroma_db"
COLLECTION_NAME = "tech_docs"

# RAG Configuration
CHUNK_SIZE = 1000
CHUNK_OVERLAP = 300
TOP_K_RESULTS = 8

# Rate Limiting
MAX_REQUESTS_PER_MINUTE = 20
MAX_TOKENS_PER_REQUEST = 4000

# Tool Execution Configuration
CODE_EXECUTION_TIMEOUT = 10  # seconds
MAX_CODE_LENGTH = 1000  # characters

# Logging Configuration
LOG_FILE = "chatbot.log"
LOG_LEVEL = "INFO"

# Supported Python Libraries (focused on beginner learning)
SUPPORTED_LIBRARIES = [
    # Core Python essentials
    "random",
    "math", 
    "datetime",
    "json",
    "os",
    "sys",
    "collections",
    "itertools",
    "functools",
    
    # Data analysis (most popular for beginners)
    "pandas",
    "numpy",
    
    # Visualization (beginner-friendly)
    "matplotlib",
    "seaborn",
    
    # Web basics
    "requests",
    "flask",
    
    # Testing (important skill)
    "pytest",
    "unittest",
    
    # File handling
    "csv",
    "pathlib",
    
    # String manipulation
    "re",
    "string",
    
    # Data structures
    "collections",
    
    # Package management
    "pip",
    "setuptools"
]

OFFICIAL_DOC_URLS = {
    # Core Python modules
    "random": [
        "https://docs.python.org/3/library/random.html",
        "https://docs.python.org/3/library/random.html#examples"
    ],
    "math": [
        "https://docs.python.org/3/library/math.html",
        "https://docs.python.org/3/library/math.html#functions"
    ],
    "datetime": [
        "https://docs.python.org/3/library/datetime.html",
        "https://docs.python.org/3/library/datetime.html#examples"
    ],
    "json": [
        "https://docs.python.org/3/library/json.html",
        "https://docs.python.org/3/library/json.html#basic-usage"
    ],
    "os": [
        "https://docs.python.org/3/library/os.html",
        "https://docs.python.org/3/library/os.html#file-names-and-command-line-arguments"
    ],
    "sys": [
        "https://docs.python.org/3/library/sys.html",
        "https://docs.python.org/3/library/sys.html#sys.argv"
    ],
    "collections": [
        "https://docs.python.org/3/library/collections.html",
        "https://docs.python.org/3/library/collections.html#namedtuple-factory-function-for-tuples-with-named-fields"
    ],
    "itertools": [
        "https://docs.python.org/3/library/itertools.html",
        "https://docs.python.org/3/library/itertools.html#itertools-recipes"
    ],
    "functools": [
        "https://docs.python.org/3/library/functools.html",
        "https://docs.python.org/3/library/functools.html#functools.partial"
    ],
    
    # Data analysis
    "pandas": [
        "https://pandas.pydata.org/docs/",
        "https://pandas.pydata.org/docs/user_guide/index.html",
    ],
    "numpy": [
        "https://numpy.org/doc/stable/",
        "https://numpy.org/doc/stable/user/absolute_beginners.html",
    ],
    
    # Visualization
    "matplotlib": [
        "https://matplotlib.org/stable/",
        "https://matplotlib.org/stable/users/index.html",
    ],
    "seaborn": [
        "https://seaborn.pydata.org/",
        "https://seaborn.pydata.org/tutorial.html",
    ],
    
    # Web basics
    "requests": [
        "https://requests.readthedocs.io/en/latest/",
        "https://requests.readthedocs.io/en/latest/user/quickstart/",
    ],
    "flask": [
        "https://flask.palletsprojects.com/en/stable/",
        "https://flask.palletsprojects.com/en/stable/quickstart/",
    ],
    
    # Testing
    "pytest": [
        "https://docs.pytest.org/en/stable/",
        "https://docs.pytest.org/en/stable/getting-started.html",
    ],
    "unittest": [
        "https://docs.python.org/3/library/unittest.html",
        "https://docs.python.org/3/library/unittest.html#basic-example",
    ],
    
    # File handling
    "csv": [
        "https://docs.python.org/3/library/csv.html",
        "https://docs.python.org/3/library/csv.html#examples"
    ],
    "pathlib": [
        "https://docs.python.org/3/library/pathlib.html",
        "https://docs.python.org/3/library/pathlib.html#basic-usage"
    ],
    
    # String manipulation
    "re": [
        "https://docs.python.org/3/library/re.html",
        "https://docs.python.org/3/library/re.html#regular-expression-syntax"
    ],
    "string": [
        "https://docs.python.org/3/library/string.html",
        "https://docs.python.org/3/library/string.html#string-constants"
    ],
    
    # Package management
    "pip": [
        "https://pip.pypa.io/en/stable/",
        "https://pip.pypa.io/en/stable/getting-started.html",
    ],
    "setuptools": [
        "https://setuptools.pypa.io/en/latest/",
        "https://setuptools.pypa.io/en/latest/userguide.html",
    ]
}

DOC_FETCH_TIMEOUT_SECONDS = 15
DOC_FETCH_USER_AGENT = "python-docs-copilot/1.0"

# Validation - deferred to runtime to allow Streamlit Cloud deployment
def validate_api_key():
    """Validate that GOOGLE_API_KEY is set. Call this at runtime, not at import."""
    if not GOOGLE_API_KEY:
        raise ValueError(
            "GOOGLE_API_KEY not found in environment variables. "
            "Please set it in .env file (local) or Streamlit secrets (cloud)."
        )
