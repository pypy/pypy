""" rpython guestbook client-side code

    this code can be tested in CPython, but will also be converted to
    JavaScript to provide the client-side functionality for the guestbook
    example
"""

from pypy.translator.js.modules import dom
from pypy.translator.js.examples.guestbook import exported_methods

def _get_messages_callback(messages):
    for message in messages:
        add_html_message(message)

def init_guestbook():
    exported_methods.get_messages(_get_messages_callback)

def _add_message_callback(message):
    add_html_message(message)

def add_message():
    doc = dom.window.document
    name = doc.getElementById('name').value
    message = doc.getElementById('message').value
    exported_methods.add_message(name, message, _add_message_callback)

def add_html_message(text=''):
    doc = dom.window.document
    div = doc.getElementById('messages')
    msgdiv = doc.createElement('div')
    msgdiv.style.border = '1px solid black'
    msgdiv.style.margin = '1em'
    msgdiv.appendChild(doc.createTextNode(text))
    div.appendChild(msgdiv)

