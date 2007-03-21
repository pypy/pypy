#!/usr/bin/env python
""" bub-n-bros testing utility
"""

import autopath

import py

from pypy.translator.js.main import rpython2javascript
from pypy.translator.js.modules.dom import document, window
from pypy.translator.js.modules.mochikit import log, logWarning,\
     createLoggingPane, logDebug, connect
from pypy.translator.js.examples.bnb.bnb import exported_methods
from pypy.translator.js import commproxy

commproxy.USE_MOCHIKIT = True

import time
import os
import sys

def logKey(msg):
    pass

class Stats(object):
    """ Class containing some statistics
    """
    def __init__(self):
        self.n_received_inline_frames = 0
        self.n_rendered_inline_frames = 0
        self.n_rendered_dynamic_sprites = 0
        self.fps = 0
        self.starttime = 0.0
        self.n_sprites = 0
    
    def register_frame(self):
        self.n_rendered_inline_frames += 1
        if self.n_rendered_inline_frames >= 10:
            next_time = time.time()
            self.fps = 10000/(next_time - self.starttime)
            self.n_rendered_inline_frames = 0
            self.starttime = next_time

stats = Stats()

class Player(object):
    def __init__(self):
        self.id = -1
        self.prev_count = 0
        self.sessionid = ""

player = Player()

class SpriteManager(object):
    def __init__(self):
        self.sprites = {}
        self.filenames = {}
        self.all_sprites = {}
        self.frames = []

    def add_icon(self, icon_code, filename):
        self.filenames[icon_code] = filename
        #self.sprite_queues[icon_code] = []
        #self.used[icon_code] = []
        # FIXME: Need to write down DictIterator once...
        #self.icon_codes.append(icon_code)

    def add_sprite(self, s, icon_code, x, y):
        #try:
        #    img = self.sprite_queues[icon_code].pop()
        #except IndexError:
        stats.n_sprites += 1
        img = document.createElement("img")
        img.src = self.filenames[icon_code]
        img.style.position = 'absolute'
        img.style.left = x + 'px'
        img.style.top = y + 'px'
        img.style.visibility = 'visible'
        document.getElementById("playfield").appendChild(img)
        try:
            self.sprites[s].style.visibility = "hidden"
            # FIXME: We should delete it
        except KeyError:
            self.sprites[s] = img
        return img

    def move_sprite(self, s, x, y):
        i = self.sprites[s]
        i.style.top = y + 'px'
        i.style.left = x + 'px'
        i.style.visibility = 'visible'

    def hide_sprite(self, s):
        i = self.sprites[s]
        i.style.visibility = "hidden"
    
    def start_clean_sprites(self):
        self.all_sprites = {}
    
    def show_sprite(self, s, icon_code, x, y):
        self.all_sprites[s] = 1
        try:
            self.move_sprite(s, x, y)
        except KeyError:
            self.add_sprite(s, icon_code, x, y)
    
    def end_clean_sprites(self):
        for i in self.sprites:
            try:
                self.all_sprites[i]
            except KeyError:
                self.hide_sprite(i)
    
    def set_z_index(self, s_num, z):
        self.sprites[s_num].style.zIndex = z
    
    #def show_sprite(self, s):
    #    i = self.sprites[s]
    #    i.style.visibility = "visible"

sm = SpriteManager()

class KeyManager(object):
    def __init__(self):
        self.keymappings = {ord('D'):'right', ord('S'):'fire', ord('A'):'left', ord('W'):'up'}
        self.key_to_bnb_down = {'right':0, 'left':1, 'fire':3, 'up':2}
        self.key_to_bnb_up = {'right':4, 'left':5, 'fire':7, 'up':6}
        self.queue = []
            
    def add_key_up(self, key):
        self.queue.append(self.key_to_bnb_up[key])
    
    def add_key_down(self, key):
        self.queue.append(self.key_to_bnb_down[key])

    def get_keys(self):
        retval = self.queue
        self.queue = []
        return retval
    
km = KeyManager()

def appendPlayfield(msg):
    body = document.getElementsByTagName('body')[0]
    bgcolor = '#000'
    body.style.backgroundColor = bgcolor
    div = document.createElement("div")
    div.id = 'playfield'
    div.style.width = msg['width']
    div.style.height = msg['height']
    div.style.position = 'absolute'
    div.style.top = '0px'
    div.style.left = '0px'
    div.appendChild(document.createTextNode('foobar?'))

    #document.body.childNodes.insert(0, div)
    body.appendChild(div)

def appendPlayfieldXXX():
    bgcolor = '#000000'
    document.body.setAttribute('bgcolor', bgcolor)
    div = document.createElement("div")
    div.id = 'playfield'
    div.style.width = 500
    div.style.height = 250
    div.style.position = 'absolute'
    div.style.top = '0px'
    div.style.left = '0px'
    document.body.appendChild(div)

def process_message(msg):
    if msg['type'] == 'def_playfield':
        appendPlayfield(msg)
    elif msg['type'] == 'def_icon':
        sm.add_icon(msg['icon_code'], msg['filename'])
    elif msg['type'] == 'ns':
        sm.add_sprite(msg['s'], msg['icon_code'], msg['x'], msg['y'])
        sm.set_z_index(msg['s'], msg['z'])
    elif msg['type'] == 'sm':
        sm.move_sprite(msg['s'], msg['x'], msg['y'])
        sm.set_z_index(msg['s'], msg['z'])
    elif msg['type'] == 'ds':
        sm.hide_sprite(msg['s'])
    elif msg['type'] == 'begin_clean_sprites':
        sm.start_clean_sprites()
    elif msg['type'] == 'clean_sprites':
        sm.end_clean_sprites()
    elif msg['type'] == 'show_sprite':
        sm.show_sprite(msg['s'], msg['icon_code'], msg['x'], msg['y'])
    elif msg['type'] == 'zindex':
        sm.set_z_index(msg['s'], msg['z'])
    #elif msg['type'] == 'ss':
    #    sm.show_sprite(msg['s'])
    elif msg['type'] == 'player_icon' or msg['type'] == 'def_key' or \
         msg['type'] == 'player_join' or msg['type'] == 'player_kill':
        pass #ignore
    else:
        logWarning('unknown message type: ' + msg['type'])


def ignore(arg):
    pass
ignore._annspecialcase_ = 'specialize:argtype(0)'

def addPlayer(player_id):
    name  = "player no. " + str(player_id)
    #name  = "player no. %d" % player_id
    #File "/Users/eric/projects/pypy-dist/pypy/translator/js/jts.py", line 52, in lltype_to_cts
    #    raise NotImplementedError("Type %r" % (t,))
    #    NotImplementedError: Type <StringBuilder>
    prev_player_id = player.id
    if player.id >= 0:
        exported_methods.remove_player(player.id, player.sessionid, ignore)
        player.id = -1
    if player_id != prev_player_id:
        exported_methods.player_name(player_id, name, player.sessionid, ignore)
        exported_methods.add_player(player_id, player.sessionid, ignore)
        player.id = player_id


def keydown(key):
    #c = chr(int(key.keyCode)).lower()
    #c = int(key.keyCode)
    key = key._event
    try:
        c = key.keyCode
        if c > ord('0') and c < ord('9'):
            addPlayer(int(chr(c)))
        #for i in km.keymappings:
        #    log(str(i))
        if c in km.keymappings:
            km.add_key_down(km.keymappings[c])
        #else:
    except Exception, e:
        log(str(e))

def keyup(key):
    key = key._event
    c = key.keyCode
    if c > ord('0') and c < ord('9'):
        pass    #don't print warning
    elif c in km.keymappings:
        km.add_key_up(km.keymappings[c])
    else:
        logWarning('unknown keyup: ' + str(c))
    
#def ignore_dispatcher(msgs):
#    pass

def bnb_dispatcher(msgs):
    s = ":".join([str(i) for i in km.get_keys()])
    exported_methods.get_message(player.sessionid, player.id, s,
                                 bnb_dispatcher)
    render_frame(msgs)

def render_frame(msgs):
    for msg in msgs['messages']:
        process_message(msg)
    stats.register_frame()
    document.title = str(stats.n_sprites) + " sprites " + str(stats.fps)

def session_dispatcher(sessionid):
    player.sessionid = sessionid
    connect(document, 'onkeydown', keydown)
    connect(document, 'onkeyup', keyup)
    exported_methods.get_message(player.sessionid, player.id, "",
                                 bnb_dispatcher)

def bnb():
    createLoggingPane(True)
    log("keys: [0-9] to select player, [wsad] to walk around")
    exported_methods.initialize_session(session_dispatcher)

def run_bnb():    
    from pypy.translator.js.examples.bnb.bnb import BnbRoot
    from pypy.translator.js.lib import server
    addr = ('', 7070)
    httpd = server.create_server(handler=BnbRoot, server_address=addr)
    httpd.source = rpython2javascript(sys.modules[__name__], ['bnb'])
    httpd.serve_forever()

if __name__ == '__main__':
    run_bnb()
