from msgstruct import *
from zlib import decompressobj, decompress
from urllib import quote
from os.path import exists
from struct import unpack
from time import time
import md5


debug = True
def log(msg):
    if debug:
        print msg


class BitmapCreationException(Exception):
    pass


#proxy messages
#PMSG_PING          = "ping"    #server wants to hear from client
#PMSG_PONG          = "pong"    #server responds to client's ping
PMSG_DEF_PLAYFIELD = "def_playfield"
PMSG_DEF_ICON      = "def_icon"
PMSG_PLAYER_ICON   = "player_icon"
PMSG_PLAYER_JOIN   = "player_join"
PMSG_PLAYER_KILL   = "player_kill"
PMSG_DEF_KEY       = "def_key"
PMSG_INLINE_FRAME  = "inline_frame"


# convert server messages to proxy messages in json format
class ServerMessage:

    _md5_file       = {}
    _bitmap2hexdigits={}
    _def_icon_queue = {}
    base_gfx_dir = 'data/images/'
    base_gfx_url = '/images/'
    gfx_extension = 'png'

    def __init__(self, base_gfx_dir = None):
        if base_gfx_dir:
            self.base_gfx_dir = base_gfx_dir
            if not self.base_gfx_dir.endswith('/'):
                self.base_gfx_dir += '/'
        self.socket = None
        self.data   = ''
        self.n_header_lines = 2
        self.gfx_dir = self.base_gfx_dir    #gets overwritten depending on playfield FnDesc
        self.gfx_url = self.base_gfx_url
        self.decompressobj = decompressobj().decompress
        self.last_active = time()
        self._count = 0

    def count(self):
        self._count += 1
        return self._count

    def dispatch(self, *values):
        #log('RECEIVED:%s(%d)' % (values[0], len(values[1:])))
        self.last_active = time()
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
        self.gfx_dir = self.base_gfx_dir
        self.gfx_url = self.base_gfx_url
        return dict(type=PMSG_DEF_PLAYFIELD, width=width, height=height,
                    backcolor=backcolor, FnDesc=FnDesc)

    def def_bitmap(self, bitmap_code, data_or_fileid, *rest):
        if type(data_or_fileid) is type(0):
            fn = self.def_bitmap2
        else:
            fn = self.def_bitmap1
        return fn(bitmap_code, data_or_fileid, *rest)

    def def_bitmap1(self, bitmap_code, data, *rest):
        import PIL.Image
        if len(rest) == 0:
            colorkey = None
        else:
            c = rest[0]
            colorkey = (c & 255, (c >> 8) & 255, (c >> 16) & 255)
        #log('def_bitmap1 bitmap_code=%d, data=%d bytes, colorkey=%s' % (
        #    bitmap_code, len(data), colorkey))

        try:
            decompressed_data = decompress(data)
        except Exception, e:
            raise BitmapCreationException('ERROR UNCOMPRESSING DATA FOR %s (%s)' % (
                bitmap_filename, str(e)))
        hexdigits = md5.new(decompressed_data).hexdigest()
        self._bitmap2hexdigits[bitmap_code] = hexdigits

        gfx_bitmap_filename = '%s%s.%s' % (self.gfx_dir, hexdigits, self.gfx_extension)
        if exists(gfx_bitmap_filename):
            #log('CACHED:%s' % gfx_bitmap_filename)
            pass
        else:
            bitmap_filename = '%s%s.ppm' % (self.gfx_dir, hexdigits)
            f = open(bitmap_filename, 'wb')
            f.write(decompressed_data)
            f.close()
            #TODO: use in memory (don't save ppm first)
            try:
                bitmap = PIL.Image.open(bitmap_filename)
            except IOError, e:
                raise BitmapCreationException('ERROR LOADING %s (%s)' % (
                    bitmap_filename, str(e)))

            #create alpha layer (PIL export this correctly with png but not with gif)
            if colorkey is not None:
                bitmap = bitmap.convert("RGBA")
                data   = bitmap.getdata()
                c      = (colorkey[0], colorkey[1], colorkey[2], 255)
                width, height = bitmap.size
                for y in range(height): #this is slowish but gfx are cached, so...
                    for x in range(width):
                        p = data.getpixel((x,y))
                        if p == c:
                            data.putpixel((x,y), (0,0,0,0))

            try:
                bitmap.save(gfx_bitmap_filename)
                log('SAVED:%s' % gfx_bitmap_filename)
            except IOError:
                raise BitmapCreationException('ERROR SAVING %s (%s)' % (
                    gfx_bitmap_filename, str(e)))

    def def_bitmap2(self, bitmap_code, fileid, *rest):
        #log('def_bitmap2: bitmap_code=%d, fileid=%d, colorkey=%s' % (bitmap_code, fileid, rest))
        hexdigits = self._md5_file[fileid]['hexdigits']
        self._bitmap2hexdigits[bitmap_code] = hexdigits
        gfx_bitmap_filename = '%s%s.%s' % (self.gfx_dir, hexdigits, self.gfx_extension)
        if exists(gfx_bitmap_filename):
            #log('SKIP DATA_REQUEST:%s' % gfx_bitmap_filename)
            pass
        else:
            self._md5_file[fileid]['bitmap_code'] = bitmap_code
            self._md5_file[fileid]['colorkey'] = rest
            position = self._md5_file[fileid]['offset']
            size     = self._md5_file[fileid]['len_data']
            msg      = message(CMSG_DATA_REQUEST, fileid, position, size)
            self.socket.send(msg)
            log('DATA_REQUEST:fileid=%d(pos=%d,size=%d):%s' % (
                fileid, position, size, gfx_bitmap_filename))

    def def_icon(self, bitmap_code, icon_code, x,y,w,h, *rest):
        import PIL.Image

        #log('def_icon bitmap_code=%s, icon_code=%s, x=%s, y=%s, w=%s, h=%s, alpha=%s' %\
        #    (bitmap_code, icon_code, x,y,w,h, rest) #ignore alpha (bubbles)

        hexdigits = self._bitmap2hexdigits[bitmap_code]
        bitmap_filename = '%s%s.%s' % (self.gfx_dir, hexdigits, self.gfx_extension)
        icon_filename = '%s%s_%d_%d_%d_%d.%s' % (
            self.gfx_dir, hexdigits, x, y, w, h, self.gfx_extension)
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

        filename = '%s%s_%d_%d_%d_%d.%s' % (
            self.gfx_url, hexdigits, x, y, w, h, self.gfx_extension)
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
        #log('player_icon player_id=%d, icon_code=%d' % (player_id, icon_code))
        return dict(type=PMSG_PLAYER_ICON, player_id=player_id, icon_code=icon_code)

    def player_join(self, player_id, client_is_self):
        #log('player_join player_id=%d, client_is_self=%d' % (player_id, client_is_self))
        return dict(type=PMSG_PLAYER_JOIN, player_id=player_id, client_is_self=client_is_self)

    def player_kill(self, player_id):
        #log('player_kill player_id=%d' % player_id)
        return dict(type=PMSG_PLAYER_KILL, player_id=player_id)

    def def_key(self, keyname, num, *icon_codes):
        #log('def_key keyname=%s, num=%d, icon_codes=%s' % (keyname, num, str(icon_codes)))
        return dict(type=PMSG_DEF_KEY, keyname=keyname, num=num, icon_codes=icon_codes)

    def md5_file(self, fileid, protofilepath, offset, len_data, checksum):
        hd = '0123456789abcdef'
        hexdigits = ''
        for c in checksum:
            i = ord(c)
            hexdigits = hexdigits + hd[i >> 4] + hd[i & 15]
        #log('md5_file fileid=%d, protofilepath=%s, offset=%d, len_data=%d, hexdigits=%s' % (
        #    fileid, protofilepath, offset, len_data, hexdigits))
        self._md5_file[fileid] = {
            'protofilepath' : protofilepath,
            'offset'        : offset,
            'len_data'      : len_data,
            'checksum'      : checksum,
            'hexdigits'     : hexdigits,
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
        MSG_PLAYER_KILL    : player_kill,
        MSG_DEF_KEY        : def_key,
        MSG_MD5_FILE       : md5_file,
        MSG_INLINE_FRAME   : inline_frame,
        }
