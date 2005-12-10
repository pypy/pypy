import SocketServer
import sys, time

# user-accessible port
PORT = 8037

class EchoServer(SocketServer.TCPServer):

    def __init__(self, *args, **kwargs):
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

if __name__ == "__main__":
    server = EchoServer(("", PORT), EchoRequestHandler)
    server.serve()
