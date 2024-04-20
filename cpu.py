
"""
ARM7 CPU
"""
from elftools.elf.elffile import ELFFile
import struct
import os

# RM7TDMI has 37 registers (31 GPR and 6 SPR)
# https://developer.arm.com/documentation/ddi0210/c/Programmer-s-Model/Registers/The-ARM-state-register-set
REG_COUNT = 17
PC = 15 # holds memory address of next instrucion
CPSR = 16
MEM_SIZE_KB = 512


register = None
memory = None
def reset():
    global register, memory
    register = Register()
    memory = Memory(size=MEM_SIZE_KB * 1024)

def extract_bits(ins, s, e):
    return (ins >> e) & ((1 << (s-e+1))-1)

class Register:
    def __init__(self):
        self.registers = [0]*REG_COUNT
    def __getitem__(self, key):
        return self.registers[key]
    def __setitem__(self, key, value):
        self.registers[key] = value

class Memory:
    def __init__(self, size):
        self.memory = [0] * size  # Initialize memory with zeros
    def write(self, address, data):
        for i, byte in enumerate(data):
            self.memory[address + i] = byte
    def read(self, address, length):
        return self.memory[address:address + length]

from enum import Enum
class ARM7Ops(Enum):
    # Basic ARM instruction set opcodes
    DATA_PROCESSING = 0b00
    LOAD_STORE = 0b01
    BRANCH = 0b10
    CONTROL = 0b11

class Cond(Enum):
    EQ = 0b0000  # Equal
    NE = 0b0001  # Not equal
    CS = 0b0010  # Carry set (same as HS)
    CC = 0b0011  # Carry clear (same as LO)
    MI = 0b0100  # Minus, negative
    PL = 0b0101  # Plus, positive or zero
    VS = 0b0110  # Overflow
    VC = 0b0111  # No overflow
    HI = 0b1000  # Unsigned higher
    LS = 0b1001  # Unsigned lower or same
    GE = 0b1010  # Signed greater than or equal
    LT = 0b1011  # Signed less than
    GT = 0b1100  # Signed greater than
    LE = 0b1101  # Signed less than or equal
    AL = 0b1110  # Always (unconditional)

class DataProcessingOps(Enum):
    # Data processing opcodes (subset)
    AND = 0b0000  # Logical AND
    EOR = 0b0001  # Logical Exclusive OR
    SUB = 0b0010  # Subtract
    RSB = 0b0011  # Reverse Subtract
    ADD = 0b0100  # Add
    ADC = 0b0101  # Add with carry
    SBC = 0b0110  # Subtract with carry
    RSC = 0b0111  # Reverse subtract with carry
    TST = 0b1000  # Test
    TEQ = 0b1001  # Test equivalence
    CMP = 0b1010  # Compare
    CMN = 0b1011  # Compare negative
    ORR = 0b1100  # Logical (inclusive) OR
    MOV = 0b1101  # Move
    BIC = 0b1110  # Bit clear
    MVN = 0b1111  # Move not

# Extending with multiplication as a special instruction opcode
class SpecialOps(Enum):
    MUL = 0b0000  # Multiply

class BranchingOps(Enum):
    # Branching operations with hypothetical binary representations
    B = 0b0000   # Unconditional branch
    BL = 0b0001  # Branch with link
    BX = 0b0010  # Branch and exchange
    BEQ = 0b0011 # Branch if equal
    BNE = 0b0100 # Branch if not equal

def check_condition(cond):
    cond = Cond(cond)
    cpsr = register[CPSR]
    z = (cpsr & (1 << 30)) != 0  # Zero flag
    n = (cpsr & (1 << 31)) != 0  # Negative flag
    c = (cpsr & (1 << 29)) != 0  # Carry flag
    v = (cpsr & (1 << 28)) != 0  # Overflow flag

    if cond == Cond.AL:
        return True
    elif cond == Cond.EQ:
        return z
    elif cond == Cond.NE:
        return not z
    elif cond == Cond.CS:
        return c
    elif cond == Cond.CC:
        return not c
    elif cond == Cond.MI:
        return n
    elif cond == Cond.PL:
        return not n
    elif cond == Cond.VS:
        return v
    elif cond == Cond.VC:
        return not v
    elif cond == Cond.HI:
        return c and not z
    elif cond == Cond.LS:
        return not c or z
    elif cond == Cond.GE:
        return n == v
    elif cond == Cond.LT:
        return n != v
    elif cond == Cond.GT:
        return not z and (n == v)
    elif cond == Cond.LE:
        return z or (n != v)
    else:
        raise ValueError(f"Unknown condition code {Cond(cond).name}")


def calc(opcode, x, y):
    if DataProcessingOps(opcode) == DataProcessingOps.ADD:
        ret = x + y
    elif DataProcessingOps(opcode) == DataProcessingOps.SUB or DataProcessingOps(opcode) == DataProcessingOps.CMP:
        ret = x - y
    elif DataProcessingOps(opcode) == DataProcessingOps.AND: 
        ret = x & y
    elif DataProcessingOps(opcode) == DataProcessingOps.ORR:
        ret = x | y
    elif DataProcessingOps(opcode) == DataProcessingOps.EOR:
        ret = x ^ y
    elif DataProcessingOps(opcode) == DataProcessingOps.MOV:
        ret = y
    else:
        raise Exception(f"{DataProcessingOps(opcode)} missing")
    return ret

def is_branch_instruction(instruction):
    # Mask to extract bits 27-25 and check if they equal 0b101
    if (instruction >> 25 & 0b111) == 0b101:
        return True  # It's a B or BL instruction
    # Check for BX instruction, which is more specific
    elif (instruction >> 4 & 0xFFFFFF) == 0x12FFF1:
        return True  # It's a BX instruction
    return False

def is_swi_instruction(instruction):
    opcode = (instruction >> 24) & 0xFF  # Extract the opcode
    return opcode == 0xEF  # SWI opcode in traditional ARM

def sign_extend(x, l):
  if x >> (l-1) == 1:
    return -((1 << l) - x)
  else:
    return x


def is_load_ins(instruction):
    # Extract bits 27-26 to check if it's a load/store instruction
    # Load/Store instructions generally start with binary '01' in bits 27-26
    if (instruction >> 26 & 0b11) == 0b01 and (instruction >> 20 & 0b1) == 1:
        return True
    return False

def is_store_ins(instruction):
    # Extract bits 27-26 to check if it's a load/store instruction
    if (instruction >> 26 & 0b11) == 0b01 and (instruction >> 20 & 0b1) == 0:
        return True
    return False

def step():
    ins = memory.read(register[PC], 4)
    ins = int.from_bytes(ins, byteorder='little')
    if not ins:
        return False
    print(bin(ins))
    
    cond = extract_bits(ins, 31, 28)
    opcode = extract_bits(ins, 24, 21)
    s_bit = extract_bits(ins, 20, 20)
    i_bit = extract_bits(ins, 25, 25)
    rn = extract_bits(ins, 19, 16)
    rd = extract_bits(ins, 15, 12)

    operand2_is_immediate = i_bit == 1
    operand2 = ins & 0xFFF  # Simplification for illustration

     
    if not check_condition(cond):
        print("Condition not fulfilled")
        new_loc = register[PC] + 4 

    else:
        if is_load_ins(ins):
            new_loc = register[PC] + 4
            print("load", rn, rd)
            data = memory.read(register[rn], 4)
            print("loaded:", int.from_bytes(data, byteorder='little'))
            register[rd] = int.from_bytes(data, byteorder='little') 
            pass
        elif is_store_ins(ins):
            new_loc = register[PC] + 4
            print("store", rn, rd)
            memory.write(register[rn], struct.pack("B",register[rd]))
            pass
        elif is_swi_instruction(ins):
            print("System interupt")
            return False
        elif is_branch_instruction(ins):
            offset = extract_bits(ins, 24, 0)
            offset <<= 2
            if offset & (1 << 25):  # Check if the sign bit is set after the shift
                offset -= (1 << 26)  # Extend the sign to 32 bits

            new_loc = register[PC] + offset + 8
            print("Branched to: 0x{:X}".format(new_loc))

        #     print(f"Condition: {Cond(cond).name}, Opcode: {BranchingOps(opcode).name}, S_bit: {s_bit}, "
        #     f"Rn: {rn}, Rd: {rd}, Rs: {rs}, Rm,: {rm} Operand2 is Immediate: {operand2_is_immediate}, Operand2: {operand2}")
            
        else:
            is_mult = extract_bits(ins, 31, 26) == 56 and extract_bits(ins, 7, 4) == 9
            new_loc = register[PC] + 4
            if is_mult:
                rs = extract_bits(ins, 11, 8)
                rm = extract_bits(ins, 3, 0)

                #IMMEDIATE VALUE
                register[rn] = register[rs] * register[rm]

                print(f"Condition: {Cond(cond).name}, Opcode: {SpecialOps(opcode).name}, S_bit: {s_bit}, "
                f"Rn: {rn}, Rd: {rd}, Rs: {rs}, Rm,: {rm} Operand2 is Immediate: {operand2_is_immediate}, Operand2: {operand2}")
            else:
                print(f"Condition: {Cond(cond).name}, Opcode: {DataProcessingOps(opcode).name}, S_bit: {s_bit}, "
                f"Rn: {rn}, Rd: {rd}, Operand2 is Immediate: {operand2_is_immediate}, Operand2: {operand2}")

                if operand2_is_immediate:
                    res = calc(opcode, register[rn], operand2)
                else:
                    res = calc(opcode, register[rn], register[operand2])
                if s_bit == 1:

                    flag_Z = (res == 0)
            
                    # Update Negative Flag (N)
                    flag_N = (res < 0)
                    
                    # # Update Carry Flag (C) - In actual hardware, this might be more complex
                    # flags['C'] = (value1 < value2)
                    
                    # # Update Overflow Flag (V) - This considers signed overflow
                    # flags['V'] = ((value1 < 0) != (value2 < 0)) and ((result < 0) != (value1 < 0))

                    print("flags:", flag_N, flag_Z)
                    if flag_Z:
                        register[CPSR] |= (1 << 30)  # Set the Zero flag if res is zero
                    else:
                        register[CPSR] &= ~(1 << 30) # Clear the Zero flag if res is not zero

                    if flag_N:
                        register[CPSR] |= (1 << 31)  # Set the Negative flag if res is negative
                    else:
                        register[CPSR] &= ~(1 << 31) # Clear the Negative flag if res is not negative

            
                if DataProcessingOps(opcode) != DataProcessingOps.CMP:
                    register[rd] = res


    register[PC] = new_loc
    return True

if __name__ == "__main__":
    reset()
    # load elf
    for filename in os.listdir('tests/'):
        if not filename.endswith(".elf"):
                continue
        with open(f"tests/{filename}", 'rb') as file:
            print("")
            print("-----------------------------------------")
            print("Next test:", filename)
            print()
            elf = ELFFile(file)
            # # Print ELF file header information
            # print("ELF File Header:")
            # for field in elf.header:
            #     print(f"  {field}: {elf.header[field]}")
            # print("\nSections:")
            # for section in elf.iter_sections():
            #     print(f"  Name: {section.name}, Type: {section['sh_type']}")
            # write the content to memory
            for segment in elf.iter_segments():
                if segment['p_type'] == 'PT_LOAD':
                    # This is a loadable segment; copy its data into memory
                    segment_data = segment.data()
                    memory_address = segment['p_paddr']
                    memory.write(memory_address, segment_data)
            register[PC] = elf.header.e_entry

        ins = 0
        print("registers:", register.registers)
        while step():
            ins += 1
            print("registers:", register.registers)
            # if ins > 20:
            #     break
        print(ins) 
        assert register[0] == 1
        reset()
            
        