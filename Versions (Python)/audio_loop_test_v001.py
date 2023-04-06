from pydub import AudioSegment
from sys import argv
from sys import exit
import math
import os

# ****************************
# ***** HELPER FUNCTIONS *****
# ****************************
def getHomogeneity(array, DEBUGLength, DEBUGStart):
	homogeneity = 0.0 # Prevalence of most common list item as a proportion (valid range: 0.0-1.0)
	for i in range(len(array)):
		print(f"Checking prevalence of frame {i}... (Loop Length: {DEBUGLength}, Loop Start: {DEBUGStart})")
		item = array[i]
		itemPrevalence = array.count(item)/len(array) # THIS IS SLOW!
		homogeneity = max(homogeneity, itemPrevalence)
		if homogeneity > (len(array) - i) / len(array): # Optimisation
			break
	return homogeneity

def getLoopLength(data):
	homogeneityThreshold = 0.5 # Use this to calibrate loop recognition
	minimumLength = 2 # Use this to balance performance vs accurate detection of very short loops
	for length in range(minimumLength, len(data) + 1):
		DEBUGLength = length
		validLength = True
		for start in range(0, length):
			DEBUGStart = start
			if getHomogeneity(data[start::length], DEBUGLength, DEBUGStart) < homogeneityThreshold:
				validLength = False
				break
		if validLength:
			return length

def slice(array, size): # Potentially merge this into getLoopLength()?
	slices = []
	for i in range(math.ceil(len(array)/size)):
		start = i * size
		end = min(start + size, len(array))
		slices.push(array[start:end])
	return slices

def getAverageLoop(loops): # Potentially merge this into getLoopLength()?
	pass
# ****************************
# *****/HELPER FUNCTIONS/*****
# ****************************

# **************************
# ***** MAIN EXECUTION *****
# **************************
print("Loading audio file...")
filename = argv[1] if len(argv) > 1 else "./long_audio_loop_mono_44-16_clean.wav"
data = list(AudioSegment.from_wav(filename).set_channels(1).get_array_of_samples())

print("Calculating length of audio loop...")
loopLength = getLoopLength(data)
print(f"Loop Length: {loopLength}")

# print("Splitting audio at loop boundaries...")
# loops = slice(data, loopLength)
# print("Scanning for anomalies...")
# averageLoop = getAverageLoop(loops)
# anomalies = []
# # TO BE COMPLETED

print("Finished!")
# **************************
# *****/MAIN EXECUTION/*****
# **************************