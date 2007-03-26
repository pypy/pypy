#!/usr/bin/env python

""" a web server that displays status info of the meta server and builds """

import py
import time
from pypy.tool.build import config
from pypy.tool.build import execnetconference
from pypy.tool.build.build import BuildRequest
from pypy.tool.build.web.server import HTTPError, Collection, Handler, \
                                       FsFile, get_nocache_headers

from pypy.tool.build.web import templesser

mypath = py.magic.autopath().dirpath()

def fix_html(html):
    return ('<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Strict//EN" '
            '"http://www.w3.org/TR/xhtml1/DTD/xhtml1-strict.dtd">\n%s' % (
            html.strip().encode('UTF-8'),))

def get_nav(context):
    template = templesser.template(mypath.join('templates/nav.html').read())
    return template.unicode(context)

def get_base_context():
    context = {
        'vhostroot': config.vhostroot,
    }
    context['nav'] = get_nav(context)
    return context

def format_time(t):
    if t is None:
        return None
    time = py.std.time
    return time.strftime('%Y/%m/%d %H:%M', time.gmtime(t))

def get_headers():
    headers = {'Content-Type': 'text/html; charset=UTF-8'}
    headers.update(get_nocache_headers())
    return headers

def format_compileinfo(compileinfo):
    # XXX hack and partially copied from Config.__str__
    from urllib import quote
    from pypy.config.pypyoption import get_pypy_config
    from pypy.config.config import Config
    from pypy.translator.driver import DEFAULTS
    #config = get_pypy_config(DEFAULTS, translating=True)
    cconfig = config.compile_config.copy()
    def add(cconfig, path_upto_here="", outermost=False):
        items = []
        children = [(child._name, child)
                    for child in cconfig._cfgimpl_descr._children]
        children.sort()
        for name, child in children:
            value_default = getattr(cconfig, name)
            if path_upto_here:
                subpath = path_upto_here + "." + name
            else:
                subpath = name
            if isinstance(value_default, Config):
                substr = add(value_default, subpath)
                if substr:
                    items.append("<li> [%s] <ul>" % (name, ))
                    items.append("  " + substr.replace("\n", "\n  "))
                    items.append("</ul> </li>")
            else:
                try:
                    value = compileinfo[subpath]
                except KeyError:
                    continue
                if value == value_default:
                    continue
                if path_upto_here == 'goal_options':
                    title = name
                else:
                    url = "http://codespeak.net/pypy/dist/pypy/doc/config/"
                    url += quote(subpath) + ".html"
                    title = '<a href="%s">%s</a>' % (url, name)
                items.append('<li> %s = %s </li>' % (title, value))
        if outermost and not lines:
            return ""
        return "\n  ".join(items)
    return "<ul> %s </ul>" % (add(cconfig, outermost=False), )

class ServerPage(object):
    """ base class for pages that communicate with the server
    """
    exposed = True
    MAX_CACHE_TIME = 30 # seconds
    _shared = {
        'lock': py.std.thread.allocate_lock(),
        'channel': None,
        'gateway': None,
        'result_cache': {},
        'initialized': False,
    }

    def __init__(self, config, gateway=None):
        self.config = config
        self.gateway = gateway
        self._shared['lock'].acquire()
        try:
            self._init_shared(gateway)
        finally:
            self._shared['lock'].release()

    def _init_shared(self, gateway=None):
        if self._shared['initialized']:
            return self._shared['channel']
        self._shared['gateway'] = gateway = gateway or self.init_gateway()
        self._shared['conference'] = conf = \
            execnetconference.conference(gateway, self.config.port, False)
        self._shared['channel'] = chan = conf.remote_exec(self.remote_code % (
                                                          self.config.path,))
        self._shared['initialized'] = True
        return chan

    def _cleanup_shared(self):
        self._shared['channel'].close()
        self._shared['gateway'].exit()
        self._shared['channel'] = None
        self._shared['gateway'] = None
        self._shared['initialized'] = False
        self.gateway = None

    def _cleanup_cache(self):
        mintime = time.time() - self.MAX_CACHE_TIME
        topop = []
        for key, (ctime, data) in self._shared['result_cache'].items():
            if ctime < mintime:
                topop.append(key)
        for key in topop:
            del self._shared['result_cache'][key]

    remote_code = """
        import sys
        sys.path += %r

        from pypy.tool.build import metaserver_instance
        from pypy.tool.build.web.app import MetaServerAccessor
        msa = MetaServerAccessor(metaserver_instance)
        while 1:
            try:
                methodname, args = channel.receive()
                ret = getattr(msa, methodname)(*args)
                channel.send(ret)
            except IOError: # XXX anything else?
                break
        channel.close()
    """
    def call_method(self, methodname, args=()):
        """ calls a method on the server
        
            methodname is the name of the method to call, args is a tuple

            careful with args, as it's used as dict key for caching (and
            also sent over the wire) so should be fairly simple
        """
        self._shared['lock'].acquire()
        try:
            # XXX should we perhaps do this only once ever X times?
            self._cleanup_cache()
            try:
                ctime, value = self._shared['result_cache'][(methodname, args)]
            except KeyError:
                pass
            else:
                if ctime > time.time() - self.MAX_CACHE_TIME:
                    return value
            performed = False
            if self._shared['channel']:
                channel = self._shared['channel']
                try:
                    channel.send((methodname, args))
                    ret = channel.receive()
                except:
                    exc, e, tb = py.std.sys.exc_info()
                    del tb
                    print ('exception occurred when calling %s(%s): '
                           '%s - %s' % (methodname, args, exc, e))
                    try:
                        self._cleanup_shared()
                    except:
                        exc, e, tb = sys.exc_info()
                        print 'errors during cleanup: %s - %s' % (exc, e)
                else:
                    performed = True
            if not performed:
                channel = self._init_shared(self.gateway)
                channel.send((methodname, args))
                ret = channel.receive()
            self._shared['result_cache'][(methodname, args)] = (time.time(),
                                                                ret)
            return ret
        finally:
            self._shared['lock'].release()
    
    def init_gateway(self):
        if self.config.server in ['localhost', '127.0.0.1']:
            gw = py.execnet.PopenGateway()
        else:
            gw = py.execnet.SshGateway(self.config.server)
        return gw

class MetaServerStatusPage(ServerPage):
    """ a page displaying overall meta server statistics """

    def __call__(self, handler, path, query):
        template = templesser.template(
            mypath.join('templates/metaserverstatus.html').read())
        context = get_base_context()
        context.update(self.get_status())
        return (get_headers(), fix_html(template.unicode(context)))

    def get_status(self):
        return self.call_method('status')

class BuildersInfoPage(ServerPage):
    def __call__(self, handler, path, query):
        template = templesser.template(
            mypath.join('templates/buildersinfo.html').read())
        context = get_base_context()
        context.update({'builders': self.get_buildersinfo()})
        return (get_headers(), fix_html(template.unicode(context)))

    def get_buildersinfo(self):
        infos = self.call_method('buildersinfo')
        ret = []
        # some massaging of the data for Templess
        for bi in infos:
            binfo = bi.copy()
            ret.append(binfo)
            binfo['sysinfo'] = [binfo['sysinfo']]
            binfo['not_busy'] = not binfo['busy_on']
            if binfo['busy_on']:
                b = binfo['busy_on']
                req = BuildRequest.fromstring(binfo['busy_on'])
                id = req.id()
                d = req.todict()
                d['id'] = id
                d['href'] = '/builds/%s' % (id,)
                d.pop('sysinfo', None) # same as builder
                d.pop('build_end_time', None) # it's still busy ;)
                d['compileinfo'] = format_compileinfo(d['compileinfo'])
                for key in ['request_time', 'build_start_time']:
                    if d[key]:
                        d[key] = time.strftime('%Y/%m/%d %H:%M:%S',
                                               time.gmtime(d[key]))
                d['vhostroot'] = config.vhostroot
                binfo['busy_on'] = [d]
            else:
                binfo['busy_on'] = []
        return ret

class BuildPage(ServerPage):
    """ display information for one build """

    def __init__(self, buildid, config, gateway=None):
        super(BuildPage, self).__init__(config, gateway)
        self._buildid = buildid

    def __call__(self, handler, path, query):
        template = templesser.template(
            mypath.join('templates/build.html').read())
        context = get_base_context()
        context.update(self.get_info())
        return (get_headers(), fix_html(template.unicode(context)))

    def get_info(self):
        bpinfo, brstr = self.call_method('buildrequest', (self._buildid,))
        br = BuildRequest.fromstring(brstr)
        if bpinfo == None:
            bpinfo = {'status': 'waiting'}
        return {
            'url': bpinfo.get('buildurl', None),
            'id': br.id(),
            'email': br.email,
            'svnurl': br.svnurl,
            'svnrev': br.normalized_rev,
            'request_time': format_time(br.request_time),
            'build_start_time': format_time(br.build_start_time),
            'build_end_time': format_time(br.build_end_time),
            'sysinfo': [{'key': k, 'value': v} for (k, v) in
                        sorted(br.sysinfo.items())],
            'compileinfo': format_compileinfo(br.compileinfo),
            'status': bpinfo['status'],
            'statusclass': bpinfo['status'].replace(' ', '_'),
            'error': bpinfo.get('error', None),
            'isdone': bpinfo.has_key('error'),
        }

class BuildsIndexPage(ServerPage):
    """ display the list of available builds """

    def __call__(self, handler, path, query):
        template = templesser.template(
            mypath.join('templates/builds.html').read())
        context = get_base_context()
        context.update({'builds': self.get_builds()})
        return (get_headers(), fix_html(template.unicode(context)))

    def get_builds(self):
        data = [(i, BuildRequest.fromstring(b)) for(i, b) in
                         self.call_method('buildrequests')]
        data.sort(lambda a, b: cmp(b[1].request_time, a[1].request_time))
        return [{'id': b.id(),
                 'href': '/builds/%s' % (b.id(),),
                 'email': b.email,
                 'svnurl': b.svnurl,
                 'svnrev': b.normalized_rev,
                 'request_time': format_time(b.request_time),
                 'build_start_time': format_time(b.build_start_time) or '-',
                 'build_end_time': format_time(b.build_end_time) or '-',
                 'status': i['status'],
                 'statusclass': i['status'].replace(' ', '_'),
                 'error': i.get('error', ''),
                 'vhostroot': config.vhostroot}
                for (i, b) in data]

class Builds(Collection):
    """ container for BuildsIndexPage and BuildPage """

    def __init__(self, config, gateway=None):
        self.index = BuildsIndexPage(config, gateway)
        self.config = config
        self.gateway = gateway
    
    def traverse(self, path, orgpath):
        """ generate a BuildPage on the fly """
        # next element of the path is the id of the build '/<collection>/<id>'
        name = path.pop()
        if name in ['', 'index']:
            return self.index
        if len(path):
            # no Collection type children here...
            raise HTTPError(404)
        # we have a name for a build, let's build a page for it (if it can't
        # be found, this page will raise an exception)
        return BuildPage(name, self.config, self.gateway)

class Logs(Collection):
    def __init__(self, config, gateway=None):
        self.config = config
        self.gateway = gateway
    
    def traverse(self, path, orgpath):
        """ generate a BuildPage on the fly """
        # next element of the path is the id of the build '/<collection>/<id>'
        name = path.pop()
        if name == '':
            # we don't have an index
            raise HTTPError(404)
        if len(path):
            # no Collection type children here...
            raise HTTPError(404)
        # we have a name for a build, let's build a page for it (if it can't
        # be found, this page will raise an exception)
        return LogPage(name, self.config, self.gateway)

class LogPage(ServerPage):
    def __init__(self, buildid, config, gateway=None):
        super(LogPage, self).__init__(config, gateway)
        self._buildid = buildid

    def __call__(self, handler, path, query):
        headers = get_headers()
        headers['Content-Type'] = 'text/plain; charset=UTF-8'
        return (headers, self.get_log())

    def get_log(self):
        return self.call_method('log', (self._buildid,))

class Application(Collection):
    """ the application root """
    def __init__(self, config):
        self.style = FsFile(mypath.join('theme/style.css'), 'text/css')
        self.index = self.metaserverstatus = MetaServerStatusPage(config)
        self.buildersinfo = BuildersInfoPage(config)
        self.builds = Builds(config)
        self.logs = Logs(config)
    
    def index(self, handler, path, query):
        template = templesser.template(
            mypath.join('templates/index.html').read())
        return (get_headers(), fix_html(template.unicode(get_base_context())))
    index.exposed = True

class AppHandler(Handler):
    def __init__(self, *args, **kwargs):
        self.application = Application(config)
        Handler.__init__(self, *args, **kwargs)

class MetaServerAccessor(object):
    def __init__(self, ms):
        self.metaserver = ms

    def status(self):
        running = len([b for b in self.metaserver._builders if b.busy_on])
        return {'builders': len(self.metaserver._builders),
                'running': running,
                'queued': len(self.metaserver._queued),
                'waiting': len(self.metaserver._waiting) + running,
                'done': len(self.metaserver._done)}

    def buildersinfo(self):
        ret = []
        for b in self.metaserver._builders:
            ret.append({
                'hostname': b.hostname,
                'sysinfo': b.sysinfo,
                'busy_on': b.busy_on and b.busy_on.serialize() or None,
            })
        return ret

    def buildrequests(self):
        ret = [(self._getinfo(b), b.serialize()) for b in
               self._all_requests()]
        return ret

    def buildrequest(self, id):
        for r in self._all_requests():
            if r.id() == id:
                return (self._getinfo(r), r.serialize())

    def buildpathinfo(self, requestid):
        for bp in self.metaserver._done:
            if bp.request.id() == requestid:
                return {
                    #'log': str(bp.log),
                    'error': str(bp.error),
                    'buildurl': self.metaserver.config.path_to_url(bp),
                }

    def log(self, requestid):
        ids = []
        for bp in self.metaserver._done:
            ids.append(bp.request.id())
            if bp.request.id() == requestid:
                return str(bp.log)
        raise Exception('not %s not found in %s' % (requestid, ids))

    def buildurl(self, id):
        for r in self.metaserver._done:
            if r.request.id() == id:
                return self.metaserver.config.path_to_url(r)

    def _all_requests(self):
        running = [b.busy_on for b in self.metaserver._builders if b.busy_on]
        done = [b.request for b in self.metaserver._done]
        return (self.metaserver._queued + self.metaserver._waiting +
                running + done)

    def _getinfo(self, br):
        status = 'waiting'
        info = self.buildpathinfo(br.id()) or {}
        if br.build_end_time:
            if info['error'] and info['error'] != 'None':
                status = 'failed'
            else:
                status = 'done'
        elif br.build_start_time:
            status = 'in progress'
        info.update({'status': status})
        return info

if __name__ == '__main__':
    from pypy.tool.build.web.server import run_server
    run_server(('', 8080), AppHandler)

