	.type	pypy_g_clear_large_memory_chunk, @function
pypy_g_clear_large_memory_chunk:
.L271:
	pushl	%ebp
	xorl	%eax, %eax
	movl	$420, %edx
	pushl	%edi
	pushl	%esi
	pushl	%ebx
	subl	$12, %esp
	movl	36(%esp), %ebp
	movl	%edx, 8(%esp)
	movl	%eax, 4(%esp)
	movl	%ebp, %ebx
	movl	$pypy_g_array_16, (%esp)
	call	open
        ;; expected {28(%esp) | 12(%esp), 16(%esp), 20(%esp), 24(%esp) | }
	cmpl	$-1, %eax
	movl	%eax, %edi
	movl	32(%esp), %esi
	jne	.L273
	jmp	.L287
	.p2align 4,,7
.L282:
	movl	%eax, 8(%esp)
	movl	%esi, 4(%esp)
	movl	%edi, (%esp)
	call	read
        ;; expected {28(%esp) | 12(%esp), 16(%esp), 20(%esp), 24(%esp) | }
	testl	%eax, %eax
	jle	.L280
.L285:
.L288:
	subl	%eax, %ebx
	addl	%eax, %esi
.L273:
	testl	%ebx, %ebx
	jle	.L280
.L279:
	cmpl	$536870912, %ebx
	movl	$536870912, %eax
	jg	.L282
.L283:
	movl	%esi, 4(%esp)
	movl	%ebx, %eax
	movl	%eax, 8(%esp)
	movl	%edi, (%esp)
	call	read
        ;; expected {28(%esp) | 12(%esp), 16(%esp), 20(%esp), 24(%esp) | }
	testl	%eax, %eax
	jg	.L288
.L280:
	movl	%edi, (%esp)
	call	close
        ;; expected {28(%esp) | 12(%esp), 16(%esp), 20(%esp), 24(%esp) | }
	movl	%ebx, %eax
.L286:
.L274:
	testl	%eax, %eax
	jle	.L270
.L277:
.L276:
	movl	%eax, 8(%esp)
	xorl	%ecx, %ecx
	movl	%ecx, 4(%esp)
	movl	%esi, (%esp)
	call	memset
        ;; expected {28(%esp) | 12(%esp), 16(%esp), 20(%esp), 24(%esp) | }
.L270:
	addl	$12, %esp
	popl	%ebx
	popl	%esi
	popl	%edi
	popl	%ebp
	ret
.L287:
	movl	%ebp, %eax
	jmp	.L286
	.size	pypy_g_clear_large_memory_chunk, .-pypy_g_clear_large_memory_chunk
