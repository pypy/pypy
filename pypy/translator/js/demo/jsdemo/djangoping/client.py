"""rpython javascript code"""

from pypy.rpython.ootypesystem.bltregistry import BasicExternal, MethodDesc, described

from pypy.translator.js.modules import mochikit
from pypy.translator.js.modules import _dom as dom

class PingHandler(BasicExternal):
    """Server side code which handles javascript calls"""
    _render_xmlhttp = True
        
    @described(retval={"aa":"aa"})
    def ping(self, ping_str="aa"):
        """Simply returns the string prefixed with a PONG"""
        return dict(response="PONG: %s" % ping_str)

ping_handler = PingHandler()    

class Pinger(object):
    """Client side javascript ping code which pings the server"""    
    def initialise(self):
        self.log = dom.get_document().getElementById("log")
    
    def ping(self):
        mochikit.logDebug("pinging")
        ping_handler.ping("PING", callback)

pinger = Pinger()

def callback(data):
    mochikit.logDebug("Got response: " + data["response"])
    log = pinger.log
    mochikit.logDebug("got log element")
    try:
        s = "<p>" + data["response"] + "</p>"
    except KeyError:
        mochikit.logDebug("Can't find data")
        s = "<p>" + "Error" + "</p>"
    mochikit.logDebug("Adding: " + s)
    log.innerHTML += s
    mochikit.logDebug("added message")

def doping_onclick(event):
    mochikit.logDebug("calling pinger")
    pinger.ping()

def ping_init():
    mochikit.createLoggingPane(True)
    pinger.initialise()
    button = dom.get_document().getElementById("doping")
    button.onclick = doping_onclick
    mochikit.logDebug("Ping button setup")

if __name__ == "__main__":
    # circular import
    from pypy.translator.js.demo.jsdemo.djangoping import client
    from pypy.translator.js.main import rpython2javascript
    print rpython2javascript(client, ["ping_init"])
