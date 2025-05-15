import os
from typing import Optional
from splunklib import client
from dotenv import load_dotenv

load_dotenv()

def get_splunk_service() -> client.Service:
    """Create and return a Splunk service connection"""
    host = os.getenv("SPLUNK_HOST", "localhost")
    port = int(os.getenv("SPLUNK_PORT", "8089"))
    username = os.getenv("SPLUNK_USERNAME")
    password = os.getenv("SPLUNK_PASSWORD")
    token = os.getenv("SPLUNK_TOKEN")
    
    try:
        if token:
            service = client.Service(
                host=host,
                port=port,
                token=token,
                verify=False
            )
        elif username and password:
            service = client.Service(
                host=host,
                port=port,
                username=username,
                password=password,
                verify=False
            )
        else:
            raise ValueError("Either SPLUNK_TOKEN or SPLUNK_USERNAME/SPLUNK_PASSWORD must be provided")
        
        # Explicitly attempt login and verify connection
        service.login()
        
        # Test the connection by trying to get server info
        _ = service.info
        
        return service
        
    except Exception as e:
        raise ValueError(f"Failed to connect to Splunk: {str(e)}\n"
                        f"Using host={host}, port={port}, "
                        f"auth_type={'token' if token else 'username/password'}")