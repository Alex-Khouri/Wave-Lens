from numba import njit
from numba.core.errors import NumbaDeprecationWarning, NumbaPendingDeprecationWarning
from numba.typed import List # Convert lists before passing to njit functions if numba deprecates Python list support

import warnings
warnings.simplefilter("ignore", RuntimeWarning)
warnings.simplefilter("ignore", NumbaDeprecationWarning)
warnings.simplefilter("ignore", NumbaPendingDeprecationWarning)

from pydub import AudioSegment
from sys import argv
from sys import exit
from math import log10
from time import time

# ***** PROGRAM SETTINGS *****
lengthVarianceThreshold = 0.7 # Applies to detection of loop length
anomalyVarianceThreshold = 0.8 # Applies to detection of audio anomalies
# *****/PROGRAM SETTINGS/*****

# ***** HELPER FUNCTIONS *****
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
	for frame in range(len(data) - 1, 0, -1):
		if data[frame] != 0:
			end = frame
			break
	return data[start:end]

@njit
def equalLists(list1, list2, varianceThreshold):
	if len(list1) != len(list2) or len(list1) < 1:
		return False
	varianceSum = 0
	varianceCount = 0
	for i in range(len(list1)):
		value1 = list1[i] if list1[i] != 0 else list1[i] + 1 # Safeguard against zero-division below
		value2 = list2[i] if list1[i] != 0 else list2[i] + 1 # "if list1[i] != 0" is not a typo
		varianceSum += abs((value2 - value1) / value1)
		varianceCount += 1
	varianceAverage = varianceSum / varianceCount
	return varianceAverage < varianceThreshold

@njit
def getLoopLength(data, frameRate, varianceThreshold):
	minLoop = frameRate // 2 # Use this to balance speed vs accurate detection of short loops
	for length in range(minLoop, len(data) // 4):
		if equalLists(data[0:length], data[length:length * 2], varianceThreshold):
			return length
	return -1

@njit
def getAnomalies(data, loopLength, varianceThreshold):
	anomalies = []
	for loopStart in range(loopLength, len(data) - loopLength + 1, loopLength):
		prevLoop = data[loopStart - loopLength:loopStart]
		currLoop = data[loopStart:loopStart + loopLength]
		if not equalLists(prevLoop, currLoop, varianceThreshold):
			anomalies.append(loopStart)
	return anomalies
# *****/HELPER FUNCTIONS/*****

# ***** DEBUGGING FUNCTIONS *****
def debugData(data, frameRate, mode): # Used for debugging
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
		correctLoop = 187513 # Measured in frames
		for size in range(correctLoop - 200, correctLoop + 200):
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
	# Loop data (average frame variance) -> EUREKA (find average frame variance of <0.5-1; determine value via testing)
	# #######################################
	elif mode == 7:
		file = open("Average Frame Variance for Loop Lengths.txt", "w")
		correctLoop = round(187513 * (frameRate / 44100)) # Measured in frames
		for value in range(correctLoop - 1000, correctLoop + 1000):
			file.write(f"{value} ")
		file.write("\n")
		for size in range(correctLoop - 1000, correctLoop + 1000):
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
	else:
		print("Invalid mode entered for 'debugData()' function")
	raise SystemExit("Program terminated by successful execution of 'debugData()' function")
# *****/DEBUGGING FUNCTIONS/*****

# ***** MAIN EXECUTION *****
start = time()
print("-------------------------------------")
print("---------- AUDIO LOOP TEST ----------")
print("-------------------------------------")
try:
	supportedFormats = ["flv", "mp3", "ogg", "wav"]
	if len(argv) < 2:
		raise IndexError(f"Error: please run this program with a valid audio file using the following command:\n\tpython ./audio_loop_test.py [YOUR AUDIO FILE NAME]\nIf you're running the executable version of this program, you must drag and drop the audio file onto the executable icon.\nSupported File Formats: {', '.join(supportedFormats)}")
	for arg in range(1, len(argv)):
		filename = argv[arg]	
		print(f"Loading audio file: {filename}")
		if not filename.split('.')[-1].lower() in supportedFormats:
			raise TypeError(f"Error: please run the program with a valid audio file (supported formats: {', '.join(supportedFormats)})")
		audio = AudioSegment.from_file(filename)
		data = list(audio.set_channels(1).get_array_of_samples())
		print("Removing leading and trailing silence...")
		data = trimSilence(data)
		debugData(data, audio.frame_rate, 0)
		print("Calculating length of audio loop...")
		loopLength = getLoopLength(data, audio.frame_rate, lengthVarianceThreshold)
		if loopLength == -1:
			raise AttributeError("Error: unable to calculate length of audio loop")
		print(f"Loop Length: {loopLength} frames")
		print("Scanning for anomalies...")
		anomalies = getAnomalies(data, loopLength, anomalyVarianceThreshold)
		if len(anomalies) > 0:
			outputFilename = f"Audio Loop Test Output {arg:03}.txt"
			file = open(outputFilename, "w")
			file.write(f"Filename: {filename}\n")
			file.write("Anomalies detected at the following locations:\n")
			for a in range(len(anomalies)):
				startHours = anomalies[a] // audio.frame_rate // 60 // 60
				startMinutes = anomalies[a] // audio.frame_rate // 60 % 60
				startSeconds = anomalies[a] // audio.frame_rate % 60 % 60
				endHours = (anomalies[a] + loopLength) // audio.frame_rate // 60 // 60
				endMinutes = (anomalies[a] + loopLength) // audio.frame_rate // 60 % 60
				endSeconds = (anomalies[a] + loopLength) // audio.frame_rate % 60 % 60
				file.write(f"{startHours:02}:{startMinutes:02}:{startSeconds:02} -> {endHours:02}:{endMinutes:02}:{endSeconds:02}\n")
			file.write("-------------------------------------\n")
			file.close()
			print(f'Anomalies detected! Check "{outputFilename}" for details.')
		else:
			print("No anomalies detected!")
		print("-------------------------------------")
except IndexError as error:
	print(f"IndexError: {error}")
except TypeError as error:
	print(f"TypeError: {error}")
except AttributeError as error:
	print(f"AttributeError: {error}")
except Exception as error:
	print(f"Error: {error}")
except SystemExit as error:
	print(f"SystemExit: {error}")
except KeyboardInterrupt as error:
	print(f"KeyboardInterrupt: {error}")
except:
	print("Error during program execution!")
finally:
	print(f"Program execution time: {(time() - start):.3f} seconds")
	print("-------------------------------------")
	print("-------------------------------------")
	exitKey = input("Press any key to exit...")
	exit()
# *****/MAIN EXECUTION/*****