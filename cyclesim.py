import os
import argparse
MemSize = 1000 # memory size, in reality, the memory size should be 2^32, but for this lab, for the space resaon, we keep it as this large number, but the memory is still 32-bit addressable.

def calculatePerformance():
    instruction_count = len(ssCore.ext_imem.IMem) / 4
    filePath = ssCore.baseioDir + "PerformanceMetrics_Result.txt"
    with open(filePath, 'w') as f:
        f.write(f'\nSingle Stage Core Performance Metrics-----------------------------\n')
        f.write(f'Number of cycles taken: {ssCore.cycle}\n')
        f.write(f'Cycles per instruction: {ssCore.cycle / instruction_count}\n')
        f.write(f'Instructions per cycle: {instruction_count / ssCore.cycle}\n')

        f.write(f'\nFive Stage Core Performance Metrics-----------------------------\n')
        f.write(f'Number of cycles taken: {fsCore.cycle}\n')
        f.write(f'Cycles per instruction: {fsCore.cycle / instruction_count}\n')
        f.write(f'Instructions per cycle: {instruction_count / fsCore.cycle}\n')

def twos_complement(val, bits):
    if (val & (1 << (bits - 1))) != 0:
        val = val - (1 << bits)
    return val
    
def twos_complement_string(s):
    s = list(s)
    for i in range(len(s)):
        if s[i] == '0':
            s[i] = '1'
        else:
            s[i] = '0'
    return '{:032b}'.format(int(''.join(s), 2) + 1)

def r_type_id(currState, nextState, register_file, memory):
    rd = currState.ID["Instr"][-12:-7]
    func3 = currState.ID["Instr"][-15:-12]
    rs1 = currState.ID["Instr"][-20:-15]
    rs2 = currState.ID["Instr"][-25:-20]
    func7 = currState.ID["Instr"][:-25]

    #-------------------------------Forwarding logic-----------------------------------
    # Forward for all instructions except for the load value
    # Forwarding from MEM Stage
    if rs1 == nextState.WB["DestReg"] and nextState.WB["WBEnable"]:
        nextState.EX["Operand1"] = nextState.WB["Wrt_data"]
    # Forwarding from EX Stage
    elif rs1 == nextState.MEM["DestReg"] and (nextState.MEM["WrDMem"] == 1 or nextState.MEM["RdDMem"] != 1):
        nextState.EX["Operand1"] = nextState.MEM["ALUresult"]
    elif rs1 == currState.EX["DestReg"] and currState.EX["RdDMem"]:
        nextState.IF["PC"] = currState.IF["PC"]
        return
    else:
        nextState.EX["Operand1"] = register_file.readRF(rs1)

    # Forwarding from MEM Stage
    if rs2 == nextState.WB["DestReg"] and nextState.WB["WBEnable"]:
        nextState.EX["Operand2"] = nextState.WB["Wrt_data"]
    # Forwarding from EX Stage
    elif rs2 == nextState.MEM["DestReg"] and (nextState.MEM["WrDMem"] == 1 or nextState.MEM["RdDMem"] != 1):
        nextState.EX["Operand2"] = nextState.MEM["ALUresult"]
    elif rs2 == currState.EX["DestReg"] and currState.EX["RdDMem"]:
        nextState.IF["PC"] = currState.IF["PC"]
        return
    else:
        nextState.EX["Operand2"] = register_file.readRF(rs2)

    #------------------------------------------------------------------

    nextState.EX["DestReg"] = rd
    # SUB
    if func3 == "000" and func7 == "0100000":
        nextState.EX["AluControlInput"] = "0110"
    # ADD
    elif func3 == "000" and func7 == "0000000":
        nextState.EX["AluControlInput"] = "0010"
    # XOR
    elif func3 == "100" and func7 == "0000000":
        nextState.EX["AluControlInput"] = "0011"
    # OR
    elif func3 == "110" and func7 == "0000000":
        nextState.EX["AluControlInput"] = "0001"
    # AND
    elif func3 == "111" and func7 == "0000000":
        nextState.EX["AluControlInput"] = "0000"

    nextState.EX["mux_out1"] = nextState.EX["Operand1"]
    nextState.EX["mux_out2"] = nextState.EX["Operand2"]
    nextState.EX["RdDMem"] = 0
    nextState.EX["WrDMem"] = 0
    nextState.EX["WBEnable"] = 1

    # Setting PC
    nextState.IF["PC"] = currState.IF["PC"] + 4


def i_type_id(currState, nextState, register_file, memory):
    # Decoding the different bits
    opcode = currState.ID["Instr"][-7:]
    rd = currState.ID["Instr"][-12:-7]
    func3 = currState.ID["Instr"][-15:-12]
    rs1 = currState.ID["Instr"][-20:-15]
    imm = currState.ID["Instr"][:-20]

    #-------------------------------Forwarding logic-----------------------------------
    # Forward for all instructions except for the load value
    # Forwarding from the MEM Stage
    if rs1 == nextState.WB["DestReg"] and nextState.WB["WBEnable"]:
        nextState.EX["Operand1"] = nextState.WB["Wrt_data"]
    # Forwarding from EX Stage
    elif rs1 == nextState.MEM["DestReg"] and (nextState.MEM["WrDMem"] == 1 or nextState.MEM["RdDMem"] != 1):
        nextState.EX["Operand1"] = nextState.MEM["ALUresult"]
    elif rs1 == currState.EX["DestReg"] and currState.MEM["RdDMem"]:
        nextState.IF["PC"] = currState.IF["PC"]
        return
    else:
        nextState.EX["Operand1"] = register_file.readRF(rs1)

    #------------------------------------------------------------------

    nextState.EX["Imm"] = twos_complement(int(imm,2), 12)
    nextState.EX["DestReg"] = rd
    nextState.EX["is_I_type"] = 1
    nextState.EX["AluOperation"] = "00"
    nextState.EX["mux_out1"] = nextState.EX["Operand1"]
    nextState.EX["RdDMem"] = 0
    nextState.EX["WrDMem"] = 0
    nextState.EX["WBEnable"] = 1

    # Read signal set to 1 for I type
    if opcode == "0000011":
        nextState.EX["RdDMem"] = 1

    # the immediate register to become 32 bits
    diff_len = 32 - len(imm)
    nextState.EX["mux_out2"] = imm[0]*diff_len + imm

    # Load
    if opcode == "0000011":   
        nextState.EX["AluControlInput"] = "0010"
    # ADDI
    elif func3 == "000":
        nextState.EX["AluControlInput"] = "0010"
    #XORI
    elif func3 == "100":
        nextState.EX["AluControlInput"] = "0011"
    #ORI
    elif func3 == "110":
        nextState.EX["AluControlInput"] = "0001"
    #ANDI
    elif func3 == "111":
        nextState.EX["AluControlInput"] = "0000"

    # Setting PC
    nextState.IF["PC"] = currState.IF["PC"] + 4


def s_type_id(currState, nextState, register_file, memory):

    imm1 = currState.ID["Instr"][-12:-7]
    rs1 = currState.ID["Instr"][-20:-15]
    rs2 = currState.ID["Instr"][-25:-20]
    imm2 = currState.ID["Instr"][:-25]
    imm = imm2 + imm1

    #-------------------------------Forwarding logic-----------------------------------
    # Forward for all instructions except for the load value
    # Forwarding from the MEM stage
    if rs1 == nextState.WB["DestReg"] and nextState.WB["WBEnable"]:
        nextState.EX["Operand1"] = nextState.WB["Wrt_data"]
    # Forwarding from the EX stage
    elif rs1 == nextState.MEM["DestReg"] and (nextState.MEM["WrDMem"] == 1 or nextState.MEM["RdDMem"] != 1):
        nextState.EX["Operand1"] = nextState.MEM["ALUresult"]
    elif rs1 == currState.EX["DestReg"] and currState.MEM["RdDMem"]:
        nextState.IF["PC"] = currState.IF["PC"]
        return

    else:
        nextState.EX["Operand1"] = register_file.readRF(rs1)

    #------------------------------------------------------------------

    nextState.EX["DestReg"] = rs2
    nextState.EX["is_I_type"] = 1
    nextState.EX["WBEnable"] = 0
    nextState.EX["RdDMem"] = 0
    nextState.EX["WrDMem"] = 1
    nextState.EX["AluControlInput"] = "0010"
    nextState.EX["mux_out1"] = nextState.EX["Operand1"]
    diff_len = 32 - len(imm)
    nextState.EX["mux_out2"] = imm[0]*diff_len + imm
    nextState.EX["Imm"] = nextState.EX["mux_out2"]
    # PC = PC + 4
    nextState.IF["PC"] = currState.IF["PC"] + 4


def j_type_id(currState, nextState, register_file, memory):
    # Decode the different bits
    opcode = currState.ID["Instr"][-7:]
    rd = currState.ID["Instr"][-12:-7]
    imm = currState.ID["Instr"][0] + currState.ID["Instr"][12:20] + currState.ID["Instr"][11:12] + currState.ID["Instr"][1:11]
    nextState.EX["Imm"] = imm
    currState.IF["branch"] = 1
    nextState.IF["jump"] = 1
    nextState.EX["DestReg"] = rd
    nextState.EX["RdDMem"] = 0
    nextState.EX["WrDMem"] = 0
    nextState.EX["WBEnable"] = 1

    # jump instruction
    nextState.EX["Operand1"] = get_bitstring('{:032b}'.format(currState.ID["PC"]))
    nextState.EX["Operand2"] = get_bitstring('{:032b}'.format(4))
    nextState.EX["mux_out1"] = nextState.EX["Operand1"]
    nextState.EX["mux_out2"] = nextState.EX["Operand2"]
    nextState.EX["AluControlInput"] = "0010"
    imm = [
        (int(nextState.EX["Imm"], 2) << 1),
        (int(twos_complement_string(nextState.EX["Imm"]), 2) << 1) * -1
    ][nextState.EX["Imm"][0] == '1']
    nextState.IF["PC"] = currState.ID["PC"] + imm


def b_type_id(currState, nextState, register_file, memory):
    # Decode the different bits
    imm = currState.ID["Instr"][0] + currState.ID["Instr"][-8] + currState.ID["Instr"][1:-25] + currState.ID["Instr"][-12:-8]
    opcode = currState.ID["Instr"][-7:]
    func3 = currState.ID["Instr"][-15:-12]
    rs1 = currState.ID["Instr"][-20:-15]
    rs2 = currState.ID["Instr"][-25:-20]

    #-------------------------------Forwarding logic-----------------------------------
    # Forward for all instructions except for the load value
    if rs1 == nextState.WB["DestReg"] and nextState.WB["WBEnable"]:
        nextState.EX["Operand1"] = nextState.WB["Wrt_data"]
    # From EX stage
    elif rs1 == nextState.MEM["DestReg"] and (nextState.MEM["WrDMem"] == 1 or nextState.MEM["RdDMem"] != 1):
        nextState.EX["Operand1"] = nextState.MEM["ALUresult"]

    elif rs1 == currState.EX["DestReg"] and currState.EX["RdDMem"]:
        nextState.IF["PC"] = currState.IF["PC"]
        return

    else:
        nextState.EX["Operand1"] = register_file.readRF(rs1)
    # Forwarding from MEM Stage
    if rs2 == nextState.WB["DestReg"] and nextState.WB["WBEnable"]:
        nextState.EX["Operand2"] = nextState.WB["Wrt_data"]
    # Forwarding from EX Stage
    elif rs2 == nextState.MEM["DestReg"] and (nextState.MEM["WrDMem"] == 1 or nextState.MEM["RdDMem"] != 1):
        nextState.EX["Operand2"] = nextState.MEM["ALUresult"]

    elif rs2 == currState.EX["DestReg"] and currState.EX["RdDMem"]:
        nextState.IF["PC"] = currState.IF["PC"]
        return
    else:
        nextState.EX["Operand2"] = register_file.readRF(rs2)

    #------------------------------------------------------------------

    nextState.EX["Imm"] = imm
    nextState.EX["mux_out1"] = nextState.EX["Operand1"]
    nextState.EX["mux_out2"] = nextState.EX["Operand2"]
    AluControlInput = currState.ID["Instr"][17:20]

    # Branching Logic
    # BEQ
    if AluControlInput == "000":
        if nextState.EX["mux_out1"] == nextState.EX["mux_out2"]:
            imm = [
                (int(nextState.EX["Imm"], 2) << 1),
                (int(twos_complement_string(nextState.EX["Imm"]), 2) << 1) * -1
            ][nextState.EX["Imm"][0] == '1']

            curr_pc = currState.ID["PC"] + imm
            nextState.IF["PC"] = curr_pc
            currState.IF["branch"] = 1
            nextState.IF["jump"] = 1
        else:
            nextState.IF["PC"] = currState.IF["PC"] + 4
    # BNE
    elif AluControlInput == "001":
        if nextState.EX["mux_out1"] != nextState.EX["mux_out2"]:
            imm = [
                (int(nextState.EX["Imm"], 2) << 1),
                (int(twos_complement_string(nextState.EX["Imm"]), 2) << 1) * -1
            ][nextState.EX["Imm"][0] == '1']
            curr_pc = currState.ID["PC"] + imm
            nextState.IF["PC"] = curr_pc
            currState.IF["branch"] = 1
            nextState.IF["jump"] = 1
        else:
            nextState.IF["PC"] = currState.IF["PC"] + 4

def get_bitstring(s):
    if '-' in s:
        return s
    return s[-1: -33: -1][::-1]

class InsMem(object):
    def __init__(self, name, ioDir):
        self.id = name

        with open(ioDir + "imem.txt") as im:
            self.IMem = [data.replace("\n", "") for data in im.readlines()]

    def readInstr(self, ReadAddress):
        #read instruction memory
        #return 32 bit hex val
        return "".join([i for idx,i in enumerate(self.IMem) if (idx >= ReadAddress) and (idx < ReadAddress + 4)])


class DataMem(object):
    def __init__(self, name, ioDir):
        self.id = name
        self.ioDir = ioDir
        with open(ioDir + "dmem.txt") as dm:
            self.DMem = [data.replace("\n", "") for data in dm.readlines()]

    def readMem(self, ReadAddress):
        #read data memory
        #return 32 bit hex val
        return "".join([i for idx,i in enumerate(self.DMem) if (idx >= ReadAddress) and (idx < ReadAddress + 4)])

    def divideString(self, s, k, fill):
        l=[]
        if len(s) % k != 0:
            s += fill * (k - len(s) % k)
        for i in range(0, len(s), k):
            l.append(s[i:i + k])
        return l

    def writeDataMem(self, Address, WriteData):
        # write data into byte addressable memory
        curr_len = len(self.DMem)
        if int(Address,2) > curr_len:
            to_append = int(Address,2) - curr_len
            self.DMem += ["00000000"]*to_append
        curr_len = len(self.DMem)
        bits_split = 8
        fill_remain = "0"
        array = self.divideString(WriteData, bits_split, fill_remain)

        array_counter = 0
        for i in range(int(Address,2),int(Address,2)+4):
            if i >= curr_len:
                self.DMem.append(array[array_counter])
            else:
                self.DMem[i] = array[array_counter]
            array_counter += 1

    def outputDataMem(self):
        curr_len = len(self.DMem)
        if 1000 > curr_len:
            to_append = 1000 - curr_len
            self.DMem += ["00000000"]*to_append
        resPath = self.ioDir + "" + self.id + "_DMEMResult.txt"
        with open(resPath, "w") as rp:
            rp.writelines([str(data) + "\n" for data in self.DMem])


class RegisterFile(object):
    def __init__(self, ioDir):
        self.outputFile = ioDir + "RFResult.txt"
        self.Registers = ["00000000000000000000000000000000" for i in range(32)]

    def readRF(self, Reg_addr):
        # Fill in
        return self.Registers[int(Reg_addr,2)]

    def writeRF(self, Reg_addr, Wrt_reg_data):
        # Fill in
        if int(Reg_addr, 2):
            self.Registers[int(Reg_addr,2)] = Wrt_reg_data

    def outputRF(self, cycle):
        op = ["State of RF after executing cycle:\t" + str(cycle) + "\n"]
        op.extend([str(val) + "\n" for val in self.Registers])
        if(cycle == 0): perm = "w"
        else: perm = "a"
        with open(self.outputFile, perm) as file:
            file.writelines(op)

class State(object):
    def __init__(self):
        self.IF = {"nop": False, "PC": 0, "branch":0, "jump":0}
        self.ID = {"nop": False, "Instr": 0, "PC": 0, "branch":0, "jump":0}
        self.EX = {"nop": False, "Operand1": 0, "Operand1": 0, "Imm": 0,
                   "mux_out1": 0, "mux_out2": 0, "DestReg": 0,
                   "is_I_type": False, "RdDMem": 0, "WrDMem": 0,
                   "AluOperation": 0, "WBEnable": 0, "PC": 0, "branch":0,
                   "AluControlInput": 0, "jump":0}
        self.MEM = {"nop": False, "ALUresult": 0, "Store_data": 0, "Rs": 0,
                   "Rt": 0, "DestReg": 0, "RdDMem": 0, "WrDMem": 0,
                   "WBEnable": 0, "PC": 0, "branch":0, "jump":0}
        self.WB = {"nop": False, "Wrt_data": 0, "Rs": 0, "Rt": 0, "DestReg": 0,
                   "WBEnable": 0, "PC": 0, "branch":0, "jump":0}


class Core(object):

    def __init__(self, ioDir, baseioDir, imem, dmem):
        self.myRF = RegisterFile(ioDir)
        self.cycle = 0
        self.halted = False
        self.ioDir = ioDir
        self.state = State()
        self.nextState = State()
        self.ext_imem = imem
        self.ext_dmem = dmem
        self.baseioDir = baseioDir
        

class SingleStageCore(Core):
    def __init__(self, ioDir, imem, dmem):
        super(SingleStageCore, self).__init__(ioDir + "SS_", ioDir, imem, dmem)
        self.opFilePath = ioDir + "StateResult_SS.txt"


    def step(self):
        # Your implementation
        if self.state.IF["nop"]:
            self.halted = True
        # ----------------------------- IF stage -------------------------------

        if self.state.IF["branch"] == 0:
            if (self.state.IF["PC"] != self.nextState.IF["PC"] or self.state.IF["PC"]==0):
                self.nextState.ID["Instr"] = self.ext_imem.readInstr(int(self.state.IF["PC"]))
                self.nextState.ID["PC"] = self.state.IF["PC"]
            else:
                self.nextState.ID["Instr"] = self.state.ID["Instr"]
        if (self.cycle == 0 and self.state.IF["nop"] == False) or self.state.IF["jump"]:
            self.nextState.IF["PC"] = self.state.IF["PC"] + 4
        self.nextState.IF["PC"] = self.state.IF["PC"]
        self.state = self.nextState

        # ----------------------------- ID stage -------------------------------

        if self.state.ID["Instr"]:
            # R Type
            if self.state.ID["Instr"][-7:] == "0110011":
                r_type_id(self.state, self.nextState, self.myRF, self.ext_dmem)
                self.nextState.EX["nop"] = False

            # I Type
            elif (self.state.ID["Instr"][-7:] == "0010011") or (self.state.ID["Instr"][-7:] == "0000011"):
                i_type_id(self.state, self.nextState, self.myRF, self.ext_dmem)
                self.nextState.EX["nop"] = False

           # S Type
            elif self.state.ID["Instr"][-7:] == "0100011":
                s_type_id(self.state, self.nextState, self.myRF, self.ext_dmem)
                self.nextState.EX["nop"] = False

            # J Type
            elif self.state.ID["Instr"][-7:] == "1101111":
                j_type_id(self.state, self.nextState, self.myRF, self.ext_dmem)

             # B Type
            elif self.state.ID["Instr"][-7:] == "1100011":
                b_type_id(self.state, self.nextState, self.myRF, self.ext_dmem)
 
            # Halt
            elif self.state.ID["Instr"][-7:] == "1111111":
                self.nextState.IF["nop"] = True
                self.nextState.ID["nop"] = True
                self.nextState.EX["nop"] = True
                self.nextState.IF["PC"] = self.state.IF["PC"]
            else:
                self.nextState.IF["PC"] = self.state.IF["PC"] + 4
                self.nextState.EX["PC"] = self.state.ID["PC"]
        else:
            self.nextState.EX["nop"] = True


        
        self.state = self.nextState

        # ----------------------------- EX stage -------------------------------

        # move the instructions to the next state
        self.nextState.IF["nop"] = self.state.IF["nop"]
        self.nextState.ID["nop"] = self.state.ID["nop"]
        self.nextState.EX["nop"] = self.state.EX["nop"]
        self.nextState.MEM["nop"] = self.state.IF["nop"]
        self.nextState.MEM["DestReg"] = self.state.EX["DestReg"]
        self.nextState.MEM["WBEnable"] = self.state.EX["WBEnable"]
        self.nextState.MEM["RdDMem"] = self.state.EX["RdDMem"]
        self.nextState.MEM["WrDMem"] = self.state.EX["WrDMem"]

        # AND operation
        if self.state.EX["AluControlInput"] == "0000":
            res = ""
            for i in range(len(self.state.EX["mux_out1"])):
                res = res + str(int(self.state.EX["mux_out1"][i]) & int(self.state.EX["mux_out2"][i]))
            self.nextState.MEM["ALUresult"] = get_bitstring('{:032b}'.format(int(res,2)))
            self.nextState.MEM["nop"] = False
        
        # XOR operation
        elif self.state.EX["AluControlInput"] == "0001":
            res = ""
            for i in range(len(self.state.EX["mux_out1"])):
                res = res + str(int(self.state.EX["mux_out1"][i]) or int(self.state.EX["mux_out2"][i]))

            self.nextState.MEM["ALUresult"] = get_bitstring('{:032b}'.format(int(res,2)))
            self.nextState.MEM["nop"] = False

        # ADD operation
        elif self.state.EX["AluControlInput"] == "0010":
            self.nextState.MEM["ALUresult"] = get_bitstring('{:032b}'.format(int(self.state.EX["mux_out1"],2) + int(self.state.EX["mux_out2"],2)))
            self.nextState.MEM["nop"] = False

        # SUB operation
        elif self.state.EX["AluControlInput"] == "0110":
            self.nextState.MEM["ALUresult"] = get_bitstring('{:032b}'.format(int(self.state.EX["mux_out1"],2) + int(twos_complement_string(self.state.EX["mux_out2"]), 2)))
            self.nextState.MEM["nop"] = False

        # OR operation
        elif self.state.EX["AluControlInput"] == "0011":
            self.nextState.MEM["ALUresult"] = get_bitstring('{:032b}'.format(int(self.state.EX["mux_out1"],2) ^ int(self.state.EX["mux_out2"],2)))
            self.nextState.MEM["nop"] = False
        else:
            self.nextState.MEM["nop"] = True

        self.state = self.nextState

        # ----------------------------- MEM stage ------------------------------
        
        self.nextState.IF["nop"] = self.state.IF["nop"]
        self.nextState.ID["nop"] = self.state.ID["nop"]
        self.nextState.EX["nop"] = self.state.EX["nop"] 
        self.nextState.MEM["nop"] = self.state.MEM["nop"]
        self.nextState.WB["nop"] = self.state.MEM["nop"]
        if self.state.MEM["WrDMem"] == 1:
            self.ext_dmem.writeDataMem(self.state.MEM["ALUresult"], self.myRF.readRF(self.state.MEM["DestReg"]))
            self.nextState.WB["WBEnable"] = 0
        elif self.state.MEM["RdDMem"] or self.state.MEM["WBEnable"]:
            if self.state.MEM["RdDMem"] == 1:
                self.nextState.WB["Wrt_data"] = self.ext_dmem.readMem(int(self.state.MEM["ALUresult"], 2))
            else:
                self.nextState.WB["Wrt_data"] = self.state.MEM["ALUresult"]

            self.nextState.WB["WBEnable"] = 1
            self.nextState.WB["DestReg"] = self.state.MEM["DestReg"]
        else:
            self.nextState.WB["nop"] = True
        self.nextState.WB["PC"] = self.state.MEM["PC"]
        self.state = self.nextState

        # ----------------------------- WB stage -------------------------------

        self.nextState.IF["nop"] = self.state.IF["nop"]
        self.nextState.ID["nop"] = self.state.ID["nop"]
        self.nextState.EX["nop"] = self.state.EX["nop"]
        self.nextState.MEM["nop"] = self.state.MEM["nop"]
        self.nextState.WB["nop"] = self.state.WB["nop"]
        if self.state.WB["WBEnable"]:
            self.myRF.writeRF(self.state.WB["DestReg"], self.state.WB["Wrt_data"])

        self.state = State()
        self.state.IF["PC"] = self.nextState.IF["PC"]
        self.state.IF["nop"] = self.nextState.IF["nop"]
        self.myRF.outputRF(self.cycle) # dump RF
        self.printState(self.nextState, self.cycle) # print states after executing cycle 0, cycle 1, cycle 2 ...

        # self.state = self.nextState #The end of the cycle and updates the current state with the values calculated in this cycle
        self.nextState = State()
        self.cycle += 1

    def printState(self, state, cycle):
        printstate = ["State after executing cycle:\t" + str(cycle) + "\n"]
        printstate.append("IF.PC:\t" + str(state.IF["PC"]) + "\n")
        printstate.append("IF.nop:\t" + str(int(state.IF["nop"])) + "\n")

        if(cycle == 0): perm = "w"
        else: perm = "a"
        with open(self.opFilePath, perm) as wf:
            wf.writelines(printstate)


class FiveStageCore(Core):
    def __init__(self, ioDir, imem, dmem):
        super(FiveStageCore, self).__init__(ioDir + "FS_", ioDir, imem, dmem)
        self.opFilePath = ioDir + "StateResult_FS.txt"


    def step(self):
        # Your implementation
        if self.state.IF["nop"] and self.state.ID["nop"] and self.state.EX["nop"] and self.state.MEM["nop"] and self.state.WB["nop"]:
            self.halted = True

        # ----------------------------- WB stage -----------------------------
        
        self.nextState.IF["nop"] = self.state.IF["nop"]
        self.nextState.ID["nop"] = self.state.ID["nop"]
        self.nextState.EX["nop"] = self.state.EX["nop"]
        self.nextState.MEM["nop"] = self.state.MEM["nop"]
        self.nextState.WB["nop"] = self.state.WB["nop"]
        if self.state.WB["WBEnable"]:
            self.myRF.writeRF(self.state.WB["DestReg"], self.state.WB["Wrt_data"])

       # ----------------------------- MEM stage ------------------------------
        self.nextState.IF["nop"] = self.state.IF["nop"]
        self.nextState.ID["nop"] = self.state.ID["nop"]
        self.nextState.EX["nop"] = self.state.EX["nop"] 
        self.nextState.MEM["nop"] = self.state.MEM["nop"]
        self.nextState.WB["nop"] = self.state.MEM["nop"]
        if self.state.MEM["WrDMem"] == 1:
            self.ext_dmem.writeDataMem(self.state.MEM["ALUresult"], self.myRF.readRF(self.state.MEM["DestReg"]))
            self.nextState.WB["WBEnable"] = 0
        elif self.state.MEM["RdDMem"] or self.state.MEM["WBEnable"]:
            if self.state.MEM["RdDMem"] == 1:
                self.nextState.WB["Wrt_data"] = self.ext_dmem.readMem(int(self.state.MEM["ALUresult"], 2))
            else:
                self.nextState.WB["Wrt_data"] = self.state.MEM["ALUresult"]

            self.nextState.WB["WBEnable"] = 1
            self.nextState.WB["DestReg"] = self.state.MEM["DestReg"]
        else:
            self.nextState.WB["nop"] = True
        self.nextState.WB["PC"] = self.state.MEM["PC"]


        # ----------------------------- EX stage -----------------------------
            # move the instructions to the next state
        self.nextState.IF["nop"] = self.state.IF["nop"]
        self.nextState.ID["nop"] = self.state.ID["nop"]
        self.nextState.EX["nop"] = self.state.EX["nop"]
        self.nextState.MEM["nop"] = self.state.IF["nop"]
        self.nextState.MEM["DestReg"] = self.state.EX["DestReg"]
        self.nextState.MEM["WBEnable"] = self.state.EX["WBEnable"]
        self.nextState.MEM["RdDMem"] = self.state.EX["RdDMem"]
        self.nextState.MEM["WrDMem"] = self.state.EX["WrDMem"]

        # AND operation
        if self.state.EX["AluControlInput"] == "0000":
            res = ""
            for i in range(len(self.state.EX["mux_out1"])):
                res = res + str(int(self.state.EX["mux_out1"][i]) & int(self.state.EX["mux_out2"][i]))
            self.nextState.MEM["ALUresult"] = get_bitstring('{:032b}'.format(int(res,2)))
            self.nextState.MEM["nop"] = False
        
        # XOR operation
        elif self.state.EX["AluControlInput"] == "0001":
            res = ""
            for i in range(len(self.state.EX["mux_out1"])):
                res = res + str(int(self.state.EX["mux_out1"][i]) or int(self.state.EX["mux_out2"][i]))

            self.nextState.MEM["ALUresult"] = get_bitstring('{:032b}'.format(int(res,2)))
            self.nextState.MEM["nop"] = False

        # ADD operation
        elif self.state.EX["AluControlInput"] == "0010":
            self.nextState.MEM["ALUresult"] = get_bitstring('{:032b}'.format(int(self.state.EX["mux_out1"],2) + int(self.state.EX["mux_out2"],2)))
            self.nextState.MEM["nop"] = False

        # SUB operation
        elif self.state.EX["AluControlInput"] == "0110":
            self.nextState.MEM["ALUresult"] = get_bitstring('{:032b}'.format(int(self.state.EX["mux_out1"],2) + int(twos_complement_string(self.state.EX["mux_out2"]), 2)))
            self.nextState.MEM["nop"] = False

        # OR operation
        elif self.state.EX["AluControlInput"] == "0011":
            self.nextState.MEM["ALUresult"] = get_bitstring('{:032b}'.format(int(self.state.EX["mux_out1"],2) ^ int(self.state.EX["mux_out2"],2)))
            self.nextState.MEM["nop"] = False
        else:
            self.nextState.MEM["nop"] = True

        # ----------------------------- ID stage -----------------------------
        
        if self.state.ID["Instr"]:
            # R Type
            if self.state.ID["Instr"][-7:] == "0110011":
                r_type_id(self.state, self.nextState, self.myRF, self.ext_dmem)
                self.nextState.EX["nop"] = False

            # I Type
            elif (self.state.ID["Instr"][-7:] == "0010011") or (self.state.ID["Instr"][-7:] == "0000011"):
                i_type_id(self.state, self.nextState, self.myRF, self.ext_dmem)
                self.nextState.EX["nop"] = False

           # S Type
            elif self.state.ID["Instr"][-7:] == "0100011":
                s_type_id(self.state, self.nextState, self.myRF, self.ext_dmem)
                self.nextState.EX["nop"] = False

            # J Type
            elif self.state.ID["Instr"][-7:] == "1101111":
                j_type_id(self.state, self.nextState, self.myRF, self.ext_dmem)

             # B Type
            elif self.state.ID["Instr"][-7:] == "1100011":
                b_type_id(self.state, self.nextState, self.myRF, self.ext_dmem)
 
            # Halt
            elif self.state.ID["Instr"][-7:] == "1111111":
                self.nextState.IF["nop"] = True
                self.nextState.ID["nop"] = True
                self.nextState.EX["nop"] = True
                self.nextState.IF["PC"] = self.state.IF["PC"]
            else:
                self.nextState.IF["PC"] = self.state.IF["PC"] + 4
                self.nextState.EX["PC"] = self.state.ID["PC"]
        else:
            self.nextState.EX["nop"] = True

        # ----------------------------- IF stage -----------------------------
        if self.state.IF["branch"] == 0:
            if (self.state.IF["PC"] != self.nextState.IF["PC"] or self.state.IF["PC"]==0):
                self.nextState.ID["Instr"] = self.ext_imem.readInstr(int(self.state.IF["PC"]))
                self.nextState.ID["PC"] = self.state.IF["PC"]
            else:
                self.nextState.ID["Instr"] = self.state.ID["Instr"]

        if (self.cycle == 0 and self.state.IF["nop"] == False) or self.state.IF["jump"]:
            self.nextState.IF["PC"] = self.state.IF["PC"] + 4
        
        
        self.myRF.outputRF(self.cycle) # dump RF
        self.printState(self.nextState, self.cycle) 
        self.state = self.nextState 
        self.nextState = State()
        self.cycle += 1

    def printState(self, state, cycle):
        printstate = ["-"*70+"\n", "State after executing cycle: " + str(cycle) + "\n"]
        printstate.extend(["IF." + key + ": " + str(val) + "\n" for key, val in state.IF.items()])
        printstate.extend(["ID." + key + ": " + str(val) + "\n" for key, val in state.ID.items()])
        printstate.extend(["EX." + key + ": " + str(val) + "\n" for key, val in state.EX.items()])
        printstate.extend(["MEM." + key + ": " + str(val) + "\n" for key, val in state.MEM.items()])
        printstate.extend(["WB." + key + ": " + str(val) + "\n" for key, val in state.WB.items()])

        if(cycle == 0): perm = "w"
        else: perm = "a"
        with open(self.opFilePath, perm) as wf:
            wf.writelines(printstate)


if __name__ == "__main__":
    ''' 
    invalidInput = 1
    while(invalidInput):
        ioDir = input("Enter the directory where the input files are stored:")
        if(os.path.exists(ioDir)):
            invalidInput = 0
        else:
            print("Invalid directory entered.")
    '''
    ioDir = ""
    imem = InsMem("Imem", ioDir)
    dmem_ss = DataMem("SS", ioDir)
    dmem_fs = DataMem("FS", ioDir)

    ssCore = SingleStageCore(ioDir, imem, dmem_ss)
    fsCore = FiveStageCore(ioDir, imem, dmem_fs)

    while(True):
        if not ssCore.halted:
            ssCore.step()
            print('took a ss step')       
        if not fsCore.halted:
            fsCore.step()
            print('took a fs step')
        if ssCore.halted and fsCore.halted:
            break

    # dump the data memories
    dmem_ss.outputDataMem()
    dmem_fs.outputDataMem()

    # dump the performance metrics
    calculatePerformance()
    print("Finished execution and generated output files in the following directory: ")
    print(ssCore.baseioDir)     