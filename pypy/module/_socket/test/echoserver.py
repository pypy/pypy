import socket, SocketServer
import sys, time

# user-accessible port
PORT = 8037

class EchoServer(SocketServer.TCPServer):

    def __init__(self, *args, **kwargs):
        self.address_family = kwargs["address_family"]
        del kwargs["address_family"]
        SocketServer.TCPServer.__init__(self, *args, **kwargs)
        self.stop = False
        
    def handle_error(self, request, client_address):
        self.stop = True

    def serve(self):
        while not self.stop:
            self.handle_request()

class EchoRequestHandler(SocketServer.StreamRequestHandler):

    def handle(self):
        while True:
            client_string = ""
            char = ""
            while char != "\n":
                char = self.rfile.read(1)
                client_string += char
            if client_string.startswith("shutdown"):
                raise RuntimeError()
            self.wfile.write(client_string)

def start_server(address_family=socket.AF_INET):
    server = EchoServer(("", PORT), EchoRequestHandler, address_family=address_family)
    server.serve()    

if __name__ == "__main__":
    start_server()
