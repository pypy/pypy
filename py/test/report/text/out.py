from __future__ import generators
import sys
import os

class Out(object):
    tty = False
    fullwidth = int(os.environ.get('COLUMNS', 80))-1
    def __init__(self, file):
        self.file = file 

    def sep(self, sepchar, title=None):
        fullwidth = self.fullwidth 
        #spacing = " " * ((79 - compwidth)/2)
        if title is not None:
            size = len(title) + 2
            half = (fullwidth-size) / 2.0
            #line = "%s%s %s %s%s" %(spacing, 
            #        sepchar * half, title, sepchar * half, spacing)
            fill = sepchar * int(half / len(sepchar))
            line = "%s %s %s" % (fill, title, fill)
            line += sepchar * int(fullwidth-(half*2+size))
        else:
            line = sepchar * int(fullwidth/len(sepchar))
        self.line(line)

class TerminalOut(Out):
    tty = True
    def __init__(self, file):
        super(TerminalOut, self).__init__(file)
        try:
            import termios,fcntl,struct
            call = fcntl.ioctl(0,termios.TIOCGWINSZ,"\000"*8)
            height,width = struct.unpack( "hhhh", call ) [:2]
            self.fullwidth = width
        except:
            pass

    def write(self, s):
        self.file.write(str(s))
        self.file.flush()

    def line(self, s=''):
        if s:
            self.file.write(s + '\n')
        else:
            self.file.write('\n')
        self.file.flush()

    def rewrite(self, s=''):
        self.write('[u%s' % s) 

class FileOut(Out):
    def write(self, s):
        self.file.write(str(s))
        self.file.flush()

    def line(self, s=''):
        if s:
            self.file.write(str(s) + '\n')
        else:
            self.file.write('\n')
        self.file.flush()

    def rewrite(self, s=''):
        self.write(s) 

def getout(file):
    # investigate further into terminal, this is not enough 
    if False and file.isatty(): 
        return TerminalOut(file) 
    else:
        return FileOut(file) 
