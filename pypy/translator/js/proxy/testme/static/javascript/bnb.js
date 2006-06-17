function BnB() { //entrypoint to be called by body.onLoad
	// init global data
	playfield = DIV({'bgcolor':'red', 'width':42, 'height':42}); //updated with def_playfield
	icon = {};
	doc = currentDocument();
	body = doc.body;
        zoom = 1;
	receiveData();
}

function BnBColorToHexString(c) {
	var r = c;	//XXX should do the correct masking here
	var g = c;
	var b = c;
	return Color.fromRGB(r,g,b).toHexString();
}

function handleServerResponse(json_doc) {
    receiveData(); //do a new request a.s.a.p
    for (var i in json_doc.messages) {
        var msg = json_doc.messages[i];
        if (msg.type == 'def_playfield') { //XXX refactor to helper functions
            var bgcolor = BnBColorToHexString(msg.backcolor);
            updateNodeAttributes(playfield,
                {'bgcolor':bgcolor, 'width':msg.width, 'height':msg.height});
            //replaceChildNodes(body, playfield);
            body.setAttribute('bgcolor', bgcolor); //XXX hack!

        } else if (msg.type == 'def_icon') {
            icon[msg.icon_code] = msg;
            icon[msg.icon_code].width  *= zoom;
            icon[msg.icon_code].height *= zoom;

        } else if (msg.type == 'inline_frame') { //msg.sounds, msg.sprites
            if (!this.inline_frame_starttime) {
                this.images = [];
                this.max_images = 500;
                for (var n = 0;n < this.max_images;n++) {
                    var img = IMG({
                        'width':'0', 'height':'0',
                        'style':'position:absolute; top:-1000px; left:0px;'});
                    this.images.push(img);
                }
                //replaceChildNodes(playfield, this.images);
                replaceChildNodes(body, this.images);

                this.inline_frame_starttime = new Date();
                this.n_inline_frames = 0;
                this.last_sprites = []
            } else {
                this.n_inline_frames++;
                var fps = 1000 / ((new Date() - this.inline_frame_starttime) / this.n_inline_frames);
                document.title = fps + " fps";
            }

            //XXX firefox isn't instant with changing img.src's!
            //Plus it is very slow when changing the .src attribute
            //So we might be better of keeping a list of animating images 
            //so we can just move those to the right location!

            var sprite_data, icon_code, img, n;
            for (n in msg.sprites) {
                if (n >= this.max_sprites)
                    continue;
                sprite_data = msg.sprites[n];
                icon_code = sprite_data[0];
                if (!(icon_code in icon)) {
                    sprite_data[0] = -100; //force draw when icon becomes avaliable
                    continue;
                }
                if (icon_code      == this.last_sprites[0] && 
                    sprite_data[1] == this.last_sprites[1] &&
                    sprite_data[2] == this.last_sprites[2])
                    continue;
                if (icon_code      != this.last_sprites[0])
                    this.images[n].src = icon[icon_code].filename;
                this.images[n].width  = icon[icon_code].width;
                this.images[n].height = icon[icon_code].height;
                if (sprite_data[1] != this.last_sprites[1])
                    this.images[n].style.left = sprite_data[1] * zoom + 'px'
                if (sprite_data[2] != this.last_sprites[2])
                    this.images[n].style.top  = sprite_data[2] * zoom + 'px'
            }
            for (;n < this.max_images;n++) {
                this.images[n].style.left = "-1000px";
            }
            this.last_sprites = msg.sprites;
        } else {
            logWarning('unknown msg.type: ' + msg.type + ', msg: ' + items(msg));
        }
    }
}

function receiveData() {
    loadJSONDoc('recv').addCallback(handleServerResponse);
}
