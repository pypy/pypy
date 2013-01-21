; Function compile flags: /Ogtpy
;	COMDAT _pypy_g_foo
_TEXT	SEGMENT
tv419 = -8						; size = 4
_l_v416$ = -4						; size = 4
_l_v413$ = -4						; size = 4
_l_v410$ = -4						; size = 4
_l_v407$ = -4						; size = 4
_l_v404$ = -4						; size = 4
_l_v401$ = -4						; size = 4
_l_v394$ = -4						; size = 4
_l_v391$ = -4						; size = 4
_l_v388$ = -4						; size = 4
_l_v385$ = -4						; size = 4
_l_v382$ = -4						; size = 4
_l_v379$ = -4						; size = 4
_l_v376$ = -4						; size = 4
_l_v368$ = -4						; size = 4
_l_v365$ = -4						; size = 4
_l_v362$ = -4						; size = 4
_l_v359$ = -4						; size = 4
_l_v356$ = -4						; size = 4
_l_v353$ = -4						; size = 4
_local$40423 = 8					; size = 1
_l_rec_1$ = 8						; size = 4
_l_a1_1$ = 12						; size = 4
_l_a2_1$ = 16						; size = 4
_l_a3_1$ = 20						; size = 4
_l_a4_1$ = 24						; size = 4
_l_a5_1$ = 28						; size = 4
_l_a6_1$ = 32						; size = 4
_pypy_g_foo PROC					; COMDAT

; 1026 : 	bool_t l_v337; bool_t l_v340; bool_t l_v345; bool_t l_v346;
; 1027 : 	bool_t l_v371; bool_t l_v398; bool_t l_v420; bool_t l_v426;
; 1028 : 	long l_v342; long l_v344; long l_v374; long l_v399; long l_v421;
; 1029 : 	struct pypy_header0 *l_v347; struct pypy_object0 *l_v372;
; 1030 : 	struct pypy_object_vtable0 *l_v339;
; 1031 : 	struct pypy_object_vtable0 *l_v397;
; 1032 : 	struct pypy_object_vtable0 *l_v419;
; 1033 : 	struct pypy_object_vtable0 *l_v425; struct pypy_src8_A0 *l_v335;
; 1034 : 	void* l_v336; void* l_v341; void* l_v343; void* l_v349; void* l_v351;
; 1035 : 	void* l_v352; void* l_v353; void* l_v354; void* l_v356; void* l_v357;
; 1036 : 	void* l_v359; void* l_v360; void* l_v362; void* l_v363; void* l_v365;
; 1037 : 	void* l_v366; void* l_v368; void* l_v369; void* l_v376; void* l_v377;
; 1038 : 	void* l_v379; void* l_v380; void* l_v382; void* l_v383; void* l_v385;
; 1039 : 	void* l_v386; void* l_v388; void* l_v389; void* l_v391; void* l_v392;
; 1040 : 	void* l_v394; void* l_v395; void* l_v401; void* l_v402; void* l_v404;
; 1041 : 	void* l_v405; void* l_v407; void* l_v408; void* l_v410; void* l_v411;
; 1042 : 	void* l_v413; void* l_v414; void* l_v416; void* l_v417; void* l_v424;
; 1043 : 	void* l_v428;
; 1044 : 
; 1045 :     block0:
; 1046 : 	OP_INT_GT(l_rec_1, 0L, l_v337);

	mov	eax, DWORD PTR _l_rec_1$[esp-4]
	sub	esp, 8
	test	eax, eax
$block0$34376:

; 1047 : 	if (l_v337) {

	jle	$block1$34379
	push	ebx
	mov	ebx, DWORD PTR _l_a2_1$[esp+8]
	push	ebp
	mov	ebp, DWORD PTR _l_a1_1$[esp+12]
	push	edi
	mov	edi, DWORD PTR _l_a3_1$[esp+16]
	add	eax, -1
	mov	DWORD PTR tv419[esp+20], eax
	push	esi
	npad	10
$LL63@pypy_g_foo:

; 1048 : 		goto block2;
; 1049 : 	}
; 1050 : 	goto block1;
; 1051 : 
; 1052 :     block1:
; 1053 : 	RPY_DEBUG_RETURN();
; 1054 : 	return /* nothing */;
; 1055 : 
; 1056 :     block2:
; 1057 : 	pypy_g_stack_check___();

	lea	eax, DWORD PTR _local$40423[esp+20]
	sub	eax, DWORD PTR __LLstacktoobig_stack_base_pointer
$block0$40413:
	cmp	eax, DWORD PTR __LLstacktoobig_stack_min
$block2$34378:
	jl	SHORT $LN16@pypy_g_foo
	cmp	eax, DWORD PTR __LLstacktoobig_stack_max
	jle	SHORT $LN17@pypy_g_foo
$LN16@pypy_g_foo:
	call	_LL_stack_too_big_slowpath
	;; expected {24(%esp) | 12(%esp), (%esp), 4(%esp), 8(%esp) | %ebx, %edi, %ebp, 44(%esp), 48(%esp), 52(%esp)}
	test	eax, eax
	jne	$LN71@pypy_g_foo
$LN17@pypy_g_foo:
$block1$40416:

; 1058 : 	l_v339 = RPyField((&pypy_g_ExcData), ed_exc_type);
; 1059 : 	l_v340 = (l_v339 == NULL);

	cmp	DWORD PTR _pypy_g_ExcData, 0

; 1060 : 	if (!l_v340) {

	jne	$LN75@pypy_g_foo

; 1061 : 		goto block1;
; 1062 : 	}
; 1063 : 	goto block3;
; 1064 : 
; 1065 :     block3:
; 1066 : 	l_v341 = RPyField((&pypy_g_pypy_rpython_memory_gc_semispace_SemiSpaceGC), ssgc_inst_free);

	mov	esi, DWORD PTR _pypy_g_pypy_rpython_memory_gc_semispace_SemiSpaceGC+12

; 1067 : 	OP_RAW_MALLOC_USAGE((0 + ROUND_UP_FOR_ALLOCATION(sizeof(struct pypy_src8_A0), sizeof(struct pypy_forwarding_stub0))), l_v342);
; 1068 : 	l_v343 = RPyField((&pypy_g_pypy_rpython_memory_gc_semispace_SemiSpaceGC), ssgc_inst_top_of_space);
; 1069 : 	OP_ADR_DELTA(l_v343, l_v341, l_v344);

	mov	eax, DWORD PTR _pypy_g_pypy_rpython_memory_gc_semispace_SemiSpaceGC+80
	sub	eax, esi

; 1070 : 	OP_INT_GT(l_v342, l_v344, l_v345);

	cmp	eax, 8
$block3$34382:

; 1071 : 	if (l_v345) {

	jge	SHORT $block4$34395

; 1184 : 	goto block1;
; 1185 : 
; 1186 :     block10:
; 1187 : 	abort();  /* debug_llinterpcall should be unreachable */
; 1188 : 	goto block5;
; 1189 : 
; 1190 :     block11:
; 1191 : 	l_v424 = pypy_g_SemiSpaceGC_obtain_free_space((&pypy_g_pypy_rpython_memory_gc_semispace_SemiSpaceGC), (0 + ROUND_UP_FOR_ALLOCATION(sizeof(struct pypy_src8_A0), sizeof(struct pypy_forwarding_stub0))));

	push	8
	push	OFFSET _pypy_g_pypy_rpython_memory_gc_semispace_SemiSpaceGC
$block11$34394:
	call	_pypy_g_SemiSpaceGC_obtain_free_space
	;; expected {32(%esp) | 20(%esp), 8(%esp), 12(%esp), 16(%esp) | %ebx, %edi, %ebp, 52(%esp), 56(%esp), 60(%esp)}
	add	esp, 8

; 1192 : 	l_v425 = RPyField((&pypy_g_ExcData), ed_exc_type);
; 1193 : 	l_v426 = (l_v425 == NULL);

	cmp	DWORD PTR _pypy_g_ExcData, 0

; 1194 : 	if (!l_v426) {

	je	SHORT $LN1@pypy_g_foo

; 1195 : 		l_v428 = NULL;

	xor	esi, esi

; 1196 : 		goto block6;

	jmp	SHORT $block6$34416
$LN1@pypy_g_foo:

; 1197 : 	}
; 1198 : 	l_v336 = l_v424;

	mov	esi, eax
$block4$34395:

; 1072 : 		goto block11;
; 1073 : 	}
; 1074 : 	l_v336 = l_v341;
; 1075 : 	goto block4;
; 1076 : 
; 1077 :     block4:
; 1078 : 	OP_INT_IS_TRUE(RUNNING_ON_LLINTERP, l_v346);
; 1079 : 	if (l_v346) {
; 1080 : 		goto block10;
; 1081 : 	}
; 1082 : 	goto block5;
; 1083 : 
; 1084 :     block5:
; 1085 : 	l_v347 = (struct pypy_header0 *)l_v336;
; 1086 : 	RPyField(l_v347, h_tid) = (GROUP_MEMBER_OFFSET(struct group_pypy_g_typeinfo_s, member1)|0L);
; 1087 : 	OP_ADR_ADD(l_v336, (0 + ROUND_UP_FOR_ALLOCATION(sizeof(struct pypy_src8_A0), sizeof(struct pypy_forwarding_stub0))), l_v349);

	lea	ecx, DWORD PTR [esi+8]
	mov	DWORD PTR [esi], 1
$block5$34398:

; 1088 : 	RPyField((&pypy_g_pypy_rpython_memory_gc_semispace_SemiSpaceGC), ssgc_inst_free) = l_v349;

	mov	DWORD PTR _pypy_g_pypy_rpython_memory_gc_semispace_SemiSpaceGC+12, ecx
$block6$34416:

; 1089 : 	OP_ADR_ADD(l_v336, 0, l_v351);
; 1090 : 	l_v352 = (void*)l_v351;
; 1091 : 	l_v428 = l_v352;
; 1092 : 	goto block6;
; 1093 : 
; 1094 :     block6:
; 1095 : 	l_v353 = (void*)l_a2_1;

	mov	DWORD PTR _l_v353$[esp+24], ebx

; 1096 : 	l_v354 = pypy_asm_gcroot(l_v353);

	mov	eax, DWORD PTR ?_constant_always_one_@?1??pypy_asm_gcroot@@9@9
	imul	eax, DWORD PTR _l_v353$[esp+24]

; 1097 : 	l_a2_1 = l_v354; /* for moving GCs */
; 1098 : 	l_v356 = (void*)l_a5_1;

	mov	edx, DWORD PTR _l_a5_1$[esp+20]
	mov	DWORD PTR _l_v356$[esp+24], edx

; 1099 : 	l_v357 = pypy_asm_gcroot(l_v356);

	mov	eax, DWORD PTR ?_constant_always_one_@?1??pypy_asm_gcroot@@9@9
	imul	eax, DWORD PTR _l_v356$[esp+24]

; 1100 : 	l_a5_1 = l_v357; /* for moving GCs */
; 1101 : 	l_v359 = (void*)l_a6_1;

	mov	eax, DWORD PTR _l_a6_1$[esp+20]
	mov	DWORD PTR _l_v359$[esp+24], eax

; 1102 : 	l_v360 = pypy_asm_gcroot(l_v359);

	mov	eax, DWORD PTR ?_constant_always_one_@?1??pypy_asm_gcroot@@9@9
	imul	eax, DWORD PTR _l_v359$[esp+24]

; 1103 : 	l_a6_1 = l_v360; /* for moving GCs */
; 1104 : 	l_v362 = (void*)l_a1_1;

	mov	DWORD PTR _l_v362$[esp+24], ebp

; 1105 : 	l_v363 = pypy_asm_gcroot(l_v362);

	mov	eax, DWORD PTR ?_constant_always_one_@?1??pypy_asm_gcroot@@9@9
	imul	eax, DWORD PTR _l_v362$[esp+24]

; 1106 : 	l_a1_1 = l_v363; /* for moving GCs */
; 1107 : 	l_v365 = (void*)l_a3_1;

	mov	DWORD PTR _l_v365$[esp+24], edi

; 1108 : 	l_v366 = pypy_asm_gcroot(l_v365);

	mov	eax, DWORD PTR ?_constant_always_one_@?1??pypy_asm_gcroot@@9@9
	imul	eax, DWORD PTR _l_v365$[esp+24]

; 1109 : 	l_a3_1 = l_v366; /* for moving GCs */
; 1110 : 	l_v368 = (void*)l_a4_1;

	mov	ecx, DWORD PTR _l_a4_1$[esp+20]
	mov	DWORD PTR _l_v368$[esp+24], ecx

; 1111 : 	l_v369 = pypy_asm_gcroot(l_v368);

	mov	eax, DWORD PTR ?_constant_always_one_@?1??pypy_asm_gcroot@@9@9
	imul	eax, DWORD PTR _l_v368$[esp+24]

; 1112 : 	l_a4_1 = l_v369; /* for moving GCs */
; 1113 : 	l_v335 = (struct pypy_src8_A0 *)l_v428;
; 1114 : 	l_v371 = (l_v335 != NULL);

	test	esi, esi

; 1115 : 	if (!l_v371) {

	je	$LN75@pypy_g_foo

; 1116 : 		goto block1;
; 1117 : 	}
; 1118 : 	goto block7;
; 1119 : 
; 1120 :     block7:
; 1121 : 	l_v372 = (struct pypy_object0 *)l_v335;
; 1122 : 	RPyField(l_v372, o_typeptr) = (&pypy_g_src8_A_vtable.a_super);
; 1123 : 	OP_INT_SUB(l_rec_1, 1L, l_v374);
; 1124 : 	pypy_g_foo(l_v374, l_v335, l_v335, l_v335, l_v335, l_v335, l_v335);

	mov	edx, DWORD PTR tv419[esp+24]
	push	esi
	push	esi
	push	esi
	push	esi
	push	esi
	push	esi
	push	edx
$block7$34426:
	mov	DWORD PTR [esi+4], OFFSET _pypy_g_src8_A_vtable
	call	_pypy_g_foo
	;; expected {52(%esp) | 40(%esp), 28(%esp), 32(%esp), 36(%esp) | %ebx, %esi, %edi, %ebp, 72(%esp), 76(%esp), 80(%esp)}
	add	esp, 28					; 0000001cH

; 1125 : 	l_v376 = (void*)l_a2_1;

	mov	DWORD PTR _l_v376$[esp+24], ebx

; 1126 : 	l_v377 = pypy_asm_gcroot(l_v376);

	mov	eax, DWORD PTR ?_constant_always_one_@?1??pypy_asm_gcroot@@9@9
	imul	eax, DWORD PTR _l_v376$[esp+24]

; 1127 : 	l_a2_1 = l_v377; /* for moving GCs */
; 1128 : 	l_v379 = (void*)l_a6_1;

	mov	eax, DWORD PTR _l_a6_1$[esp+20]
	mov	DWORD PTR _l_v379$[esp+24], eax

; 1129 : 	l_v380 = pypy_asm_gcroot(l_v379);

	mov	eax, DWORD PTR ?_constant_always_one_@?1??pypy_asm_gcroot@@9@9
	imul	eax, DWORD PTR _l_v379$[esp+24]

; 1130 : 	l_a6_1 = l_v380; /* for moving GCs */
; 1131 : 	l_v382 = (void*)l_a1_1;

	mov	DWORD PTR _l_v382$[esp+24], ebp

; 1132 : 	l_v383 = pypy_asm_gcroot(l_v382);

	mov	eax, DWORD PTR ?_constant_always_one_@?1??pypy_asm_gcroot@@9@9
	imul	eax, DWORD PTR _l_v382$[esp+24]

; 1133 : 	l_a1_1 = l_v383; /* for moving GCs */
; 1134 : 	l_v385 = (void*)l_v335;

	mov	DWORD PTR _l_v385$[esp+24], esi

; 1135 : 	l_v386 = pypy_asm_gcroot(l_v385);

	mov	eax, DWORD PTR ?_constant_always_one_@?1??pypy_asm_gcroot@@9@9
	imul	eax, DWORD PTR _l_v385$[esp+24]

; 1136 : 	l_v335 = l_v386; /* for moving GCs */
; 1137 : 	l_v388 = (void*)l_a3_1;

	mov	DWORD PTR _l_v388$[esp+24], edi

; 1138 : 	l_v389 = pypy_asm_gcroot(l_v388);

	mov	eax, DWORD PTR ?_constant_always_one_@?1??pypy_asm_gcroot@@9@9
	imul	eax, DWORD PTR _l_v388$[esp+24]

; 1139 : 	l_a3_1 = l_v389; /* for moving GCs */
; 1140 : 	l_v391 = (void*)l_a5_1;

	mov	ecx, DWORD PTR _l_a5_1$[esp+20]
	mov	DWORD PTR _l_v391$[esp+24], ecx

; 1141 : 	l_v392 = pypy_asm_gcroot(l_v391);

	mov	eax, DWORD PTR ?_constant_always_one_@?1??pypy_asm_gcroot@@9@9
	imul	eax, DWORD PTR _l_v391$[esp+24]

; 1142 : 	l_a5_1 = l_v392; /* for moving GCs */
; 1143 : 	l_v394 = (void*)l_a4_1;

	mov	edx, DWORD PTR _l_a4_1$[esp+20]
	mov	DWORD PTR _l_v394$[esp+24], edx

; 1144 : 	l_v395 = pypy_asm_gcroot(l_v394);

	mov	eax, DWORD PTR ?_constant_always_one_@?1??pypy_asm_gcroot@@9@9
	imul	eax, DWORD PTR _l_v394$[esp+24]

; 1145 : 	l_a4_1 = l_v395; /* for moving GCs */
; 1146 : 	l_v397 = RPyField((&pypy_g_ExcData), ed_exc_type);
; 1147 : 	l_v398 = (l_v397 == NULL);

	cmp	DWORD PTR _pypy_g_ExcData, 0

; 1148 : 	if (!l_v398) {

	jne	$LN75@pypy_g_foo

; 1149 : 		goto block1;
; 1150 : 	}
; 1151 : 	goto block8;
; 1152 : 
; 1153 :     block8:
; 1154 : 	OP_INT_SUB(l_rec_1, 1L, l_v399);
; 1155 : 	pypy_g_foo(l_v399, l_v335, l_v335, l_v335, l_v335, l_v335, l_v335);

	mov	eax, DWORD PTR tv419[esp+24]
	push	esi
	push	esi
	push	esi
	push	esi
	push	esi
	push	esi
	push	eax
$block8$34437:
	call	_pypy_g_foo
	;; expected {52(%esp) | 40(%esp), 28(%esp), 32(%esp), 36(%esp) | %ebx, %edi, %ebp, 72(%esp), 76(%esp), 80(%esp)}
	add	esp, 28					; 0000001cH

; 1156 : 	l_v401 = (void*)l_a2_1;

	mov	DWORD PTR _l_v401$[esp+24], ebx

; 1157 : 	l_v402 = pypy_asm_gcroot(l_v401);

	mov	eax, DWORD PTR ?_constant_always_one_@?1??pypy_asm_gcroot@@9@9
	imul	eax, DWORD PTR _l_v401$[esp+24]

; 1158 : 	l_a2_1 = l_v402; /* for moving GCs */
; 1159 : 	l_v404 = (void*)l_a1_1;

	mov	DWORD PTR _l_v404$[esp+24], ebp

; 1160 : 	l_v405 = pypy_asm_gcroot(l_v404);

	mov	eax, DWORD PTR ?_constant_always_one_@?1??pypy_asm_gcroot@@9@9
	imul	eax, DWORD PTR _l_v404$[esp+24]

; 1161 : 	l_a1_1 = l_v405; /* for moving GCs */
; 1162 : 	l_v407 = (void*)l_a3_1;

	mov	DWORD PTR _l_v407$[esp+24], edi

; 1163 : 	l_v408 = pypy_asm_gcroot(l_v407);

	mov	eax, DWORD PTR ?_constant_always_one_@?1??pypy_asm_gcroot@@9@9
	imul	eax, DWORD PTR _l_v407$[esp+24]

; 1164 : 	l_a3_1 = l_v408; /* for moving GCs */
; 1165 : 	l_v410 = (void*)l_a6_1;

	mov	ecx, DWORD PTR _l_a6_1$[esp+20]
	mov	DWORD PTR _l_v410$[esp+24], ecx

; 1166 : 	l_v411 = pypy_asm_gcroot(l_v410);

	mov	eax, DWORD PTR ?_constant_always_one_@?1??pypy_asm_gcroot@@9@9
	imul	eax, DWORD PTR _l_v410$[esp+24]

; 1167 : 	l_a6_1 = l_v411; /* for moving GCs */
; 1168 : 	l_v413 = (void*)l_a5_1;

	mov	edx, DWORD PTR _l_a5_1$[esp+20]
	mov	DWORD PTR _l_v413$[esp+24], edx

; 1169 : 	l_v414 = pypy_asm_gcroot(l_v413);

	mov	eax, DWORD PTR ?_constant_always_one_@?1??pypy_asm_gcroot@@9@9
	imul	eax, DWORD PTR _l_v413$[esp+24]

; 1170 : 	l_a5_1 = l_v414; /* for moving GCs */
; 1171 : 	l_v416 = (void*)l_a4_1;

	mov	esi, DWORD PTR _l_a4_1$[esp+20]
	mov	DWORD PTR _l_v416$[esp+24], esi

; 1172 : 	l_v417 = pypy_asm_gcroot(l_v416);

	mov	eax, DWORD PTR ?_constant_always_one_@?1??pypy_asm_gcroot@@9@9
	imul	eax, DWORD PTR _l_v416$[esp+24]

; 1173 : 	l_a4_1 = l_v417; /* for moving GCs */
; 1174 : 	l_v419 = RPyField((&pypy_g_ExcData), ed_exc_type);
; 1175 : 	l_v420 = (l_v419 == NULL);

	cmp	DWORD PTR _pypy_g_ExcData, 0

; 1176 : 	if (!l_v420) {

	jne	SHORT $LN75@pypy_g_foo

; 1177 : 		goto block1;
; 1178 : 	}
; 1179 : 	goto block9;
; 1180 : 
; 1181 :     block9:
; 1182 : 	OP_INT_SUB(l_rec_1, 1L, l_v421);
; 1183 : 	pypy_g_foo(l_v421, l_a6_1, l_a5_1, l_a4_1, l_a3_1, l_a2_1, l_a1_1);

	sub	DWORD PTR _l_rec_1$[esp+20], 1
	sub	DWORD PTR tv419[esp+24], 1
	cmp	DWORD PTR _l_rec_1$[esp+20], 0
	mov	eax, ebp
	mov	ebp, DWORD PTR _l_a6_1$[esp+20]
	mov	ecx, ebx
	mov	ebx, DWORD PTR _l_a5_1$[esp+20]
	mov	edx, edi
$block9$34446:
	mov	edi, esi
	mov	DWORD PTR _l_a4_1$[esp+20], edx
	mov	DWORD PTR _l_a5_1$[esp+20], ecx
	mov	DWORD PTR _l_a6_1$[esp+20], eax
$block0_1$34376:
	jg	$LL63@pypy_g_foo
	pop	esi
	pop	edi
	pop	ebp
	pop	ebx

; 1199 : 	goto block4;
; 1200 : }

	add	esp, 8
	ret	0
$LN71@pypy_g_foo:
$block0$40426:
$block0$40437:
$block0$40434:
$block2$40415:

; 1048 : 		goto block2;
; 1049 : 	}
; 1050 : 	goto block1;
; 1051 : 
; 1052 :     block1:
; 1053 : 	RPY_DEBUG_RETURN();
; 1054 : 	return /* nothing */;
; 1055 : 
; 1056 :     block2:
; 1057 : 	pypy_g_stack_check___();

	mov	DWORD PTR _pypy_g_ExcData, OFFSET _pypy_g_exceptions_RuntimeError_vtable
	mov	DWORD PTR _pypy_g_ExcData+4, OFFSET _pypy_g_exceptions_RuntimeError
$block1$40435:
$block1$40438:
$block1$40427:
$LN75@pypy_g_foo:
	pop	esi
	pop	edi
	pop	ebp
	pop	ebx
$block1$34379:

; 1199 : 	goto block4;
; 1200 : }

	add	esp, 8
	ret	0
_pypy_g_foo ENDP
