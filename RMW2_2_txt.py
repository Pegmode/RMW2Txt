
import pdb
from enum import Enum
import argparse


class ChannelType(Enum):
    PULSE = 1
    WAVE = 2
    NOISE = 3
INPATH = "pulse1.bin"
OUTPATH = "output.txt"
CHANNELTYPE = ChannelType.PULSE#default type
PRINTOUTPUT = False
INFOTEXT = f'''RMW2 sequence data generated by RMW2TXT

code: Pegmode
RMW2 format specs: Accuracy, Forple, Pegmode

'''



class FileBuffer():
    def __init__(self,buffer):
        self.pos = 0
        self.buffer = buffer
        self.currentOctave = 0
    def advance(self, offset=1):
        self.post += offset
    def read(self, offset=0):
        data = self.buffer[self.pos]
        self.pos += offset
        return data
    def isEOF(self):
        return self.pos >= len(self.buffer)

class RowText():
    headerString = f'{"adrs": <4}|{"raw data": <8}|| Description\n============================='
    def __init__(self,position, data):
        self.dataText = f"{hex(data)[2:]}"
        self.descriptionText = ""
        self.row = position
    def addData(self, data):
        self.dataText = f"{self.dataText} {hex(data)[2:]}"
    def addDescription(self, text):
        self.descriptionText = f"{self.descriptionText} {text}"
    def addDescriptionSpaceless(self, text):
        self.descriptionText = f"{self.descriptionText}{text}"
    def prependDescription(self, text):
        self.descriptionText = f"{text} {self.descriptionText}"
    def getRowString(self):
        # return f"{self.dataText} || {self.descriptionText}"
        return f'{hex(self.row)[2:] : <4}|{self.dataText : <8}||{self.descriptionText}'
    def printRowString(self):
        print(self.getRowString())

instructionTableNormal = {
    0x0: "C-",
    0x1: "C#",
    0x2: "D-",
    0x3: "D#",
    0x4: "E-",
    0x5: "F-",
    0x6: "F#",
    0x7: "G-",
    0x8: "G#",
    0x9: "A-",
    0xA: "A#",
    0xB: "B-",
    0xC: "Command",
    0xD: "Wait",#wait to next note
    0xE: "Rest",#silence, wait to next note
    0xF: "Octave"
}

instructionTableNoise = {#instruction table for when were dealing with noise channel
    0x0 : "A#6 V00   ($01)",
    0x1 : "A-6 V00   ($11)",
    0x2 : "G-6 V00   ($21)",
    0x3 : "D#6 V00   ($31)",
    0x4 : "B-5 V00   ($41)",
    0x5 : "G-5 V00   ($51)",
    0x6 : "G-6 V01   ($29)",
    0x7 : "D#6 V01   ($39)",
    0x8 : "D#6 V01   ($2A)",
    0x9 : "B-5 V01   ($3A)",
    0xA : "B-5 V01   ($49)",
    0xB : "G-5 V01   ($59)",
    0xC: "Command",
    0xD: "Wait",#wait to next note
    0xE: "Rest",#silence, wait to next note
    0xF: "Octave"
}

commandTable = {
    0x0: "set timer speed",
    0x1: "set duty cycle",
    0x2: "set volume/envelope",
    0x3: "Jump",
    0x4: "Pan",
    0x9: "return from subroutine",
    0xD: "Jump to subroutine",
    0xE: "stop channel"
}

waitTimes = {#number of frames the wait command args represent
    0 : 128,
    1 : 64,
    2 : 32,
    3 : 16,
    4 : 8,
    5 : 4,
    6 : 2,
    7 : 1,
    8 : 192,
    9 : 96,
    0xA : 48,
    0xB : 24,
    0xC : 12,
    0xD : 6,
    0xE : 3,
    0xF : 1       
}

def noteArg(buffer:FileBuffer, text:RowText):#handler for note arg, wait x frames
    arg = buffer.read(offset=1) & 0xF
    waitFrames = waitTimes[arg]
    octave = buffer.currentOctave
    if CHANNELTYPE == ChannelType.NOISE:
        octave = ""
    description = f"{octave} for {waitFrames} frames"
    text.addDescriptionSpaceless(description)

def commandArg(buffer:FileBuffer, text:RowText):
    arg = buffer.read(offset=1) & 0xF
    argText = commandTable[arg]
    text.addDescription(argText)
    commandArgHandlers[arg](buffer, text)


def waitArg(buffer:FileBuffer, text:RowText):
    arg = buffer.read(offset=1) & 0xF
    waitFrames = waitTimes[arg]
    description = f"for {waitFrames} frames"
    text.addDescription(description)
    text.addData(arg)


def octaveArg(buffer:FileBuffer, text:RowText):
    arg = buffer.read(offset=1) & 0xF
    warnText = ""
    if arg == 0 or 8 <= arg <= 0xF:
        warnText = "WARNING: broken value (0,8-F)"
    description = f"{arg} {warnText}"
    buffer.currentOctave = arg
    text.addDescription(description)
    text.addData(arg)

def cmdSetTimerArg(buffer:FileBuffer, text:RowText):
    arg = buffer.read(offset=1)
    description = f"to {arg} ({hex(arg)})"
    text.addDescription(description)
    text.addData(arg)

def cmdSetDutyArg(buffer:FileBuffer, text:RowText):
    arg = buffer.read(offset=1)
    duty = ""
    #SORRY
    if 0x00 <= arg <= 0x3f:
        duty = "12.5%"
    elif 0x40 <= arg <= 0x7f:
        duty = "25%"
    elif 0x80 <= arg <= 0xbf:
        duty = "50%"
    elif 0xc0 <= arg <= 0xff:
        duty = "75%"
    description = f"duty value:{hex(arg)[2:]} ({duty})"
    text.addDescription(description)
    text.addData(arg)

def cmdSetBaseVolumeArg(buffer:FileBuffer, text:RowText):
    arg = buffer.read(offset=1)
    vol = arg>>4        # fix the accidental fade and volume bits being swapped
    fade = arg & 0xF
    #SORRY
    if CHANNELTYPE != ChannelType.WAVE:
        fadeText = ""
        if 0 == fade or 0x8 == fade:
            fadeText = "Nothing"
        if 0x1 <= fade <= 0x7:
            fadeText = "Fade out"
        if 0x9 <= fade <= 0xF:
            fadeText = "Fade in"    
        description = f"volume:{hex(vol)[2:].upper()} fade:{hex(fade)[2:].upper()} ({fadeText})"
    else:#channel type == WAVE
        volText = ""
        if 0x0 <= fade <= 0x1f or 0x80 <= fade <= 0x9f:
            volText = "off"
        if 0x20 <= fade <= 0x3f or 0xa0 <= fade <= 0xbf:
            volText = "max"
        if 0x40 <= fade <= 0x5f or 0xc0 <= fade <= 0xdf:
            volText = "mid"
        if 0x60 <= fade <= 0x7f or 0xe0 <= fade <= 0xff:
            volText = "low"   
        description = f"volume:{hex(vol)[2:].upper()}({volText})"
    text.addDescription(description)
    text.addData(arg)

def cmdJumpArg(buffer:FileBuffer, text:RowText):
    arg1 = buffer.read(offset=1)
    arg2 = buffer.read(offset=1)
    description = f"to ${hex(arg2)[2:].upper()}{hex(arg1)[2:].upper()}"
    text.addDescription(description)
    text.addData(arg1)
    text.addData(arg2)

def cmdPanArg(buffer:FileBuffer, text:RowText):
    arg = buffer.read(offset=1)
    description = f"value:{hex(arg)[2:]}"
    text.addDescription(description)
    text.addData(arg)

def cmdReturnSubArg(buffer:FileBuffer, text:RowText):
    return#doesn't contain args


def cmdJumpSubArg(buffer:FileBuffer, text:RowText):
    arg1 = buffer.read(offset=1)
    arg2 = buffer.read(offset=1)
    description = f"at ${hex(arg2)[2:].upper()}{hex(arg1)[2:].upper()}"
    text.addDescription(description)
    text.addData(arg1)
    text.addData(arg2)

def cmdStopArg(buffer:FileBuffer, text:RowText):
    return#doesn't contain args)


instructionHandlers = {#
    0x0: noteArg,
    0x1: noteArg,
    0x2: noteArg,
    0x3: noteArg,
    0x4: noteArg,
    0x5: noteArg,
    0x6: noteArg,
    0x7: noteArg,
    0x8: noteArg,
    0x9: noteArg,
    0xA: noteArg,
    0xB: noteArg,
    0xC: commandArg,
    0xD: waitArg,#wait to next note
    0xE: waitArg,#silence, wait to next note
    0xF: octaveArg 
}

commandArgHandlers = {
    0x0: cmdSetTimerArg,
    0x1: cmdSetDutyArg,
    0x2: cmdSetBaseVolumeArg,
    0x3: cmdJumpArg,
    0x4: cmdPanArg,
    0x9: cmdReturnSubArg,
    0xD: cmdJumpSubArg,
    0xE: cmdStopArg
}

def handleProgramArgs():
    global INPATH, OUTPATH, CHANNELTYPE, PRINTOUTPUT 
    parse = argparse.ArgumentParser(description= "Convert game boy RMW2 sound sequence data to human readable .txt")
    parse.add_argument('inputFilepath', help = "path to the .bin file that contains sound sequence data")
    parse.add_argument('-o', '--output', help = "text output filepath")
    parse.add_argument('-p', '--print', help = "print output to terminal", action='store_true')
    group = parse.add_mutually_exclusive_group()
    group.add_argument('-pu', '--pulse', help = "set sequence to pulse channel", action='store_true')
    group.add_argument('-wv', '--wave', help = "set sequence to wave channel", action='store_true')
    group.add_argument('-ni', '--noise', help = "set sequence to noise channel", action='store_true')
    args = parse.parse_args()
    INPATH =  args.inputFilepath
    if args.output != None:
        OUTPATH = args.output
    if args.wave:
        CHANNELTYPE = ChannelType.WAVE
    elif args.noise:
        CHANNELTYPE = ChannelType.NOISE
    PRINTOUTPUT = args.print


    
def main():
    handleProgramArgs()
    f = open(INPATH, "rb")
    inbuffer = f.read()
    f.close()
    buffer = FileBuffer(inbuffer)
    finalText = ""

    while not buffer.isEOF():
        rowText = RowText(buffer.pos, buffer.read())
        command = buffer.read() >> 4
        if CHANNELTYPE != ChannelType.NOISE:
            commandText = instructionTableNormal[command]
        else:
            commandText = instructionTableNoise[command]
        rowText.addDescription(commandText)
        instructionHandlers[command](buffer, rowText)
        rowString =  rowText.getRowString()
        finalText += "\n" + rowString
        #rowText.printRowString()
        #pdb.set_trace()
    f = open(OUTPATH, "w")
    finalText = INFOTEXT + RowText.headerString + finalText
    f.write(finalText)
    f.close()
    if PRINTOUTPUT:
        print(finalText)
main()
