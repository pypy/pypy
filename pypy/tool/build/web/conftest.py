import py
from py.__.doc.conftest import Directory as Dir, DoctestText, \
                                            ReSTChecker

mypath = py.magic.autopath().dirpath()

Option = py.test.config.Option
option = py.test.config.addoptions("pypybuilder test options",
        Option('', '--webcheck',
               action="store_true", dest="webcheck", default=False,
               help=("run (X)HTML validity tests (using "
                     "http://www.w3c.org/validator)")
        ),
)

class Directory(Dir):
    def run(self):
        if self.fspath == mypath:
            return ['test', 'README.txt', 'README_TEMPLESSER.txt']
        return super(Directory, self).run()
