from BaseHTTPServer import HTTPServer, BaseHTTPRequestHandler
import py
from os   import system
from cgi  import parse_qs
from sys  import platform
from time import sleep
from pypy.translator.js.log import log
log = log.browsertest


class config:

    #XXX refactor this into using the webbrowser module 
    #    (http://docs.python.org/lib/module-webbrowser.html)
    if platform == 'darwin':
        browser = ('/Applications/Firefox.app/Contents/MacOS/', 'firefox-bin')

        #XXX Safari does not accept a http://... format, it still thinks it's a file://...
        #browser = ('/Applications/Safari.app/Contents/MacOS/', 'Safari')

    elif platform == 'linux2':
        browser = ('/usr/bin/', 'firefox')

    else:   #win32...
        browser = ('', 'firefox-bin')
        
    http_port = 10001

    html_page = """<html>
<head>
<title>%(jsfilename)s</title>
<script type="text/javascript">
%(jscode)s
</script>
<script type="text/javascript">
    function runTest() {
        var result = undefined;
        try {
            result = %(jstestcase)s;
        } catch (e) {
            //result = 'Exception("' + e.toString() + '")'
            result = 'undefined'
        }
        var resultform = document.forms['resultform'];
        resultform.result.value = result;
        resultform.submit();
    };
</script>
</head>
<body onload="runTest()">
    %(jsfilename)s
    <form method="post" name="resultform" id="resultform">
        <input name="result" type="hidden" value="UNKNOWN" />
    </form>
</body>
</html>"""

    refresh_page = """<html>
<head>
<meta http-equiv="refresh" content="0">
</head>
<body>
refresh after %(jsfilename)s
</body>
</html>"""


class TestCase(object):
    def __init__(self, jsfilename, jstestcase):
        self.jsfilename = jsfilename
        self.jstestcase = jstestcase
        self.result     = None


class TestHandler(BaseHTTPRequestHandler):
    """The HTTP handler class that provides the tests and handles results"""

    def do_GET(self):
        global do_status
        log('do_GET path', self.path)
        if self.path != "/":
            self.send_error(404, "File not found")
            return
        jstestcase = jstest.jstestcase
        jsfilename = str(jstest.jsfilename)
        jscode     = open(jsfilename).read()
        html_page  = config.html_page % locals()
        log('do_GET sends', jsfilename)
        self.serve_data('text/html', html_page)
        do_status = 'do_GET'

    def do_POST(self):
        global do_status
        log('do_POST path', self.path)
        if self.path != "/":
            self.send_error(404, "File not found")
            return
        form = parse_qs(self.rfile.read(int(self.headers['content-length'])))
        jstest.result = form['result'][0]
        log('do_POST received result', jstest.result)

        #we force a page refresh here because of two reason:
        # 1. we don't have the next testcase ready yet
        # 2. browser should ask again when we do have a test
        jsfilename = jstest.jsfilename
        refresh_page = config.refresh_page % locals()
        self.serve_data('text/html', refresh_page)
        log('do_POST sends refresh page')
        do_status = 'do_POST'

    def serve_data(self, content_type, data):
        self.send_response(200)
        self.send_header("Content-type", content_type)
        self.send_header("Content-length", len(data))
        self.end_headers()
        self.wfile.write(data)


class BrowserTest(object):
    """The browser driver"""

    def start_server(self, port):
        log('BrowserTest.start_server')
        server_address = ('', port)
        self.httpd = HTTPServer(server_address, TestHandler)

    def get_result(self):
        global do_status
        do_status = None
        while do_status != 'do_GET':
            log('waiting for do_GET')
            self.httpd.handle_request()
        while do_status != 'do_POST':
            log('waiting for do_POST')
            self.httpd.handle_request()
        while not jstest.result:
            log('waiting for result')
            sleep(1.0)
        return jstest.result


def jstest(jsfilename, jstestcase):
    global driver, jstest
    jstest = TestCase(jsfilename, jstestcase)

    try:
        driver
    except:
        browser_path, browser_exe = config.browser
        cmd = 'killall %(browser_exe)s 2>&1 2>/dev/null' % locals()
        log(cmd)
        system(cmd)

        driver = BrowserTest()
        driver.start_server(config.http_port)

        cmd = '"%s%s" http://localhost:%d &' % (browser_path, browser_exe, config.http_port)
        log(cmd)
        system(cmd)

    result = driver.get_result()
    return result
