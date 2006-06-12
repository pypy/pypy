//note: we assume Mochikit is already included

function sendToServer() { //XXX for now, just get (proxy) server data
    loadJSONDoc('send').addCallback(
        function (json_doc) {
            var messages = json_doc.messages;
            for (var i in messages) {
                var message = messages[i];
                var s = message.type;
                if (message.type == 'def_icon') {   //code, filename, width, height
                    s += ', filename=' + message.filename;
                }
                document.body.firstChild.nodeValue = s;
            }
            callLater(0.01, sendToServer);  //again...
        }
    );
}

callLater(0.01, sendToServer);
