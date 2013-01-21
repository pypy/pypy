_pypy_g_clear_large_memory_chunk:
L137:
	pushl	%ebp
	movl	%esp, %ebp
	pushl	%edi
	pushl	%esi
	pushl	%ebx
	subl	$28, %esp
	movl	L_pypy_g_array_21$non_lazy_ptr, %eax
	movl	$420, 8(%esp)
	movl	$0, 4(%esp)
	movl	%eax, (%esp)
	call	L_open$stub
        ;; expected {4(%ebp) | -12(%ebp), -8(%ebp), -4(%ebp), (%ebp) | }
	cmpl	$-1, %eax
	movl	%eax, %edi
	je	L157
L138:
	movl	12(%ebp), %ebx
	movl	8(%ebp), %esi
	testl	%ebx, %ebx
	jg	L158
L145:
	movl	%edi, (%esp)
	call	L_close$stub
        ;; expected {4(%ebp) | -12(%ebp), -8(%ebp), -4(%ebp), (%ebp) | }
	movl	%ebx, %edx
	movl	%esi, %eax
L140:
	testl	%edx, %edx
	jle	L154
L142:
	movl	%edx, 8(%esp)
	movl	$0, 4(%esp)
	movl	%eax, (%esp)
	call	L_memset$stub
        ;; expected {4(%ebp) | -12(%ebp), -8(%ebp), -4(%ebp), (%ebp) | }
L154:
	addl	$28, %esp
	popl	%ebx
	popl	%esi
	popl	%edi
	leave
	ret
	.align 4,0x90
L158:
	movl	12(%ebp), %ebx
	movl	8(%ebp), %esi
	jmp	L149
	.align 4,0x90
L159:
	movl	%eax, %esi
	movl	%edx, %ebx
L149:
L152:
	cmpl	$536870913, %ebx
	movl	$536870912, %eax
	cmovl	%ebx, %eax
	movl	%eax, 8(%esp)
	movl	%esi, 4(%esp)
	movl	%edi, (%esp)
	call	L_read$stub
        ;; expected {4(%ebp) | -12(%ebp), -8(%ebp), -4(%ebp), (%ebp) | }
	testl	%eax, %eax
	jle	L145
L153:
L146:
	movl	%ebx, %edx
	subl	%eax, %edx
	testl	%edx, %edx
	leal	(%esi,%eax), %eax
	jg	L159
	movl	%edx, %ebx
	movl	%eax, %esi
	jmp	L145
	.align 4,0x90
L157:
	movl	12(%ebp), %edx
	movl	8(%ebp), %eax
	jmp	L140
	.align 4,0x90