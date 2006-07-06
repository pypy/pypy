#!/usr/bin/env python
""" bub-n-bros testing utility
"""

import autopath

import py

from pypy.translator.js import conftest

conftest.option.tg = True
conftest.option.browser = "default"

from pypy.translator.js.test.runtest import compile_function
from pypy.translator.js.modules._dom import get_document
from pypy.translator.js.modules.xmlhttp import XMLHttpRequest
from pypy.translator.js.modules.mochikit import log, logWarning, createLoggingPane
from pypy.translator.js.modules.bltns import date
from pypy.translator.js.demo.jsdemo.bnb import BnbRootInstance

import time
import os

os.chdir("../demo/jsdemo")

def logKey(msg):
    #log(msg)
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
            next_time = date()
            self.fps = 10000/(next_time - self.starttime)
            self.n_rendered_inline_frames = 0
            self.starttime = next_time

stats = Stats()

class Player(object):
    def __init__(self):
        self.id = -1
        self.prev_count = 0

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
        img = get_document().createElement("img")
        img.setAttribute("src", self.filenames[icon_code])
        img.setAttribute("style", 'position:absolute; left:'+x+'px; top:'+y+'px; visibility:visible')
        get_document().getElementById("playfield").appendChild(img)
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
        #pass
    
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
    
    #def show_sprite(self, s):
    #    i = self.sprites[s]
    #    i.style.visibility = "visible"

sm = SpriteManager()

def appendPlayfield(msg):
    bgcolor = '#000000'
    get_document().body.setAttribute('bgcolor', bgcolor)
    div = get_document().createElement("div")
    div.setAttribute("id", "playfield")
    div.setAttribute('width', msg['width'])
    div.setAttribute('height', msg['height'])
    div.setAttribute('style', 'position:absolute; top:0px; left:0px')
    get_document().body.appendChild(div)

def appendPlayfieldXXX():
    bgcolor = '#000000'
    get_document().body.setAttribute('bgcolor', bgcolor)
    div = get_document().createElement("div")
    div.setAttribute("id", "playfield")
    div.setAttribute('width', 500)
    div.setAttribute('height', 250)
    div.setAttribute('style', 'position:absolute; top:0px; left:0px')
    get_document().body.appendChild(div)

def process_message(msg):
    if msg['type'] == 'def_playfield':
        appendPlayfield(msg)
    elif msg['type'] == 'def_icon':
        sm.add_icon(msg['icon_code'], msg['filename'])
    elif msg['type'] == 'ns':
        sm.add_sprite(msg['s'], msg['icon_code'], msg['x'], msg['y'])
    elif msg['type'] == 'sm':
        sm.move_sprite(msg['s'], msg['x'], msg['y'])
    elif msg['type'] == 'ds':
        sm.hide_sprite(msg['s'])
    elif msg['type'] == 'begin_clean_sprites':
        sm.start_clean_sprites()
    elif msg['type'] == 'clean_sprites':
        sm.end_clean_sprites()
    elif msg['type'] == 'show_sprite':
        sm.show_sprite(msg['s'], msg['icon_code'], msg['x'], msg['y'])
    #elif msg['type'] == 'ss':
    #    sm.show_sprite(msg['s'])
    elif msg['type'] == 'player_icon' or msg['type'] == 'def_key' or \
         msg['type'] == 'player_join' or msg['type'] == 'player_kill':
        pass #ignore
    else:
        logWarning('unknown message type: ' + msg['type'])


def addPlayer(player_id):
    name  = "player no. " + str(player_id)
    #name  = "player no. %d" % player_id
    #File "/Users/eric/projects/pypy-dist/pypy/translator/js/jts.py", line 52, in lltype_to_cts
    #    raise NotImplementedError("Type %r" % (t,))
    #    NotImplementedError: Type <StringBuilder>
    prev_player_id = player.id
    if player.id >= 0:
        #log("removing " + name)
        BnbRootInstance.remove_player(player.id, ignore_dispatcher)
        player.id = -1
    if player_id != prev_player_id:
        #log("adding " + name)
        BnbRootInstance.add_player(player_id, ignore_dispatcher)
        BnbRootInstance.player_name(player_id, name, ignore_dispatcher)
        player.id = player_id


def keydown(key):
    #c = chr(int(key.keyCode)).lower()
    #c = int(key.keyCode)
    c = key.keyCode
    if c == 48: #ord('0'):
        addPlayer(0)
    elif c == 49: #ord('1'):  #bwah. should really work on being able to cast to int
        addPlayer(1)
    elif c == 50: #ord('2'):
        addPlayer(2)
    elif c == 51: #ord('3'):
        addPlayer(3)
    elif c == 52: #ord('4'):
        addPlayer(4)
    elif c == 53: #ord('5'):
        addPlayer(5)
    elif c == 54: #ord('6'):
        addPlayer(6)
    elif c == 55: #ord('7'):
        addPlayer(7)
    elif c == 56: #ord('8'):
        addPlayer(8)
    elif c == 57: #ord('9'):
        addPlayer(9)
    elif c == 68: #ord('D'):  #right
        BnbRootInstance.key(player.id, 0, ignore_dispatcher)
        logKey('start right')
    elif c == 83: #ord('S'):  #left
        BnbRootInstance.key(player.id, 1, ignore_dispatcher)
        logKey('start left')
    elif c == 69: #ord('E'):  #up
        BnbRootInstance.key(player.id, 2, ignore_dispatcher)
        logKey('start up')
    elif c == 88: #ord('X'):  #fire
        BnbRootInstance.key(player.id, 3, ignore_dispatcher)
        logKey('start fire')
    else:
        logWarning('unknown keydown: ' + str(c))


def keyup(key):
    c = key.keyCode
    if c == 48 or c == 49 or c == 50 or c == 51 or c == 52 or\
       c == 53 or c == 54 or c == 55 or c == 56 or c == 57: #XXX c in (...) didn't work
        pass    #don't print warning
    elif c == 68: #ord('D'):  #right
        BnbRootInstance.key(player.id, 4, ignore_dispatcher)
        logKey('stop right')
    elif c == 83: #ord('S'):  #left
        BnbRootInstance.key(player.id, 5, ignore_dispatcher)
        logKey('stop left')
    elif c == 69: #ord('E'):  #up
        BnbRootInstance.key(player.id, 6, ignore_dispatcher)
        logKey('stop up')
    elif c == 88: #ord('X'):  #fire
        BnbRootInstance.key(player.id, 7, ignore_dispatcher)
        logKey('stop fire')
    else:
        logWarning('unknown keyup: ' + str(c))

def ignore_dispatcher(msgs):
    pass

def bnb_dispatcher(msgs):
    BnbRootInstance.get_message(bnb_dispatcher)

    #sm_restart = int(msgs['add_data'][0]['sm_restart'])
    #if sm_restart == 123:
    #    log("sm_restart")
    #    stats.__init__()
    #    sm.__init__()
    #    sm.begin_clean_sprites()
    #    playfield = get_document().getElementById("playfield")
    #    get_document().body.removeChild(playfield)
    #    appendPlayfieldXXX()

    count = int(msgs['add_data'][0]['n'])
    if count != player.prev_count + 1:
        logWarning("incorrect response order, expected " + str(player.prev_count+1) + ' got ' + str(count))
        sm.frames.append(msgs)
    player.prev_count = count
    #else:
    #    player.prev_count = count
    #    for i in sm.frames:
    #        render_frame(i)
    render_frame(msgs)

def render_frame(msgs):
    for msg in msgs['messages']:
        process_message(msg)
    stats.register_frame()
    get_document().title = str(stats.n_sprites) + " sprites " + str(stats.fps)

def session_dispatcher(msgs):
    BnbRootInstance.get_message(bnb_dispatcher)

def run_bnb():
    def bnb():
        genjsinfo = get_document().getElementById("genjsinfo")
        get_document().body.removeChild(genjsinfo)
        createLoggingPane(True)
        log("keys: [0-9] to select player, [esdx] to walk around")
        BnbRootInstance.initialize_session(session_dispatcher)
        get_document().onkeydown = keydown
        get_document().onkeyup   = keyup
    
    from pypy.translator.js.demo.jsdemo.bnb import BnbRoot
    fn = compile_function(bnb, [], root = BnbRoot, run_browser = False)
    fn()

if __name__ == '__main__':
    run_bnb()
