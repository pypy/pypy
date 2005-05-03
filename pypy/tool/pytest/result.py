import sys 
import py

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
        assert isinstance(text, str)
        assert isinstance(name, str)
        self._blocknames.append(name) 
        self._blocks[name] = text 

    def getnamedtext(self, name): 
        return self._blocks[name]

    def repr_short_error(self): 
        if not self.isok(): 
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

    def isok(self): 
        return self['outcome'].lower() == 'ok'
    def iserror(self): 
        return self['outcome'].lower()[:3] == 'err'
    def istimeout(self): 
        return self['outcome'].lower() == 't/o'

class ResultFromMime(Result): 
    def __init__(self, path): 
        super(ResultFromMime, self).__init__(init=False) 
        f = open(str(path), 'r') 
        from email import message_from_file 
        msg = message_from_file(f)
        # XXX security wise evil (keep in mind once we accept reporsts
        # from anonymous
        #print msg['_reprs']
        self._reprs = eval(msg['_reprs']) 
        del msg['_reprs']
        for name, value in msg.items(): 
            if name in self._reprs: 
                value = eval(value)  # XXX security
            self._headers[name] = value 
        self.fspath = py.path.local(self['fspath']) 
        self.path = path 
    
        payload = msg.get_payload() 
        if payload: 
           for submsg in payload: 
                assert submsg.get_main_type() == 'text'
                fn = submsg.get_filename() 
                assert fn
                self.addnamedtext(fn, submsg.get_payload())
    def __repr__(self): 
        return '<%s (%s) %r rev=%s>' %(self.__class__.__name__, 
                                  self['outcome'], 
                                  self.fspath.purebasename, 
                                  self['pypy-revision'])

def stdinit(result): 
    import getpass
    import socket
    try:
        username = getpass.getuser()
    except:
        username = 'unknown'
    userhost = '%s@%s' % (username, socket.gethostname())
    result['testreport-version'] = "1.1" 
    result['userhost'] = userhost 
    result['platform'] = sys.platform 
    result['python-version-info'] = sys.version_info 
    info = try_getcpuinfo() 
    if info is not None:
        result['cpu model'] = info['model name']
        result['cpu mhz'] = info['cpu mhz']
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
