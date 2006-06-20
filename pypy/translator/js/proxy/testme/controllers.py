from turbogears import controllers, expose
from cherrypy import session
from msgstruct import *
import PIL.Image
import zlib
import socket
import urllib
import re
from servermessage import ServerMessage, log, PMSG_INLINE_FRAME
from random import random
from md5 import md5


class Root(controllers.Root):

    _serverMessage = {}

    host = 'localhost'
    try:
        port = re.findall('value=".*"', urllib.urlopen('http://%s:8000' % host).read())[0]
    except IOError:
        import sys
        log("ERROR: Can't connect to BnB server on %s:8000" % host)
        sys.exit()
    port = int(port[7:-1])
    
    def serverMessage(self):
        sessionid = session['_id']
        if sessionid not in self._serverMessage:
            self._serverMessage[sessionid] = ServerMessage()
        return self._serverMessage[sessionid]

    def sessionSocket(self, close=False):
        sm = self.serverMessage()
        if sm.socket is None:
            player_id = 0 #XXX hardcoded for now
            sm.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sm.socket.connect((self.host, self.port))
            sm.socket.send(message(CMSG_PROTO_VERSION, 2))  #, version
            sm.socket.send(message(CMSG_ENABLE_SOUND, 0))   #, has_sound
            sm.socket.send(message(CMSG_ENABLE_MUSIC, 0))   #, has_music
            sm.socket.send(message(CMSG_UDP_PORT, "\\"))    #, port
            sm.socket.send(message(CMSG_PING))              #so server starts sending data
            #sm.socket.send(message(CMSG_ADD_PLAYER, player_id))
            #sm.socket.send(message(CMSG_PLAYER_NAME, player_id, 'PyPy'))
            #XXX todo: session.socket.close() after a timeout
        return sm.socket

    @expose(html='testme.templates.bnb')
    def index(self):
        self._close()
        session['_id'] = md5(str(random())).hexdigest() #force new session id to restart a game!
        return dict()

    @expose(format='json')
    def player_name(self, name):
        self.sessionSocket().send(message(CMSG_PLAYER_NAME, name))
        return self.recv()

    @expose(format='json')
    def add_player(self, player_id):
        self.sessionSocket().send(message(CMSG_ADD_PLAYER, int(player_id)))
        return self.recv()

    @expose(format='json')
    def remove_player(self, player_id):
        self.sessionSocket().send(message(CMSG_REMOVE_PLAYER, int(player_id)))
        return self.recv()

    @expose(format='json')
    def key(self, player_id, keynum):
        self.sessionSocket().send(message(CMSG_KEY, int(player_id), int(keynum)))
        return self.recv()

    @expose(format='json')
    def recv(self):
        #XXX hangs if not first sending CMSG_PING!
        sm   = self.serverMessage()
        size = 10000 #XXX should really loop until all data is handled
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

        len_before = len(messages)
        #XXX we could do better by not generating only the last inline_frame message anyway!
        inline_frames = [i for i,msg in enumerate(messages) if msg['type'] == PMSG_INLINE_FRAME]
        for i in reversed(inline_frames[:-1]):
            del messages[i]

        #if messages:
        #    log('MESSAGES:lenbefore=%d, inline_frames=%s, lenafter=%d' % (
        #        len_before, inline_frames, len(messages)))
        return dict(messages=messages)

    @expose(format='json')
    def close(self):
        self._close()
        return dict()

    def _close(self):
        sessionid = session['_id']
        if sessionid in self._serverMessage:
            sm = self.serverMessage()
            if sm.socket is not None:
                sm.socket.close()
            del self._serverMessage[sessionid]

