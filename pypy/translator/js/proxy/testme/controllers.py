from turbogears import controllers, expose
from cherrypy import session
from msgstruct import *
import PIL.Image
import zlib
import socket
import urllib
import re
from servermessage import ServerMessage, log
from random import random
from md5 import md5


class Root(controllers.Root):

    _serverMessage = {}

    host = 'localhost'
    port = re.findall('value=".*"', urllib.urlopen('http://%s:8000' % host).read())[0]
    port = int(port[7:-1])
    
    def serverMessage(self):
        sessionid = session['_id']
        if sessionid not in self._serverMessage:
            self._serverMessage[sessionid] = ServerMessage()
        return self._serverMessage[sessionid]

    def sessionSocket(self, close=False):
        sm = self.serverMessage()
        if sm.socket is None:
            sm.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sm.socket.connect((self.host, self.port))
            sm.socket.send(message(CMSG_PROTO_VERSION, 2))
            #XXX todo: session.socket.close() after a timeout
        return sm.socket

    @expose(html='testme.templates.bnb')
    def index(self):
        self._close()
        session['_id'] = md5(str(random())).hexdigest() #force new session id to restart a game!
        return dict()

    @expose(format='json')
    def ping(self):
        self.sessionSocket().send(message(CMSG_PING))
        return self.recv()

    @expose(format='json')
    def recv(self):
        #XXX hangs if not first sending a ping!
        sm   = self.serverMessage()
        size = 1024
        data = sm.data + self.sessionSocket().recv(size)
        while sm.n_header_lines > 0 and '\n' in data:
            sm.n_header_lines -= 1
            header_line, data = data.split('\n',1)
            #log('RECEIVED HEADER LINE: %s' % header_line)
        
        #log('RECEIVED DATA CONTAINS %d BYTES' % len(data))
        messages = []
        while data:
            values, data = decodemessage(data)
            if not values:
                break  # incomplete message
            messageOutput = sm.dispatch(*values)
            if messageOutput:
                if type(messageOutput) is type([]):
                    messages += messageOutput
                else:
                    messages.append(messageOutput)
        sm.data = data
        #log('RECEIVED DATA REMAINING CONTAINS %d BYTES' % len(data))

        #if messages:
        #    log('MESSAGES:%s' % messages)
        return dict(messages=messages)

    def _close(self):
        sessionid = session['_id']
        if sessionid in self._serverMessage:
            sm = self.serverMessage()
            if sm.socket is not None:
                sm.socket.close()
            del self._serverMessage[sessionid]

    @expose(format='json')
    def close(self):
        self._close()
        return dict()

