#!/usr/bin/env python

""" a web server that displays status info of the meta server and builds """

import py
from pypy.tool.build import config
from pypy.tool.build import execnetconference
from pypy.tool.build.webserver import HTTPError, Resource, Collection, Handler

mypath = py.magic.autopath().dirpath()

class Template(object):
    def __init__(self, path):
        self.template = path.read()
        
    def render(self, context):
        return self.template % context

class IndexPage(Resource):
    """ the index page """
    def handle(self, handler, path, query):
        template = Template(mypath.join('templates/index.html'))
        return {'Content-Type': 'text/html'}, template.render({})

class ServerStatus(Resource):
    """ a page displaying overall meta server statistics """

    remote_code = """
        import sys
        sys.path += %r

        try:
            from pypy.tool.build import metaserver_instance
            ret = metaserver_instance.status()
            channel.send(ret)
            channel.close()
        except:
            import sys, traceback
            exc, e, tb = sys.exc_info()
            channel.send(str(exc) + ' - ' + str(e))
            for line in traceback.format_tb(tb):
                channel.send(line[:-1])
            del tb
    """

    def handle(self, handler, path, query):
        template = Template(mypath.join('templates/serverstatus.html'))
        return ({'Content-Type': 'text/html; charset=UTF-8'},
                template.render(self.get_status()))

    def get_status(self):
        if config.server in ['localhost', '127.0.0.1']:
            gw = py.execnet.PopenGateway()
        else:
            gw = py.execnet.SshGateway(config.server)

        conference = execnetconference.conference(gw, config.port, False)
        channel = conference.remote_exec(self.remote_code % (config.path,))
        ret = channel.receive()
        channel.close()
        return ret

class Application(Collection):
    """ the application root """
    index = IndexPage()
    serverstatus = ServerStatus()
    foo = Collection()
    foo.index = IndexPage()

class AppHandler(Handler):
    application = Application() # shared by all instances!

if __name__ == '__main__':
    from pypy.tool.build.webserver import run_server
    run_server(('', 8080), AppHandler)

