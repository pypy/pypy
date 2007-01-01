#!/usr/bin/env python
"""
In this example I'll show how to manipulate DOM tree
from inside RPython code

Note that this is low-level API to manipulate it, which
might be suitable if you don't like boilerplate on top.

There is ongoing effort to provide API of somewhat higher level,
which will be way easier to manipulate.
"""

from pypy.translator.js.examples import server
from pypy.translator.js.main import rpython2javascript
from pypy.translator.js.modules import dom
# dom manipulating module

HTML = """
<html>
<head>
  <script src="source.js"/>
  <title>pypy.js tutorial</title>
</head>
<body>
<table id="atable">
  <tr><td>A row</td></tr>
</table>
<a href="#" onclick="addrow()">Add row</a>
<a href="#" onclick="delrow()">Del row</a>
</body>
</html>
"""

# these are exposed functions
def addrow():
    doc = dom.get_document()
    
    # we need to call a helper, similiar to document in JS
    tr = doc.createElement("tr")
    td = doc.createElement("td")
    td.appendChild(doc.createTextNode("A row"))
    tr.appendChild(td)
    dom.get_document().getElementById("atable").appendChild(tr)

def delrow():
    table = dom.get_document().getElementById("atable")
    # note -1 working here like in python, this is last element in list
    table.removeChild(table.childNodes[-1])

class Handler(server.TestHandler):

    def index(self):
        return HTML
    index.exposed = True

    def source_js(self):
        return "text/javascript", rpython2javascript(None, ["addrow", "delrow"])
    source_js.exposed = True

# server start, same as before
if __name__ == '__main__':
    server.start_server(handler=Handler)
