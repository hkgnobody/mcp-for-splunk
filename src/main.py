# src/main.py
import logging
from fastapi import FastAPI, Response, status
from modelcontext.server import Server, ToolInfo
# Import the connection function and custom error from the connector module
from .splunk_connector import get_splunk_service, SplunkConnectionError

# Configure basic logging
# Consider making the log level configurable via environment variable later
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# --- MCP Server Setup ---
# Create MCP Server instance.
# The 'tools' list will be populated later as tools are implemented.
mcp_server = Server(
    tools=[] # Start with an empty list of tools for the MVP base
)

# The MCP Server instance (mcp_server) creates its own FastAPI app.
# We get a reference to it to add custom routes like /health.
app: FastAPI = mcp_server.app
app.title = "Splunk MCP Server"
app.version = "0.0.1" # Initial MVP version

# --- Event Handlers ---
@app.on_event("startup")
async def startup_event():
    """
    Event handler triggered when the FastAPI application starts.
    Attempts an initial connection to Splunk to verify configuration early.
    """
    logger.info(f"Starting {app.title} v{app.version}...")
    try:
        # Attempt to establish the initial connection.
        # The service object itself isn't stored here, just used for the check.
        get_splunk_service()
        logger.info("Initial connection check to Splunk successful during startup.")
    except SplunkConnectionError as e:
        # Log a warning if the initial connection fails, but allow the server to start.
        # Connection attempts will be retried when tools are called.
        logger.warning(f"WARNING: Could not connect to Splunk on startup: {e}. "
                       "The server will start, but tools may fail until connection is established.")
    except ValueError as e:
        # Log configuration errors critically, as they likely prevent operation.
        logger.error(f"CRITICAL: Configuration error for Splunk connection during startup: {e}")
    except Exception as e:
        # Catch any other unexpected errors during the startup check.
        logger.error(f"CRITICAL: An unexpected error occurred during startup Splunk connection check: {e}", exc_info=True)
    logger.info("Startup complete. MCP server is running.")


@app.on_event("shutdown")
async def shutdown_event():
    """
    Event handler triggered when the FastAPI application shuts down.
    """
    logger.info(f"Shutting down {app.title}.")
    # Add any cleanup tasks here if necessary (e.g., closing persistent connections if any were managed differently)


# --- Custom Routes ---
@app.get("/health", tags=["Management"], status_code=status.HTTP_200_OK)
async def health_check(response: Response):
    """
    Performs a health check of the server and its critical dependency (Splunk).

    Returns a status indicating server health and Splunk connectivity.
    Sets HTTP status code to 503 Service Unavailable if Splunk connection fails.
    """
    splunk_status = "disconnected"
    splunk_version = None
    splunk_error_message = None
    service_available = True # Assume available unless Splunk check fails

    try:
        # Attempt to get the Splunk service; this will trigger a connection attempt if needed.
        service = get_splunk_service()
        if service and service.info:
            # Successfully connected and retrieved info.
            splunk_status = "connected"
            splunk_version = service.info.get("version", "N/A")
        else:
            # This case should ideally not happen if get_splunk_service raises errors correctly.
            splunk_status = "unknown_state"
            splunk_error_message = "Splunk service object is missing or info could not be retrieved."
            service_available = False

    except SplunkConnectionError as e:
        splunk_status = "connection_error"
        splunk_error_message = str(e)
        service_available = False
        logger.warning(f"Health Check: Splunk connection error: {e}") # Log as warning during health check
    except ValueError as e: # Catch config errors
        splunk_status = "configuration_error"
        splunk_error_message = str(e)
        service_available = False
        logger.error(f"Health Check: Splunk configuration error: {e}") # Log as error
    except Exception as e:
        splunk_status = "unexpected_error"
        splunk_error_message = str(e)
        service_available = False
        logger.error(f"Health Check: Unexpected error during Splunk connection: {e}", exc_info=True)

    # Set HTTP status code based on Splunk connectivity
    if not service_available:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE

    return {
        "server_status": "ok", # The MCP server itself is running
        "service_available": service_available, # Indicates if core dependency (Splunk) is reachable
        "splunk_connectivity": {
            "status": splunk_status,
            "splunk_version": splunk_version,
            "error_details": splunk_error_message
        }
    }

# --- Main Execution ---
# The MCP server's app ('app') will be run by Uvicorn as configured
# in the Dockerfile or docker-compose.yml.
# Example command: uvicorn src.main:app --host 0.0.0.0 --port 8000 --reload
