

internal %std.list.int* %std.range(int %length) {
entry:
	%tmp.1 = setlt int %length, 1
	%tmp.3 = malloc %std.list.int
	%tmp.6 = getelementptr %std.list.int* %tmp.3, int 0, uint 0
	br bool %tmp.1, label %then, label %endif

then:
	store uint 0, uint* %tmp.6
	%tmp.8 = getelementptr %std.list.int* %tmp.3, int 0, uint 1
	store int* null, int** %tmp.8
	ret %std.list.int* %tmp.3

endif:
	%tmp.15 = cast int %length to uint
	store uint %tmp.15, uint* %tmp.6
	%tmp.17 = getelementptr %std.list.int* %tmp.3, int 0, uint 1
	%tmp.18 = malloc int, uint %tmp.15
	store int* %tmp.18, int** %tmp.17
	%tmp.255 = setgt int %length, 0
	br bool %tmp.255, label %no_exit, label %UnifiedReturnBlock

no_exit:
	%indvar = phi uint [ %indvar.next, %no_exit ], [ 0, %endif ]
	%i.0.0 = cast uint %indvar to int
	%tmp.29 = load int** %tmp.17
	%tmp.31 = getelementptr int* %tmp.29, uint %indvar
	store int %i.0.0, int* %tmp.31
	%tmp.34 = add int %i.0.0, 1
	%tmp.25 = setlt int %tmp.34, %length
	%indvar.next = add uint %indvar, 1
	br bool %tmp.25, label %no_exit, label %UnifiedReturnBlock

UnifiedReturnBlock:
	%UnifiedRetVal = phi %std.list.int* [ %tmp.3, %endif ], [ %tmp.3, %no_exit ]
	ret %std.list.int* %UnifiedRetVal
}
