function BnB() { //entrypoint to be called by body.onLoad
	// init global data
	playfield = DIV({'bgcolor':'red', 'width':42, 'height':42}); //updated with def_playfield
	icon = {};
	doc = currentDocument();
	body = doc.body;

        offsetx = 64;
        offsety = 64;
        zoom = 1;

        prev_sprites = [];

        spacebar     = 32;  //XXX hardcoded for now
        cursor_left  = 37;
        cursor_up    = 38;
        cursor_right = 39;
        cursor_down  = 40;
        keycodes = [cursor_right, cursor_left, cursor_up, spacebar]
        key_is_down = [false, false, false, false]

	receiveData();
        handleKeysEvents();
}

function BnBKeyDown(e) {
    var c = String.fromCharCode(e.charCode);
    if (c == 'a') {
        addPlayer(0);
        return;
    }
    if (c == 'r') {
        removePlayer(0);
        return;
    }
    if (c == '-') {
        newZoom(zoom / 2);
        return;
    }
    if (c == '+') {
        newZoom(zoom * 2);
        return;
    }
    for (var i = 0;i < 4;i++) {
        if (e.keyCode == keycodes[i]) {
            var player_id = 0;  //XXX hardcoded for now
            var keynum    = i;
            for (var n = 0;n < 4;n++) {
                if (n != i && key_is_down[n]) {
                    key_is_down[n] = false;
                    sendKey(player_id, n + 4); //fake keyup
                    log('fake keyup:' + n);
                }
            }
            if (!key_is_down[i]) {
                key_is_down[i] = true;
                sendKey(player_id, keynum);
                log('keydown:' + i);
            }
            break;
        }
    }
}

function BnBKeyUp(e) { 
    for (var i = 0;i < 4;i++) {
        if (e.keyCode == keycodes[i]) {
            var player_id = 0;  //XXX hardcoded for now
            var keynum    = i + 4;
            if (key_is_down[i]) {
                key_is_down[i] = false;
                sendKey(player_id, keynum);
                log('keyup:' + i);
            }
            break;
        }
    }
}

function handleKeysEvents() {
    document.onkeydown = BnBKeyDown;
    document.onkeyup   = BnBKeyUp;
    document.onkeypress= BnBKeyDown;
}

function newZoom(z) {
    for (var icon_code in icon) {
        var ic = icon[icon_code];
        ic.width  *= z / zoom;
        ic.height *= z / zoom;
    }
    zoom = z;
    prev_sprites = []; //force redraw
}

function BnBColorToHexString(c) {
	var r = c;	//XXX should do the correct masking here
	var g = c;
	var b = c;
	return Color.fromRGB(r,g,b).toHexString();
}

function handleServerResponse(json_doc) {
    //setTimeout(0, 'receiveData'); //do a new request a.s.a.p
    receiveData();
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
                this.max_images = 999;
                for (var n = 0;n < this.max_images;n++) { //why is firefox so F!@#King slow?
                    var img = IMG({
                        'width':'0', 'height':'0',
                        'style':'position:absolute; top:-1000px; left:0px;'});
                    this.images.push(img);
                }
                //replaceChildNodes(playfield, this.images);
                replaceChildNodes(body, this.images);

                this.inline_frame_starttime = new Date();
                this.n_inline_frames = 0;
            } else {
                this.n_inline_frames++;
                var fps = 1000 / ((new Date() - this.inline_frame_starttime) / this.n_inline_frames);
                document.title = fps + " fps, " +
                    this.n_dynamic_sprites + "/" + prev_sprites.length;
            }

            //XXX firefox isn't instant with changing img.src's!
            //Plus it is very slow when changing the .src attribute
            //So we might be better of keeping a list of animating images 
            //so we can just move those to the right location!

            var sprite_data, icon_code, img, n, prev;
            this.n_dynamic_sprites = 0;
            for (n = 0;n < msg.sprites.length && n < this.max_images;n++) {
                sprite_data = msg.sprites[n];
                icon_code = sprite_data[0];
                if (!(icon_code in icon)) {
                    sprite_data[0] = -100; //force redraw when icon becomes avaliable
                    continue;
                }
                if (n < prev_sprites.length) {
                    prev = prev_sprites[n];
                    if (sprite_data[0] == prev[0] && 
                        sprite_data[1] == prev[1] &&
                        sprite_data[2] == prev[2])
                        continue;
                } else {
                    prev = [-200,-200,-200]; //always draw new sprites
                }
                this.n_dynamic_sprites++;
                if (icon_code      != prev[0])
                    this.images[n].src = icon[icon_code].filename;
                this.images[n].width  = icon[icon_code].width;
                this.images[n].height = icon[icon_code].height;
                if (sprite_data[1] != prev[1])
                    this.images[n].style.left = offsetx + sprite_data[1] * zoom + 'px'
                if (sprite_data[2] != prev[2])
                    this.images[n].style.top  = offsety + sprite_data[2] * zoom + 'px'
            }
            var n_max = prev_sprites.length;
            if (n_max == 0) n_max = this.max_images;
            for (;n < n_max;n++) {
                this.images[n].style.left = "-1000px";
            }
            prev_sprites = msg.sprites;
        } else {
            logWarning('unknown msg.type: ' + msg.type + ', msg: ' + items(msg));
        }
    }
}

function playerName(name) {
    loadJSONDoc('player_name?name=' + name).addCallback(handleServerResponse);
}

function addPlayer(player_id) {
    loadJSONDoc('add_player?player_id=' + player_id).addCallback(handleServerResponse);
}

function removePlayer(player_id) {
    loadJSONDoc('remove_player?player_id=' + player_id).addCallback(handleServerResponse);
}

function receiveData() {
    loadJSONDoc('recv').addCallback(handleServerResponse);
}

function sendKey(player_id, keynum) {
    loadJSONDoc('key?player_id=' + player_id + '&keynum=' + keynum).addCallback(handleServerResponse);
}
