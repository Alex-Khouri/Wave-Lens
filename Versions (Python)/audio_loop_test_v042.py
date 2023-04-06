"""
Audio Loop Test

Description: Detects anomalies in test audio data that consists entirely of loops
Author: Alexander Khouri
Company: Serato Ltd
Date: September 2022
"""

import warnings
warnings.filterwarnings("ignore")

from matplotlib import pyplot
from matplotlib.backends.backend_pdf import PdfPages
from numba import njit
# from numba.typed import List # Convert lists before passing to njit functions if numba removes Python list support
from pydub import AudioSegment
from sys import argv
from sys import exit
from math import ceil
from math import floor
from time import time

# ***** HELPER FUNCTIONS *****
def safeInt(value, default):
	try:
		return int(value)
	except:
		return default

def safePath(path):
	return path.replace('\\', '_').replace('/', '_').replace(':', '_').replace('*', '_').replace('?', '_').replace('"', '_').replace('<', '_').replace('>', '_').replace('|', '_').replace('.', '_') # Remove forbidden Windows path characters

@njit
def average(items):
	if len(items) > 0:
		return sum(items) / len(items)
	else:
		return 0.0

@njit
def trimSilence(data):
	start = 0
	end = len(data) - 1
	for frame in range(len(data)):
		if data[frame] != 0:
			start = frame
			break
	for frame in range(len(data) - 1, start, -1):
		if data[frame] != 0:
			end = frame
			break
	return data[start:end + 1]

@njit
def getLoopLength(data, frameRate, minLoop, maxLoop):
	loopLength = -1
	loopVariance = -1
	for length in range(minLoop * frameRate, maxLoop * frameRate):
		list1 = data[0:length]
		list2 = data[length:length * 2]
		varianceSum = 0
		for i in range(len(list1)):
			value1 = list1[i] if list1[i] != 0 else list1[i] + 1 # Safeguard against zero-division below
			value2 = list2[i] if list1[i] != 0 else list2[i] + 1 # "if list1[i] != 0" is not a typo
			varianceSum += abs((value2 - value1) / value1)
		variance = varianceSum / len(list1)
		if variance < loopVariance or loopLength == -1:
			loopLength = length
			loopVariance = variance
	return loopLength

@njit
def getLoopVariances(data, frameRate, loopLength):
	variances = []
	for loopStart in range(loopLength, len(data) - loopLength + 1, loopLength):
		prevLoop = data[loopStart - loopLength:loopStart]
		currLoop = data[loopStart:loopStart + loopLength]
		varianceSum = 0
		for i in range(len(currLoop)):
			value1 = prevLoop[i] if prevLoop[i] != 0 else prevLoop[i] + 1 # Safeguard against zero-division below
			value2 = currLoop[i] if prevLoop[i] != 0 else currLoop[i] + 1 # "if prevLoop[i] != 0" is not a typo
			varianceSum += abs((value2 - value1) / value1)
		variance = varianceSum / len(currLoop)
		variances.append(variance)
	return variances

def drawVariances(variances, loopLength, frameRate, filePath, fileName):
	smoothedVariances = [average(variances[max(x - 9, 0):x + 1]) for x in range(len(variances))] # 5-point average
	timestamps = [round(x * (loopLength / frameRate)) for x in range(len(variances))] # Measured in seconds
	figure, axes = pyplot.subplots()
	pyplot.rcParams["figure.figsize"] = [8.00, 4.00]
	pyplot.rcParams["figure.autolayout"] = True
	pyplot.grid()
	pyplot.margins(x=0, y=0)
	pyplot.suptitle("Audio Loop Test Output", fontsize=12)
	pyplot.title(filePath, fontsize=10)
	pyplot.xlabel("Time")
	pyplot.ylabel("Loop Variance")
	pyplot.plot(timestamps, variances, 'b.-', linewidth=1, markersize=1)
	pyplot.plot(timestamps, smoothedVariances, 'r.-', linewidth=1, markersize=1)
	pyplot.xlim(0, timestamps[-1] + ceil(2 * loopLength / frameRate))
	pyplot.ylim(0, ceil(max(variances)))
	figure.canvas.draw()
	xLabels = [label.get_text() for label in axes.get_xticklabels()]
	xLabels = [f"{int(x) // 60 // 60:02}:{int(x) // 60 % 60:02}:{int(x) % 60 % 60:02}" for x in xLabels]
	axes.set_xticklabels(xLabels, rotation=45, horizontalalignment='right')
	pyplot.savefig(f"ALP Output [{safePath(fileName)}].png", bbox_inches='tight')
	PdfPages.savefig(f"ALP Output [{safePath(fileName)}].pdf", bbox_inches='tight')
# *****/HELPER FUNCTIONS/*****

# ***** MAIN EXECUTION *****
print("-------------------------------------")
print("---------- AUDIO LOOP TEST ----------")
print("-------------------------------------")
try:
	supportedFormats = ["flv", "mp3", "ogg", "wav"]
	if len(argv) < 2:
		raise IndexError(f"Error: please run this program with a valid audio file using the following command:\n\tpython ./audio_loop_test.py [YOUR AUDIO FILE NAME]\nIf you're running the executable version of this program, you must drag and drop the audio file(s) onto the executable icon.\nSupported File Formats: {', '.join(supportedFormats)}")
	print("Please enter the minimum and maximum possible values of the loop length used in the audio (press 'Enter' to use default values).")
	print("This will help the program discover the loop length faster by reducing the range of time values that it needs to test.")
	minLoop = safeInt(input("Minimum loop length (seconds; default = 1): "), 1)
	maxLoop = safeInt(input("Maximum loop length (seconds; default = 30): "), 30)
	loopLength = -1
	for arg in range(1, len(argv)):
		filePath = argv[arg]
		fileName = filePath.replace('\\', '/').split('/')[-1]
		print(f"Loading audio file: {filePath}")
		if not filePath.split('.')[-1].lower() in supportedFormats:
			raise TypeError(f"Error: please run the program with a valid audio file (supported formats: {', '.join(supportedFormats)})")
		audio = AudioSegment.from_file(filePath)
		data = list(audio.set_channels(1).get_array_of_samples())
		print("Removing leading and trailing silence...")
		data = trimSilence(data)
		if loopLength == -1:
			print("Calculating length of audio loop...")
			loopLength = getLoopLength(data, audio.frame_rate, minLoop, maxLoop)
			if loopLength == -1:
				raise AttributeError("Error: unable to calculate length of audio loop")
		print(f"Loop Length: {loopLength} frames")
		print("Analysing loop variance...")
		variances = getLoopVariances(data, audio.frame_rate, loopLength)
		drawVariances(variances, loopLength, audio.frame_rate, filePath, fileName)
		print(f"Finished! Check 'ALP Output' files for more information.")
		print("-------------------------------------")
except IndexError as error:
	print(error)
except TypeError as error:
	print(error)
except AttributeError as error:
	print(error)
except Exception as error:
	print(error)
except SystemExit as error:
	print(error)
except KeyboardInterrupt as error:
	print(error)
except:
	print("Error with program execution!")
finally:
	print("-------------------------------------")
	print("-------------------------------------")
	exitKey = input("Press any key to exit...")
	exit()
# *****/MAIN EXECUTION/*****