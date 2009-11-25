_pypy_g_populate:
L2135:
	subl	$76, %esp
	movl	%esi, 64(%esp)
	movl	80(%esp), %esi
	movl	%ebx, 60(%esp)
	call	L2175
"L00000000060$pb":
L2175:
	popl	%ebx
	movl	%edi, 68(%esp)
	testl	%esi, %esi
	movl	%ebp, 72(%esp)
	jle	L2169
L2137:
L2138:
	movl	L__LLstacktoobig_stack_base_pointer$non_lazy_ptr-"L00000000060$pb"(%ebx), %eax
	leal	47(%esp), %edx
	subl	(%eax), %edx
	movl	L__LLstacktoobig_stack_min$non_lazy_ptr-"L00000000060$pb"(%ebx), %eax
	cmpl	(%eax), %edx
	jl	L2139
	movl	L__LLstacktoobig_stack_max$non_lazy_ptr-"L00000000060$pb"(%ebx), %eax
	cmpl	(%eax), %edx
	jg	L2139
L2171:
	movl	L_pypy_g_ExcData$non_lazy_ptr-"L00000000060$pb"(%ebx), %edi
	movl	(%edi), %ebp
	testl	%ebp, %ebp
	je	L2172
L2169:
	movl	60(%esp), %ebx
	movl	64(%esp), %esi
	movl	68(%esp), %edi
	movl	72(%esp), %ebp
	addl	$76, %esp
	ret
	.align 4,0x90
L2139:
	call	L_LL_stack_too_big_slowpath$stub
        ;; expected {76(%esp) | 60(%esp), 64(%esp), 68(%esp), 72(%esp) | 84(%esp)}
	testl	%eax, %eax
	je	L2171
L2142:
	movl	L_pypy_g_ExcData$non_lazy_ptr-"L00000000060$pb"(%ebx), %edi
	movl	L_pypy_g_exceptions_RuntimeError_vtable$non_lazy_ptr-"L00000000060$pb"(%ebx), %eax
	movl	%eax, (%edi)
	movl	(%edi), %ebp
	movl	L_pypy_g_exceptions_RuntimeError$non_lazy_ptr-"L00000000060$pb"(%ebx), %eax
	testl	%ebp, %ebp
	movl	%eax, 4(%edi)
	jne	L2169
L2143:
	.align 4,0x90
L2172:
	movl	L_pypy_g_pypy_rpython_memory_gc_semispace_SemiSpaceGC$non_lazy_ptr-"L00000000060$pb"(%ebx), %ebp
	decl	%esi
	movl	%esi, 28(%esp)
	movl	12(%ebp), %edx
	movl	80(%ebp), %eax
	subl	%edx, %eax
	cmpl	$15, %eax
	jle	L2144
L2146:
	leal	16(%edx), %eax
	movl	%edx, %ecx
	movl	$31, (%edx)
	movl	%eax, 12(%ebp)
L2147:
	movl	L___gcnoreorderhack$non_lazy_ptr-"L00000000060$pb"(%ebx), %edi
	movl	84(%esp), %esi
	/* GCROOT %esi */
	testl	%ecx, %ecx
	je	L2169
L2148:
	movl	L_pypy_g_pypy_translator_goal_gcbench_Node_vtable$non_lazy_ptr-"L00000000060$pb"(%ebx), %eax
	movl	L_pypy_g_pypy_rpython_memory_gc_semispace_SemiSpaceGC$non_lazy_ptr-"L00000000060$pb"(%ebx), %ebp
	movl	$0, 8(%edx)
	movl	$0, 12(%edx)
	movl	%eax, 4(%edx)
	movl	%edx, 8(%esi)
	movl	12(%ebp), %edx
	movl	80(%ebp), %eax
	subl	%edx, %eax
	cmpl	$15, %eax
	jle	L2149
L2151:
	leal	16(%edx), %eax
	movl	$31, (%edx)
	movl	%eax, 12(%ebp)
	movl	%edx, %eax
L2152:
	/* GCROOT %esi */
	testl	%eax, %eax
	je	L2169
L2153:
	movl	L_pypy_g_pypy_translator_goal_gcbench_Node_vtable$non_lazy_ptr-"L00000000060$pb"(%ebx), %eax
	movl	$0, 8(%edx)
	movl	$0, 12(%edx)
	movl	%eax, 4(%edx)
	movl	8(%esi), %eax
	movl	%edx, 12(%esi)
	movl	%eax, 4(%esp)
	movl	28(%esp), %eax
	movl	%eax, (%esp)
	call	_pypy_g_populate
        ;; expected {76(%esp) | 60(%esp), 64(%esp), 68(%esp), 72(%esp) | %esi}
	movl	L_pypy_g_ExcData$non_lazy_ptr-"L00000000060$pb"(%ebx), %eax
	movl	%esi, %edx
	/* GCROOT %edx */
	movl	(%eax), %esi
	testl	%esi, %esi
	jne	L2169
L2154:
	movl	12(%edx), %eax
	movl	%eax, 4(%esp)
	movl	28(%esp), %eax
	movl	%eax, (%esp)
	call	_pypy_g_populate
        ;; expected {76(%esp) | 60(%esp), 64(%esp), 68(%esp), 72(%esp) | }
	jmp	L2169
L2144:
	movl	$16, 4(%esp)
	xorl	%esi, %esi
	movl	%ebp, (%esp)
	call	_pypy_g_SemiSpaceGC_try_obtain_free_space
        ;; expected {76(%esp) | 60(%esp), 64(%esp), 68(%esp), 72(%esp) | 84(%esp)}

	movl	(%edi), %edx
	testl	%edx, %edx
	je	L2173
L2164:
	movl	L_pypy_g_ExcData$non_lazy_ptr-"L00000000060$pb"(%ebx), %eax
	xorl	%ecx, %ecx
	xorl	%edx, %edx
	movl	(%eax), %eax
	testl	%eax, %eax
	jne	L2147
	movl	L_pypy_g_pypy_rpython_memory_gc_semispace_SemiSpaceGC$non_lazy_ptr-"L00000000060$pb"(%ebx), %ebp
	movl	%esi, %edx
	jmp	L2146
L2149:
	movl	$16, 4(%esp)
	movl	%ebp, (%esp)
	call	_pypy_g_SemiSpaceGC_try_obtain_free_space
        ;; expected {76(%esp) | 60(%esp), 64(%esp), 68(%esp), 72(%esp) | %esi}
	movl	L_pypy_g_ExcData$non_lazy_ptr-"L00000000060$pb"(%ebx), %edi
	xorl	%edx, %edx
	movl	(%edi), %ecx
	testl	%ecx, %ecx
	je	L2174
L2157:
	movl	(%edi), %ecx
	testl	%ecx, %ecx
	je	L2160
	movl	L___gcnoreorderhack$non_lazy_ptr-"L00000000060$pb"(%ebx), %edi
	xorl	%eax, %eax
	xorl	%edx, %edx
	jmp	L2152
L2173:
L2162:
	testb	%al, %al
	jne	L2165
L2166:
	movl	L_pypy_g_exceptions_MemoryError_vtable$non_lazy_ptr-"L00000000060$pb"(%ebx), %eax
	movl	%eax, (%edi)
	movl	L_pypy_g_exceptions_MemoryError_1$non_lazy_ptr-"L00000000060$pb"(%ebx), %eax
	movl	%eax, 4(%edi)
	jmp	L2164
L2160:
	movl	L_pypy_g_pypy_rpython_memory_gc_semispace_SemiSpaceGC$non_lazy_ptr-"L00000000060$pb"(%ebx), %ebp
	movl	L___gcnoreorderhack$non_lazy_ptr-"L00000000060$pb"(%ebx), %edi
	jmp	L2151
L2174:
L2155:
	testb	%al, %al
	jne	L2158
L2159:
	movl	L_pypy_g_exceptions_MemoryError_vtable$non_lazy_ptr-"L00000000060$pb"(%ebx), %eax
	movl	%eax, (%edi)
	movl	L_pypy_g_exceptions_MemoryError_1$non_lazy_ptr-"L00000000060$pb"(%ebx), %eax
	movl	%eax, 4(%edi)
	jmp	L2157
L2165:
	movl	12(%ebp), %esi
	jmp	L2164
L2158:
	movl	12(%ebp), %edx
	jmp	L2157
	.align 4,0x90
