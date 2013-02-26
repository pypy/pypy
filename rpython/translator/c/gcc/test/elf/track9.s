	.type	pypy_g_stuff, @function
pypy_g_stuff:
.LFB41:
	.loc 2 1513 0
	pushl	%ebp
.LCFI87:
	movl	%esp, %ebp
.LCFI88:
	subl	$72, %esp
.LCFI89:
.L543:
	.loc 2 1521 0
	movl	$420, 8(%esp)
	movl	$0, 4(%esp)
	movl	$pypy_g_array_16, (%esp)
	call	open
	/* GC_NOCOLLECT open */
.L542:
	.loc 2 1588 0
	leave
	ret
.LFE41:
	.size	pypy_g_stuff, .-pypy_g_stuff
