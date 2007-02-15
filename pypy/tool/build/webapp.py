""" a web server that displays status info of the meta server and builds """

from pypy.tool.build.webserver import HTTPError, Resource, Collection, Handler

class IndexPage(Resource):
    """ the index page """
    def handle(self, handler, path, query):
        return {'Content-Type': 'text/html'}, """\
<html>
  <head>
    <title>Build meta server web interface (temp index page)</title>
  </head>
  <body>
    <a href="/serverstatus">server status</a>
  </body>
</html>
"""

class ServerStatus(Resource):
    """ a page displaying overall meta server statistics """
    def handle(self, handler, path, query):
        return {'Content-Type': 'text/plain'}, 'foo'

class Application(Collection):
    """ the application root """
    index = IndexPage()
    serverstatus = ServerStatus()

class AppHandler(Handler):
    application = Application() # shared by all instances!

if __name__ == '__main__':
    from pypy.tool.build.webserver import run_server
    run_server(('', 8080), AppHandler)

