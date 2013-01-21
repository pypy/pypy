	.type	pypy_g_foo, @function
pypy_g_foo:
.L1780:
	subl	$76, %esp
	movl	80(%esp), %ecx
	movl	%esi, 64(%esp)
	movl	104(%esp), %esi
	testl	%ecx, %ecx
	movl	%ebp, 72(%esp)
	movl	100(%esp), %ebp
	movl	%ebx, 60(%esp)
	movl	%edi, 68(%esp)
	jle	.L1779
.L1783:
.L1782:
.L1784:
	movl	_LLstacktoobig_stack_base_pointer, %edx
	leal	59(%esp), %eax
	xorl	%ebx, %ebx
	subl	%edx, %eax
	cmpl	_LLstacktoobig_stack_min, %eax
	jl	.L1786
	cmpl	_LLstacktoobig_stack_max, %eax
	jg	.L1786
.L1787:
	testl	%ebx, %ebx
	jne	.L1830
.L1795:
.L1797:
.L1799:
.L1791:
	movl	pypy_g_ExcData, %eax
	testl	%eax, %eax
	je	.L1831
.L1779:
	movl	60(%esp), %ebx
	movl	64(%esp), %esi
	movl	68(%esp), %edi
	movl	72(%esp), %ebp
	addl	$76, %esp
	ret
	.p2align 4,,7
.L1786:
	call	LL_stack_too_big_slowpath
	;; expected {76(%esp) | 60(%esp), 64(%esp), 68(%esp), 72(%esp) | %esi, %ebp, 84(%esp), 88(%esp), 92(%esp), 96(%esp)}
	testl	%eax, %eax
	je	.L1787
	movl	$1, %ebx
	jmp	.L1787
	.p2align 4,,7
.L1831:
.L1802:
	movl	pypy_g_pypy_rpython_memory_gc_semispace_SemiSpaceGC+12, %edx
	movl	pypy_g_pypy_rpython_memory_gc_semispace_SemiSpaceGC+80, %ecx
	subl	%edx, %ecx
	cmpl	$7, %ecx
	jle	.L1804
.L1829:
.L1805:
.L1808:
	movl	$4, (%edx)
	movl	%edx, %edi
	movl	$pypy_g_pypy_rpython_memory_gc_semispace_SemiSpaceGC, %ebx
	leal	8(%edx), %edx
	movl	%edx, 12(%ebx)
	movl	%edi, %ebx
.L1809:
	movl	%esi, %edi
	movl	84(%esp), %eax
	movl	88(%esp), %esi
#APP
	/* GCROOT %eax */
	/* GCROOT %edi */
#NO_APP
	movl	%eax, 48(%esp)
	movl	96(%esp), %eax
#APP
	/* GCROOT %esi */
	/* GCROOT %eax */
	/* GCROOT %ebp */
#NO_APP
	movl	%eax, 44(%esp)
	movl	92(%esp), %eax
#APP
	/* GCROOT %eax */
#NO_APP
	movl	%eax, 40(%esp)
	testl	%ebx, %ebx
	je	.L1779
.L1811:
	movl	$pypy_g_src8_A_vtable, 4(%ebx)
	movl	80(%esp), %eax
	movl	%ebx, 24(%esp)
	movl	%ebx, 20(%esp)
	decl	%eax
	movl	%eax, 52(%esp)
	movl	%ebx, 16(%esp)
	movl	%ebx, 12(%esp)
	movl	%ebx, 8(%esp)
	movl	%ebx, 4(%esp)
	movl	%eax, (%esp)
	call	pypy_g_foo
	;; expected {76(%esp) | 60(%esp), 64(%esp), 68(%esp), 72(%esp) | %ebx, %esi, %edi, %ebp, 40(%esp), 44(%esp), 48(%esp)}
	movl	pypy_g_ExcData, %ecx
#APP
	/* GCROOT %esi */
	/* GCROOT %edi */
#NO_APP
	movl	%esi, 36(%esp)
	movl	48(%esp), %eax
	movl	40(%esp), %esi
#APP
	/* GCROOT %eax */
	/* GCROOT %ebp */
#NO_APP
	movl	%eax, 32(%esp)
	movl	%ebx, %eax
	movl	44(%esp), %ebx
#APP
	/* GCROOT %eax */
	/* GCROOT %ebx */
	/* GCROOT %esi */
#NO_APP
	testl	%ecx, %ecx
	jne	.L1779
.L1814:
	movl	%eax, 24(%esp)
	movl	52(%esp), %edx
	movl	%eax, 20(%esp)
	movl	%eax, 16(%esp)
	movl	%eax, 12(%esp)
	movl	%eax, 8(%esp)
	movl	%eax, 4(%esp)
	movl	%edx, (%esp)
	call	pypy_g_foo
	;; expected {76(%esp) | 60(%esp), 64(%esp), 68(%esp), 72(%esp) | %ebx, %esi, %edi, %ebp, 32(%esp), 36(%esp)}
	movl	%esi, %eax
	movl	pypy_g_ExcData, %esi
#APP
	/* GCROOT %edi */
#NO_APP
	movl	%edi, 28(%esp)
	movl	32(%esp), %edx
#APP
	/* GCROOT %ebp */
#NO_APP
	movl	36(%esp), %edi
#APP
	/* GCROOT %edx */
	/* GCROOT %edi */
#NO_APP
	movl	%ebx, %ecx
#APP
	/* GCROOT %eax */
	/* GCROOT %ecx */
#NO_APP
	testl	%esi, %esi
	jne	.L1779
.L1816:
	movl	%edi, 20(%esp)
	movl	28(%esp), %edi
	movl	%ebp, 8(%esp)
	movl	52(%esp), %ebp
	movl	%edx, 24(%esp)
	movl	%eax, 16(%esp)
	movl	%ecx, 12(%esp)
	movl	%edi, 4(%esp)
	movl	%ebp, (%esp)
	call	pypy_g_foo
	;; expected {76(%esp) | 60(%esp), 64(%esp), 68(%esp), 72(%esp) | }
	jmp	.L1779
.L1807:
	.p2align 4,,7
.L1804:
.L1817:
	movl	$pypy_g_pypy_rpython_memory_gc_semispace_SemiSpaceGC, (%esp)
	movl	$8, %ebx
	movl	%ebx, 4(%esp)
	call	pypy_g_SemiSpaceGC_try_obtain_free_space
	;; expected {76(%esp) | 60(%esp), 64(%esp), 68(%esp), 72(%esp) | %esi, %ebp, 84(%esp), 88(%esp), 92(%esp), 96(%esp)}
	movl	pypy_g_ExcData, %ecx
	xorl	%edx, %edx
	testl	%ecx, %ecx
	je	.L1832
.L1819:
	xorl	%ebx, %ebx
	testl	%ecx, %ecx
	jne	.L1809
	jmp	.L1829
.L1790:
.L1789:
.L1792:
.L1793:
.L1830:
.L1794:
	movl	$pypy_g_exceptions_RuntimeError_vtable, %edi
	movl	$pypy_g_exceptions_RuntimeError, %ebx
	movl	%edi, pypy_g_ExcData
	movl	%ebx, pypy_g_ExcData+4
	jmp	.L1791
.L1832:
.L1820:
	testb	%al, %al
	je	.L1833
.L1822:
	movl	pypy_g_pypy_rpython_memory_gc_semispace_SemiSpaceGC+12, %edx
	jmp	.L1819
.L1833:
.L1823:
.L1824:
.L1825:
	movl	$pypy_g_exceptions_MemoryError_vtable, %ecx
	movl	$pypy_g_exceptions_MemoryError_1, %eax
	movl	%ecx, pypy_g_ExcData
	movl	%eax, pypy_g_ExcData+4
	jmp	.L1819
	.size	pypy_g_foo, .-pypy_g_foo
