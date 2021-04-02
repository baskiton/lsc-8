#!/usr/bin/python
# -*- coding: UTF-8 -*-

import re
import argparse
import ast
import operator as op


class ExceptionWithLineNumber(Exception):
    def __init__(self, message: str, line_number: int):
        super().__init__(message)
        self._line_number = line_number

    def __str__(self):
        return f'{super().__str__()} at line {self._line_number}'


class WrongParameterException(ExceptionWithLineNumber):
    def __init__(self, line_number: int, arg):
        super().__init__('Wrong parameter', line_number)
        self.arg = arg

    def __str__(self):
        return f'Wrong parameter at line {self._line_number}: {self.arg}'


class FewArgumentsException(ExceptionWithLineNumber):
    def __init__(self, line_number: int, necessary_arguments: int = None):
        if necessary_arguments is None:
            super().__init__('Few arguments', line_number)
        else:
            super().__init__(f'Few arguments, need {necessary_arguments} args',
                             line_number)


class TooManyArgumentsException(ExceptionWithLineNumber):
    def __init__(self, line_number: int, necessary_arguments: int = None):
        if necessary_arguments is None:
            super().__init__('Too many arguments', line_number)
        else:
            super().__init__(
                f'Too many arguments, need {necessary_arguments} args',
                line_number
            )


class CommaExpectedException(ExceptionWithLineNumber):
    def __init__(self, line_number: int):
        super().__init__('Comma expected', line_number)


class WrongOperandSize(ExceptionWithLineNumber):
    def __init__(self, line_number, need, arg):
        super().__init__(f'Operand "{arg.name}" over {need} byte', line_number)


class WrongOperandValue(ExceptionWithLineNumber):
    def __init__(self, line_num, have):
        super().__init__(f'I/O port number should be between 0 and 15,'
                         f' you have {have}', line_num)


class NameIsNotDefined(ExceptionWithLineNumber):
    def __init__(self, line_num, name):
        super().__init__(f"Name \"{name}\" is not defined", line_num)


class Token:
    def __init__(self, cls, group=None, subgroup=None, name=None):
        self.cls = cls
        self.group = group
        self.subgroup = subgroup
        self.name = name
        self.allocate = None
        self.value = None
        self.size = 0

    @staticmethod
    def is_this(line: list, pos: int):
        return Token.get_token(line, pos)

    def specify(self, line, pos):
        return self

    @staticmethod
    def get_token(line, pos):
        return Token('Token', name=line[pos]).specify(line, pos)

    def syntax_check(self, line_num, pos, line):
        return True

    @staticmethod
    def instance_check(size, line, pattern, line_num):
        for i in range(size):
            if not isinstance(line[i], pattern[i]):
                raise WrongParameterException(line_num, line[i].name)

    def generate(self, line, pos, l_num):
        return []

    def __repr__(self):
        return f'[{self.cls}: {self.group}: {self.name}]'


class Undefined(Token):
    def __init__(self):
        super().__init__('Undefined')

    def __repr__(self):
        return f'[{self.cls}]'


class Comma(Token):
    def __init__(self, name):
        super().__init__('Comma', name=name)

    @staticmethod
    def is_this(line, pos):
        if line[pos] == ',':
            return Comma.get_token(line, pos)

    @staticmethod
    def get_token(line, pos):
        return Comma(line[pos]).specify(line, pos)

    def __repr__(self):
        return f'[{self.name}]'


class Action(Token):
    INSTRUCTION_SET = (
        # Data transfer commands
        'mov', 'push', 'pop',
        'in', 'out',

        # Arithmetic commands
        'inc', 'dec',
        'add', 'adc', 'sub', 'sbb',
        'and', 'xor', 'or', 'cmp',
        'rlc', 'rol',   # synonymic
        'rrc', 'ror',   # synonymic
        'ral', 'rcl',   # synonymic
        'rar', 'rcr',   # synonymic

        # Control transfer commands
        'jmp', 'call', 'ret',

        'clc', 'stc', 'cli', 'sti',

        'jnc', 'jae', 'jnb',    # CF=0
        'jc', 'jb', 'jnae',     # CF=1
        'jnz', 'jne',           # ZF=0
        'jz', 'je',             # ZF=1
        'jns',                  # SF=0
        'js',                   # SF=1
        'jnp', 'jpo',           # PF=0
        'jp', 'jpe',            # PF=1

        'cnc', 'cnz', 'cp', 'cpo',  # CF, ZF, SF, PF = 0
        'cc', 'cz', 'cm', 'cpe',    # CF, ZF, SF, PF = 1

        'rnc', 'rnz', 'rp', 'rpo',  # CF, ZF, SF, PF = 0
        'rc', 'rz', 'rm', 'rpe',    # CF, ZF, SF, PF = 1

        # Interrupt commands
        'int', 'into', 'iret',

        # Control commands
        'hlt',
        'nop',
    )

    DIRECTIVE_SET = ('db', 'dw', 'dd', 'dq', 'dt', 'dup',
                     'byte', 'word', 'dword', 'qword', 'tbyte',
                     'equ', '=', 'end', 'endp',
                     'proc', 'label', 'org',
                     'near', 'far')

    def __init__(self, name, group=None):
        super().__init__('Action', group=group, name=name)

    @staticmethod
    def is_this(line, pos):
        if line[pos] in Action.INSTRUCTION_SET:
            return Instruction(line[pos])
        elif line[pos] in Action.DIRECTIVE_SET:
            return Directive(line[pos])
        return False


class Instruction(Action):
    def __init__(self, name):
        super().__init__(group='Instruction', name=name)
        self.size = 1

    @staticmethod
    def get_token(line, pos):
        return Instruction(name=line[pos])

    def syntax_check(self, line_num, pos, line):
        name = self.name
        instr_len = len(line[pos:])

        pattern_2op = [Instruction, Register, Comma, Operand]

        pattern_1op = [Instruction, Operand]
        pattern_1op_1 = [Instruction, (Name, Immediate)]
        pattern_1op_2 = [Instruction, (Immediate, Symbol)]
        pattern_1op_3 = [Instruction, Register]
        pattern_1op_4 = [Instruction, (Register, Immediate)]

        pattern_0op = [Instruction]

        if name in ('mov', 'add', 'adc', 'sub', 'sbb',
                    'and', 'xor', 'or', 'cmp',):
            if instr_len == 4:      # 2 op
                self.instance_check(4, line[pos:], pattern_2op, line_num)
                self.allocate_check(1, instr_len, line, line_num, pos)
                if ((line[pos + 3].name == 'mem' and
                     line[pos + 1].name == 'mem') or
                        (self.name != 'mov' and
                         line[pos + 1].name != 'a')):
                    raise WrongParameterException(line_num, line[pos])

            elif instr_len < len(pattern_2op):
                raise FewArgumentsException(line_num, 2)
            else:
                raise TooManyArgumentsException(line_num, 2)

        elif name in ('hlt', 'nop', 'iret', 'ret',
                      'rnc', 'rnz', 'rp', 'rpo',
                      'rc', 'rz', 'rm', 'rpe',
                      'rlc', 'rol', 'rrc', 'ror',
                      'ral', 'rcl', 'rar', 'rcr',
                      'clc', 'stc', 'cli', 'sti'):  # 0 op
            if instr_len == 1:
                return

            elif instr_len < len(pattern_0op):
                raise FewArgumentsException(line_num)
            else:
                raise TooManyArgumentsException(line_num, 0)

        else:           # 1 op
            if instr_len == 2:
                if name in ['inc', 'dec', 'pop']:
                    self.instance_check(2, line[pos:], pattern_1op_3, line_num)
                    self.allocate_check(1, instr_len, line, line_num, pos)

                elif name in ('in', 'out'):
                    self.instance_check(2, line[pos:], pattern_1op_2, line_num)
                    self.allocate_check(1, instr_len, line, line_num, pos)
                    line[pos + 1].size = 0

                elif name == 'int':
                    self.instance_check(2, line[pos:], pattern_1op_2, line_num)
                    self.allocate_check(1, instr_len, line, line_num, pos)
                    # line[pos + 1].size = 0

                elif name in ('jmp', 'call',
                              'jnc', 'jae', 'jnb', 'jc', 'jb', 'jnae',
                              'jnz', 'jne', 'jz', 'je', 'jns', 'js',
                              'jnp', 'jpo', 'jp', 'jpe',
                              'cnc', 'cnz', 'cp', 'cpo',
                              'cc', 'cz', 'cm', 'cpe'):
                    self.instance_check(2, line[pos:], pattern_1op_1, line_num)

                elif name == 'push':
                    self.instance_check(2, line[pos:], pattern_1op_4, line_num)
                    self.allocate_check(1, instr_len, line, line_num, pos)

                else:
                    raise WrongParameterException(line_num, name)

            elif instr_len < len(pattern_1op):
                raise FewArgumentsException(line_num, 1)
            else:
                raise TooManyArgumentsException(line_num, 1)

    @staticmethod
    def allocate_check(alloc_need, instr_len, line, line_num, pos):
        for i in range(pos + 1, instr_len, 2):
            if line[i].allocate != alloc_need:
                raise WrongOperandSize(line_num, alloc_need, line[i])

    def generate(self, line, pos, l_num):
        # Transition
        ret = 0b00_000_011
        call = 0b01_000_010
        jmp = 0b01_000_000

        # Flags
        f_nc = 0b000_000
        f_nz = 0b001_000
        f_ns = 0b010_000
        f_np = 0b011_000
        f_c = 0b100_000
        f_z = 0b101_000
        f_s = 0b110_000
        f_p = 0b111_000

        if self.name == 'hlt':
            return [0b11_111_111]

        elif self.name in ('in', 'out'):
            opc = {'in': 0b01_000_001, 'out': 0b01_100_001}
            code = opc[self.name] | (line[pos + 1].value << 1)
            return [code]

        elif self.name == 'ret':
            return [0b00_100_010]

        elif self.name == 'rnc':
            return [ret | f_nc]

        elif self.name == 'rc':
            return [ret | f_c]

        elif self.name == 'rnz':
            return [ret | f_nz]

        elif self.name == 'rz':
            return [ret | f_z]

        elif self.name == 'rp':
            return [ret | f_ns]

        elif self.name == 'rm':
            return [ret | f_s]

        elif self.name == 'rpo':
            return [ret | f_np]

        elif self.name == 'rpe':
            return [ret | f_p]

        elif self.name == 'call':
            return [0b00_111_001]

        elif self.name == 'cnc':
            return [call | f_nc]

        elif self.name == 'cc':
            return [call | f_c]

        elif self.name == 'cnz':
            return [call | f_nz]

        elif self.name == 'cz':
            return [call | f_z]

        elif self.name == 'cp':
            return [call | f_ns]

        elif self.name == 'cm':
            return [call | f_s]

        elif self.name == 'cpo':
            return [call | f_np]

        elif self.name == 'cpe':
            return [call | f_p]

        elif self.name == 'jmp':
            return [0b00_111_000]

        elif self.name in ('jnc', 'jae', 'jnb'):
            return [jmp | f_nc]

        elif self.name in ('jc', 'jb', 'jnae'):
            return [jmp | f_c]

        elif self.name in ('jnz', 'jne'):
            return [jmp | f_nz]

        elif self.name in ('jz', 'je'):
            return [jmp | f_z]

        elif self.name == 'jns':
            return [jmp | f_ns]

        elif self.name == 'js':
            return [jmp | f_s]

        elif self.name in ('jnp', 'jpo'):
            return [jmp | f_np]

        elif self.name in ('jp', 'jpe'):
            return [jmp | f_p]

        elif self.name == 'mov':
            dst = line[pos + 1].code << 3
            if isinstance(line[pos + 3], (Immediate, Symbol, Variable)):
                code = 0b00_000_110
                src = 0b110
            else:
                code = 0b11_000_000
                src = line[pos + 3].code

            return [code | dst | src]

        elif self.name in ('inc', 'dec'):
            code = 0b00_000_000
            dst = line[pos + 1].code << 3
            if self.name == 'dec':
                code |= 1
            return [code | dst]

        elif self.name in ('pop', 'push'):
            code = 0b01_000_100
            if isinstance(line[pos + 1], Immediate):
                code = 0b00_110_010
                src_dst = 0
            else:
                src_dst = line[pos + 1].code << 3
            if self.name == 'pop':
                code |= 2

            return [code | src_dst]

        elif self.name in ('add', 'adc', 'sub', 'sbb',
                           'and', 'xor', 'or', 'cmp'):
            select = {
                'add': 0b000_000,
                'adc': 0b001_000,
                'sub': 0b010_000,
                'sbb': 0b011_000,
                'and': 0b100_000,
                'xor': 0b101_000,
                'or': 0b110_000,
                'cmp': 0b111_000
            }
            code = 0b10_000_000
            if isinstance(line[pos + 3], Immediate):
                code = 0b00_000_100
                src = 0b100
            else:
                src = line[pos + 3].code

            return [code | src | select.get(self.name)]

        elif self.name == 'int':
            return [0b00_101_010]

        elif self.name == 'iret':
            return [0b00_111_010]

        elif self.name in ('clc', 'stc', 'cli', 'sti'):
            code = {'clc': 0b00, 'stc': 0b01, 'cli': 0b10, 'sti': 0b11}
            return [0b00_000_101 | (code[self.name] << 4)]

        return [255]


class Directive(Action):
    ALLOCATING = {'db': 1, 'dw': 2, 'dd': 4, 'dq': 8, 'dt': 10}

    def __init__(self, name):
        super().__init__(group='Directive', name=name)
        self.allocate = Directive.ALLOCATING.get(name)

    def syntax_check(self, line_num, pos, line):
        name = self.name

        if name in ('db', 'dw', 'dd', 'dq', 'dt'):
            pattern = [Comma, (Immediate, Name)]
            if len(line[pos:]) % 2:
                raise WrongParameterException(line_num, self.name)

            if (len(line) > 3) and (line[pos + 2].name == 'dup'):
                temp_line = line[pos + 3:]
                temp_line.append(Comma(','))
                temp_line *= line[pos + 1].value
                del temp_line[-1]
                del line[pos + 1:]
                line += temp_line

            self.instance_check(1, line[pos+1:pos+2], [pattern[1]], line_num)
            self.allocate_apply(line[pos + 1], line_num)
            for i in range(pos + 2, len(line), 2):
                self.instance_check(2, line[i:i+2], pattern, line_num)
                self.allocate_apply(line[i + 1], line_num)

            if isinstance(line[0], Variable):
                line[0].allocate = self.allocate
                line[0].value = line[2].value
                self.value = line[2].value

        elif name in ('equ', '='):
            if line[pos + 1].size > line[pos - 1].allocate:
                line[pos - 1].allocate = line[pos + 1].size
                line[pos - 1].size = line[pos + 1].size
                # raise WrongOperandSize(line_num, 1, line[pos + 1])
            line[pos - 1].value = line[pos + 1].value
            return -1

        elif name == 'org':
            if (pos or (not isinstance(line[pos + 1], Immediate)) or
                    (line[pos + 1].allocate > 2)):
                raise WrongParameterException(line_num, name)
            self.value = line[pos + 1].value
            if not Lexer.ORG:
                Lexer.ORG = line[pos + 1].value
            return -1

        elif name in ('end', 'endp'):
            return -1

    def allocate_apply(self, token: Token, line_num):
        if token.allocate is not None:
            if self.allocate < token.allocate:
                raise WrongOperandSize(line_num, self.allocate, token)

            elif (isinstance(token, Immediate) and
                  (self.allocate > token.allocate)):
                token.allocate = self.allocate
                token.size = self.allocate


class Operand(Token):
    def __init__(self, name, group=None):
        super().__init__('Operand', group=group, name=name)

    @staticmethod
    def is_this(line, pos):
        if (line[pos][0].isdigit() or
                line[pos] in ('a', 'b', 'c', 'd', 'e', 'h', 'l', 'mem', '?') or
                line[pos][0] in ('"', "'", '-', '(')):
            return Operand.get_token(line, pos)
        return False

    @staticmethod
    def get_token(line, pos):
        return Operand(name=line[pos]).specify(line, pos)

    def specify(self, line, pos):
        if (line[pos][0].isdigit() or line[pos][0] in ('"', "'", '-') or
                line[pos] == '?'):
            val = Immediate.value_parse(line[pos])
            if isinstance(val, Undefined):
                return val
            return Immediate(line[pos], val)

        elif line[pos].startswith('('):
            return Immediate(line[pos], line[pos][1:-1].split())

        # elif line[pos] == '?':
        #     return

        return Register(line[pos])

    def syntax_check(self, line_num, pos, line):
        if not pos:
            raise WrongParameterException(line_num, self.name)


class Register(Operand):
    def __init__(self, reg):
        super().__init__(group='Register', name=reg)
        self.allocate = 1
        self.code = self._get_code(self.name)

    @staticmethod
    def _get_code(name):
        code = {
            'a': 0b000,
            'b': 0b001,
            'c': 0b010,
            'd': 0b011,
            'e': 0b100,
            'h': 0b101,
            'l': 0b110,
            'mem': 0b111
        }
        return code.get(name)


class Immediate(Operand):
    def __init__(self, name: str, value=None):
        super().__init__(group='Immediate', name=name)
        self.value = value
        self.type = None
        self._set_allocate()
        self._set_size()

    @staticmethod
    def value_parse(value: str):
        if value[0].isdigit() or (value[0] == '-'):
            if value.endswith('b') and re.match(r'^-?[01]+$', value[:-1]):
                return Immediate._get_value(value[:-1], 2)   # bin

            elif ((value.endswith('o') or value.endswith('q')) and
                  re.match(r'^-?[0-8]+$', value[:-1])):
                return Immediate._get_value(value[:-1], 8)   # oct

            elif (value.endswith('h') and
                  re.match(r'^-?[\d]+[\da-f]*$', value[:-1])):
                return Immediate._get_value(value[:-1], 16)  # hex

            elif value.endswith('d') and re.match(r'^-?[\d]+$', value[:-1]):
                return Immediate._get_value(value[:-1], 10)  # dec

            elif re.match(r'^-?[\d]+$', value):
                return Immediate._get_value(value, 10)       # dec

        elif value == '?':
            return 0

        elif re.match(r"""('.*?')|(".*?")""", value):
            return value[1:-1]  # ascii

        return Undefined()

    @staticmethod
    def _get_value(value, base):
        value = int(value, base)
        return value
        # if -128 <= value <= 255:
        #     return value

    def _set_allocate(self):
        if isinstance(self.value, (str, list)) or (-128 <= self.value <= 255):
            self.allocate = 1   # BYTE
        elif -32768 <= self.value <= 65535:
            self.allocate = 2   # WORD
        elif (2 ** (8 * 4)) / -2 <= self.value <= (2 ** (8 * 4)) - 1:
            self.allocate = 4   # DWORD
        elif (2 ** (8 * 8)) - 2 <= self.value <= (2 ** (8 * 8)) - 1:
            self.allocate = 8   # QWORD
        elif (2 ** (8 * 10)) / 2 <= self.value <= (2 ** (8 * 10)) - 1:
            self.allocate = 10  # 10 BYTES
        else:
            print(type(self.value), self.value)
            raise TypeError

    def _set_size(self):
        # self.size = self.allocate
        if isinstance(self.value, str):
            self.size = len(self.value)
        else:
            self.size = self.allocate

    def generate(self, line, pos, l_num):
        if isinstance(self.value, str):
            zeros = ((self.allocate * (
                    (len(self.value) // self.allocate) +
                    bool(len(self.value) % self.allocate)
            )) - len(self.value))
            values = [ch for ch in bytes(self.value, encoding='ascii')]
            return values + ([0] * zeros)

        elif line[pos - 1].name in ('in', 'out'):
            return []
        else:
            if self.value < 0:
                signed = True
            elif self.allocate == 1 and self.value > 127:
                signed = False
            elif self.allocate == 2 and self.value > 32_767:
                signed = False
            elif self.allocate == 4 and self.value > 2_147_483_647:
                signed = False
            elif self.allocate == 8 and self.value > ((2 ** 64) / 2) - 1:
                signed = False
            elif self.allocate == 10 and self.value > ((2 ** 80) / 2) - 1:
                signed = False
            else:
                signed = False

            return [i for i in self.value.to_bytes(self.allocate, 'little',
                                                   signed=signed)]

    def syntax_check(self, line_num, pos, line):
        if line[pos - 1] in ('in', 'out') and self.value > 15:
            raise WrongOperandValue(line_num, self.value)


class Name(Operand, Token):
    def __init__(self, name, group=None, value_type=None):
        Token.__init__(self, 'Name', group=group)
        self.value_type = value_type  # address, data, constant
        self.type = None
        self.name = name

    @staticmethod
    def is_this(line, pos):
        if re.match(r'^[a-z_][a-z\d?@_$]{0,31}:?$', line[pos]):
            return Name.get_token(line, pos)
        return False

    @staticmethod
    def get_token(line, pos):
        return Name(line[pos]).specify(line, pos)

    def specify(self, line, name_pos):
        if name_pos != 0:
            # if (len(line[name_pos]) >= 3) and
            return self

        if line[0].endswith(':'):
            line[0] = line[0][:-1]
            return self._label(line[0])     # Label

        elif len(line) < 2:
            return Undefined()

        elif len(line) == 2:
            if line[1] == 'proc':
                return self._label(line[0])     # Label
            elif line[1] == 'endp':
                return self._label(line[0])
        elif len(line) >= 3:
            if line[1] == 'proc':
                del line[1:]
                return self._label(line[0])     # Label
            elif line[1] == 'label':
                del line[1:]
                return self._label(line[0])     # Label

            elif line[1] in ('db', 'dw', 'dd', 'dq', 'dt'):
                return self._variable(line, name_pos)  # Variable

            elif line[1] in ('equ', '='):
                del line[3:]
                return self._symbol(line[0])    # Symbol

        return Undefined()

    def syntax_check(self, line_num, pos, line):
        return True

    @staticmethod
    def _label(name):
        return Label(name)

    @staticmethod
    def _variable(line, name_pos):

        return Variable(line[name_pos])

    @staticmethod
    def _symbol(name):
        return Symbol(name)

    def __repr__(self):
        return f'[{self.cls}: {self.group}: "{self.name}": {self.value}]'

    def generate(self, line, pos, l_num):
        ret = []
        if pos:
            if self.value is None:
                raise NameIsNotDefined(l_num, self.name)
            ret = [i for i in self.value.to_bytes(self.allocate, 'little',
                                                    signed=True)]
        return ret


class Label(Name):
    """
    <name>:
        Examples:
            CLEAR_SCREEN: MOV AL,20H
            FOO: DB 0FH
            SUBROUTINE3:

    <name> LABEL NEAR
    <name> LABEL FAR
        Examples:
            FOO LABEL NEAR
            GOO LABEL FAR

    <name> PROC
    <name> PROC NEAR
    <name> PROC FAR
        Examples:
            REPEAT PROC NEAR
            CHECKING PROC ;same as CHECKING PROC NEAR
            FIND_CHR PROC FAR

    EXTRN <name>:NEAR
    EXTRN <name>:FAR
        Examples:
            EXTRN FOO:NEAR
            EXTRN ZOO:FAR

    """

    def __init__(self, name):
        super().__init__(name, group='Label', value_type='address')
        self.segment = None
        self.offset = None  # 16-bit unsigned number.
        self.type = None  # NEAR (2 byte pointer) or FAR (4 byte pointer).
        self.cs_assume = None
        self.allocate = 2
        self.size = 2

    def generate(self, line, pos, l_num):
        if pos:
            return [i for i in self.value.to_bytes(self.allocate, 'little',
                                                   signed=False)]
        return []


class Variable(Name):
    """
    <name> <define-dir>         ;no colon!
           <define-dir> - DB/DW/DD/DQ/DT
    <name> <struc-name> <expression>
           <struc-name> - STRUC
    <name> <rec-name> <expression>
           <rec-name> - RECORD
        Example:
            START_MOVE DW ?

            CORRAL STRUC
                    *
                    *
                    *
                   ENDS
            HORSE CORRAL <'SADDLE'>

            GARAGE RECORD CAR:8='P'
            SMALL GARAGE 10 DUP(<'Z'>)

    <name> LABEL <size>
                 <size> is one of the following size specifiers:
                     BYTE - specifies 1 byte
                     WORD - specifies 2 bytes
                     DWORD - specifies 4 bytes
                     QWORD - specifies 8 bytes
                     TBYTE - specifies 10 bytes
        Example:
            CURSOR LABEL WORD

    EXTRN <name>:<size>
        Example:
            EXTRN FOO:DWORD

    """

    def __init__(self, name, allocate=None):
        super().__init__(name, group='Variable', value_type='data')
        self.segment = None
        self.offset = None  # 16-bit unsigned number.
        self.type = None
        self.allocate = allocate
        # Directive Tvpe    Size
        # DB        BYTE    1 byte
        # DW        WORD    2 bytes
        # DD        DWORD   4 bytes
        # DQ        QWORD   8 bytes
        # DT        TBYTE   10 bytes

    def generate(self, line, pos, l_num):
        if pos:
            if isinstance(self.value, str):
                return [ch for ch in bytes(self.value, encoding='ascii')]
            else:
                return [i for i in self.value.to_bytes(self.allocate, 'little',
                                                       signed=True)]
        return []


class Symbol(Name):
    """
    <name> EQU <expression>
               <expression> may be another symbol, an instruction mnemonic,
               a valid expression, or any other entry (such as text or
               indexed references).
        Examples:
            FOO EQU 7H
            ZOO EQU FOO

    <name> = <expression>
             <expression> may be any valid expression.
        Examples:
            GOO = 0FH
            GOO = $+2
            GOO = GOO+FOO

    EXTRN <name>:ABS
        Examples:
            EXTRN BAZ:ABS
            BAZ must be defined by an EQU or = directive to a valid expression.

    """

    def __init__(self, name):
        super().__init__(name, group='Symbol', value_type='constant')
        self.allocate = 1
        self.size = 1

    def generate(self, line, pos, l_num):
        if line[pos - 1].name in ('in', 'out'):
            return []
        if pos:
            if isinstance(self.value, str):
                return [ch for ch in bytes(self.value, encoding='ascii')]
            else:
                return [i for i in self.value.to_bytes(self.allocate, 'little',
                                                       signed=True)]
        return []


class NameTable:
    def __init__(self):
        self.table = {}

    def add_name(self, name_token: Name):
        if name_token.name in self.table:
            return
        self.table[name_token.name] = name_token

    def get(self, name):
        result = None
        try:
            result = self.table.get(name)
        except KeyError:
            result = None
        finally:
            return result

    def __repr__(self):
        return str(self.table)

    def __getitem__(self, name):
        return self.table.get(name)

    def __iter__(self):
        for key in self.table:
            yield key

    def __len__(self):
        return len(self.table)


class Lexer:
    ORG = 0

    def __init__(self, text: str):
        self._lines = text.splitlines()
        self._table = {}
        self._name_table = NameTable()
        self.listing = []

    def analyze(self, verbose):
        for l_number in range(len(self._lines)):
            line = self._lines[l_number]
            if not len(line):
                continue
            parts = self._splitter(line)
            if not len(parts):
                continue
            tokens = []
            for pos in range(len(parts)):
                token = self._token_converter(parts, pos)
                if token is None:
                    continue
                elif isinstance(token, Undefined):
                    raise WrongParameterException(l_number + 1, parts[pos])
                tokens.append(token)
                if (isinstance(token, Name) and
                        token.group is not None and
                        not pos):
                    self._name_table.add_name(token)
            self._table[l_number + 1] = tokens

        self._analyze_names()

        self._syntax_analyze()

        for name in self._name_table:
            if isinstance(self._name_table[name], Label):
                self._name_table[name].value += Lexer.ORG

        self._math_calculate()

        if verbose:
            print('\nName Table')
            for i in self._name_table:
                print(f'{self._name_table[i]}')
                
            for i in sorted(self._table):
                print('\n', i, end=': ')
                for j in self._table[i]:
                    print(j, j.size, j.allocate, end=', ')
                # print(i, self._table[i])

    def _analyze_names(self):
        for num in sorted(self._table):
            for pos in range(len(self._table[num])):
                if (isinstance(self._table[num][pos], Name) and
                        self._table[num][pos].group is None and
                        self._table[num][pos].name in self._name_table):
                    self._table[num][pos] =\
                        self._name_table[self._table[num][pos].name]

    @staticmethod
    def _token_converter(line: list, pos: int):
        spaces = [Comma, Action, Operand, Name]

        for space in spaces:
            try:
                token = space.is_this(line, pos)
            except IndexError:
                return None
            else:
                if token:
                    return token
        return Undefined()

    @staticmethod
    def _splitter(line: str):
        parts = []

        comment_idx = re.search(r';.*', line)
        if comment_idx:
            line = line[:comment_idx.start(0)]

        while True:
            string = re.search(r"""('.*?')|(".*?")""", line)
            string2 = re.search(r'\(.+\)', line)
            if string:
                parts += line[:string.start()].replace(',',
                                                       ' , ').lower().split()
                parts.append(line[string.start():string.end()])
                line = line[string.end():]

            elif string2:
                parts += line[:string2.start()].replace(',',
                                                        ' , ').lower().split()
                parts.append(line[string2.start():string2.end()])
                line = line[string2.end():]

            else:
                parts += line.replace(',', ' , ').lower().split()
                break

        return parts

    def _syntax_analyze(self):
        address_gen = 0
        for l_num in sorted(self._table):
            for pos in range(len(self._table[l_num])):
                resp = self._table[l_num][pos].syntax_check(l_num, pos,
                                                            self._table[l_num])
                if resp == -1:
                    del self._table[l_num]
                    break
                size = self._table[l_num][pos].size
                if not pos and isinstance(self._table[l_num][pos], Label):
                    self._table[l_num][pos].value = address_gen
                    continue
                elif not pos and isinstance(self._table[l_num][pos], Symbol):
                    continue
                address_gen += size

    def _math_calculate(self):
        for l_num in sorted(self._table):
            for pos in range(len(self._table[l_num])):
                if (isinstance(self._table[l_num][pos], Immediate) and
                        isinstance(self._table[l_num][pos].value, list)):
                    value = self._table[l_num][pos].value
                    for i in range(len(value)):
                        res = self._name_table.get(value[i].lower())
                        if res:
                            value[i] = str(res.value)
                    ev = self._eval(ast.parse(' '.join(value),
                                              mode='eval').body)
                    self._table[l_num][pos].value = ev

        for name in self._name_table:
            if isinstance(self._name_table.get(name).value, list):
                value = self._name_table.get(name).value
                for i in range(len(value)):
                    res = self._name_table.get(value[i].lower())
                    if res:
                        value[i] = str(res.value)
                ev = self._eval(ast.parse(' '.join(value), mode='eval').body)
                self._name_table[name].value = ev

    def _eval(self, node):
        operators = {ast.Add: op.add, ast.Sub: op.sub, ast.USub: op.neg,
                     ast.BitXor: op.xor, ast.BitAnd: op.and_, ast.BitOr: op.or_,
                     ast.LShift: op.lshift, ast.RShift: op.rshift}

        if isinstance(node, ast.Num):   # <number>
            return node.n

        elif isinstance(node, ast.BinOp):   # <left> <operator> <right>
            return operators[type(node.op)](self._eval(node.left), self._eval(node.right))

        elif isinstance(node, ast.UnaryOp):     # <operator> <operand> e.g., -1
            return operators[type(node.op)](self._eval(node.operand))

        else:
            raise TypeError(node)

    def listing_gen(self):
        for l_num, line in self._table.items():
            for pos in range(len(line)):
                try:
                    self.listing += line[pos].generate(line, pos, l_num)
                except AttributeError:
                    raise NameIsNotDefined(l_num, line[pos].name)
        return self.listing

    def listing_to_txt_hex(self):
        text_hex = []
        for i in self.listing:
            text_hex.append(f'{i:02X}')
        return text_hex


def create_parser():
    prs = argparse.ArgumentParser(
        prog='ASM Translator',
        description="""Converting AMS-code to the byte-code
         of 8-bit LogiSim CPU.""",
        usage=""" python lsc8-asm.py <file> [--out|-o <OUT>] [--help|-h] [--verbose|-v]
examples:
        python lsc8-asm.py file.asm
        python lsc8-asm.py file.asm -o file.txt -v""",
        epilog='(c) by baskiton, 2020'
    )
    prs.add_argument('file', type=argparse.FileType(mode='r'),
                     help='Filename with ASM-code')
    prs.add_argument('--out', '-o', type=argparse.FileType(mode='w'),
                     help='Write result to LogiSim file')
    prs.add_argument('--verbose', '-v', action='store_true', default=False,
                     help='Verbose output')

    return prs


if __name__ == '__main__':
    parser = create_parser()
    namespace = parser.parse_args()

    asm_file = namespace.file.read()

    lex = Lexer(asm_file)
    lex.analyze(namespace.verbose)
    lex.listing_gen()
    if namespace.verbose:
        print('\n' + str(lex.listing))

    # Uncomment this to store binary fromat file
    # with open('bin.bin', 'wb') as bin_file:
    #     bin_file.write(bytearray(lex.listing))

    if namespace.out:
        namespace.out.write('v2.0 raw\n')
        namespace.out.write(' '.join(lex.listing_to_txt_hex()))

    if (not namespace.out) or namespace.verbose:
        print('Result:\nv2.0 raw\n' + ' '.join(lex.listing_to_txt_hex()))
