# RMW2Txt
Custom tool to make sound sequence data from the Rockman World 2 sound engine human readable. Intended for reverse engineering, GB developers or musicians wanting to work with the RMW2 engine. Based on .vgm2txt.

## usage
RMW2TXT takes in takes in sound sequence data in the form a .bin file. Currently you must rip this yourself. EG: title/wily station sequence can be found in the North American release of Mega Man II at `0x1C6E6-0x1C758`.

usage: `RMW2Txt {inputfilepath} [optional args]`
### args
- `-o, --output`: path to text output. (Default: `output.txt`)
- `-p, -print`: print output to terminal
- `-pu, --pulse`: set sequence to pulse channel (on by deafault)
- `-wv, --wave`: set sequence to wavetable channel (required if sequence is for wavetable channel)
- `-ni, --noise`: set sequence to noise channel (required if sequence is for noise channel)

## Credits/thanks
Thanks to Accuracy and Forple for reverse engineering the format. Extra thanks to them for helping with ironing out the tool
