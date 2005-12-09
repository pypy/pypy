import SocketServer
import sys, time

# user-accessible port
PORT = 8037

class EchoRequestHandler(SocketServer.StreamRequestHandler):

    def handle(self):
        while True:
            client_string = ""
            char = ""
            while char != "\n":
                char = self.rfile.read(1)
                client_string += char
            if client_string.startswith("shutdown"):
                sys.exit(1)
            self.wfile.write(client_string)

if __name__ == "__main__":
    server = SocketServer.TCPServer(("", PORT), EchoRequestHandler)
    server.serve_forever()
