from turbogears import controllers, expose
from cherrypy import session
from msgstruct import *
import PIL.Image
from zlib import decompressobj, decompress
from urllib import quote
from os import mkdir
from os.path import exists
from md5 import md5
from struct import unpack


debug = True
def log(msg):
    if debug:
        print msg


class BitmapCreationException(Exception):
    pass


#proxy messages
#PMSG_PING          = "ping"	#server wants to hear from client
#PMSG_PONG          = "pong"	#server responds to client's ping
PMSG_DEF_PLAYFIELD = "def_playfield"
PMSG_DEF_ICON      = "def_icon"
PMSG_PLAYER_ICON   = "player_icon"
PMSG_PLAYER_JOIN   = "player_join"
PMSG_DEF_KEY       = "def_key"
PMSG_INLINE_FRAME  = "inline_frame"


# convert server messages to proxy messages in json format
class ServerMessage:

    _md5_file       = {}
    _def_icon_queue = {}
    base_gfx_dir = 'testme/static/images/'
    base_gfx_url = 'static/images/'
    gfx_extension = 'gif'

    def __init__(self, base_gfx_dir = None):
        if base_gfx_dir:
            self.base_gfx_dir = base_gfx_dir
        self.socket = None
        self.data   = ''
        self.n_header_lines = 2
        self.gfx_dir = self.base_gfx_dir    #gets overwritten depending on playfield FnDesc
        self.gfx_url = self.base_gfx_url
        self.decompressobj = decompressobj().decompress


    def dispatch(self, *values):
        #log('RECEIVED:%s(%d)' % (values[0], len(values[1:])))
        fn = self.MESSAGES.get(values[0])
        if fn:
            try:
                return fn(self, *values[1:])
            except BitmapCreationException, e:
                log(str(e))
                return dict()
        else:
            log("UNKNOWN:%s" % str(values))
            return dict(type='unknown', values=values)

    #server message handlers...
    def ignore(self, *values):
        #log('ignore %s' % str(values))
        return

    def def_playfield(self, width, height, backcolor, FnDesc):
        #log('def_playfield width=%s, height=%s, backcolor=%s, FnDesc=%s' % (\
        #    width, height, backcolor, FnDesc))
        hexdigest    = md5(FnDesc).hexdigest()
        self.gfx_dir = self.base_gfx_dir + hexdigest + '/'
        self.gfx_url = self.base_gfx_url + hexdigest + '/'
        try:
            mkdir(self.gfx_dir)
        except OSError:
            pass
        return dict(type=PMSG_DEF_PLAYFIELD, width=width, height=height,
                    backcolor=backcolor, FnDesc=FnDesc)

    def def_bitmap(self, bitmap_code, data_or_fileid, *rest):
        if type(data_or_fileid) is type(0):
            fn = self.def_bitmap2
        else:
            fn = self.def_bitmap1
        return fn(bitmap_code, data_or_fileid, *rest)

    def def_bitmap1(self, bitmap_code, data, *rest):
        if len(rest) == 0:
            colorkey = None
        else:
            colorkey = rest[0]
        #log('def_bitmap1 bitmap_code=%d, data=%d bytes, colorkey=%s' % (
        #    bitmap_code, len(data), colokey))
        gif_bitmap_filename = '%sbitmap%d.%s' % (self.gfx_dir, bitmap_code, self.gfx_extension)
        if exists(gif_bitmap_filename):
            #log('CACHED:%s' % gif_bitmap_filename)
            pass
        else:
            bitmap_filename = '%sbitmap%d.ppm' % (self.gfx_dir, bitmap_code)
            try:
                decompressed_data = decompress(data)
            except Exception, e:
                raise BitmapCreationException('ERROR UNCOMPRESSING DATA FOR %s (%s)' % (
                    bitmap_filename, str(e)))
            f = open(bitmap_filename, 'wb')
            f.write(decompressed_data)
            f.close()
            #TODO: use in memory (don't save ppm first)
            try:
                bitmap = PIL.Image.open(bitmap_filename)
            except IOError, e:
                raise BitmapCreationException('ERROR LOADING %s (%s)' % (
                    bitmap_filename, str(e)))

            #create alpha layer that hopefully gets into the .gif...
            #if colorkey is not None:
            #    bitmap = bitmap.convert("RGBA")
            #    pixel = bitmap.getpixel( (0,0) )
            #    log('%s: colorkey=%s, pixel=%s' % (bitmap_filename, colorkey, str(pixel)))
            #    colorkeyT = (1, 1, 1, 255)
            #    alpha = [pixel == (1,1,1,255) for pixel in list(bitmap.getdata())]
            #    bitmap.putalpha(alpha)

            try:
                bitmap.save(gif_bitmap_filename)
                log('SAVED:%s' % gif_bitmap_filename)
            except IOError:
                raise BitmapCreationException('ERROR SAVING %s (%s)' % (
                    gif_bitmap_filename, str(e)))

    def def_bitmap2(self, bitmap_code, fileid, *rest):
        #log('def_bitmap2: bitmap_code=%d, fileid=%d, colorkey=%s' % (bitmap_code, fileid, rest))
        gif_bitmap_filename = '%sbitmap%d.%s' % (self.gfx_dir, bitmap_code, self.gfx_extension)
        if exists(gif_bitmap_filename):
            #log('SKIP DATA_REQUEST:%s' % gif_bitmap_filename)
            pass
        else:
            self._md5_file[fileid]['bitmap_code'] = bitmap_code
            self._md5_file[fileid]['colorkey'] = rest
            position = self._md5_file[fileid]['offset']
            size     = self._md5_file[fileid]['len_data']
            msg      = message(CMSG_DATA_REQUEST, fileid, position, size)
            self.socket.send(msg)
            log('DATA_REQUEST:%s' % gif_bitmap_filename)

    def def_icon(self, bitmap_code, icon_code, x,y,w,h, *rest):
        #log('def_icon bitmap_code=%s, icon_code=%s, x=%s, y=%s, w=%s, h=%s, alpha=%s' %\
        #    (bitmap_code, icon_code, x,y,w,h, rest) #ignore alpha (bubbles)

        bitmap_filename = '%sbitmap%d.%s' % (self.gfx_dir, bitmap_code, self.gfx_extension)
        icon_filename = '%sicon%d.%s' % (self.gfx_dir, icon_code, self.gfx_extension)
        if exists(icon_filename):
            #log('CACHED:%s' % icon_filename)
            pass
        elif exists(bitmap_filename):
            #TODO: use in memory (don't save ppm first)
            icon    = PIL.Image.open(bitmap_filename)
            box     = (x, y, x+w, y+h)
            region  = icon.crop(box)
            region.save(icon_filename)
            log('SAVED:%s' % icon_filename)
        else:   #bitmap is not available yet (protocol 2)
            #log('%s NOT AVAILABLE FOR %s' % (bitmap_filename, icon_filename))
            if bitmap_code not in self._def_icon_queue:
                self._def_icon_queue[bitmap_code] = []
            self._def_icon_queue[bitmap_code].append((icon_code, x, y, w, h, rest))
            return

        filename = '%sicon%d.%s' % (self.gfx_url, icon_code, self.gfx_extension)
        return dict(type=PMSG_DEF_ICON, icon_code=icon_code, filename=filename, width=w, height=h)

    def zpatch_file(self, fileid, position, data): #response to CMSG_DATA_REQUEST
        #log('zpatch_file fileid=%d, position=%d, len(data)=%d' % (fileid, position, len(data)))
        bitmap_code = self._md5_file[fileid]['bitmap_code']
        colorkey    = self._md5_file[fileid]['colorkey']
        try:
            t = self.def_bitmap(bitmap_code, data, *colorkey)
        except BitmapCreationException, e:
            log(str(e))
            return #i.e. not attempting to create icons 
        messages = []
        if bitmap_code in self._def_icon_queue:
            #log('%d icons queued for bitmap %d' % (
            #    len(self._def_icon_queue[bitmap_code]), bitmap_code))
            for t in self._def_icon_queue[bitmap_code]:
                icon_code, x, y, w, h, rest = t
                messages.append(self.def_icon(bitmap_code, icon_code, x, y, w, h, *rest))
            del self._def_icon_queue[bitmap_code]
        return messages
    
    def player_icon(self, player_id, icon_code):
        log('player_icon player_id=%d, icon_code=%d' % (player_id, icon_code))
        return dict(type=PMSG_PLAYER_ICON, player_id=player_id, icon_code=icon_code)

    def player_join(self, player_id, client_is_self):
        log('player_join player_id=%d, client_is_self=%d' % (player_id, client_is_self))
        return dict(type=PMSG_PLAYER_JOIN, player_id=player_id, client_is_self=client_is_self)

    def def_key(self, keyname, num, *icon_codes):
        log('def_key keyname=%s, num=%d, icon_codes=%s' % (keyname, num, str(icon_codes)))
        return dict(type=PMSG_DEF_KEY, keyname=keyname, num=num, icon_codes=icon_codes)

    def md5_file(self, fileid, protofilepath, offset, len_data, checksum):
        #log('md5_file fileid=%d, protofilepath=%s, offset=%d, len_data=%d, checksum=...' % (
        #    fileid, protofilepath, offset, len_data))
        self._md5_file[fileid] = {
            'protofilepath' : protofilepath,
            'offset'        : offset,
            'len_data'      : len_data,
            'checksum'      : checksum,
            }

    def inline_frame(self, data):
        decompressed_data = d = self.decompressobj(data)
        #log('inline_frame len(data)=%d, len(decompressed_data)=%d' % (
        #    len(data), len(d)))

        return_raw_data = False
        if return_raw_data:
            return dict(type=PMSG_INLINE_FRAME, data=decompressed_data)

        #note: we are not returning the raw data here but we could let the Javascript
        #      handle it. If this is working we can convert this to RPython and move it
        #      to the client instead. (based on BnB update_sprites in display/pclient.py)
        sounds, sprites = [], []

        base = 0
        while d[base+4:base+6] == '\xFF\xFF':
            key, lvol, rvol = struct.unpack("!hBB", udpdata[base:base+4])
            sounds.append((key, lvol, rvol))
            base += 6

        for j in range(base, len(d)-5, 6):
            info = d[j:j+6]
            x, y, icon_code = unpack("!hhh", info[:6])
            sprites.append((icon_code, x, y))

        return dict(type=PMSG_INLINE_FRAME, sounds=sounds, sprites=sprites)

    MESSAGES = {
        MSG_BROADCAST_PORT : ignore,
        MSG_PING           : ignore,
        MSG_PONG           : ignore,
        MSG_DEF_PLAYFIELD  : def_playfield,
        MSG_DEF_BITMAP     : def_bitmap,
        MSG_ZPATCH_FILE    : zpatch_file,
        MSG_DEF_ICON       : def_icon,
        MSG_PLAYER_ICON    : player_icon,
        MSG_PLAYER_JOIN    : player_join,
        MSG_DEF_KEY        : def_key,
        MSG_MD5_FILE       : md5_file,
        MSG_INLINE_FRAME   : inline_frame,
        }
