import py
from py.__.path.local.local import LocalPath

def normalize_revision(svnurl, rev, highest_if_error=True):
    """ return the actual revision of a certain repo state

        if the string HEAD is provided, this looks up the trunk revision, if
        the provided revision is an int (or string containing an int), the
        revision id of the last revision before rev is returned, including (so
        if rev itself had changes, rev is returned)
    """
    if rev == 'HEAD':
        u = py.path.svnurl(svnurl)
    else:
        rev = int(rev)
        u = py.path.svnurl(svnurl, rev=rev)
    try:
        return int(u.info().created_rev)
    except py.error.Error:
        if not highest_if_error:
            raise
        u = py.path.svnurl(svnurl)
        return int(u.info().created_rev)

class BuildPath(LocalPath):
    """ a subclass from py.path.local that has some additional properties

        * BuildPath.request holds the request object
    
        * BuildPath.zipfile returns a zip file (path object) with the build 
          results (if available)

        * BuildPath.log has the log of the build (if available)

        * BuildPath.done indicates whether the build is done or still in
          progress
        
    """

    def _request(self):
        req = self.join('request')
        if not req.check():
            return None
        return BuildRequest.fromstring(req.read())

    def _set_request(self, request):
        self.ensure('request', file=True).write(request.serialize())

    request = property(_request, _set_request)

    def _zipfile(self):
        return self.ensure('data.zip', file=True)

    def _set_zipfile(self, iterable):
        # XXX not in use right now...
        fp = self._zipfile().open('w')
        try:
            for chunk in iterable:
                fp.write(chunk)
        finally:
            fp.close()

    zipfile = property(_zipfile, _set_zipfile)

    def _log(self):
        log = self.join('log')
        if not log.check():
            return ''
        return log.read()
    
    def _set_log(self, data):
        self.ensure('log', file=True).write(data)

    log = property(_log, _set_log)

    def _done(self):
        return not not self.log
    done = property(_done)

    _reg_error = py.std.re.compile(r'uring compilation:\n([^:]+): (.*)')
    def _error(self):
        import exceptions
        if self.done and not self.zipfile.size():
            log = self.log
            match = self._reg_error.search(log)
            if not match:
                return Exception
            exc = match.group(1)
            msg = match.group(2)
            try:
                exc = eval('%s(%r)' % (exc, msg))
            except Exception, e:
                print e
                exc = Exception('%s: %s' % (exc, msg))
            return exc
        return None

    error = property(_error)

class BuildRequest(object):
    """ build request data

        holds information about a build request, and some functionality to
        serialize and unserialize itself
    """
    def __init__(self, email, sysinfo, compileinfo, svnurl, svnrev, revrange,
                 request_time=None, build_start_time=None,
                 build_end_time=None):
        self.email = email
        self.sysinfo = sysinfo
        self.compileinfo = compileinfo
        self.svnurl = svnurl
        self.svnrev = svnrev
        self.revrange = revrange
        self.request_time = request_time or py.std.time.time()
        self.build_start_time = build_start_time
        self.build_end_time = build_end_time

    def __str__(self):
        return '<BuildRequest %s:%s>' % (self.svnurl, self.normalized_rev)

    def __repr__(self):
        """ the result of this method can be exec-ed when build.py is imported
        """
        return 'build.BuildRequest(%r, %r, %r, %r, %r, %r, %s, %s, %s)' % (
                self.email, self.sysinfo, self.compileinfo, self.svnurl,
                self.svnrev, self.revrange, self.request_time,
                self.build_start_time, self.build_end_time)

    def todict(self):
        data = {'normalized_rev': self.normalized_rev} # it's a property
        data.update(self.__dict__)
        data.pop('_nr', 0)
        return data

    def serialize(self):
        return """\
email: %(email)s
sysinfo: %(sysinfo)r
compileinfo: %(compileinfo)r
svnurl: %(svnurl)s
svnrev: %(svnrev)s
revrange: %(revrange)s
normalized_rev: %(normalized_rev)s
request_time: %(request_time)s
build_start_time: %(build_start_time)s
build_end_time: %(build_end_time)s
""" % self.todict()

    def id(self):
        # XXX can this be made better? we certainly don't want clashes :|
        sorted_sysinfo = sorted(self.sysinfo.items())
        sorted_compileinfo = sorted(self.compileinfo.items())
        str = '%r\n%r\n%r\n%r\n%r' % (self.email, sorted_sysinfo,
                                      sorted_compileinfo, self.svnurl,
                                      self.normalized_rev)
        return '%s.%s' % (self.request_time, py.std.md5.new(str).hexdigest())

    def fromstring(cls, s):
        data = {}
        for line in s.strip().split('\n'):
            try:
                key, value = line.split(':', 1)
            except ValueError:
                raise SyntaxError('line %r not in the right format' % (line,))
            data[key.strip()] = value.strip()
        ret = cls(data['email'], eval(data['sysinfo']),
                  eval(data['compileinfo']), data['svnurl'], data['svnrev'],
                  int(data['revrange']))
        ret._nr = int(data['normalized_rev'])
        ret.request_time = eval(data['request_time'])
        ret.build_start_time = eval(data['build_start_time'])
        ret.build_end_time = eval(data['build_end_time'])
        return ret
    fromstring = classmethod(fromstring)

    def has_satisfying_data(self, other):
        """ return True if other request's data satisfies our needs """
        return (self.sysinfo == other.sysinfo and
                self.compileinfo == other.compileinfo and
                self.svnurl == other.svnurl and
                self.rev_in_range(other.normalized_rev))

    _nr = None
    def _normalized_rev(self):
        if self._nr is None:
            self._nr = normalize_revision(self.svnurl, self.svnrev)
        return self._nr
    normalized_rev = property(_normalized_rev)

    def rev_in_range(self, comparerev):
        return (self.normalized_rev >= comparerev - self.revrange and
                self.normalized_rev <= comparerev + self.revrange)

    def __eq__(self, other):
        return isinstance(other, self.__class__) and repr(self) == repr(other)

    def __ne__(self, other):
        return not self.__eq__(other)

