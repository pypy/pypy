	.type	pypy_g_SemiSpaceGC_scan_copied, @function
pypy_g_SemiSpaceGC_scan_copied:
.L1215:
	pushl	%esi
	pushl	%ebx
	subl	$20, %esp
	movl	32(%esp), %esi
	movl	36(%esp), %ebx
	testl	%esi, %esi
	jne	.L1216
	jmp	.L1227
.L1220:
.L1231:
	movl	%ebx, 4(%esp)
	movl	%esi, 8(%esp)
	movl	%esi, (%esp)
	call	pypy_g_trace___trace_copy
	;; expected {28(%esp) | 20(%esp), 24(%esp), %edi, %ebp | }
	movl	%ebx, 4(%esp)
	movl	%esi, (%esp)
	call	pypy_g_SemiSpaceGC_get_size
	;; expected {28(%esp) | 20(%esp), 24(%esp), %edi, %ebp | }
	addl	%eax, %ebx
.L1216:
	cmpl	12(%esi), %ebx
	jb	.L1231
.L1221:
	addl	$20, %esp
	movl	%ebx, %eax
	popl	%ebx
	popl	%esi
	ret
	.p2align 4,,7
.L1229:
	movl	%ebx, 4(%esp)
	movl	%esi, 8(%esp)
	movl	%esi, (%esp)
	call	pypy_g_trace___trace_copy
	;; expected {28(%esp) | 20(%esp), 24(%esp), %edi, %ebp | }
	movl	%ebx, 4(%esp)
	movl	%esi, (%esp)
	call	pypy_g_SemiSpaceGC_get_size
	;; expected {28(%esp) | 20(%esp), 24(%esp), %edi, %ebp | }
	addl	%eax, %ebx
	jmp	.L1221
.L1227:
	call	RPyAbort
	cmpl	12(%esi), %ebx
	jb	.L1229
	addl	$20, %esp
	movl	%ebx, %eax
	popl	%ebx
	popl	%esi
	ret
	.size	pypy_g_SemiSpaceGC_scan_copied, .-pypy_g_SemiSpaceGC_scan_copied
