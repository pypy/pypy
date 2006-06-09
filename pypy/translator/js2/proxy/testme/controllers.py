import turbogears
from turbogears import controllers
import cherrypy
from msgstruct import *
import PIL.Image
import zlib
import socket
import urllib
import re


class SessionData:

    def broadcast_port(self, *values):
        print 'MESSAGE (IGNORE):broadcast_port', values

    def ping(self):
        print 'MESSAGE:ping'

    def def_playfield(self, width, height, backcolor, FnDesc):
        print 'MESSAGE:def_playfield width=%s, height=%s, backcolor=%s, FnDesc=%s' %\
            (width, height, backcolor, FnDesc)

    def def_bitmap(self, code, data, *rest):
        print 'MESSAGE:def_bitmap code=%s, data=%d bytes, colorkey=%s' %\
            (code, len(data), rest)
        bitmap_filename = 'testme/static/images/bitmap%d.ppm' % code
        f = open(bitmap_filename, 'wb')
        f.write(zlib.decompress(data))
        f.close()

        #TODO: use in memory (don't save ppm first)
        bitmap = PIL.Image.open(bitmap_filename)
        gif_bitmap_filename = 'testme/static/images/bitmap%d.gif' % code
        bitmap.save(gif_bitmap_filename)

    def def_icon(self, bitmap_code, code, x,y,w,h, *rest):
        print 'MESSAGE:def_icon bitmap_code=%s, code=%s, x=%s, y=%s, w=%s, h=%s, alpha=%s' %\
            (bitmap_code, code, x,y,w,h, rest)

        #TODO: use in memory (don't save ppm first)
        bitmap_filename = 'testme/static/images/bitmap%d.gif' % bitmap_code
        icon_filename = 'testme/static/images/icon%d.gif' % code
        icon    = PIL.Image.open(bitmap_filename)
        box     = (x, y, x+w, y+h)
        region  = icon.crop(box)
        region.save(icon_filename)
        print 'SAVED:', icon_filename

    #note: we should add the feature that we can ignore/replace messages with
    #      other messages. This is mostly important to avoid sending all the
    #      pixel data to the client which it can not use in this format anyway.

    MESSAGES = {
        MSG_BROADCAST_PORT : broadcast_port,
        MSG_PING           : ping,
        MSG_DEF_PLAYFIELD  : def_playfield,
        MSG_DEF_BITMAP     : def_bitmap,
        MSG_DEF_ICON       : def_icon,
        }

    def __init__(self):
        self.socket = None
        self.data   = ''

    def handleServerMessage(self, *values):
        #print 'RECEIVED MESSAGE:%s(%d)' % (values[0], len(values[1:]))
        fn = self.MESSAGES.get(values[0])
        if fn:
            fn(self, *values[1:])
        else:
            print "UNKNOWN MESSAGE:", values


class Root(controllers.Root):

    _sessionData = {}
    n_header_lines = 2

    host = 'localhost'
    port = re.findall('value=".*"', urllib.urlopen('http://%s:8000' % host).read())[0]
    port = int(port[7:-1])
    
    def sessionData(self):
        session = cherrypy.session
        sessionid = session['_id']
        if sessionid not in self._sessionData:
            self._sessionData[sessionid] = SessionData()
        return self._sessionData[sessionid]

    def sessionSocket(self, close=False):
        d = self.sessionData()
        if d.socket is None:
            d.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            d.socket.connect((self.host, self.port))
            #XXX todo: session.socket.close() after a timeout
        return d.socket

    @turbogears.expose()
    def send(self, data=message(CMSG_PING)):
        self.sessionSocket().send(data)
        print 'SENT:' + repr(data)
        return self.recv()

    @turbogears.expose()
    def recv(self):
        #XXX hangs if not first sending a ping!
        d = self.sessionData()
        size = 1024
        data = d.data + self.sessionSocket().recv(size)
        while self.n_header_lines > 0 and '\n' in data:
            self.n_header_lines -= 1
            header_line, data = data.split('\n',1)
            print 'RECEIVED HEADER LINE: %s' % header_line
        
        #print 'RECEIVED DATA CONTAINS %d BYTES' % len(data)
        while data:
            values, data = decodemessage(data)
            if not values:
                break  # incomplete message
            d.handleServerMessage(*values)
        d.data = data
        #print 'RECEIVED DATA REMAINING CONTAINS %d BYTES' % len(data)

        return dict(data=data)

    @turbogears.expose()
    def close(self):
        session = cherrypy.session
        sessionid = session['_id']
        d = self.sessionData()
        if d.socket is not None:
            d.socket.close()
        del self._sessionData[sessionid]

