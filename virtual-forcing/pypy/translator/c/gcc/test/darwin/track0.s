_pypy_g_clear_large_memory_chunk:
L80:
	pushl	%ebp
	pushl	%edi
	pushl	%esi
	pushl	%ebx
	call	L103
"L00000000006$pb":
L103:
	popl	%ebx
	subl	$28, %esp
	movl	$420, 8(%esp)
	movl	$0, 4(%esp)
	movl	L_pypy_g_array_21$non_lazy_ptr-"L00000000006$pb"(%ebx), %eax
	movl	%eax, (%esp)
	call	L_open$stub
        ;; expected {44(%esp) | 28(%esp), 32(%esp), 36(%esp), 40(%esp) | }
	cmpl	$-1, %eax
	movl	%eax, %ebp
	je	L100
L81:
	movl	52(%esp), %esi
	movl	48(%esp), %edi
	testl	%esi, %esi
	jg	L101
L88:
	movl	%ebp, (%esp)
	call	L_close$stub
        ;; expected {44(%esp) | 28(%esp), 32(%esp), 36(%esp), 40(%esp) | }
	movl	%esi, %edx
	movl	%edi, %eax
L83:
	testl	%edx, %edx
	jle	L97
L85:
	movl	%edx, 8(%esp)
	movl	$0, 4(%esp)
	movl	%eax, (%esp)
	call	L_memset$stub
        ;; expected {44(%esp) | 28(%esp), 32(%esp), 36(%esp), 40(%esp) | }
L97:
	addl	$28, %esp
	popl	%ebx
	popl	%esi
	popl	%edi
	popl	%ebp
	ret
	.align 4,0x90
L101:
	movl	52(%esp), %esi
	movl	48(%esp), %edi
	jmp	L92
	.align 4,0x90
L102:
	movl	%eax, %edi
	movl	%edx, %esi
L92:
L95:
	cmpl	$536870913, %esi
	movl	$536870912, %eax
	cmovl	%esi, %eax
	movl	%eax, 8(%esp)
	movl	%edi, 4(%esp)
	movl	%ebp, (%esp)
	call	L_read$stub        
        ;; expected {44(%esp) | 28(%esp), 32(%esp), 36(%esp), 40(%esp) | }
	testl	%eax, %eax
	jle	L88
L96:
L89:
	movl	%esi, %edx
	subl	%eax, %edx
	testl	%edx, %edx
	leal	(%edi,%eax), %eax
	jg	L102
	movl	%edx, %esi
	movl	%eax, %edi
	jmp	L88
	.align 4,0x90
L100:
	movl	52(%esp), %edx
	movl	48(%esp), %eax
	jmp	L83
	.align 4,0x90
