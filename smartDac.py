# Author: Pavle Tsotskolauri
# University: Tbilisi State University
# Email: pavle.tsotskolauri922@ens.tsu.edu.ge


import argparse
import smbus
import RPi.GPIO as GPIO
import time
import math


def check_range_margin(arg):
    try:
        value = int(arg)
    except ValueError as err:
       raise argparse.ArgumentTypeError(str(err))

    if value < 0 or value > 5:
        message = "Expected 0 <= value <= 5, got value = {}".format(value)
        raise argparse.ArgumentTypeError(message)


def check_range_slewRate(arg):
    try:
        value = int(arg)
    except ValueError as err:
       raise argparse.ArgumentTypeError(str(err))

    if value < 0 or value > 15:
        message = "Expected 0 <= value <= 5, got value = {}".format(value)
        raise argparse.ArgumentTypeError(message)
    


# Registers
regStatus           = 0xD0
regConfig           = 0xD1
regMedConfig        = 0xD2
regTrigger          = 0xD3
regDAC              = 0x21
regDAC_MarginH      = 0x25
regDAC_MarginL      = 0x26
regPMBusOp          = 0x01
regPMBus_Status     = 0x78
regPMBus_Ver        = 0x98


# Commands
cmdReset            = 0x000A
cmdPowerOn          = 0x0000
cmdPowerOff         = 0x0010
cmdPowerOff_10k     = 0x0018
cmdLock             = 0x2000
cmdUnlock           = 0x5000
cmdNVMProg          = 0x0010
cmdNVMReload        = 0x0020
cmdErase            = 0x0000
cmdFactory          = 0x0200

# Medical Commands
medAlarmHP = 0x4
medAlarmMP = 0x2
medAlarmLP = 0x1

medDeadTime_0 = [0x00, "16 sec", "2.60 sec", "2.55 sec"]
medDeadTime_1 = [0x01, "16 sec", "3.06 sec", "2.96 sec"]
medDeadTime_2 = [0x02, "16 sec", "3.52 sec", "3.38 sec"]
medDeadTime_3 = [0x03, "16 sec", "4.00 sec", "3.80 sec"]

medPulseOff_0 = [0x00, "40 msec", "40 msec", "15 msec"]
medPulseOff_1 = [0x01, "60 msec", "60 msec", "36 msec"]
medPulseOff_2 = [0x02, "80 msec", "80 msec", "58 msec"]
medPulseOff_3 = [0x03, "100 msec", "100 msec", "80 msec"]

medPulseOn_0 = [0x00, "80 msec", "130 msec", "130 msec"]
medPulseOn_1 = [0x01, "103 msec", "153 msec", "153 msec"]
medPulseOn_2 = [0x02, "126 msec", "176 msec", "176 msec"]
medPulseOn_3 = [0x03, "150 msec", "200 msec", "200 msec"]

#Function Generator Commands
cmdSawL             = 0x01
cmdSawH             = 0x02
cmdSquare           = 0x03
cmdTriangle         = 0x00
cmdStartFunc        = 0x01

# Code step definitions
step_1      = [0x00, 1]
step_2      = [0x01, 2]
step_3      = [0x02, 3]
step_4      = [0x03, 4]
step_6      = [0x04, 6]
step_8      = [0x05, 8]
step_16     = [0x06, 16]
step_32     = [0x07, 32]

# Slew Rate Definitons from Datasheet
slew_0      = [0x00, 25.6 * math.pow(10, -6)]
slew_1      = [0x01, 25.6 * math.pow(10, -6) * 1.25]
slew_2      = [0x02, 25.6 * math.pow(10, -6) * 1.5]
slew_3      = [0x03, 25.6 * math.pow(10, -6) * 1.75]
slew_4      = [0x04, 204.8 * math.pow(10, -6)]
slew_5      = [0x05, 204.8 * math.pow(10, -6) * 1.25]
slew_6      = [0x06, 204.8 * math.pow(10, -6) * 1.5]
slew_7      = [0x07, 204.8 * math.pow(10, -6) * 1.75]
slew_8      = [0x08, 1.6384 * math.pow(10, -3)]
slew_9      = [0x09, 1.6384 * math.pow(10, -6) * 1.25] 
slew_10     = [0x0A, 1.6384 * math.pow(10, -6) * 1.5]
slew_11     = [0x0B, 1.6384 * math.pow(10, -6) * 1.75] 
slew_12     = [0x0C, 12 * math.pow(10, -6)]
slew_13     = [0x0D, 8 * math.pow(10, -6)]
slew_14     = [0x0E, 4 * math.pow(10, -6)]
slew_15     = 0x0F
slew_no     = 0x0F

# Masks
cmdPowerOnMask = 0xFFE7


parser = argparse.ArgumentParser(
    prog="DAC Control", description='Smart DAC Control Interface')
subparsers = parser.add_subparsers(dest="command", help="DAC Sub fucntions")

# Subparser for DAC Voltage output
parser_Volt = subparsers.add_parser("v", help="Set DAC Voltage")
parser_Volt.add_argument("voltage", type=float,
                         default=False, help="Set DAC Voltage")

# Subparser for Register Write
parser_Write = subparsers.add_parser("w", help="Write Register")
parser_Write.add_argument("register", type=lambda x: int(x, 0), 
                        choices=[regStatus, regConfig, regMedConfig, regTrigger,
                            regDAC, regDAC_MarginH, regDAC_MarginL, regPMBusOp, regPMBus_Status, regPMBus_Ver],
                        metavar=f"Readable Register: {hex(regStatus).upper()}, {hex(regConfig).upper()}, {hex(regTrigger).upper()}, {hex(regPMBusOp).upper()}, {hex(regPMBus_Status).upper()}, {hex(regPMBus_Ver).upper()}",
                        help="Register to Write")
parser_Write.add_argument("value", type=lambda x: int(x, 0), help="Value to be written in register")

# Subparser for Register Read
parser_Read = subparsers.add_parser("r", help="Read Register")
# lambda x: int(x,16) - ამას არგუმენტად გადაცემული თექვსმეტობითი გადაყავს ათობითში,
# int(x, 0) - 0-ს დროს Int ავტომატურად გამოიცნობს თუ რა სისტემაშია რიცხვი პრეფიქსის მიხედვით
parser_Read.add_argument("read", type=lambda x: int(x, 0), 
                        choices=[regStatus, regConfig, regMedConfig, regTrigger,
                            regDAC, regDAC_MarginH, regDAC_MarginL, regPMBusOp, regPMBus_Status, regPMBus_Ver],
                        metavar=f"Readable Register: {hex(regStatus).upper()}, {hex(regConfig).upper()}, {hex(regTrigger).upper()}, {hex(regPMBusOp).upper()}, {hex(regPMBus_Status).upper()}, {hex(regPMBus_Ver).upper()}",
                        help="Register to Read")
                        
# Subparser for DAC Power settings
parser_Power = subparsers.add_parser("p", help="DAC Power Modes")
parser_Power.add_argument("mode", type=str, default="on",
                            choices=["on", "off", "10k"], metavar="Power Mode",
                            help="DAC Power Mode: On, Off (with High Z), Off with 10K Resistor")

#Subparser for DAC Memory Control
parser_NVM = subparsers.add_parser("nvm", help="NVM Control")
parser_NVM.add_argument("mode", type=str, choices=["prog", "reload"],
                          help="Write Current Configuration into NVM or Reload the NVM")

# Subparser for Arbitrary Waveform Generator
parser_Func = subparsers.add_parser("func", help="DAC Function Generator Configuration")
parser_Func.add_argument("-M", "--mode", type=str, default="square",
                        choices=["square", "triangle", "sawH", "sawL"], metavar="Mode",
                        help="Signal Shapes: Square, Triangle, sawH (Saw-Tooth Rising Slope), sawL (Saw-Tooth Falling Slope)")
parser_Func.add_argument("-H", "--marginH", type=float, default="5",
                          help="DAC Margin High Value for Function Generator [0 to 5V], Default=5")
parser_Func.add_argument("-L", "--marginL", type=float, default="0",
                          help="DAC Margin Low Value for Function Generator [0 to 5V], Default=0")
parser_Func.add_argument("-S", "--slew", type=int, default="0",
                          help="Slew Rate for Function Generator, Default=0", metavar="Slew Rate [0 to 15]")
parser_Func.add_argument("-C", "--codestep", type=int, default="0",
                          help="Code Step for Function Generator, Default=0", metavar="Code Step [0 to 7]")


# Subparser for Medial Alarm Generator
parser_Func = subparsers.add_parser("med", help="DAC Medical Alarm Configuration")
parser_Func.add_argument("-M", "--mode", type=str, default="l",
                        choices=["l", "m", "h"], metavar="Mode",
                        help="Medical Alarm Modes: l - Low Priority, m - Medium Priority, h - High Priority")
parser_Func.add_argument("-T", "--deadtime", type=int, default=0,
                        choices=[0, 1, 2, 3], metavar="Deadtime",
                        help="Dead Time Vary based on priority. Check datasheet for details")
parser_Func.add_argument("-O", "--on", type=int, default=0,
                        choices=[0, 1, 2, 3], metavar="Pulse On Time",
                        help="Pulse on Time Vary based on priority. Check datasheet for details")
parser_Func.add_argument("-F", "--off", type=int, default=0,
                        choices=[0, 1, 2, 3], metavar="Pulse Off Time",
                        help="Pulse off Time Vary based on priority. Check datasheet for details")


# Arguments for sub functions
parser.add_argument("-s", "--status", action="store_true",
                    help="Read Status Register")
parser.add_argument("-l", "--lock", action="store_true",
                    help="Lock the DAC")
parser.add_argument("-u", "--unlock", action="store_true",
                    help="Unlock the DAC")
parser.add_argument("-c", "--config", action="store_true",
                    help="Read Configuration Register")
parser.add_argument("-t", "--trigger", action="store_true",
                    help="Read Trigger Register")
parser.add_argument("-o", "--genoff", action="store_true",
                    help="Turn Off Function Generator")                   
parser.add_argument("-r", "--reset", action="store_true",
                    help="Reset DAC")
parser.add_argument("-f", "--factory", action="store_true",
                    help="Factory Reset")
parser.add_argument("-v", "--verbose", action="store_true",
                    help="Verbose")
parser.add_argument("--version", action="store_true",
                    help="DAC Version")

args = parser.parse_args()
# parser.parse_args(["func", "-m", "square", "-H", "5", "-l", "0", "-s", "0"])


GPIO.setwarnings(False)
GPIO.setmode(GPIO.BCM)

channel = 1                             # I2C Channel
DAC_addr = 0x48                         # DAC I2C Address
bus = smbus.SMBus(channel)


class dac:
    def nibble(val):
        # split the DAC code into nibbles
        list = []
        list.append(val >> 8)
        list.append(val & 0xFF)
        return list

    def calcDACCode(val):
        # DAC_CODE = voltage*1023.0/1.21/2.0 # internal Reference = 1.21 Mode
        DAC_CODE = val * 1023.0/5  # calculate DAC Code
        # round it to become integer
        DAC_CODE = round(DAC_CODE)
        DACCode = DAC_CODE << 2
        return DACCode

    def slew_rate(arg):
        if arg == 0:        return slew_0
        elif arg == 1:      return slew_1
        elif arg == 2:      return slew_2
        elif arg == 3:      return slew_3
        elif arg == 4:      return slew_4
        elif arg == 5:      return slew_5
        elif arg == 6:      return slew_6
        elif arg == 7:      return slew_7
        elif arg == 8:      return slew_8
        elif arg == 9:      return slew_9
        elif arg == 10:     return slew_10
        elif arg == 11:     return slew_11
        elif arg == 12:     return slew_12
        elif arg == 13:     return slew_13
        elif arg == 14:     return slew_14
        elif arg == 15:     return slew_15
        elif args == "no":  return slew_no
        else: print("Please enter Slew Rate number from 0 to 15")

    def code_step(arg):
        if arg == 0:        return step_1
        elif arg == 1:      return step_2
        elif arg == 2:      return step_3
        elif arg == 3:      return step_4
        elif arg == 4:      return step_6
        elif arg == 5:      return step_8
        elif arg == 6:      return step_16
        elif arg == 7:      return step_32
        else: print("Please enter Code Step number from 0 to 7")

    def calcDeadtime(arg):
        if arg == 0:          return medDeadTime_0
        elif arg == 1:        return medDeadTime_1
        elif arg == 2:        return medDeadTime_2
        elif arg == 3:        return medDeadTime_3
    
    def calcPulse_off_time(arg):
        if arg == 0:          return medPulseOff_0
        elif arg == 1:        return medPulseOff_1
        elif arg == 2:        return medPulseOff_2
        elif arg == 3:        return medPulseOff_3
    
    def calcPulse_on_time(arg):
        if arg == 0:          return medPulseOn_0
        elif arg == 1:        return medPulseOn_1
        elif arg == 2:        return medPulseOn_2
        elif arg == 3:        return medPulseOn_3

    def setVoltage(voltage):
        DACVal = dac.calcDACCode(voltage)
        bus.write_i2c_block_data(DAC_addr, regDAC, dac.nibble(DACVal))
        return DACVal

    def read(reg):
        return bus.read_i2c_block_data(DAC_addr, reg, 2)

    def readStatus():                                       # Read 0xD0 Status Registerate
        return bus.read_i2c_block_data(DAC_addr, regStatus, 2)

    def readConfig():                                       # Read 0xD1 Configuration Register
        return bus.read_i2c_block_data(DAC_addr, regConfig, 2)

    def readTrigger():                                       # Read 0xD3 Trigger Register
        return bus.read_i2c_block_data(DAC_addr, regTrigger, 2)

    def lock():
        # clear the unlock (Trigger) bits to be able to lock again
        bus.write_i2c_block_data(DAC_addr, regTrigger, dac.nibble(cmdErase))
        bus.write_i2c_block_data(DAC_addr, regConfig, dac.nibble(cmdLock))     # Lock Code

    def unLock():
        bus.write_i2c_block_data(DAC_addr, regTrigger, dac.nibble(cmdUnlock))  # Unlock Code
        bus.write_i2c_block_data(DAC_addr, regConfig, dac.nibble(cmdErase))    # clear lock bits

    def reset():
        bus.write_i2c_block_data(DAC_addr, regTrigger, dac.nibble(cmdReset))   # Reset Code

    def power(val):
        if val == "on":
            bus.write_i2c_block_data(
                DAC_addr, regConfig, dac.nibble(cmdPowerOn))
        elif val == "off":
            bus.write_i2c_block_data(
                DAC_addr, regConfig, dac.nibble(cmdPowerOff))
        elif val == "10k":
            bus.write_i2c_block_data(
                DAC_addr, regConfig, dac.nibble(cmdPowerOff_10k))

    def write(reg, val):
        regdata = dac.nibble(val)
        bus.write_i2c_block_data(DAC_addr, reg, [regdata[0], regdata[1]])  # Reset Code
    
    def NVM(mode):
        if mode == "prog":
            bus.write_i2c_block_data(DAC_addr, regTrigger, dac.nibble(cmdNVMProg))
        elif mode == "reload":
            bus.write_i2c_block_data(DAC_addr, regTrigger, dac.nibble(cmdNVMReload))
    
    def funcGen(mode, marginH, marginL, slew_rate, code_step):
        dac.funcGenOff()
        time.sleep(0.5)
        margH = dac.calcDACCode(marginH)            # calculate DAC Margin High value
        margL = dac.calcDACCode(marginL)            # calculate DAC Margin Low value
        # print(margH, margL)
        slew = dac.slew_rate(slew_rate)             # select Slew Rate
        step = dac.code_step(code_step)             # Select Code Step
        # cmd = cmdSquare | (slew << 5)
        # print(hex(cmd))
        if mode == "square":
            cmd = (cmdSquare << 14) | (slew[0] << 5)                                        # Generate Command
            freq = (1.0 / (2.0 * slew[1]))                                                  # Calculate Frequency
            bus.write_i2c_block_data(DAC_addr, regConfig, dac.nibble(cmd))                  # Send commands to DAC
            bus.write_i2c_block_data(DAC_addr, regDAC_MarginH, dac.nibble(margH))           # Send Margin High Value 
            bus.write_i2c_block_data(DAC_addr, regDAC_MarginL, dac.nibble(margL))           # Send Margin Low Value
            bus.write_i2c_block_data(DAC_addr, regTrigger, dac.nibble(cmdStartFunc << 8))   # Enable Functon Generator Output
            print(f"Genenrator Mode: {mode}, Margin High = {marginH}V, Margin Low = {marginL}V, Slew Rate = {hex(slew[0])}, Frequency = {freq:.2f}Hz")

        elif mode == "triangle":
            cmd = ((cmdTriangle << 14) | (slew[0] << 5) | (step[0] << 9))                   # Generate Command
            freq = (1.0 / (2.0 * slew[1] * (((margH - margL) >> 2) + 1) / step[1]))         # Calculate Frequency
            bus.write_i2c_block_data(DAC_addr, regConfig, dac.nibble(cmd))                  # Send commands to DAC
            bus.write_i2c_block_data(DAC_addr, regDAC_MarginH, dac.nibble(margH))           # Send Margin High Value 
            bus.write_i2c_block_data(DAC_addr, regDAC_MarginL, dac.nibble(margL))           # Send Margin Low Value
            bus.write_i2c_block_data(DAC_addr, regTrigger, dac.nibble(cmdStartFunc << 8))   # Enable Functon Generator Output
            print(f"Genenrator Mode: {mode}, Margin High = {marginH}V, Margin Low = {marginL}V, Slew Rate = {hex(slew[0])}, Code Step = {step[1]}LSB, Frequency = {freq:.2f}Hz")
        
        elif mode == "sawH":
            cmd = (cmdSawH << 14) | (slew[0] << 5) | (step[0] << 9)                         # Generate Command
            freq = (1.0 / (slew[1] * (((margH - margL) >> 2) + 1) / step[1]))               # Calculate Frequency
            bus.write_i2c_block_data(DAC_addr, regConfig, dac.nibble(cmd))                  # Send commands to DAC
            bus.write_i2c_block_data(DAC_addr, regDAC_MarginH, dac.nibble(margH))           # Send Margin High Value 
            bus.write_i2c_block_data(DAC_addr, regDAC_MarginL, dac.nibble(margL))           # Send Margin Low Value
            bus.write_i2c_block_data(DAC_addr, regTrigger, dac.nibble(cmdStartFunc << 8))   # Enable Functon Generator Output
            print(f"Genenrator Mode: {mode}, Margin High = {marginH}V, Margin Low = {marginL}V, Slew Rate = {hex(slew[0])}, Code Step = {step[1]}LSB, Frequency = {freq:.2f}Hz")
        elif mode == "sawL":
            cmd = (cmdSawL << 14) | (slew[0] << 5) | (step[0] << 9)                         # Generate Command
            freq = (1.0 / (slew[1] * (((margH - margL) >> 2) + 1) / step[1]))               # Calculate Frequency
            bus.write_i2c_block_data(DAC_addr, regConfig, dac.nibble(cmd))                  # Send commands to DAC
            bus.write_i2c_block_data(DAC_addr, regDAC_MarginH, dac.nibble(margH))           # Send Margin High Value 
            bus.write_i2c_block_data(DAC_addr, regDAC_MarginL, dac.nibble(margL))           # Send Margin Low Value
            bus.write_i2c_block_data(DAC_addr, regTrigger, dac.nibble(cmdStartFunc << 8))   # Enable Functon Generator Output

            print(f"Genenrator Mode: {mode}, Margin High = {marginH}V, Margin Low = {marginL}V, Slew Rate = {hex(slew[0])}, Code Step = {step[1]}LSB, Frequency = {freq:.2f}Hz")


    def medGen(mode, deadtime, on, off):
        dead_time = dac.calcDeadtime(deadtime)
        onTime = dac.calcPulse_on_time(on)
        offTime = dac.calcPulse_off_time(off)
        if mode == 'l':
            cmd = (medAlarmLP << 8) | (dead_time[0] << 4) | (offTime[0] << 2) | (onTime[0] << 0)
            bus.write_i2c_block_data(DAC_addr, regMedConfig, dac.nibble(cmd))
            print(f"Medical Signal: Priority Low, Interburst Time: {dead_time[1]}, Pulse Off Time: {offTime[1]}, Pulse On Time: {onTime[1]}")
        elif mode == 'm':
            cmd = (medAlarmMP << 8) | (dead_time[0] << 4) | (offTime[0] << 2) | (onTime[0] << 0)
            bus.write_i2c_block_data(DAC_addr, regMedConfig, dac.nibble(cmd))
            print(f"Medical Signal: Priority Medium, Interburst Time: {dead_time[2]}, Pulse Off Time: {offTime[2]}, Pulse On Time: {onTime[2]}")
        elif mode == 'h':
            cmd = (medAlarmHP << 8) | (dead_time[0] << 4) | (offTime[0] << 2) | (onTime[0] << 0)
            bus.write_i2c_block_data(DAC_addr, regMedConfig, dac.nibble(cmd))
            print(f"Medical Signal: Priority High, Interburst Time: {dead_time[3]}, Pulse Off Time: {offTime[3]}, Pulse On Time: {onTime[3]}")

    def funcGenOff():
        bus.write_i2c_block_data(DAC_addr, regTrigger, dac.nibble(cmdErase))    # Turn off the Function Generator
    
    def factoryReset():
        bus.write_i2c_block_data(DAC_addr, regTrigger, dac.nibble(cmdFactory))  # DAC Factory Reset

    def version():
        return bus.read_i2c_block_data(DAC_addr, regStatus, 2)                  # DAC Version
        



if args.command == "v":
    val = dac.setVoltage(args.voltage)
    voltage = ((val >> 2) / 1023) * 5
    if args.verbose:
        print("DAC output: {:f}V".format(voltage))
    else:
        print("DAC output: {:.2f}V".format(voltage))

if args.command == "r":
    data = dac.read(args.read)
    print(hex(data[0]), hex(data[1]))

if args.command == "w":
    dac.write(args.register, args.value)

if args.command == "p":
    dac.power(args.mode)

if args.command == "nvm":
    dac.NVM(args.mode)
    if args.mode == "prog":
        print("NVM Updated")
    elif args.mode == "reload":
        print("NVM Reloaded")

if args.command == "func":
        dac.funcGen(args.mode, args.marginH, args.marginL, args.slew, args.codestep)

if args.command == "med":
        dac.medGen(args.mode, args.deadtime, args.on, args.off)

if args.status:
    data = dac.readStatus()
    print("Status Register (0xD0): ", hex(data[0]), hex(data[1]))

if args.config:
    data = dac.readConfig()
    print("General Configuration Register (0xD1): ", hex(data[0]), hex(data[1]))

if args.trigger:
    data = dac.readTrigger()
    print("Trigger Register (0xD3): ", hex(data[0]), hex(data[1]))

if args.lock:
    dac.lock()
    print("DAC Locked")

if args.unlock:
    dac.unLock()
    print("DAC Unlocked")

if args.genoff:
    dac.funcGenOff()
    print("Function Generator Turned Off")

if args.reset:
    dac.reset()
    print("DAC Reseted")

if args.factory:
    dac.factoryReset()
    print("DAC Loaded with Factory Configuration")

if args.version:
    data = dac.version()
    print("DAC Version: ", hex(data[1]).upper())