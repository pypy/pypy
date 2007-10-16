
""" xmlhttp controllers, usefull for testing
"""

import py
from pypy.rpython.ootypesystem.bltregistry import BasicExternal, MethodDesc

from pypy.translator.js.examples.bnb.servermessage import log, ServerMessage,\
    PMSG_INLINE_FRAME, PMSG_DEF_ICON
from pypy.translator.js.examples.bnb.msgstruct import *
from pypy.translator.js.lib.support import callback
from pypy.translator.js.lib import server

import re, time, sys, os, urllib, socket, copy, md5, random

class SpriteManager(object):
    def __init__(self):
        self.sprite_sets = {}
        self.positions = {}
        self.num = 0
        self.next_pos = {}
        self.last_seen = set()
        self.seen = set()
        self.num_frame = 0
        self.z_index = {}
    
    def def_icon(self, icon_code):
        self.sprite_sets[icon_code] = []
    
    def get_frame_number(self):
        self.num_frame += 1
    
    def get_sprite(self, icon_code, x, y):
        try:
            to_ret = self.positions[(icon_code, x, y)]
            del self.positions[(icon_code, x, y)]
            self.next_pos[(icon_code, x, y)] = to_ret
            self.seen.add((icon_code, to_ret))
            return "still", to_ret
        except KeyError:
            try:
                try:
                    to_ret = self.sprite_sets[icon_code].pop()
                except KeyError:
                    self.def_icon(icon_code)
                    raise IndexError
                self.next_pos[(icon_code, x, y)] = to_ret
                self.seen.add((icon_code, to_ret))
                return "move", to_ret
            except IndexError:
                next = self.num
                self.num += 1
                self.next_pos[(icon_code, x, y)] = next
                self.seen.add((icon_code, next))
                return "new", next
    
    def end_frame(self):
        self.positions = copy.deepcopy(self.next_pos)
        self.next_pos = {}
        to_ret = []
        for ic, i in self.last_seen - self.seen:
            self.sprite_sets[ic].append(i)
            to_ret.append(i)
        self.last_seen = self.seen
        self.seen = set()
        return to_ret

class ExportedMethods(server.ExportedMethods):
    _serverMessage = {}
    _spriteManagers = {}

    host = 'localhost'

    def getport(self):
        if hasattr(self, '_port'):
            return self._port
        try:
            port = re.findall('value=".*"', urllib.urlopen('http://%s:8000' % self.host).read())[0]
            port = int(port[7:-1])
        except IOError:
            log("ERROR: Can't connect to BnB server on %s:8000" % self.host)
            raise IOError
        except IndexError:
            log("ERROR: Connected to BnB server but unable to detect a running game")
            raise IOError
        self._port = port
        return port
    port = property(getport)

    #def _close(self, sessionid):
    #    if sessionid in self._serverMessage:
    #        sm = self.serverMessage()
    #        if sm.socket is not None:
    #            sm.socket.close()
    #        del self._serverMessage[sessionid]
    def get_sprite_manager(self, sessionid):
        return self._spriteManagers[sessionid]

    def sessionSocket(self, sessionid, close=False):
        sm = self.serverMessage(sessionid)
        if sm.socket is None:
            player_id = 0 #XXX hardcoded for now
            sm.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sm.socket.connect((self.host, self.port))
            sm.socket.send(message(CMSG_PROTO_VERSION, 2))  #, version a kuku
            sm.socket.send(message(CMSG_ENABLE_SOUND, 0))   #, has_sound
            sm.socket.send(message(CMSG_ENABLE_MUSIC, 0))   #, has_music
            sm.socket.send(message(CMSG_UDP_PORT, "\\"))    #, port
            sm.socket.send(message(CMSG_PING))              #so server starts sending data
        return sm.socket

    def _closeIdleConnections(self):
        t = time.time() - 20.0 #20 seconds until considered idle
        for sessionid, sm in self._serverMessage.items():
            if sm.last_active < t:
                log("Close connection with sessionid %s because it was idle for %.1f seconds" % (
                    sessionid, time.time() - sm.last_active))
                if sm.socket is not None:
                    sm.socket.close()
                del self._serverMessage[sessionid]

    def serverMessage(self, sessionid):
        self._closeIdleConnections()
        if sessionid not in self._serverMessage:
            self._serverMessage[sessionid] = ServerMessage('data/images')
        return self._serverMessage[sessionid]

    @callback(retval=None)
    def player_name(self, player_id=0, name="", sessionid=""):
        log("Changing player #%s name to %s" % (player_id, name))
        socket = self.sessionSocket(sessionid)
        socket.send(message(CMSG_PLAYER_NAME, int(player_id), name))

    @callback(retval=None)
    def add_player(self, player_id=0, sessionid=""):
        log("Adding player " + player_id)
        socket = self.sessionSocket(sessionid)
        socket.send(message(CMSG_ADD_PLAYER, int(player_id)))

    @callback(retval=None)
    def remove_player(self, player_id=0, sessionid=""):
        log("Remove player " + player_id)
        socket = self.sessionSocket(sessionid)
        socket.send(message(CMSG_REMOVE_PLAYER, int(player_id)))

    @callback(retval=str)
    def initialize_session(self):
        sessionid = md5.md5(str(random.random())).hexdigest()
        self._create_session(sessionid)
        return sessionid

    def _create_session(self, sessionid):
        sm = ServerMessage('data/images/')
        self._serverMessage[sessionid] = sm
        self._spriteManagers[sessionid] = SpriteManager()
        return sessionid

    @callback(retval={str:[{str:str}]})
    def get_message(self, sessionid="", player_id=0, keys=""):
        """ This one is long, ugly and obscure
        """
        #XXX hangs if not first sending CMSG_PING!
        try:
            sm   = self.serverMessage(sessionid)
        except KeyError:
            self._create_session(sessionid)
            sm   = self.serverMessage(sessionid)           
        data = sm.data
        sock = self.sessionSocket(sessionid)
        while True:
            try:
                data += sock.recv(4096, socket.MSG_DONTWAIT)
            except:    
                break
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

        len_before = len(messages)
        inline_frames = [i for i,msg in enumerate(messages) if msg['type'] == PMSG_INLINE_FRAME]
        for i in reversed(inline_frames[:-1]):
            del messages[i]

        to_append = []
        sprite_manager = self.get_sprite_manager(sessionid)

        sm_restart = 0
        if player_id != -1:
            if keys:
                for i in keys.split(":"):
                    self.sessionSocket(sessionid).\
                         send(message(CMSG_KEY, int(player_id), int(i)))
                
        def get_partial_frame(next, z_num):
            new_sprite, s_num = sprite_manager.get_sprite(*next)
            if new_sprite == 'new':
                to_append.append({'type':'ns', 's':s_num, 'icon_code':str(next[0]), 'x':str(next[1]), 'y':str(next[2]), 'z':z_num})
                sprite_manager.z_index[s_num] = z_num
            elif new_sprite == 'move':
                to_append.append({'type':'sm', 's':str(s_num), 'x':str(next[1]), 'y':str(next[2]), 'z':z_num})
                sprite_manager.z_index[s_num] = z_num
            else:
                if sprite_manager.z_index[s_num] != z_num:
                    to_append.append({'type':'zindex', 's':s_num, 'z':z_num})
                    sprite_manager.z_index[s_num] = z_num
            return s_num
        
        z_num = 0
        for i, msg in enumerate(messages):
            if msg['type'] == PMSG_INLINE_FRAME:
                for next in msg['sprites']:
                    s_num = get_partial_frame(next, z_num)
                    z_num += 1
                del messages[i]

        empty_frame = False
        if sprite_manager.seen == set([]):
            empty_frame = True
        
        if not empty_frame:
            for i in sprite_manager.end_frame():
                to_append.append({'type':'ds', 's':str(i)})
        messages += to_append
        return dict(messages=messages, add_data=[{'n':sm.count(), 'sm_restart':sm_restart}])

exported_methods = ExportedMethods()

class BnbHandler(server.Collection):
    """ BnB server handler
    """
    exported_methods = exported_methods
    static_dir = py.path.local(__file__).dirpath().join("data")
    
    index = server.Static(static_dir.join("bnb.html"))
    images = server.StaticDir("data/images", type="image/png")

    def source_js(self):
        return "text/javascript", self.server.source
    source_js.exposed = True

    MochiKit = server.StaticDir('MochiKit')
    
    #@turbogears.expose(format='json')

    #@turbogears.expose(format='json')

##    @turbogears.expose(format='json')
##    def key(self, player_id, keynum):
##        self.sessionSocket().send(message(CMSG_KEY, int(player_id), int(keynum)))
##        return dict()

    #@turbogears.expose(format='json')
    def close(self):
        self._close()
        return dict()

class BnbRoot(server.NewHandler):
    application = BnbHandler()

