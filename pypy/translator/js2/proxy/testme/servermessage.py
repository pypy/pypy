from turbogears import controllers, expose
from cherrypy import session
from msgstruct import *
import PIL.Image
import zlib
import socket
import urllib
import re


debug = True
def log(msg):
    if debug:
        print msg


#proxy messages
PMSG_PING          = "ping"
PMSG_DEF_PLAYFIELD = "def_playfield"
PMSG_DEF_ICON      = "def_icon"
PMSG_PLAYER_JOIN   = "player_join"


# convert server messages to proxy messages in json format
class ServerMessage:

    def __init__(self):
        self.socket = None
        self.data   = ''

    def dispatch(self, *values):
        #log('RECEIVED MESSAGE:%s(%d)' % (values[0], len(values[1:])))
        fn = self.MESSAGES.get(values[0])
        if fn:
            return fn(self, *values[1:])
        else:
            log("UNKNOWN MESSAGE:%s" % str(values))
            return dict(type='unknown', values=values)

    #UNKNOWN MESSAGE:('k', 'right', 0, 0, 1, 2, 3)  #def_key
    #UNKNOWN MESSAGE:('k', 'left', 1, 4, 5, 6, 7)
    #UNKNOWN MESSAGE:('k', 'jump', 2, 8, 9, 10, 11)
    #UNKNOWN MESSAGE:('k', 'fire', 3, 12, 13, 14, 15)
    #UNKNOWN MESSAGE:('k', '-right', 4)
    #UNKNOWN MESSAGE:('k', '-left', 5)
    #UNKNOWN MESSAGE:('k', '-jump', 6)
    #UNKNOWN MESSAGE:('k', '-fire', 7)
    #UNKNOWN MESSAGE:('i', 0, 16)                   #player_icon
    #UNKNOWN MESSAGE:('i', 1, 17)
    #UNKNOWN MESSAGE:('i', 2, 18)
    #UNKNOWN MESSAGE:('i', 3, 19)
    #UNKNOWN MESSAGE:('i', 4, 20)
    #UNKNOWN MESSAGE:('i', 5, 21)
    #UNKNOWN MESSAGE:('i', 6, 22)
    #UNKNOWN MESSAGE:('i', 7, 23)
    #UNKNOWN MESSAGE:('i', 8, 24)
    #UNKNOWN MESSAGE:('i', 9, 25)
    #UNKNOWN MESSAGE:('G',)                         #pong

    #server message handlers...
    def broadcast_port(self, *values):
        log('MESSAGE (IGNORE):broadcast_port %s' % str(values))

    def ping(self):
        log('MESSAGE:ping')
        return dict(type=PMSG_PING)

    def def_playfield(self, width, height, backcolor, FnDesc):
        log('MESSAGE:def_playfield width=%s, height=%s, backcolor=%s, FnDesc=%s' %\
            (width, height, backcolor, FnDesc))
        return dict(type=PMSG_DEF_PLAYFIELD, width=width, height=height,
                    backcolor=backcolor, FnDesc=FnDesc)

    def def_bitmap(self, code, data, *rest):
        log('MESSAGE:def_bitmap code=%s, data=%d bytes, colorkey=%s' %\
            (code, len(data), rest))
        bitmap_filename = 'testme/static/images/bitmap%d.ppm' % code
        f = open(bitmap_filename, 'wb')
        f.write(zlib.decompress(data))
        f.close()

        #TODO: use in memory (don't save ppm first)
        bitmap = PIL.Image.open(bitmap_filename)
        gif_bitmap_filename = 'testme/static/images/bitmap%d.gif' % code
        bitmap.save(gif_bitmap_filename)

    def def_icon(self, bitmap_code, code, x,y,w,h, *rest):
        log('MESSAGE:def_icon bitmap_code=%s, code=%s, x=%s, y=%s, w=%s, h=%s, alpha=%s' %\
            (bitmap_code, code, x,y,w,h, rest))

        #TODO: use in memory (don't save ppm first)
        bitmap_filename = 'testme/static/images/bitmap%d.gif' % bitmap_code
        icon_filename = 'testme/static/images/icon%d.gif' % code
        icon    = PIL.Image.open(bitmap_filename)
        box     = (x, y, x+w, y+h)
        region  = icon.crop(box)
        region.save(icon_filename)
        log('SAVED:%s' % icon_filename)

        filename = 'static/images/icon%d.gif' % code
        return dict(type=PMSG_DEF_ICON, code=code, filename=filename, width=w, height=h)

    def player_join(self, player_id, client_is_self):
        log('MESSAGE:player_join player_id=%d, client_is_self=%d' % (player_id, client_is_self))
        return dict(type=PMSG_PLAYER_JOIN, player_id=player_id, client_is_self=client_is_self)
        
    MESSAGES = {
        MSG_BROADCAST_PORT : broadcast_port,
        MSG_PING           : ping,
        MSG_DEF_PLAYFIELD  : def_playfield,
        MSG_DEF_BITMAP     : def_bitmap,
        MSG_DEF_ICON       : def_icon,
        MSG_PLAYER_JOIN    : player_join,
        }

