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

# ***** PROGRAM SETTINGS *****
debuggingMode = 0 # 0 = off
# *****/PROGRAM SETTINGS/*****

# ***** HELPER FUNCTIONS *****
def safeInt(value, default):
	try:
		return int(value)
	except:
		return default

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
	return data[start:end + 1], start

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

def drawVariances(variances, loopLength, frameRate, inputFilename, outputFilename):
	smoothedVariances = [average(variances[max(x - 9, 0):x + 1]) for x in range(len(variances))] # 5-point average
	timestamps = [round(x * (loopLength / frameRate)) for x in range(len(variances))] # Measured in seconds
	figure, axes = pyplot.subplots()
	pyplot.rcParams["figure.figsize"] = [8.00, 4.00]
	pyplot.rcParams["figure.autolayout"] = True
	pyplot.grid()
	pyplot.margins(x=0, y=0)
	pyplot.suptitle(outputFilename, fontsize=12)
	pyplot.title(inputFilename, fontsize=10)
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
	pyplot.savefig(f"{outputFilename}.png", bbox_inches='tight')
	PdfPages.savefig(f"{outputFilename}.pdf", bbox_inches='tight')
# *****/HELPER FUNCTIONS/*****

# ***** DEBUGGING FUNCTIONS *****
def debug(data, frameRate, mode):
	if mode == 0:
		return 0
	print("DEBUGGING: Analysing data...")
	# #######################################
	# Raw audio frames (CSV; 100 milliseconds per row)
	# #######################################
	if mode == 1:
		timeLength = 600 # Measured in seconds
		columnLimit = min(16384, frameRate // 10)
		rowLimit = 1048576
		valueLimit = columnLimit * rowLimit
		file = open("Audio Loop Test Raw Audio Frames.csv", "w")
		for frame in range(min(valueLimit, len(data), timeLength * frameRate)):
			file.write(str(data[frame]))
			if (frame + 1) % columnLimit == 0:
				file.write('\n')
			else:
				file.write(',')
		file.close()
	# #######################################
	# Raw audio frames (text)
	# #######################################
	elif mode == 2:
		timelength = 60000 # measured in milliseconds
		file = open("Audio Loop Test Raw Audio Frames.txt", "w")
		for i in range(timelength):
			start = i * (framerate // 1000)
			end = start + (framerate // 1000)
			file.write(f"{i//1000:03}.{i%1000:03}: {str(data[start:end])}\n")
		file.close()
	# #######################################
	# Loop data (length and frames; text)
	# #######################################
	elif mode == 3:
		timeLength = 300 # Measured in seconds
		start = 0
		end = 0
		file = open("Audio Loop Test Loop Data.txt", "w")
		for frame in range(100, min(len(data), timeLength * frameRate)):
			if data[frame] != 0 and len([x for x in data[frame-100:frame] if x == 0]) == 100:
				end = frame
				file.write(f"Length: {end - start} || {data[start:end]}\n")
				start = frame
		file.close()
	# #######################################
	# Loop data (length and frames; graph)
	# #######################################
	elif mode == 4:
		timeLength = 300 # Measured in seconds
		sentinelSize = 100 # Measured in audio frames
		start = 0
		end = 0
		loops = []
		for frame in range(100, min(len(data), timeLength * frameRate)):
			if data[frame] != 0 and data[frame-sentinelSize:frame].count(0) == sentinelSize:
				end = frame
				loops.append(data[start:end])
				start = frame
		pyplot.rcParams["figure.figsize"] = [7.00, 3.50]
		pyplot.rcParams["figure.autolayout"] = True
		pyplot.xlim(0, max([len(x) for x in loops]))
		pyplot.ylim(min(data), max(data))
		pyplot.grid()
		for loop in range(1):
			for frame in range(len(loops[loop])):
				x = frame
				y = loops[loop][frame]
				pyplot.plot(x, y, marker="o", markersize=2, markeredgecolor="red", markerfacecolor="red")
		pyplot.show()
	# #######################################
	# Variance data (length and sum)
	# #######################################
	elif mode == 5:
		timeLength = 300 # Measured in seconds
		sentinelSize = 100 # Measured in audio frames
		loopLengths = []
		blockSizes = [10, 50, 100, 500, 1000, 5000, 10000] # Measured in audio frames
		sumBlockVariances = [[] for x in range(len(blockSizes))] # Format: [[size1_loop1, size1_loop2...], [size2_loop1, size2_loop2...]...]
		start = 0
		end = 0
		prevLoop = -1
		for frame in range(sentinelSize, min(len(data), timeLength * frameRate)):
			if data[frame] != 0 and data[frame-sentinelSize:frame].count(0) == sentinelSize:
				end = frame
				currLoop = data[start:end]
				if prevLoop != -1 and len(prevLoop) != 0: # Safeguard against zero-division
					loopLengths.append(len(currLoop))
					for size in range(len(blockSizes)):
						blockSize = blockSizes[size]
						sumBlockVariance = []
						blockCount = 0
						for frameB in range(blockSize, min(len(prevLoop), len(currLoop))):
							prevLoopTotal = sum(prevLoop[frameB-blockSize:frameB])
							currLoopTotal = sum(currLoop[frameB-blockSize:frameB])
							if prevLoopTotal != 0: # Safeguard against zero-division
								sumBlockVariance.append(abs((currLoopTotal - prevLoopTotal) / prevLoopTotal))
						sumBlockVariances[size].append(average(sumBlockVariance))
					print(f"{round(frame / min(len(data), timeLength * frameRate) * 100)}% complete...")
				prevLoop = currLoop
				start = end
		print("100% complete!")
		averageLength = round(average(loopLengths))
		lengthVariance = sum([abs((loopLengths[x] - loopLengths[x-1]) / loopLengths[x-1]) for x in range(1, len(loopLengths)) if loopLengths[x-1] != 0]) / len([length for length in loopLengths if length != 0]) 
		blockVariances = [average(x) for x in sumBlockVariances]
		file = open("Audio Loop Test Variance Data.txt", "w")
		file.write(f"Average Loop Length: {averageLength}\n")
		file.write(f"Average Loop Length Variance: {lengthVariance}\n")
		for block in range(len(blockVariances)):
			file.write(f"Average Variance for {blockSizes[block]}ms Block Size: {blockVariances[block]}\n")
		file.close()
	# #######################################
	# Variance data (signal contour broken into individual wave crests)
	# #######################################
	elif mode == 6:
		# ########## PART ONE: CORRECT LOOP CALCULATION ##########
		timeLength = 300 # Measured in seconds
		sentinelSize = 100 # Measured in audio frames
		start = 0
		end = 0
		loops = []
		for frame in range(sentinelSize, min(len(data), timeLength * frameRate)):
			if data[frame] != 0 and data[frame-sentinelSize:frame].count(0) == sentinelSize:
				end = frame
				loops.append(data[start:end])
				start = end
		loopWaves = [[] for x in range(len(loops))]
		for l in range(len(loops)):
			loop = loops[l]
			start = 0
			end = 0
			for frame in range(2, len(loop)):
				if loop[frame-1] < loop[frame] and loop[frame-1] <= loop[frame-2]:
					end = frame
					wave = loop[start:end]
					loopWaves[l].append(wave)
					start = frame
		waveLengths = [len(x) for x in loopWaves]
		print(f"Variance of correctly-calculated wave segments (n={len(loopWaves)}): {1 - (min(waveLengths) / max(waveLengths))}")
		# ########## PART TWO: INCORRECT LOOP CALCULATION ##########
		correctLength = 187513 # Measured in frames
		for size in range(correctLength - 200, correctLength + 200):
			timeLength = 300 # Measured in seconds
			start = 0
			end = 0
			loops = []
			for frame in range(min(len(data), timeLength * frameRate)):
				if frame > 0 and frame % size == 0:
					end = frame
					loops.append(data[start:end])
					start = end
			loopWaves = [[] for x in range(len(loops))]
			for l in range(len(loops)):
				loop = loops[l]
				start = 0
				end = 0
				for frame in range(2, len(loop)):
					if loop[frame-1] < loop[frame] and loop[frame-1] <= loop[frame-2]:
						end = frame
						wave = loop[start:end]
						loopWaves[l].append(wave)
						start = frame
			waveLengths = [len(x) for x in loopWaves]
			print(f"Variance of incorrectly-calculated wave segments (n = {len(loopWaves)}; Loop Size = {size}): {1 - (min(waveLengths) / max(waveLengths))}")
	# #######################################
	# Loop data (average frame variance)
	# #######################################
	elif mode == 7:
		file = open("Average Frame Variance for Loop Lengths.txt", "w")
		correctLength = round(187513 * (frameRate / 44100)) # Measured in frames
		for value in range(correctLength - 1000, correctLength + 1000):
			file.write(f"{value} ")
		file.write("\n")
		for size in range(correctLength - 1000, correctLength + 1000):
			variances = []
			for frame in range(size):
				value1 = data[frame]
				value2 = data[frame + size]
				if value1 == 0: # Safeguard against zero-division below
					value1 += 1
					value2 += 1
				variances.append(abs((value2 - value1) / value1))
			file.write(f"{round(average(variances), 3)} ")
		file.close()
	# #######################################
	# Cumulative frame variance
	# #######################################
	elif mode == 8:
		fileTXT = open("Cumulative Frame Variance.txt", "w")
		fileCSV = open("Cumulative Frame Variance.csv", "w")
		correctLength = round(187513 * (frameRate / 44100)) # Measured in frames
		for length in range(correctLength - 5, correctLength + 6):
			loop1 = data[0:length]
			loop2 = data[length:length*2]
			varianceSum = 0
			varianceCount = 0
			for i in range(length):
				value1 = loop1[i] if loop1[i] != 0 else loop1[i] + 1 # Safeguard against zero-division below
				value2 = loop2[i] if loop1[i] != 0 else loop2[i] + 1 # "if loop1[i] != 0" is not a typo
				varianceSum += abs((value2 - value1) / value1)
				varianceCount += 1
				varianceAverage = varianceSum / varianceCount
				if length == correctLength:
					fileTXT.write(f"Cumulative Variance for Frame {i+1:06}/{correctLength}: {varianceAverage}\n")
				if i % 100 == 0:
					fileCSV.write(f"{varianceAverage},")
			fileCSV.write("\n")
		fileTXT.close()
		fileCSV.close()
	# #######################################
	# Debugging version of getLoopLength()
	# #######################################
	elif mode == 9:
		print("Number of Candidates: ")
		candidates = []
		for length in range(frameRate * 10, frameRate * 15):
			optimised = False
			optimisationLimit = 6 # Measured in seconds
			list1 = data[0:length]
			list2 = data[length:length * 2]
			varianceSum = 0
			windowSize = min(len(list1), frameRate * optimisationLimit) if optimised else len(list1)
			for i in range(windowSize):
				value1 = list1[i] if list1[i] != 0 else list1[i] + 1 # Safeguard against zero-division below
				value2 = list2[i] if list1[i] != 0 else list2[i] + 1 # "if list1[i] != 0" is not a typo
				varianceSum += abs((value2 - value1) / value1)
			varianceAverage = varianceSum / windowSize
			if varianceAverage < 4:
				candidates.append(f"{varianceAverage}_{length}")
				print(f"{len(candidates)} || {candidates[-1]}")
		candidates.sort()
		for candidate in candidates:
			print(f"{candidate.split('_')[1]}: {candidate.split('_')[0]}")
	# #######################################
	# Variance for loop lengths (over time range)
	# #######################################
	elif mode == 10:
		fileTXT = open("Average Frame Variance for Loop Lengths.txt", "w")
		fileCSV = open("Average Frame Variance for Loop Lengths.csv", "w")
		for length in range(round(frameRate * 11.2), round(frameRate * 11.4)):
			list1 = data[0:length]
			list2 = data[length:length * 2]
			varianceSum = 0
			for i in range(len(list1)):
				value1 = list1[i] if list1[i] != 0 else list1[i] + 1 # Safeguard against zero-division below
				value2 = list2[i] if list1[i] != 0 else list2[i] + 1 # "if list1[i] != 0" is not a typo
				varianceSum += abs((value2 - value1) / value1)
			varianceAverage = varianceSum / len(list1)
			fileTXT.write(f"{(length / frameRate):.8f} seconds: {varianceAverage:.8f}\n")
			fileCSV.write(f"{varianceAverage},")
		fileTXT.close()
		fileCSV.close()
	else:
		print("Invalid mode entered for 'debug()' function")
	raise SystemExit("Program terminated by successful execution of 'debug()' function")
# *****/DEBUGGING FUNCTIONS/*****

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
	start = time()
	loopLength = -1
	for arg in range(1, len(argv)):
		filename = argv[arg]	
		print(f"Loading audio file: {filename}")
		if not filename.split('.')[-1].lower() in supportedFormats:
			raise TypeError(f"Error: please run the program with a valid audio file (supported formats: {', '.join(supportedFormats)})")
		audio = AudioSegment.from_file(filename)
		data = list(audio.set_channels(1).get_array_of_samples())
		print("Removing leading and trailing silence...")
		data, startOffset = trimSilence(data)
		debug(data, audio.frame_rate, debuggingMode)
		if loopLength == -1:
			print("Calculating length of audio loop...")
			loopLength = getLoopLength(data, audio.frame_rate, minLoop, maxLoop)
			if loopLength == -1:
				raise AttributeError("Error: unable to calculate length of audio loop")
		print(f"Loop Length: {loopLength} frames")
		print("Analysing loop variance...")
		variances = getLoopVariances(data, audio.frame_rate, loopLength)
		outputFilename = f"Audio Loop Test Output {arg:03}"
		drawVariances(variances, loopLength, audio.frame_rate, filename, outputFilename)
		print(f'Finished! Check "{outputFilename}" for more information.')
		print("-------------------------------------")
	print(f"Program execution time: {(time() - start):.3f} seconds")
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