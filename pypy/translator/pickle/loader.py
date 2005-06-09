import zipfile, marshal, md5

class Loader:
    def __init__(self, fname):
        self.f = self.open_file(fname)

    def open_file(self, fname):
        raise SyntaxError, "implement open_file"

    def next_block(self):
        raise SyntaxError, "implement next_block"

    def load(self):
        dic = {}
        for blk in self.next_block():
            exec blk in dic
        try:
            return dic['ginst_Translator']
        finally:
            self.close()

    def close(self):
        self.f.close()


class TextLoader(Loader):

    def open_file(self, fname):
        return file(fname)

    def next_block(self):
        data = self.f.read().split('## SECTION ##\n')
        while data:
            yield data.pop(0)
    
class ZipLoader(Loader):
    """ load compiled code from a ZIP file """
        
    def open_file(self, fname):
        return zipfile.ZipFile(fname, "r")

    def next_block(self):
        root = self.f.read('root')
        dump = self.f.read(root)
        assert md5.new(dump).hexdigest() == root, "broken checksum"
        blocknames = marshal.loads(dump)
        for name in blocknames:
            dump = self.f.read(name)
            assert md5.new(dump).hexdigest() == name, "broken checksum"
            yield marshal.loads(dump)
