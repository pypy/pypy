import py
from py.__.documentation.conftest import Directory as Dir, DoctestText, \
                                            ReSTChecker
mypath = py.magic.autopath().dirpath()

Option = py.test.Config.Option
option = py.test.Config.addoptions("pypybuilder test options",
        Option('', '--functional',
               action="store_true", dest="functional", default=False,
               help="run pypybuilder functional tests"
        ),
)

class Directory(Dir):
    def run(self):
        if self.fspath == mypath:
            return ['test']
        return super(Directory, self).run()
