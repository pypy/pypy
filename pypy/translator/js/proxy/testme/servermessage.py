from turbogears import controllers, expose
from cherrypy import session
from msgstruct import *
import PIL.Image
from zlib import decompress
from urllib import quote
from os import mkdir
from os.path import exists
from md5 import md5


debug = True
def log(msg):
    if debug:
        print msg


#proxy messages
PMSG_PING          = "ping"	#server wants to hear from client
PMSG_PONG          = "pong"	#server responds to client's ping
PMSG_DEF_PLAYFIELD = "def_playfield"
PMSG_DEF_ICON      = "def_icon"
PMSG_PLAYER_ICON   = "player_icon"
PMSG_PLAYER_JOIN   = "player_join"
PMSG_DEF_KEY       = "def_key"


# convert server messages to proxy messages in json format
class ServerMessage:

    base_gfx_dir = 'testme/static/images/'
    base_gfx_url = 'static/images/'

    def __init__(self):
        self.socket = None
        self.data   = ''
        self.n_header_lines = 2
        self.gfx_dir = self.base_gfx_dir    #gets overwritten depending on playfield FnDesc
        self.gfx_url = self.base_gfx_url

    def dispatch(self, *values):
        #log('RECEIVED MESSAGE:%s(%d)' % (values[0], len(values[1:])))
        fn = self.MESSAGES.get(values[0])
        if fn:
            return fn(self, *values[1:])
        else:
            log("UNKNOWN MESSAGE:%s" % str(values))
            return dict(type='unknown', values=values)

    #server message handlers...
    def broadcast_port(self, *values):
        log('MESSAGE (IGNORE):broadcast_port %s' % str(values))

    def ping(self, *rest):
        log('MESSAGE:ping udpsockcounter=%s' % str(rest))
        return dict(type=PMSG_PING)

    def pong(self):
        log('MESSAGE:pong')
        return dict(type=PMSG_PONG)

    def def_playfield(self, width, height, backcolor, FnDesc):
        log('MESSAGE:def_playfield width=%s, height=%s, backcolor=%s, FnDesc=%s' %\
            (width, height, backcolor, FnDesc))
        hexdigest    = md5(FnDesc).hexdigest()
        self.gfx_dir = self.base_gfx_dir + hexdigest + '/'
        self.gfx_url = self.base_gfx_url + hexdigest + '/'
        try:
            mkdir(self.gfx_dir)
        except OSError:
            pass
        return dict(type=PMSG_DEF_PLAYFIELD, width=width, height=height,
                    backcolor=backcolor, FnDesc=FnDesc)

    def def_bitmap(self, code, data, *rest):
        log('MESSAGE:def_bitmap code=%s, data=%d bytes, colorkey=%s' %\
            (code, len(data), rest))
        gif_bitmap_filename = '%sbitmap%d.gif' % (self.gfx_dir, code)
        if exists(gif_bitmap_filename):
            return
        bitmap_filename = '%sbitmap%d.ppm' % (self.gfx_dir, code)
        f = open(bitmap_filename, 'wb')
        f.write(decompress(data))
        f.close()

        #TODO: use in memory (don't save ppm first)
        bitmap = PIL.Image.open(bitmap_filename)
        bitmap.save(gif_bitmap_filename)

    def def_icon(self, bitmap_code, code, x,y,w,h, *rest):
        log('MESSAGE:def_icon bitmap_code=%s, code=%s, x=%s, y=%s, w=%s, h=%s, alpha=%s' %\
            (bitmap_code, code, x,y,w,h, rest))

        icon_filename   = '%sicon%d.gif' % (self.gfx_dir, code)
        if not exists(icon_filename):
            #TODO: use in memory (don't save ppm first)
            bitmap_filename = '%sbitmap%d.gif' % (self.gfx_dir, bitmap_code)
            icon    = PIL.Image.open(bitmap_filename)
            box     = (x, y, x+w, y+h)
            region  = icon.crop(box)
            region.save(icon_filename)
            log('SAVED:%s' % icon_filename)

        filename = '%sicon%d.gif' % (self.gfx_url, code)
        return dict(type=PMSG_DEF_ICON, code=code, filename=filename, width=w, height=h)

    def player_icon(self, player_id, code):
        log('MESSAGE:player_icon player_id=%d, code=%d' % (player_id, code))
        return dict(type=PMSG_PLAYER_ICON, player_id=player_id, code=code)

    def player_join(self, player_id, client_is_self):
        log('MESSAGE:player_join player_id=%d, client_is_self=%d' % (player_id, client_is_self))
        return dict(type=PMSG_PLAYER_JOIN, player_id=player_id, client_is_self=client_is_self)

    def def_key(self, keyname, num, *ico_codes):
        log('MESSAGE:def_key keyname=%s, num=%d, ico_codes=%s' % (keyname, num, str(ico_codes)))
        return dict(type=PMSG_DEF_KEY, keyname=keyname, num=num, ico_codes=ico_codes)
 
    MESSAGES = {
        MSG_BROADCAST_PORT : broadcast_port,
        MSG_PING           : ping,
        MSG_DEF_PLAYFIELD  : def_playfield,
        MSG_DEF_BITMAP     : def_bitmap,
        MSG_DEF_ICON       : def_icon,
        MSG_PLAYER_ICON    : player_icon,
        MSG_PLAYER_JOIN    : player_join,
        MSG_PONG           : pong,
        MSG_DEF_KEY        : def_key,
        }
