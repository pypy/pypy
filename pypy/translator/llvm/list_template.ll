;Template for lists

internal uint %std.len(%std.list.%(item)s* %a) {
	%p = getelementptr %std.list.%(item)s* %a, int 0, uint 0
	%length1 = load uint* %p
	ret uint %length1
}

internal int %std.len(%std.list.%(item)s* %a) {
	%length1 = call uint %std.len(%std.list.%(item)s* %a)
	%length = cast uint %length1 to int
	ret int %length
}


internal %std.list.%(item)s* %std.make(uint %len, %(item)s* %s) {
	%ret = malloc %std.list.%(item)s, uint 1
	%lenp = getelementptr %std.list.%(item)s* %ret, int 0, uint 0
	%lsp = getelementptr %std.list.%(item)s* %ret, int 0, uint 1
	store uint %len, uint* %lenp
	store %(item)s* %s, %(item)s** %lsp
	ret %std.list.%(item)s* %ret
}


internal %std.list.%(item)s* %std.newlist(%(item)s %init) {
	%nmem = malloc %(item)s, uint 1
	%ret = call %std.list.%(item)s* %std.make(uint 1, %(item)s* %nmem)
	call void %std.setitem(%std.list.%(item)s* %ret, int 0, %(item)s %init)
	ret %std.list.%(item)s* %ret
}	

internal %(item)s %std.getitem(%std.list.%(item)s* %s, int %p) {
	%sp1 = getelementptr %std.list.%(item)s* %s, int 0, uint 1
	%s1 = load %(item)s** %sp1
	%len = call uint %std.len(%std.list.%(item)s* %s)
	%ilen = cast uint %len to int
	%negpos = add int %ilen, %p
	%is_negative = setlt int %p, 0
	%usedpos = select bool %is_negative, int %negpos, int %p
	%p_item = getelementptr %(item)s* %s1, int %usedpos
	%value = load %(item)s* %p_item
	ret %(item)s %value
}

internal void %std.setitem(%std.list.%(item)s* %s, int %p, %(item)s %n) {
	%sp1 = getelementptr %std.list.%(item)s* %s, int 0, uint 1
	%s1 = load %(item)s** %sp1
	%len = call uint %std.len(%std.list.%(item)s* %s)
	%ilen = cast uint %len to int
	%negpos = add int %ilen, %p
	%is_negative = setlt int %p, 0
	%usedpos = select bool %is_negative, int %negpos, int %p
	%itemp = getelementptr %(item)s* %s1, int %usedpos
	store %(item)s %n, %(item)s* %itemp
	ret void
}
