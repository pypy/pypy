import sys 
import py
import re

class Result(object): 
    def __init__(self, init=True): 
        self._headers = {}
        self._blocks = {}
        self._blocknames = []
        if init: 
            stdinit(self) 

    def __setitem__(self, name, value): 
        self._headers[name.lower()] = value 

    def __getitem__(self, name): 
        return self._headers[name.lower()]

    def get(self, name, default): 
        return self._headers.get(name, default) 
    
    def __delitem__(self, name): 
        del self._headers[name.lower()]

    def items(self): 
        return self._headers.items()

    def addnamedtext(self, name, text): 
        assert isinstance(text, basestring)
        assert isinstance(name, str)
        self._blocknames.append(name) 
        self._blocks[name] = text 

    def getnamedtext(self, name): 
        return self._blocks[name]

    def repr_short_error(self): 
        if not self.isok(): 
            if 'reportdiff' in self._blocks: 
                return "output comparison failed, see reportdiff"
            else: 
                text = self.getnamedtext('stderr') 
                lines = text.strip().split('\n')
                if lines: 
                    return lines[-1]

    def repr_mimemessage(self): 
        from email.MIMEMultipart  import MIMEMultipart 
        from email.MIMEText  import MIMEText
        
        outer = MIMEMultipart()
        items = self._headers.items()
        items.sort()
        reprs = {}
        for name, value in items:
            assert ':' not in name
            chars = map(ord, name)
            assert min(chars) >= 33 and max(chars) <= 126
            outer[name] = str(value) 
            if not isinstance(value, str): 
                typename = type(value).__name__ 
                assert typename in vars(py.std.__builtin__)
                reprs[name] = typename 

        outer['_reprs'] = repr(reprs) 
    
        for name in self._blocknames: 
            text = self._blocks[name]
            m = MIMEText(text)
            m.add_header('Content-Disposition', 'attachment', filename=name)
            outer.attach(m) 
        return outer 

    def grep_nr(self,text,section='stdout'):
        stdout = self._blocks[section]
        find = re.search('%s(?P<nr>\d+)'%text,stdout)
        if find: 
            return float(find.group('nr'))
        return 0. 

    def ratio_of_passed(self):
        if self.isok():
            return 1.   
        elif self.istimeout():
            return 0.
        else:
            nr = self.grep_nr('Ran ')
            if nr > 0:
                return (nr - (self.grep_nr('errors=') + self.grep_nr('failures=')))/nr
            else:
              passed = self.grep_nr('TestFailed: ',section='stderr')
              run = self.grep_nr('TestFailed: \d+/',section='stderr')
              if run > 0:
                  return passed/run
              else:
                  run = self.grep_nr('TestFailed: \d+ of ',section='stderr')
                  if run > 0 :
                      return (run-passed)/run
                  else:
                      return 0.0

    def isok(self):
        return self['outcome'].lower() == 'ok'

    def iserror(self):
        return self['outcome'].lower()[:3] == 'err' or self['outcome'].lower() == 'fail'

    def istimeout(self): 
        return self['outcome'].lower() == 't/o'

# XXX backward compatibility
def sanitize(msg, path):
    if 'exit-status' in msg.keys():
        return msg
    f = open(str(path), 'r')
    msg = f.read()
    f.close()    
    for broken in ('exit status', 'cpu model', 'cpu mhz'):
        valid = broken.replace(' ','-')
        invalid = msg.find(broken+':')
        msg = (msg[:invalid] + valid +
               msg[invalid+len(valid):])
    from email import message_from_string
    msg = message_from_string(msg)
    return msg

def sanitize_reprs(reprs):
    if 'exit status' in reprs:
        reprs['exit-status'] = reprs.pop('exit status')
            
class ResultFromMime(Result): 
    def __init__(self, path): 
        super(ResultFromMime, self).__init__(init=False) 
        f = open(str(path), 'r')
        from email import message_from_file
        msg = message_from_file(f)
        f.close()
        msg = sanitize(msg, path)
        # XXX security wise evil (keep in mind once we accept reporsts
        # from anonymous
        #print msg['_reprs']
        self._reprs = eval(msg['_reprs'])
        del msg['_reprs']
        sanitize_reprs(self._reprs)
        for name, value in msg.items(): 
            if name in self._reprs: 
                value = eval(value)  # XXX security
            self._headers[name] = value 
        self.fspath = self['fspath']
        if self['platform'] == 'win32' and '\\' in self.fspath: 
            self.testname = self.fspath.split('\\')[-1]
        else: 
            self.testname = self.fspath.split('/')[-1]
        #if sys.platform != 'win32' and '\\' in self.fspath: 
        #    self.fspath = py.path.local(self['fspath'].replace('\\'
        self.path = path 
    
        payload = msg.get_payload() 
        if payload: 
           for submsg in payload: 
                assert submsg.get_content_type() == 'text/plain'
                fn = submsg.get_filename() 
                assert fn
                # XXX we need to deal better with encodings to
                #     begin with
                content = submsg.get_payload()
                for candidate in 'utf8', 'latin1': 
                    try:
                        text = unicode(content, candidate)
                    except UnicodeDecodeError: 
                        continue
                else:
                    unicode(content, candidate) 
                self.addnamedtext(fn, text) 

    def ismodifiedtest(self): 
        # XXX we need proper cross-platform paths! 
        return 'modified' in self.fspath

    def __repr__(self): 
        return '<%s (%s) %r rev=%s>' %(self.__class__.__name__, 
                                  self['outcome'], 
                                  self.fspath, 
                                  self['pypy-revision'])

def stdinit(result): 
    import getpass
    import socket
    try:
        username = getpass.getuser()
    except:
        username = 'unknown'
    userhost = '%s@%s' % (username, socket.gethostname())
    result['testreport-version'] = "1.1.1"
    result['userhost'] = userhost 
    result['platform'] = sys.platform 
    result['python-version-info'] = sys.version_info 
    info = try_getcpuinfo() 
    if info is not None:
        result['cpu-model'] = info.get('model name', "unknown")
        result['cpu-mhz'] = info.get('cpu mhz', 'unknown')
#
#
#
def try_getcpuinfo(): 
    if sys.platform.startswith('linux'): 
        cpuinfopath = py.path.local('/proc/cpuinfo')
        if cpuinfopath.check(file=1): 
            d = {}
            for line in cpuinfopath.readlines(): 
                if line.strip(): 
                   name, value = line.split(':', 1)
                   name = name.strip().lower()
                   d[name] = value.strip()
            return d 
