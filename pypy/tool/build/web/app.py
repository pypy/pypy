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

def format_time(t):
    if t is None:
        return None
    time = py.std.time
    return time.strftime('%Y/%m/%d %H:%M', time.gmtime(t))

def get_headers():
    headers = {'Content-Type': 'text/html; charset=UTF-8'}
    headers.update(get_nocache_headers())
    return headers

class ServerPage(object):
    """ base class for pages that communicate with the server
    """
    exposed = True
    _calllock = py.std.thread.allocate_lock()
    _channel_holder = []
    _result_cache = {}
    MAX_CACHE_TIME = 30 # seconds

    def __init__(self, config, gateway=None):
        self.config = config
        self.gateway = gateway or self.init_gateway()

    remote_code = """
        import sys
        sys.path += %r

        from pypy.tool.build import metaserver_instance
        from pypy.tool.build.web.app import MetaServerAccessor
        msi = MetaServerAccessor(metaserver_instance)
        while 1:
            try:
                methodname, args = channel.receive()
                ret = getattr(msi, methodname)(*args)
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
        self._calllock.acquire()
        try:
            try:
                time, value = self._result_cache[(methodname, args)]
            except KeyError:
                pass
            else:
                if time > py.std.time.time() - self.MAX_CACHE_TIME:
                    return value
            performed = False
            if self._channel_holder:
                channel = self._channel_holder[0]
                try:
                    channel.send((methodname, args))
                    ret = channel.receive()
                except:
                    exc, e, tb = py.std.sys.exc_info()
                    del tb
                    print ('exception occurred when calling %s(%s): '
                           '%s - %s' % (methodname, args, exc, e))
                else:
                    performed = True
            if not performed:
                conference = execnetconference.conference(self.gateway,
                                                          self.config.port, False)
                channel = conference.remote_exec(self.remote_code % (
                                                 self.config.path,))
                channel.send((methodname, args))
                ret = channel.receive()
                while self._channel_holder:
                    self._channel_holder.pop()
                self._channel_holder.append(channel)
            self._result_cache[(methodname, args)] = (py.std.time.time(), ret)
            return ret
        finally:
            self._calllock.release()
    
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
        return (get_headers(), fix_html(template.unicode(self.get_status())))

    def get_status(self):
        return self.call_method('status')

class BuildersInfoPage(ServerPage):
    def __call__(self, handler, path, query):
        template = templesser.template(
            mypath.join('templates/buildersinfo.html').read())
        return (get_headers(), fix_html(template.unicode(
                                  {'builders': self.get_buildersinfo()})))

    def get_buildersinfo(self):
        infos = self.call_method('buildersinfo')
        # some massaging of the data for Templess
        for binfo in infos:
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
                # templesser doesn't understand dicts this way...
                d['compileinfo'] = [{'key': k, 'value': v} for (k, v) in
                                    d['compileinfo'].items()]
                for key in ['request_time', 'build_start_time']:
                    if d[key]:
                        d[key] = time.strftime('%Y/%m/%d %H:%M:%S',
                                               time.gmtime(d[key]))
                binfo['busy_on'] = [d]
            else:
                binfo['busy_on'] = []
        return infos

class BuildPage(ServerPage):
    """ display information for one build """

    def __init__(self, buildid, config, gateway=None):
        super(BuildPage, self).__init__(config, gateway)
        self._buildid = buildid

    def __call__(self, handler, path, query):
        template = templesser.template(
            mypath.join('templates/build.html').read())
        return (get_headers(),
                fix_html(template.unicode(self.get_info())))

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
            'compileinfo': [{'key': k, 'value': v} for (k, v) in
                            sorted(br.compileinfo.items())],
            'status': bpinfo['status'],
            'statusclass': bpinfo['status'].replace(' ', '_'),
            'error': bpinfo.get('error', None),
        }

class BuildsIndexPage(ServerPage):
    """ display the list of available builds """

    def __call__(self, handler, path, query):
        template = templesser.template(
            mypath.join('templates/builds.html').read())
        return (get_headers(),
                fix_html(template.unicode({'builds': self.get_builds()})))

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
                 'error': i.get('error', '')}
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

class Application(Collection):
    """ the application root """
    def __init__(self, config):
        self.style = FsFile(mypath.join('theme/style.css'), 'text/css')
        self.index = self.metaserverstatus = MetaServerStatusPage(config)
        self.buildersinfo = BuildersInfoPage(config)
        self.builds = Builds(config)
    
    def index(self, handler, path, query):
        template = templesser.template(
            mypath.join('templates/index.html').read())
        return (get_headers(),
                fix_html(template.unicode({})))
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

    def buildurl(self, id):
        for r in self.metaserver._done:
            if r.request.id() == id:
                return self.metaserver.config.path_to_url(r)

    def _all_requests(self):
        running = [b.busy_on for b in self.metaserver._builders if b.busy_on]
        done = [b.request for b in self.metaserver._done]
        return self.metaserver._queued + self.metaserver._waiting + running + done

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

