function BnB() { //entrypoint to be called by body.onLoad
	// init global data
	playfield = DIV({'bgcolor':'red', 'width':42, 'height':42}); //updated with def_playfield
	icon = {};
	x = 0; y = 0; //for filling the playfield with loaded icons
	doc = currentDocument();
	body = doc.body;
	sendPing();
}

function BnBColorToHexString(c) {
	var r = c;	//XXX should do the correct masking here
	var g = c;
	var b = c;
	return Color.fromRGB(r,g,b).toHexString();
}

function handleServerResponse(json_doc) {
    for (var i in json_doc.messages) {
        var msg = json_doc.messages[i];
        if (msg.type == 'def_playfield') { //XXX refactor to helper functions
            var bgcolor = BnBColorToHexString(msg.backcolor);
            updateNodeAttributes(playfield,
                {'bgcolor':bgcolor, 'width':msg.width, 'height':msg.height});
            replaceChildNodes(body, playfield);
            body.setAttribute('bgcolor', bgcolor); //XXX hack!

        } else if (msg.type == 'def_icon') {
            icon[msg.icon_code] = msg;
            //icon[msg.icon_code].image = new Image();
            //icon[msg.icon_code].image.src = msg.filename;
            /*
            var img = IMG({//'src':msg.filename,
                //'title':msg.filename,
                'width':msg.width, 'height':msg.height,
                'id':'icon_code'+msg.icon_code,
                'style':'position:absolute; top:0px; left:0px;'});
            appendChildNodes(playfield, img);
            */

        } else if (msg.type == 'inline_frame') { //msg.sounds, msg.sprites
            var images = [];
            for (var n in msg.sprites) {
                var sprite_data = msg.sprites[n];
                var icon_code = sprite_data[0];
                var x         = sprite_data[1];
                var y         = sprite_data[2];
                //var obj       = $('icon_code'+icon_code);
                //obj.style.left = x + 'px';
                //obj.style.top  = y + 'px';
                //obj.src = icon[icon_code].filename;

                //XXX need to test performance here. Maybe we should cash images and
                //    reuse what's already attached to the playfield.
                //    On the other hand this might not be bad and communication overhead
                //    seems to be the killer anyway.
                if (icon_code in icon) {
                    var img = IMG({'src':icon[icon_code].filename,
                        'width':icon[icon_code].width, 'height':icon[icon_code].height,
                        'style':'position:absolute; top:' + y + 'px; left:' + x + 'px;'});
                    images.push(img);
                }
            }
            replaceChildNodes(playfield, images);
        }
        else {
            logWarning('unknown msg.type: ' + msg.type + ', msg: ' + items(msg));
        }
    }
    sendPing();
}

function sendPing() {
    loadJSONDoc('ping').addCallback(handleServerResponse);
}
