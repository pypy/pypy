#!/usr/bin/env python
#
# MSK (Malbolge Survival Kit) Malbolge Interpreter
# 2008, Toni Ruottu
#
# I hereby place this interpreter into the public domain.
#

from pypy.rlib.streamio import open_file_as_stream
from pypy.rlib.rStringIO import RStringIO
import sys

class MBException(Exception): pass

class Vm(object):

    def __init__(self, source=None, relax=False, book=False):
        self.d = 0
        self.decode_cipher = \
            r'''+b(29e*j1VMEKLyC})8&m#~W>qxdRp0wkrUo[D7,XTcA"lI''' + \
            r'''.v%{gJh4G\-=O@5`_3i<?Z';FNQuY]szf$!BS/|t:Pn6^Ha'''
        self.encode_cipher = [ord(c) for c in \
            r'''5z]&gqtyfr$(we4{WP)H-Zn,'''+'['+r'''%\3dL+Q;>U!pJS72FhOA1C''' + \
            r'''B6v^=I_0/8|jsb9m<.TVac`uY*MK'X~xDl}REokN:#?G"i@''' ]
        self.cipher_length = len(self.decode_cipher)
        self.WORD_SIZE = 10
        self.REG_MAX = self.tri2dec([2,2,2,2,2,2,2,2,2,2])
        self.MEM_SIZE = self.REG_MAX + 1
        self.instructions = ['j', 'i', '*', 'p', '<', '/', 'v', 'o']
        self.real_io_operations = book
        self.output = RStringIO()

        if source:
            self.load( source, relax )
            self.run()

        print self.output.getvalue()

    def error(self, msg):
        print "ERROR: " + msg
        raise MBException()

    def get_mem(self, ofs):
        u_ofs = ofs
        assert u_ofs >= 0
        return self.mem[u_ofs]

    def set_mem(self, ofs, value):
        u_ofs = ofs
        assert u_ofs >= 0
        self.mem[u_ofs] = value

    def is_graphical_ascii(self, c):
        return 33 <= c <= 126

    def dec2tri(self, d):
        i = self.WORD_SIZE
        t = [0,0,0,0,0,0,0,0,0,0]
        while d > 0:
            i -= 1
            t[i] = d % 3
            d = d / 3
        return t

    def tri2dec(self, t):
        d = 0
        i = 0
        while i < self.WORD_SIZE-1:
            d = (d + t[i]) * 3
            i += 1
        return d + t[i]

    def op(self, at, dt):
        table = [
            [1,0,0],
            [1,0,2],
            [2,2,1]
        ]
        o = [0,0,0,0,0,0,0,0,0,0]
        for i in xrange(self.WORD_SIZE):
            o[i] = table[dt[i]][at[i]]
        return o

    def validate_source(self, length):
        pass
        # if [c for c in self.mem[(:length)] if not self.is_graphical_ascii(c)]:
        #     self.error('source code contains invalid character(s)')
        # valid = set(self.instructions)
        # used = set([self.decode(_) for _ in xrange(length)])
        # if len(used - valid) > 0:
        #     self.error('source code contains invalid instruction(s)')

    def load(self, source, relax=False):
        if len(source) < 2:
            self.error('source code too short: must be no shorter than 2')
        if len(source) > self.MEM_SIZE:
            self.error('source code too long: must be no longer than ' + str(self.MEM_SIZE))
        code = [ord(_) for _ in source if not _.isspace()]
        self.mem = code
        for i in range(self.MEM_SIZE - len(code)):
            self.mem.append(0)
        if not relax:
            self.validate_source(len(code))
        for i in xrange(len(code),self.MEM_SIZE):
            at = self.dec2tri(self.mem[i-1])
            dt = self.dec2tri(self.mem[i-2])
            self.mem[i] = self.tri2dec(self.op(at, dt))

    def i_setdata(self):
        self.d = self.get_mem(self.d)

    def i_setcode(self):
        self.c = self.get_mem(self.d)

    def i_rotate(self):
        t = self.dec2tri( self.get_mem(self.d))
        size = len(t) - 1
        assert size >= 0
        t = t[size:] + t[:size] 
        self.set_mem(self.d, self.tri2dec(t))
        self.a = self.get_mem(self.d)

    def i_op(self):
        at = self.dec2tri(self.a)
        dt = self.dec2tri(self.get_mem(self.d))
        self.set_mem(self.d, self.tri2dec(self.op(at, dt)))
        self.a = self.get_mem(self.d)

    def i_write(self):
        self.output.write(chr(self.a & 0xff))

    def i_read(self):
        raise NotImplementedError
        x = self.input.read(1)
        if (len(x) < 1): #EOF
            self.a = self.REG_MAX
        else:
            self.a = ord(x)

    def i_stop(self):
        pass

    def i_nop(self):
        pass

    def validate(self, addr):
        if not self.is_graphical_ascii(self.get_mem(self.c)):
            self.error('illegal code detected')

    def decode(self,addr):
        return self.decode_cipher[( self.get_mem(addr) - 33 + addr ) % self.cipher_length]

    def is_running(self):
        return self.i != 'v'

    def fetch(self):
        self.validate(self.get_mem(self.c))
        self.i = self.decode(self.c)

    def execute(self):
        if self.i == 'j': self.i_setdata()
        elif self.i == 'i': self.i_setcode()
        elif self.i == '*': self.i_rotate()
        elif self.i == 'p': self.i_op()
        elif self.i == 'v': self.i_stop()
        elif self.i == 'o': self.i_nop()
        else:
            if self.real_io_operations:
                if self.i == '<': self.i_read()
                elif self.i == '/': self.i_write()
            else:
                if self.i == '<': self.i_write()
                elif self.i == '/': self.i_read()

    def modify(self):
        self.set_mem(self.c, self.encode_cipher[self.get_mem(self.c) - 33])

    def increment_c(self):
        self.c += 1
        if self.c > self.REG_MAX:
            self.c = 0

    def increment_d(self):
        self.d += 1
        if self.d > self.REG_MAX:
            self.d = 0

    def run(self):
        self.a = 0  # accumulator
        self.c = 0  # code pointer
        self.d = 0  # data pointer
        self.i = '' # instruction
        while self.is_running():
            self.fetch()
            self.execute()
            self.modify()
            self.increment_c()
            self.increment_d()

def entry_point(args):
    f = open_file_as_stream(args[1])
    source = f.readall()
    f.close()

    relax = '--relaxed' in args
    book = '--by-the-book' in args

    try:
        Vm(source,relax=relax,book=book)
    except MBException, e:
        return 1
    except KeyboardInterrupt:
        pass
    return 0

def target(driver, args):
    return entry_point, None
