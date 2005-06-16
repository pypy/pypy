import zipfile, marshal, md5

class Writer:
    def __init__(self, fname):
        self.pieces = []
        self.chunksize = 100000
        self.count = 0
        self.blocknum = 0
        self.opened = False
        self.f = self.open_file(fname)

    def open_file(self, fname):
        raise SyntaxError, "implement open_file"

    def write(self, text):
        self.pieces.append(text)
        self.count += len(text) + 1
        if self.count >= self.chunksize:
            src = ''.join(self.pieces)
            del self.pieces[:]
            self.count -= self.chunksize
            self.putblock(src)
            self.blocknum += 1

    def close(self):
        src = ''.join(self.pieces)
        self.putblock(src)
        self.finalize()
        if self.opened:
            self.f.close()

    def finalize(self):
        pass


class TextWriter(Writer):

    def open_file(self, fname):
        if type(fname) is str:
            self.opened = True
            return file(fname, 'w')
        return fname # should be a file-like object

    def putblock(self, src):
        self.f.write(src)
        print >> self.f, '## SECTION ##'
    
class ZipWriter(Writer):
    """ write compiled code to a ZIP file """

    def __init__(self, fname):
        Writer.__init__(self, fname)
        self.blocknames = []
        
    def open_file(self, fname):
        if type(fname) is str:
            self.opened = True
            return zipfile.ZipFile(fname, "w", zipfile.ZIP_DEFLATED)
        return fname

    def putblock(self, src):
        cod = compile(src, 'block_%d' % self.blocknum, 'exec')
        dump = marshal.dumps(cod)
        digest = md5.new(dump).hexdigest()
        self.blocknames.append(digest)
        self.f.writestr(digest, dump)

    def finalize(self):
        dump = marshal.dumps(self.blocknames)
        digest = md5.new(dump).hexdigest()
        self.f.writestr(digest, dump)
        self.f.writestr('root', digest)

__all__ = ['Writer', 'TextWriter', 'ZipWriter']
