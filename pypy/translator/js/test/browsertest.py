from BaseHTTPServer import HTTPServer as BaseHTTPServer, BaseHTTPRequestHandler
import py
from os   import system
from cgi  import parse_qs
from sys  import platform
from time import sleep
import webbrowser
from pypy.translator.js.log import log
log = log.browsertest

class HTTPServer(BaseHTTPServer):
    allow_reuse_address = True

class config:
    http_port = 10001

    html_page = """<html>
<head>
<script type="text/javascript">
%(jscode)s
// code for running the unittest...

function runTest() {
    var result = undefined;
    try {
        result = %(jstestcase)s;
    } catch (e) {
        try {
            result = "throw '" + e.toSource() + "'";
        } catch (dummy) {
            result = "throw 'unknown javascript exception'";
        }
    }

    if (result != undefined || !in_browser) {  // if valid result (no timeout)
        handle_result(result);
    }
};

function handle_result(result) {
    var resultform = document.forms['resultform'];
    if (typeof(result) == typeof({})) {
        result = result.chars;  //assume it's a rpystring
    }
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
    <div id="logdiv"></div>
</body>
</html>"""

    refresh_page = """<html>
<head>
<meta http-equiv="refresh" content="0">
</head>
<body>
<pre>
// testcase: %(jstestcase)s
%(jscode)s
</pre>
</body>
</html>"""


class TestCase(object):
    def __init__(self, jsfilename, jstestcase):
        self.jsfilename = jsfilename
        self.jscode     = open(jsfilename).read()
        self.jstestcase = jstestcase
        self.result     = None


class TestHandler(BaseHTTPRequestHandler):
    """The HTTP handler class that provides the tests and handles results"""

    def do_GET(self):
        global do_status
        if self.path != "/test.html":
            self.send_error(404, "File /test.html not found")
            return
        jsfilename = jstest.jsfilename
        jstestcase = jstest.jstestcase
        jscode     = jstest.jscode
        if self.server.html_page:
            if self.server.is_interactive:
                isinteractive = ''
            else:
                isinteractive = 'resultform.submit();'
            try:
                html_page  = open(self.server.html_page).read() % locals()
            except IOError:
                log("HTML FILE WAS NOT FOUND!!!!")
                self.send_error(404, "File %s not found" % self.server.html_page)
                return
        else:
            html_page = config.html_page % locals()
        
        open("html_page.html", "w").write(html_page)
        self.serve_data('text/html', html_page)
        do_status = 'do_GET'

    def do_POST(self):
        global do_status
        if self.path != "/test.html":
            self.send_error(404, "File /test.html not found")
            return
        form = parse_qs(self.rfile.read(int(self.headers['content-length'])))
        if self.server.is_interactive:
            if not form.has_key('ok'):
                jstest.result = 'Not clicked OK'
            else:
                jstest.result = 'OK'
                #assert False, "Clicked not ok"
        else:
            jstest.result = form['result'][0]
        
        #we force a page refresh here because of two reason:
        # 1. we don't have the next testcase ready yet
        # 2. browser should ask again when we do have a test
        jsfilename = jstest.jsfilename
        jstestcase = jstest.jstestcase
        jscode     = jstest.jscode
        refresh_page = config.refresh_page % locals()
        self.serve_data('text/html', refresh_page)
        do_status = 'do_POST'

    def serve_data(self, content_type, data):
        self.send_response(200)
        self.send_header("Content-type", content_type)
        self.send_header("Content-length", len(data))
        self.end_headers()
        self.wfile.write(data)


class BrowserTest(object):
    """The browser driver"""

    def start_server(self, port, html_page, is_interactive):
        server_address = ('', port)
        self.httpd = HTTPServer(server_address, TestHandler)
        self.httpd.is_interactive = is_interactive
        self.httpd.html_page = html_page

    def get_result(self):
        global do_status
        do_status = None
        while do_status != 'do_GET':
            self.httpd.handle_request()
        while do_status != 'do_POST':
            self.httpd.handle_request()
        return jstest.result


def jstest(jsfilename, jstestcase, browser_to_use, html_page = None, is_interactive = False):
    global driver, jstest
    jstest = TestCase(str(jsfilename), str(jstestcase))

    try:
        driver.httpd.html_page = html_page
        driver.httpd.is_interactive = is_interactive
    except:
        driver = BrowserTest()
        driver.start_server(config.http_port, html_page, is_interactive)
        if browser_to_use == 'default':
            browser_to_use = None
        if browser_to_use != 'none':
            webbrowser.get(browser_to_use).open('http://localhost:%d/test.html' % config.http_port)

    result = driver.get_result()
    return result
