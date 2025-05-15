from contextlib import asynccontextmanager
from collections.abc import AsyncIterator
from dataclasses import dataclass
from typing import Dict, Any, List, Optional

from mcp.server.fastmcp import FastMCP, Context
from splunklib import client
from splunklib.results import ResultsReader
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from src.splunk_client import get_splunk_service
import logging
import time

# Create logs directory if it doesn't exist
log_dir = os.path.dirname(os.path.dirname(__file__)) + '/logs'
os.makedirs(log_dir, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    filename=log_dir + '/mcp_splunk_server.log'
)
logger = logging.getLogger(__name__)

@dataclass
class SplunkContext:
    service: client.Service

@asynccontextmanager
async def splunk_lifespan(server: FastMCP) -> AsyncIterator[SplunkContext]:
    """Manage Splunk connection lifecycle"""
    logger.info("Initializing Splunk connection...")
    try:
        service = get_splunk_service()
        logger.info("Splunk connection established successfully")
        yield SplunkContext(service=service)
    except Exception as e:
        logger.error(f"Failed to establish Splunk connection: {str(e)}")
        raise
    finally:
        logger.info("Closing Splunk connection")

# Initialize FastMCP server
mcp = FastMCP(
    "MCP Server for Splunk",
    description="MCP server for Splunk interaction",
    version="0.1.0",
    lifespan=splunk_lifespan
)

@mcp.tool()
def get_splunk_health(ctx: Context) -> Dict[str, Any]:
    """
    Get Splunk connection health status
    
    Returns:
        Dict containing Splunk connection status and version information
    """
    logger.info("Checking Splunk health status...")
    try:
        service = ctx.request_context.lifespan_context.service
        info = {
            "status": "connected",
            "version": service.info["version"],
            "server_name": service.info.get("host", "unknown")
        }
        logger.info(f"Health check successful: {info}")
        return info
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}")
        raise

@mcp.tool()
def list_indexes(ctx: Context) -> Dict[str, Any]:
    """
    Retrieves a list of all accessible indexes from the configured Splunk instance.
    
    Returns:
        Dict containing list of indexes and count
    """
    service = ctx.request_context.lifespan_context.service
    indexes = [index.name for index in service.indexes]
    return {
        "indexes": sorted(indexes),
        "count": len(indexes)
    }

@mcp.tool()
def run_oneshot_search(
    ctx: Context,
    query: str,
    earliest_time: Optional[str] = "-15m",
    latest_time: Optional[str] = "now",
    max_results: Optional[int] = 100
) -> Dict[str, Any]:
    """
    Execute a one-shot Splunk search that returns results immediately. Use this tool for quick,
    simple searches where you need immediate results and don't need to track job progress.
    
    Args:
        query: The Splunk search query (SPL) to execute
        earliest_time: Search start time (default: "-15m")
        latest_time: Search end time (default: "now")
        max_results: Maximum number of results to return (default: 100)
    
    Returns:
        Dict containing:
            - search_results: List of search results
            - results_count: Number of results returned
            - query_executed: The query that was executed
    
    Example:
        # These are equivalent:
        run_oneshot_search(query="index=main | head 10")
        run_oneshot_search(query="search index=main | head 10")
    """
    service = ctx.request_context.lifespan_context.service
    
    # Add 'search' command if not present and query doesn't start with a pipe
    if not query.strip().lower().startswith(('search ', '| ')):
        query = f"search {query}"
    
    logger.info(f"Executing one-shot search: {query}")
    
    try:
        kwargs = {
            "earliest_time": earliest_time,
            "latest_time": latest_time,
            "count": max_results
        }
        
        results = []
        job = service.jobs.oneshot(query, **kwargs)
        
        for result in ResultsReader(job):
            if isinstance(result, dict):
                results.append(result)
            if len(results) >= max_results:
                break
        
        return {
            "search_results": results,
            "results_count": len(results),
            "query_executed": query
        }
    except Exception as e:
        logger.error(f"One-shot search failed: {str(e)}")
        raise

@mcp.tool()
def run_splunk_search(
    ctx: Context,
    query: str,
    earliest_time: Optional[str] = "-24h",
    latest_time: Optional[str] = "now"
) -> Dict[str, Any]:
    """
    Execute a normal Splunk search job with progress tracking. Use this tool for complex or
    long-running searches where you need to track progress and get detailed job information.
    
    Args:
        query: The Splunk search query (SPL) to execute
        earliest_time: Search start time (default: "-24h")
        latest_time: Search end time (default: "now")
    
    Returns:
        Dict containing:
            - job_id: Search job ID (sid)
            - is_done: Whether the search is complete
            - scan_count: Number of events scanned
            - event_count: Number of events matched
            - results: Search results
            - query_executed: The actual query that was executed
    
    Example:
        # These are equivalent:
        run_splunk_search(query="index=* | stats count by source")
        run_splunk_search(query="search index=* | stats count by source")
    """
    # Add 'search' command if not present and query doesn't start with a pipe
    if not query.strip().lower().startswith(('search ', '| ')):
        query = f"search {query}"
    
    logger.info(f"Starting normal search with query: {query}")
    service = ctx.request_context.lifespan_context.service
    
    try:
        # Create the search job
        job = service.jobs.create(
            query,
            earliest_time=earliest_time,
            latest_time=latest_time
        )
        
        # Poll for completion
        while not job.is_done():
            stats = job.content
            progress = {
                "done": stats.get('isDone', '0') == '1',
                "progress": float(stats.get('doneProgress', 0)) * 100,
                "scan_progress": float(stats.get('scanCount', 0)),
                "event_progress": float(stats.get('eventCount', 0))
            }
            logger.info(
                f"Search job {job.sid} in progress... "
                f"Progress: {progress['progress']:.1f}%, "
                f"Scanned: {progress['scan_progress']} events, "
                f"Matched: {progress['event_progress']} events"
            )
            time.sleep(2)
        
        # Get the final results
        results = []
        for result in job.results():
            results.append(result)
        
        # Get final job stats
        stats = job.content
        
        return {
            "job_id": job.sid,
            "is_done": True,
            "scan_count": int(float(stats.get('scanCount', 0))),
            "event_count": int(float(stats.get('eventCount', 0))),
            "results": results,
            "query_executed": query,
            "duration": float(stats.get('runDuration', 0)),
            "status": {
                "progress": 100,
                "is_finalized": stats.get('isFinalized', '0') == '1',
                "is_failed": stats.get('isFailed', '0') == '1'
            }
        }
    except Exception as e:
        logger.error(f"Search failed: {str(e)}")
        raise

@mcp.tool()
def list_apps(ctx: Context) -> Dict[str, Any]:
    """
    List all installed Splunk apps.
    
    Returns:
        Dict containing list of apps and their properties
    """
    logger.info("Retrieving list of Splunk apps")
    service = ctx.request_context.lifespan_context.service
    
    try:
        apps = []
        for app in service.apps:
            apps.append({
                "name": app.name,
                "label": app.content.get("label"),
                "version": app.content.get("version"),
                "description": app.content.get("description"),
                "author": app.content.get("author"),
                "visible": app.content.get("visible")
            })
        
        return {
            "count": len(apps),
            "apps": apps
        }
    except Exception as e:
        logger.error(f"Failed to list apps: {str(e)}")
        raise

@mcp.tool()
def list_users(ctx: Context) -> Dict[str, Any]:
    """
    List all Splunk users.
    
    Returns:
        Dict containing list of users and their properties
    """
    logger.info("Retrieving list of Splunk users")
    service = ctx.request_context.lifespan_context.service
    
    try:
        users = []
        for user in service.users:
            users.append({
                "username": user.name,
                "realname": user.content.get("realname"),
                "email": user.content.get("email"),
                "roles": user.content.get("roles", []),
                "type": user.content.get("type"),
                "defaultApp": user.content.get("defaultApp")
            })
        
        return {
            "count": len(users),
            "users": users
        }
    except Exception as e:
        logger.error(f"Failed to list users: {str(e)}")
        raise

@mcp.tool()
def list_kvstore_collections_by_app(
    ctx: Context,
    app: Optional[str] = None
) -> Dict[str, Any]:
    """
    List all KV Store collections in Splunk. Use this tool to discover available KV Store collections
    either across all apps or within a specific app.
    
    Args:
        app: Optional app name (e.g., 'search', 'myapp'). If provided, lists collections only from 
            that specific app. If not provided, lists collections from all accessible apps.
    
    Returns:
        Dict containing:
            - count: Total number of collections found
            - collections: List of collections with their properties:
                - name: Collection name
                - fields: Field definitions
                - accelerated_fields: Indexed fields
                - replicated: Whether collection is replicated
    
    Example:
        To list collections in 'search' app:
        list_kvstore_collections(app='search')
        
        To list all collections:
        list_kvstore_collections()
    """
    logger.info(f"Retrieving KV Store collections for app: {app if app else 'all apps'}")
    service = ctx.request_context.lifespan_context.service
    
    try:
        collections = []
        kvstore = service.kvstore
        
        if app:
            kvstore = service.kvstore[app]
        
        for collection in kvstore:
            collections.append({
                "name": collection.name,
                "fields": collection.content.get("fields", []),
                "accelerated_fields": collection.content.get("accelerated_fields", {}),
                "replicated": collection.content.get("replicated", False)
            })
        
        return {
            "count": len(collections),
            "collections": collections
        }
    except Exception as e:
        logger.error(f"Failed to list KV Store collections: {str(e)}")
        raise

@mcp.tool()
def get_kvstore_data(
    ctx: Context,
    collection: str,
    app: Optional[str] = None,
    query: Optional[Dict] = None
) -> Dict[str, Any]:
    """
    Retrieve data from a specific KV Store collection. Use this tool when you need to fetch
    documents from a KV Store collection, with optional filtering capabilities.
    
    Args:
        collection: Name of the collection to retrieve data from
        app: Optional app name where the collection resides. If not provided, searches in
            default app context
        query: Optional MongoDB-style query filter (e.g., {"field": "value"}) to filter
            the documents to retrieve
    
    Returns:
        Dict containing:
            - count: Number of documents retrieved
            - documents: List of documents from the collection
    
    Example:
        To get all documents:
        get_collection_data(collection="mycollection", app="myapp")
        
        To get filtered documents:
        get_collection_data(collection="mycollection", app="myapp", 
                          query={"status": "active"})
    """
    logger.info(f"Retrieving data from KV Store collection: {collection}")
    service = ctx.request_context.lifespan_context.service
    
    try:
        if app:
            collection = service.kvstore[app][collection]
        else:
            collection = service.kvstore[collection]
            
        documents = collection.data.query(query) if query else collection.data.query()
        
        return {
            "count": len(documents),
            "documents": documents
        }
    except Exception as e:
        logger.error(f"Failed to get KV store data: {str(e)}")
        raise

@mcp.tool()
def create_kvstore_collection(
    ctx: Context,
    app: str,
    collection: str,
    fields: Optional[List[Dict[str, Any]]] = None,
    accelerated_fields: Optional[Dict[str, List[List[str]]]] = None,
    replicated: bool = True
) -> Dict[str, Any]:
    """
    Create a new KV Store collection in a specified Splunk app. Use this tool when you need
    to create a new collection for storing custom data in Splunk.
    
    Args:
        app: Name of the app where the collection should be created (e.g., 'search', 'myapp')
        collection: Name for the new collection (must be unique within the app)
        fields: Optional list of field definitions to structure the collection data. Each field
            definition should be a dict with 'name', 'type', and optional 'required' keys
        accelerated_fields: Optional dict defining indexed fields for better query performance
        replicated: Whether the collection should be replicated across search heads
    
    Returns:
        Dict containing:
            - status: Operation status
            - collection: Details of the created collection
    
    Example:
        Create a simple collection:
        create_kvstore_collection(app="myapp", collection="users")
        
        Create a structured collection:
        create_kvstore_collection(
            app="myapp",
            collection="users",
            fields=[
                {"name": "username", "type": "string", "required": True},
                {"name": "age", "type": "number"}
            ],
            accelerated_fields={"username_idx": [["username"]]}
        )
    """
    logger.info(f"Creating new KV Store collection: {collection} in app: {app}")
    service = ctx.request_context.lifespan_context.service
    
    try:
        collection_config = {
            "name": collection,
            "replicated": replicated
        }
        
        if fields:
            collection_config["field"] = fields
            
        if accelerated_fields:
            collection_config["accelerated_fields"] = accelerated_fields
            
        new_collection = service.kvstore[app].create(
            name=collection,
            **collection_config
        )
        
        return {
            "status": "success",
            "collection": {
                "name": new_collection.name,
                "fields": new_collection.content.get("fields", []),
                "accelerated_fields": new_collection.content.get("accelerated_fields", {}),
                "replicated": new_collection.content.get("replicated", False)
            }
        }
    except Exception as e:
        logger.error(f"Failed to create KV Store collection: {str(e)}")
        raise

@mcp.tool()
def get_configurations(
    ctx: Context,
    conf_file: str,
    stanza: Optional[str] = None
) -> Dict[str, Any]:
    """
    Get Splunk configurations.
    
    Args:
        conf_file: Configuration file name (e.g., 'props', 'transforms', 'inputs')
        stanza: Optional stanza name to get specific configuration
    
    Returns:
        Dict containing configuration settings
    """
    logger.info(f"Retrieving configurations from {conf_file}")
    service = ctx.request_context.lifespan_context.service
    
    try:
        confs = service.confs[conf_file]
        
        if stanza:
            stanza_obj = confs[stanza]
            return {
                "stanza": stanza,
                "settings": dict(stanza_obj.content)
            }
        
        all_stanzas = {}
        for stanza_obj in confs:
            all_stanzas[stanza_obj.name] = dict(stanza_obj.content)
            
        return {
            "file": conf_file,
            "stanzas": all_stanzas
        }
    except Exception as e:
        logger.error(f"Failed to get configurations: {str(e)}")
        raise