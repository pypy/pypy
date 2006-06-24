
""" xmlhttp controllers, usefull for testing
"""

import turbogears
import cherrypy
from pypy.translator.js.demo.jsdemo.controllers import Root
from pypy.rpython.ootypesystem.bltregistry import BasicExternal, MethodDesc

from pypy.translator.js.proxy.testme.servermessage import ServerMessage, PMSG_INLINE_FRAME
from pypy.translator.js.proxy.testme.msgstruct import *
from cherrypy import session

import re, time, sys, os, urllib, socket

class SortY(object):
    def __init__(self, data):
        self.data = data
    
    def __cmp__(self, other):
        return cmp(self.data['y'], other.data['y'])

# Needed double inheritance for both server job
# and semi-transparent communication proxy
class BnbRoot(Root, BasicExternal):
    _serverMessage = {}

    host = 'localhost'
    try:
        port = re.findall('value=".*"', urllib.urlopen('http://%s:8000' % host).read())[0]
    except IOError:
        import sys
        log("ERROR: Can't connect to BnB server on %s:8000" % host)
        sys.exit()
    port = int(port[7:-1])
    
    _methods = {
        'get_message' : MethodDesc( [('callback', (lambda : None))] , {'aa':[{'aa':'bb'}]})
    }
    
    def serverMessage(self):
        sessionid = session['_id']
        if sessionid not in self._serverMessage:
            self._serverMessage[sessionid] = ServerMessage('static/images')
        return self._serverMessage[sessionid]
    
    @turbogears.expose(html="jsdemo.templates.bnb")
    def index(self):
        import time
        self.last_frames = set()
        return dict(now=time.ctime(), onload=self.jsname, code=self.jssource)
    
    def sessionSocket(self, close=False):
        sm = self.serverMessage()
        if sm.socket is None:
            player_id = 0 #XXX hardcoded for now
            sm.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sm.socket.connect((self.host, self.port))
            sm.socket.send(message(CMSG_PROTO_VERSION, 2))  #, version a kuku
            sm.socket.send(message(CMSG_ENABLE_SOUND, 0))   #, has_sound
            sm.socket.send(message(CMSG_ENABLE_MUSIC, 0))   #, has_music
            sm.socket.send(message(CMSG_UDP_PORT, "\\"))    #, port
            sm.socket.send(message(CMSG_PING))              #so server starts sending data
            #sm.socket.send(message(CMSG_ADD_PLAYER, player_id))
            #sm.socket.send(message(CMSG_PLAYER_NAME, player_id, 'PyPy'))
            #XXX todo: session.socket.close() after a timeout
        return sm.socket
    
    @turbogears.expose(format="json")
    def get_message(self):
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
        to_append = []
        next_last = set()
        keep_sprites = []
        for i, msg in enumerate(messages):
            if msg['type'] == PMSG_INLINE_FRAME:
                for next in msg['sprites']:
#                    if not next in self.last_frames:
                        # sort them by y axis
                    to_append.append(SortY({'type':'sprite', 'x':str(next[1]), 'y':str(next[2]), 'icon_code':str(next[0])}))
                    #next_last.add(next)
                del messages[i]
        
        self.last_frames = next_last
        to_append.sort()
        messages += [i.data for i in to_append]
        
        messages.append({'type':'end_frame'})
        return dict(messages=messages)

BnbRootInstance = BnbRoot()
