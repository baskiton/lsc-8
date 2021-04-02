org 0E000h

jmp RESET

INT_PTR equ 0
INT_CNT equ 8

MDA_PORT equ 4
KBD_PORT equ 5
STGC_DATA_PORT equ 6
STGC_CMD_PORT equ 7

;----- Data Segment Pointer -----
DATA equ 02h    ; h-address for 0200h, after the VECTOR TABLE
MEM_SIZE_PTR equ 0  ; point for l-address

BOOT_LOCN equ 0C00h   ; address for BOOT location


ERR01:
    hlt

MEM_TO_MEM proc
    push a
    push b
m1:
    pop l
    pop h
    mov a, mem
    inc l
    jnz m2
    inc h
m2:
    push h
    push l
    mov h, d
    mov l, e
    mov mem, a
    inc e
    jnz m3
    inc d
m3:
    dec c
    jnz m1
    pop l
    pop h
    ret
MEM_TO_MEM endp

;PRINT_MSG proc
    
;PRINT_MSG endp

;--------------------------------------------
; THESE ARE THE VECTORS WHICH ARE MOVED INTO
;  THE PROCESSOR INTERRUPT AREA DURING POWER ON
;--------------------------------------------
VECTOR_TABLE label near ; VECTOR TABLE FOR MOVE TO INTERRUPTS
    dw DUMMY_RETURN     ; int 00h - reserved
    dw DUMMY_RETURN     ; int 01h - reserved
    dw DUMMY_RETURN     ; int 02h - reserved
    dw BOOT_STRAP       ; int 03h - BOOT_STRAP
    dw VIDEO_IO         ; int 04h - VIDEO_IO
    dw KEYBOARD_IO      ; int 05h - KEYBOARD_IO
    dw MEMORY_SIZE      ; int 06h - MEMORY_SIZE
    dw STORAGE_IO       ; int 07h - STORAGE_IO
    dw DUMMY_RETURN     ; int 08h
    dw DUMMY_RETURN     ; int 09h
    dw DUMMY_RETURN     ; int 0Ah
    dw DUMMY_RETURN     ; int 0Bh
    dw DUMMY_RETURN     ; int 0Ch
    dw DUMMY_RETURN     ; int 0Dh
    dw DUMMY_RETURN     ; int 0Eh
    dw DUMMY_RETURN     ; int 0Fh

DUMMY_RETURN:
    iret


;----- INT 6 ----------------------------
; Return memory syze in KB to register A
;----------------------------------------
MEMORY_SIZE proc
    mov h, DATA
    mov l, MEM_SIZE_PTR
    mov a, mem
    iret
MEMORY_SIZE endp


;----- INT 3 ----------------------------
; BOOT STRAP LOADER
;   Sector 0 read into the Boot Location (0C00h).
;   Control is transferred there after check
;   the last byte of sector is 0ABh.
;----------------------------------------
B_FAIL: db 'BOOT FAILURE, INSERT SYSTEM STORAGE AND PRESS ANY KEY', 0Ah

BOOT_STRAP proc
    sti
    mov a, 0    ; reset the storage system
    int 7h
    
    mov b, 0    ; storage #0 select
B1:
    mov a, 1    ; check for storage available
    int 7h
    push a
    and a, 10000000b    ; storage is install
    pop a
    jz B2
    and a, 01000000b    ; storage is available
    jnz B3
B2:
    inc b
    mov a, 5
    sub a, b    ; if storage number <= 4
    jnz B1  ; loop for checked the next storage
    jmp BOOT_ERR0     ; else BOOT ERROR 0
    
B3:
    push b      ; save storage number
    mov a, 2    ; read the first sector to boot location
    mov c, 1
    mov d, 0
    mov e, 0
    mov h, (BOOT_LOCN >> 8)
    mov l, (BOOT_LOCN & 255)
    int 7h
    
B4:     ; check the last byte of sector is 0ABh
    pop b       ; restore storage number
    cmp a, 0ABh
    jz BOOT_LOCN   ; jmp to boot location
    jmp B2      ; try the next storage
    
BOOT_STRAP endp

BOOT_ERR0:
    mov a, 3    ; print error message
    mov b, 0
    mov c, 54
    mov h, (B_FAIL >> 8)
    mov l, (B_FAIL & 255)
    int 4h
    
    mov a, 0
    int 5h
    
    mov a, 1
    mov b, 0Ah
    mov c, 1
    int 4h
    
    jmp BOOT_STRAP


;----- INT 4 ----------------------------
; VIDEO I/O
;   THESE ROUTINES PROVIDE THE TTY INTERFACE
;   THE FOLLOWING FUNCTIONS ARE PROVIDED:
;       (A)=0   Clear screen
;       (A)=1   Write Character at current cursor position
;           (B) Char to write
;           (C) Count of Characters to write
;       (A)=2   Convert and Write a number to ASCII
;           (B) Number to ASCII
;       (A)=3   Write String at current cursor position
;           (B)=0   Write String by known length
;               (C) Length of String
;           (B)=1   Write a String with a '$' at the end
;           (H)(L) Address of String
;----------------------------------------
VIDEO_IO proc
    push d
    push e
    push h
    push l
    
    or a, a     ; (A)=0
    jz CLEAR_SCREEN
    dec a       ; (A)=1
    jz WRITE_CH
    dec a       ; (A)=2
    jz WRITE_ASCII
    dec a       ; (A)=3
    jz WRITE_STR
    
VIDEO_RETURN:
    pop l
    pop h
    pop e
    pop d
    
    iret
VIDEO_IO endp

;----------------------------------------
; Clear screen
; INPUT
;   NONE
; OUTPUT
;   NONE
;----------------------------------------
CLEAR_SCREEN proc
    mov a, 0Ch      ; 0Ch - symbol for clear
    out MDA_PORT
    
    jmp VIDEO_RETURN
CLEAR_SCREEN endp

;----------------------------------------
; Write Character at the current position
; INPUT
;   (B) Char to write
;   (C) Count of Characters to write
; OUTPUT
;   NONE
;----------------------------------------
WRITE_CH proc
    mov a, b
WCH1:   ; Write Loop
    out MDA_PORT
    dec c
    jnz WCH1
    
    jmp VIDEO_RETURN
WRITE_CH endp

;----------------------------------------
; Convert and Write a number to ASCII
; INPUT
;   (B) Number to ASCII
; OUTPUT
;   NONE
;----------------------------------------
WRITE_ASCII proc
    push c
    mov a, b
    mov c, 0    ; remainder
    mov d, 0    ; Counter of digit
    jmp DECIMAL_LOOP

PREPARE:
    mov c, 0

DECIMAL_LOOP:
    sub a, 10       ; equ divide by 10
    jc SAVE_ORD     ; jump if a < 0
    inc c           ; else increment remainder
    jmp DECIMAL_LOOP

SAVE_ORD:
    add a, 10   ; return digit to positive
    or a, 30h   ; convert to ASCII
    push a      ; save digit
    inc d       ; increment counter of digit
    
    mov a, c
    cmp a, 10
    jnc PREPARE     ; jump if remainder >= 10
    or a, 30h        ; else return from loop
    push a      ; save digit
    inc d       ; increment counter of digit

PRINT_LOOP:
    pop a
    out MDA_PORT
    dec d
    jnz PRINT_LOOP
    
    pop c
    jmp VIDEO_RETURN
WRITE_ASCII endp

;----------------------------------------
; Write String at current cursor position
; INPUT
;   (B)=0   Write String by known length
;       (C) Length of String
;   (B)=1   Write a String with a '$' at the end
;   (H)\
;   (L) -   Address of String
; OUTPUT
;   NONE
;----------------------------------------
WRITE_STR proc
    mov a, b
    or a, a     ; (B)=0
    jz WS_L1    ; if (B)=0 jump to write with length
    dec a       ; (B)=1
    jz WS_S1    ; if (B)=1 jump to write with a '$' at the end
    jmp VIDEO_RETURN    ; else return

WS_L1:  ; write with length loop
    mov a, mem
    out MDA_PORT
    inc l
    jnz WS_L2
    inc h
WS_L2:
    dec c
    jnz WS_L1   ; if c > 0 repeat loop
    jmp VIDEO_RETURN

WS_S1:   ; write with a '$' at the end
    mov a, mem
    cmp a, '$'  ; 24h
    jz VIDEO_RETURN
    out MDA_PORT
    inc l
    jnz WS_S2
    inc h
WS_S2:
    jmp WS_S1

WRITE_STR endp


;----- INT 5 ----------------------------
; KEYBOARD I/O
; INPUT
;   (A)=0 - Read the next ASCII char struk from the keyboard wihout echo.
;   (A)=1 - Read the next ASCII char struk from the keyboard with echo.
;           Wait input if buffer is empty.
;           Return result in (A)
;   (A)=2 - Set the Z Flag to indicate if an ASCII char is
;           available to be read without echo.
;           (ZF)=1 - No code available.
;           (ZF)=0 - Code is available. Return code to (A) with
;                    saved buffer state.
;   (A)=3 - Read the keyboard String and store to the buffer without echo.
;   (A)=4 - Read the keyboard String and store to the buffer with echo.
;       (H)(L) - Address of buffer in the RAM.
;       initial buffer:
;           +---+---+---+---+---+---+- - -
;           ¦max¦ ? ¦ ?   ?   ?   ?   ?
;           +---+---+---+---+---+---+- - -
;       buffer out:
;           +---+---+---+---+---+---+- - -
;           ¦max¦len¦ T   E   X   T   0Ah
;           +---+---+---+---+---+---+- - -
;           max - max buffer length
;           len - actual buffer length without trailing CR (0Ah)
;   (A)=12(0Ch) - Clear buffer before input and call function from (B)
;       (B) - Number of function to call
; OUTPUT
;   AS NOTED ABOVE, ONLY (A) AND FLAGS CHANGED
;   ALL REGISTERS PRESERVED
;----------------------------------------
KEYBOARD_IO proc
K0:
    cmp a, 0Ch  ; clear buffer and call
    jz KC
    or a, a     ; (A)=0
    jz K1       ; read ASCII without echo
    dec a       ; (A)=1
    jz K2       ; read ASCII with echo
    dec a       ; (A)=2
    jz K3       ; read status
    dec a       ; (A)=3
    jz K4       ; read string without echo
    dec a       ; (A)=4
    jz K5       ; read string with echo
    iret    ; EXIT

;------ read ASCII without echo
K1:
    in KBD_PORT
    or a, a
    jz K1
    iret    ; EXIT

;------ read ASCII with echo
K2:
    in KBD_PORT
    or a, a
    jz K2
    out MDA_PORT
    iret    ; EXIT

;------ read status
K3:
    pop a
    mov a, 11h
    out KBD_PORT
    in KBD_PORT
    or a, a
    sti
    ret     ; EXIT

;------ read string without echo
K4:
    push b
    push c
    mov c, 0    ; counter for string length
    mov b, mem  ; get buffer max length
    inc l
    jnz K4_1
    inc h
K4_1:
    push h      ; save address of actual length string
    push l
K4_2:
    inc l
    jnz K4_3
    inc h
K4_3:
    in KBD_PORT ; get ASCII char
    or a, a
    jz K4_3
    
    mov mem, a
    cmp a, 0Ah  ; char is end of string?
    jz K_END
    
    inc c
    dec b
    jz K_END   ; string length == max length?
    
    jmp K4_2

;------ read string with echo
K5:
    push b
    push c
    mov c, 0    ; counter for string length
    mov b, mem  ; get buffer max length
    inc l
    jnz K5_1
    inc h
K5_1:
    push h      ; save address of actual length string
    push l
K5_2:   ; LOOP
    inc l       ; set addr for next char
    jnz K5_3
    inc h
K5_3:
    in KBD_PORT ; get ASCII char
    or a, a     ; buffer is empty?
    jz K5_3
    
    cmp a, 0Ah  ; end of string?
    jz K_END
    cmp a, 08h  ; backspace?
    jz K5_BSP
    
    inc c
    dec b
    jz K_END   ; string length == max length?
    
    mov mem, a
    out MDA_PORT
    jmp K5_2

K5_BSP:
    push a
    mov a, c
    or a, a     ; string length is null?
    jz K5_3
    dec c
    inc b
    pop a
    out MDA_PORT
    
    mov a, l
    sub a, 1
    mov l, a
    jnc K5_3
    dec h
    
    jmp K5_3

K_END:
    mov mem, a
    out MDA_PORT
    pop l
    pop h
    mov mem, c  ; store string length to buffer
    pop c
    pop b
    iret    ; EXIT

;------ Clear buffer
KC:
    out KBD_PORT
    mov a, b
    jmp K0

KEYBOARD_IO endp


;----- INT 7 ----------------------------
; STORAGE I/O
; INPUT
;       (A)=0   Reset Storage System
;
;       (A)=1   Verify Storage
;       (A)=2   Read Storage
;       (A)=3   Write Storage
; For Read/Write/Verif
;       (B) - Drive Number (0-3 allowed, value checked)
;       (C) - Number of Sectors
;       (D) - High Sector Number
;       (E) - Low Sector Number
;       (H, L)  Address of Buffer (Not required for verify)
;
; INFO
;   Storage Controller has 256 bytes per sector

; OUTPUT
;   (A) - Return params from VERIFY
;----------------------------------------
STORAGE_IO proc
    or a, a     ; (A)=0
    jz STRG_RESET
    
    ; drive num test
    push a  ; save function
    mov a, 3
    sub a, b
    pop a
    jc STRG_END
    
    dec a       ; (A)=1
    jz STRG_VERF
    dec a       ; (A)=2
    jz STRG_READ
    dec a       ; (A)=3
    jz STRG_WRITE
    
STRG_END:
    ; Bad Command
    iret

;----- RESET THE STORAGE SYSTEM
STRG_RESET:
    mov a, 4    ; reset command
    out STGC_CMD_PORT
    
    iret

;----- STORAGE VERIFY
STRG_VERF:
    mov a, b
    out STGC_CMD_PORT
    in STGC_CMD_PORT    ; get storage params
    
    iret

;----- STORAGE READ
STRG_READ:
    call STRG_SETUP
    
STRG_READ_LOOP:
    mov b, 0    ; set 256 bytes per sector
SR1:
    in STGC_DATA_PORT
    mov mem, a      ; mov data byte to buffer
    inc l
    jnz SR2
    inc h
SR2:
    dec b
    jnz SR1     ; end of sector?
    
    dec c
    jnz STRG_READ_LOOP  ; sectors counter is end?
SR3:
    iret

;----- STORAGE WRITE
STRG_WRITE:
    call STRG_SETUP
    
STRG_WRITE_LOOP:
    mov b, 0    ; set 256 bytes per sector
SW1:
    mov a, mem
    out STGC_DATA_PORT  ; mov data bytes to storage
    inc l
    jnz SW2
    inc h
SW2:
    dec b
    jnz SW1     ; end of sector?
    
    dec c
    jnz STRG_WRITE_LOOP     ; sectors counter is end?
SW3:
    iret

STORAGE_IO endp

STRG_SETUP proc
    mov a, b
    out STGC_CMD_PORT   ; select drive
    mov a, d
    out STGC_DATA_PORT  ; set HIGH sector number
    mov a, e
    out STGC_DATA_PORT  ; set LOW sector number

    ret
STRG_SETUP endp


;----------------------------------------
; START COMPUTER ROUTINE
;----------------------------------------
RESET label near
START:
    cli     ; DISABLE INTERRUPTS

;----- TEST OF REGISTERS
    mov a, 0FFh
    mov b, a
    mov c, b
    mov d, c
    mov e, d
    mov h, e
    mov l, h
    
    xor a, l
    jnz ERR01

;----- MEMORY TEST
    mov l, 0
    mov h, 0
    mov c, 0FFh
mt1:
    mov a, 01010101b
    mov mem, a
    cmp a, mem
    jnz mt2
    inc c
    mov a, l
    add a, 0FFh
    mov l, a
    mov a, h
    adc a, 03h
    mov h, a
    jmp mt1
mt2:
    mov h, DATA
    mov l, MEM_SIZE_PTR
    mov mem, c
    
;----- SETUP INTERRUPT VECTOR TABLE
    mov c, (INT_CNT << 1)   ; count of byte
    mov d, 0    ; high addr destination
    mov e, INT_PTR    ; low addr destination
    mov a, (VECTOR_TABLE >> 8)    ; high addr source
    mov b, (VECTOR_TABLE & 255)   ; low addr source
    call MEM_TO_MEM     ; transfer Vector Table to the RAM


sti
jmp code
msg1: db 'LSC-8 BIOS (C), VER 1.0, 2020', 0Ah, 0Ah
msg2: db ' KB RAM', 0Ah
msg3: db 0Ah, 'STORAGE #'
msg4: db ' : '
msg5: db 'NONE'

msg6: db 'ERROR'
msg7: db ' RO'
msg8: db ' VOL'
msg9: db ' FIXED'
msg10: db ' REMOVABLE'
msg11: db ' DRIVE'

msg_128K: db '128K'
msg_512K: db '512K'
msg_1M: db '  1M'
msg_2M: db '  2M'
msg_4M: db '  4M'
msg_8M: db '  8M'
msg_16M: db ' 16M'

code:
    mov a, 0
    int 4h  ; clear screen
    
    mov a, 3
    mov b, 0    ; prt str with length
    mov c, (msg2 - msg1)    ; set str length
    mov h, (msg1 >> 8)
    mov l, (msg1 & 255)
    int 4h  ; print copyright
    
    int 6h
    mov b, a
    mov a, 2
    int 4h  ; print mem size
    
    mov a, 3
    mov b, 0    ; prt str with length
    mov c, 8    ; set str length
    mov h, (msg2 >> 8)
    mov l, (msg2 & 255)
    int 4h  ; print 'KB RAM'
    
;----- INIT STORAGE SYSTEM
    mov a, 0
    int 7h  ; reset storage system
    
    mov b, 0    ;set storage #0
VERIF_LOOP:
    mov e, b  ; save storage number
    
    mov a, 3
    mov b, 0
    mov c, (msg4 - msg3)
    mov h, (msg3 >> 8)
    mov l, (msg3 & 255)
    int 4h  ; print 'STORAGE #'
    
    mov a, 30h
    add a, e
    mov b, a
    mov a, 1
    mov c, 1
    int 4h  ; print storage number
    
    mov a, 3
    mov b, 0
    mov c, 3
    mov h, (msg4 >> 8)
    mov l, (msg4 & 255)
    int 4h  ; print ' : '
    
    mov b, e    ; restore storage number
    mov a, 1
    int 7h  ; veryf storage #(B)
    push a
    and a, 10000000b
    pop a
    jz VF_NONE  ; if verif(7) return 0
    
    push a
    and a, 0111b
    dec a   ; if 1
    jz VF_128K
    dec a   ; if 2
    jz VF_512K
    dec a   ; if 3
    jz VF_1M
    dec a   ; if 4
    jz VF_2M
    dec a   ; if 5
    jz VF_4M
    dec a   ; if 6
    jz VF_8M
    dec a   ; if 7
    jz VF_16M
    jmp VF_ERR

V1:
    pop a
    push a
    and a, 00010000b    ; FIX / REMOV
    jz VF_FIXED
    
    mov a, 3
    mov b, 0
    mov c, 10
    mov h, (msg10 >> 8)
    mov l, (msg10 & 255)
    int 4h  ; print ' REMOVABLE'
    
    pop a
    push a
    and a, 01000000b
    jz VF_DRIVE

V2:
    pop a
    and a, 1000b    ; RO / VOL
    jz VF_RO
    
    mov a, 3
    mov b, 0
    mov c, 4
    mov h, (msg8 >> 8)
    mov l, (msg8 & 255)
    int 4h  ; print ' VOL'

V3:
    mov b, e
    inc b
    mov a, 4
    sub a, b
    jnz VERIF_LOOP
    
    mov a, 1
    mov b, 0Ah
    mov c, 2
    int 4h
    jmp BOOT_STRAP  ; end verify routine
    ; jmp code_2  ; end verify routine

VF_DRIVE:
    mov a, 3
    mov b, 0
    mov c, 6
    mov h, (msg11 >> 8)
    mov l, (msg11 & 255)
    int 4h  ; print ' DRIVE'
    pop a
    jmp V3

VF_FIXED:
    mov a, 3
    mov b, 0
    mov c, 6
    mov h, (msg9 >> 8)
    mov l, (msg9 & 255)
    int 4h  ; print ' FIXED'
    jmp V2

VF_RO:
    mov a, 3
    mov b, 0
    mov c, 3
    mov h, (msg7 >> 8)
    mov l, (msg7 & 255)
    int 4h  ; print ' RO'
    jmp V3
    
VF_NONE:
    mov a, 3
    mov b, 0
    mov c, 4
    mov h, (msg5 >> 8)
    mov l, (msg5 & 255)
    int 4h  ; print 'NONE'
    pop a
    jmp V3
    
VF_ERR:
    mov a, 3
    mov b, 0
    mov c, 5
    mov h, (msg6 >> 8)
    mov l, (msg6 & 255)
    int 4h  ; print 'ERROR'
    pop a
    jmp V3
    
VF_128K:
    mov a, 3
    mov b, 0
    mov c, 4
    mov h, (msg_128K >> 8)
    mov l, (msg_128K & 255)
    int 4h  ; print '128K'
    jmp V1
    
VF_512K:
    mov a, 3
    mov b, 0
    mov c, 4
    mov h, (msg_512K >> 8)
    mov l, (msg_512K & 255)
    int 4h  ; print '512K'
    jmp V1
    
VF_1M:
    mov a, 3
    mov b, 0
    mov c, 4
    mov h, (msg_1M >> 8)
    mov l, (msg_1M & 255)
    int 4h  ; print '1M'
    jmp V1
    
VF_2M:
    mov a, 3
    mov b, 0
    mov c, 4
    mov h, (msg_2M >> 8)
    mov l, (msg_2M & 255)
    int 4h  ; print '2M'
    jmp V1
    
VF_4M:
    mov a, 3
    mov b, 0
    mov c, 4
    mov h, (msg_4M >> 8)
    mov l, (msg_4M & 255)
    int 4h  ; print '4M'
    jmp V1
    
VF_8M:
    mov a, 3
    mov b, 0
    mov c, 4
    mov h, (msg_8M >> 8)
    mov l, (msg_8M & 255)
    int 4h  ; print '8M'
    jmp V1
    
VF_16M:
    mov a, 3
    mov b, 0
    mov c, 4
    mov h, (msg_16M >> 8)
    mov l, (msg_16M & 255)
    int 4h  ; print '16M'
    jmp V1
