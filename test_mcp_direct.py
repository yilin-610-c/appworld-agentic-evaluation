import asyncio
import os
import json
import subprocess
import time
import sys
from contextlib import asynccontextmanager

# Try to import MCPClient from appworld if available
try:
    from appworld.serve._mcp import MCPClient
except ImportError:
    print("Error: appworld not found. Make sure you are in the correct environment.")
    sys.exit(1)

# Configuration
API_PORT = 9005  # Use different ports to avoid conflicts
MCP_PORT = 10005
TASK_ID = "82e2fac_1"

def check_port_available(port):
    import socket
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.bind(('127.0.0.1', port))
        sock.close()
        return True
    except OSError:
        sock.close()
        return False

@asynccontextmanager
async def run_servers():
    print(f"Starting AppWorld servers for task {TASK_ID}...")
    
    # Clean up ports if needed
    for port in [API_PORT, MCP_PORT]:
        if not check_port_available(port):
            print(f"Port {port} in use, attempting to kill...")
            subprocess.run(f"lsof -ti :{port} | xargs kill -9", shell=True)
            await asyncio.sleep(1)

    # Set APPWORLD_ROOT
    env = os.environ.copy()
    appworld_root = '/home/lyl610/green1112/appworld'
    env['APPWORLD_ROOT'] = appworld_root
    
    # Start API Server
    print(f"Starting API Server on port {API_PORT}...")
    # OLD:
    # api_cmd = [
    #     "python", "-m", "appworld.cli",
    #     "serve", "apis",
    #     "--port", str(API_PORT)
    # ]
    # NEW: Use custom script to serve specific task
    script_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'src', 'green_agent', 'serve_task_apis.py')
    api_cmd = ["python", script_path, TASK_ID, str(API_PORT)]
    
    api_proc = subprocess.Popen(
        api_cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=env,
        cwd=os.getcwd() # Use current dir to find the script
    )
    
    # Wait longer for API server to initialize task DB
    print("Waiting for API Server to initialize...")
    await asyncio.sleep(8) 
    if api_proc.poll() is not None:
        _, stderr = api_proc.communicate()
        raise Exception(f"API Server failed: {stderr.decode()}")
    print("✓ API Server started")

    # Start MCP Server
    print(f"Starting MCP Server on port {MCP_PORT}...")
    from appworld.apps import get_all_apps
    app_names = ",".join(get_all_apps(skip_admin=True, skip_api_docs=True))
    
    mcp_cmd = [
        "python", "-m", "appworld.cli",
        "serve", "mcp", "http",
        "--port", str(MCP_PORT),
        "--remote-apis-url", f"http://localhost:{API_PORT}",
        "--app-names", app_names,
        "--output-type", "both"
    ]
    mcp_proc = subprocess.Popen(
        mcp_cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=env,
        cwd=appworld_root
    )
    
    await asyncio.sleep(5)
    if mcp_proc.poll() is not None:
        _, stderr = mcp_proc.communicate()
        raise Exception(f"MCP Server failed: {stderr.decode()}")
    print("✓ MCP Server started")

    try:
        yield f"http://localhost:{MCP_PORT}/mcp"
    finally:
        print("Shutting down servers...")
        mcp_proc.terminate()
        api_proc.terminate()
        mcp_proc.wait()
        api_proc.wait()

async def test_tools():
    async with run_servers() as mcp_url:
        print(f"\nConnecting to MCP: {mcp_url}")
        
        mcp_config = {
            "type": "http",
            "remote_mcp_url": f"http://localhost:{MCP_PORT}"
        }
        
        client = MCPClient.from_dict(mcp_config)
        client.connect()
        print("✓ Connected to MCP")
        
        tools = client.list_tools()
        print(f"✓ Discovered {len(tools)} tools")
        
        # Test 1: supervisor__show_account_passwords
        print("\n--- Testing supervisor__show_account_passwords ---")
        try:
            result = client.call_tool("supervisor__show_account_passwords", arguments={})
            print("Result Type:", type(result))
            print("Result Raw:", result)
            print("Result JSON:", json.dumps(result, indent=2, default=str))
        except Exception as e:
            print(f"Error: {e}")

        # Test 2: supervisor__show_profile
        print("\n--- Testing supervisor__show_profile ---")
        try:
            result = client.call_tool("supervisor__show_profile", arguments={})
            print("Result Type:", type(result))
            print("Result Raw:", result)
            print("Result JSON:", json.dumps(result, indent=2, default=str))
        except Exception as e:
            print(f"Error: {e}")
            
        client.disconnect()

if __name__ == "__main__":
    asyncio.run(test_tools())

