function BnB() { //entrypoint to be called by body.onLoad
	// init global data
	playfield = DIV({'bgcolor':'red', 'width':42, 'height':42}); //updated with def_playfield
	icon = {};
	x = 0; y = 0; //for filling the playfield with loaded icons
	doc = currentDocument();
	body = doc.body;
	sendToServer();
}

function BnBColorToHexString(c) {
	var r = c;	//XXX should do the correct masking here
	var g = c;
	var b = c;
	return Color.fromRGB(r,g,b).toHexString();
}

function sendToServer() { //XXX for now, just get (proxy) server data
    loadJSONDoc('send').addCallback(
        function (json_doc) {
            for (var i in json_doc.messages) {
                var msg = json_doc.messages[i];
		if (msg.type == 'def_playfield') { //XXX refactor to helper functions
		    var bgcolor = BnBColorToHexString(msg.backcolor);
		    updateNodeAttributes(playfield,
			{'bgcolor':bgcolor, 'width':msg.width, 'height':msg.height});
		    replaceChildNodes(body, playfield);
		    body.setAttribute('bgcolor', bgcolor); //XXX hack!
		} else if (msg.type == 'def_icon') {
		    if (!(msg.code in icon)) {
			icon[msg.code] = true; //new Image();
			var img = IMG({'src':msg.filename, 'title':msg.filename,
				'width':msg.width, 'height':msg.height});
			appendChildNodes(playfield, img);
		    }
		}
            }
            sendToServer();
        }
    );
}
