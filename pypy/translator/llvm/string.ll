internal uint %std.len(%std.string* %a) {
	%p = getelementptr %std.string* %a, int 0, uint 0
	%length1 = load uint* %p
	ret uint %length1
}

internal %std.string* %std.make(uint %len, sbyte* %s) {
	%ret = malloc %std.string, uint 1
	%lenp = getelementptr %std.string* %ret, int 0, uint 0
	%lsp = getelementptr %std.string* %ret, int 0, uint 1
	store uint %len, uint* %lenp
	store sbyte* %s, sbyte** %lsp
	ret %std.string* %ret
}


internal %std.string* %std.add(%std.string* %a, %std.string* %b) {
	%lena = call uint %std.len(%std.string* %a)
	%lenb = call uint %std.len(%std.string* %b)
	%totlen = add uint %lena, %lenb
	%nmem1 = malloc sbyte, uint %totlen
	%oldsp1 = getelementptr %std.string* %a, int 0, uint 1
	%oldsp2 = getelementptr %std.string* %b, int 0, uint 1
	%olds1 =  load sbyte** %oldsp1
	%olds2 =  load sbyte** %oldsp2
	%nposp = getelementptr sbyte* %nmem1, uint %lena
	call void %llvm.memcpy(sbyte* %nmem1, sbyte* %olds1, uint %lena, uint 0)
	call void %llvm.memcpy(sbyte* %nposp, sbyte* %olds2, uint %lenb, uint 0)
	%ret = call %std.string* %std.make(uint %totlen, sbyte* %nmem1)
	ret %std.string* %ret
}


internal sbyte %std.getitem(%std.string* %s, int %p) {
	%sp1 = getelementptr %std.string* %s, int 0, uint 1
	%s1 = load sbyte** %sp1
	%len = call uint %std.len(%std.string* %s)
	%ilen = cast uint %len to int
	%negpos = add int %ilen, %p
	%is_negative = setlt int %p, 0
	%usedpos = select bool %is_negative, int %negpos, int %p
	%negusedpos = setlt int %usedpos, 0
	%posbig = setgt int %usedpos, %ilen
	%wrongindex = or bool %negusedpos, %posbig
	%charp = getelementptr sbyte* %s1, int %usedpos
	%value = load sbyte* %charp
	%ret = select bool %wrongindex, sbyte 33, sbyte %value
	ret sbyte %value
}
