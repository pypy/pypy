import sys; sys.path.insert(0, '../../..')
import py, re

mydir = py.magic.autopath().dirpath()

r_end = re.compile(r"""(.+)\s*========================== closed ==========================
execution time: (.+) seconds
exit status: (.+)
$""")

r_timeout = re.compile(r"""==========================timeout==========================
""")

class Result:
    name = '?'
    exit_status = '?'
    execution_time = '?'
    timeout = False
    finalline = ''
    
    def read(self, fn):
        self.name = fn.purebasename
        data = fn.read(mode='r')
        match = r_end.search(data)
        assert match
        self.finalline = match.group(1)
        self.execution_time = float(match.group(2))
        self.exit_status = match.group(3)
        self.timeout = bool(r_timeout.match(data))

    def __str__(self):
        return '%-17s %3s  %5s  %s' % (
            self.name,
            self.exit_status,
            self.timeout and 'timeout' or str(self.execution_time)[:5],
            self.finalline)


files = mydir.listdir("*.txt")
files.sort()
for fn in files:
    result = Result()
    try:
        result.read(fn)
    except AssertionError:
        pass
    print result
