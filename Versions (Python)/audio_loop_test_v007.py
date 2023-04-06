import warnings
warnings.simplefilter("ignore", RuntimeWarning)

from pydub import AudioSegment
from sys import argv
from sys import exit


# ***** HELPER FUNCTIONS *****
def printData(data, frameRate): # Used for debugging
	timeLength = 600 # Measured in seconds
	columnLimit = min(16384, frameRate // 10)
	rowLimit = 1048576
	valueLimit = columnLimit * rowLimit
	file = open("Audio Loop Test Raw Audio Frames.csv", "w")
	for frame in range(min(valueLimit, len(data), timeLength * frameRate)):
		file.write(str(data[frame]))
		if (frame + 1) % columnLimit == 0: # One row = 100 milliseconds
			file.write('\n')
		else:
			file.write(',')
	# timeLength = 60000 # Measured in milliseconds
	# for i in range(timeLength):
	# 	start = i * (frameRate // 1000)
	# 	end = start + (frameRate // 1000)
	# 	file.write(f"{i//1000:03}.{i%1000:03}: {str(data[start:end])}\n")
	file.close()
	raise SystemExit("Program terminated by successful execution of 'printData()' function")

def analyseData(data, frameRate): # Used for debugging
	timeLength = 300 # Measured in seconds
	sentinelSize = 100
	blockSizes = [10, 100, 1000, 10000, 100000]
	sigmaLengthVariance = 0
	sigmaBlockVariances = [[] for x in range(len(blockSizes))] # Format: [[size1_loop1, size1_loop2], [size2_loop1, size2_loop2], etc]
	start = 0
	end = 0
	prevLoop = -1
	for frame in range(sentinelSize, min(len(data), timeLength * frameRate)):
		if data[frame] != 0 and data[frame-sentinelSize:frame].count(0) == sentinelSize:
			end = frame
			currLoop = data[start:end]
			if prevLoop != -1 and len(prevLoop) != 0: # Safeguard for zero-division
				print(f"Checking loop spanning [{start // frameRate // 60:02}:{start // frameRate % 60:02}]-[{end // frameRate // 60:02}:{end // frameRate % 60:02}]...")
				sigmaLengthVariance += (len(currLoop) - len(prevLoop)) / len(prevLoop)
				for size in range(len(blockSizes)):
					blockSize = blockSizes[size]
					sigmaBlockVariance = 0.0
					blockCount = 0
					for frame2 in range(blockSize, min(len(prevLoop), len(currLoop))):
						prevLoopTotal = sum(prevLoop[frame2-blockSize:frame2])
						currLoopTotal = sum(currLoop[frame2-blockSize:frame2])
						if prevLoopTotal == 0: # Safeguard for zero-division
							prevLoopTotal += 1
							currLoopTotal += 1
						sigmaBlockVariance += (currLoopTotal - prevLoopTotal) / prevLoopTotal
						blockCount += 1
					sigmaBlockVariances[size].append(sigmaBlockVariance / blockCount)
			prevLoop = currLoop
			start = end
	lengthVariance = sigmaLengthVariance / len(loops)
	blockVariances = [(sum(x) / len(x)) for x in sigmaBlockVariances]
	file = open("Audio Loop Test Variance Data.txt", "w")
	file.write(f"Average Loop Length Variance: {lengthVariance}")
	for block in range(len(blockVariances)):
		file.write(f"Average Variance for {blockSizes[block]}ms Block Size: {blockVariances[block]}")
	file.close()
	# timeLength = 300 # Measured in seconds
	# start = 0
	# end = 0
	# file = open("Audio Loop Test Loop Data.txt", "w")
	# for frame in range(100, min(len(data), timeLength * frameRate)):
		# if data[frame] != 0 and len([x for x in data[frame-100:frame] if x == 0]) == 100:
			# end = frame
			# file.write(f"Length: {end - start} || {data[start:end]}\n")
			# start = frame
	# file.close()
	raise SystemExit("Program terminated by successful execution of 'printData()' function")

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

def equalLists(list1, list2): # Use this to calibrate equality check if desired loops aren't totally identical
	deltaThreshold = 0.01 # i.e. Disparity of corresponding list values must be less than this
	if len(list1) != len(list2):
		return False
	for i in range(len(list1)):
		value1 = list1[i] if (list1[i] != 0 and list2[i] != 0) else list1[i] + (1 / deltaThreshold) # Safeguard against zero-division below
		value2 = list2[i] if (list1[i] != 0 and list2[i] != 0) else list2[i] + (1 / deltaThreshold)
		if abs((value2 - value1) / value1) > deltaThreshold:
			return False
	return True

def getDeltaValues(data):
	return [(data[x] - data[x-1]) for x in range(1, len(data))]

def getLoopLength(data, sampleRate):
	frameWindow = sampleRate // 4 # Use this to balance performance vs accurate detection of short loops
	for length in range(frameWindow, len(data) // 4):
		if equalLists(data[0:frameWindow], data[length:length + frameWindow]):
			return length
	return -1

def getAnomalies(data, loopLength, sampleRate):
	anomalies = [] # Format: [[anomaly_1_start, anomaly_1_end], [anomaly_2_start, anomaly_2_end], etc...]
	testLoop = data[0:loopLength]
	anomalyActive = False
	anomalyStart = None
	anomalyEnd = None
	for loopStart in range(loopLength * 2, len(data) - loopLength + 1, loopLength):
		currentLoop = data[loopStart:loopStart + loopLength]
		for frame in range(loopLength):
			if currentLoop[frame] != testLoop[frame]: # Calibrate this comparison if desired audio loops aren't totally identical
				if not anomalyActive:
					anomalyStart = loopStart + frame
					anomalyActive = True
			else:
				if anomalyActive:
					anomalyEnd = loopStart + frame - 1
					if len(anomalies) > 0 and (anomalyStart - anomalies[-1][1]) < (5 * audio.frame_rate): # Join items <5 secs apart
						anomalies[-1][1] = anomalyEnd
					else:
						anomalies.append([anomalyStart, anomalyEnd])
					anomalyActive = False
	if anomalyActive: # Capture anomalies that run until last audio frame
		anomalyEnd = len(data) - 1
		if len(anomalies) > 0 and (anomalyStart - anomalies[-1][1]) < (5 * audio.frame_rate):
			anomalies[-1][1] = anomalyEnd
		else:
			anomalies.append([anomalyStart, anomalyEnd])
		anomalyActive = False
	return anomalies
# *****/HELPER FUNCTIONS/*****

# ***** MAIN EXECUTION *****
print("-------------------------------------")
print("---------- AUDIO LOOP TEST ----------")
print("-------------------------------------")
try:
	supportedFormats = ["flv", "mp3", "ogg", "wav"]
	if len(argv) < 2:
		raise IndexError(f"Error: please run this program with a valid audio file using the following command:\n\tpython ./audio_loop_test.py [YOUR AUDIO FILE NAME]\nIf you're running the executable version of this program, you must drag and drop the audio file onto the executable icon.\nSupported File Formats: {', '.join(supportedFormats)}")
	for filename in argv[1:]:	
		print(f"Loading audio file: {filename}")
		if not filename.split('.')[-1].lower() in supportedFormats:
			raise TypeError(f"Error: please run the program with a valid audio file (supported formats: {', '.join(supportedFormats)})")
		audio = AudioSegment.from_file(filename)
		data = list(audio.set_channels(1).get_array_of_samples())
		print("Removing leading and trailing silence...")
		data = trimSilence(data)
		# printData(data, audio.frame_rate) # Used for debugging
		analyseData(data, audio.frame_rate) # Used for debugging
		print("Converting absolute audio values to delta values...") # Compensates for inaccurate clock during audio recording
		deltaData = getDeltaValues(data)
		print("Calculating length of audio loop...")
		loopLength = getLoopLength(deltaData, audio.frame_rate)
		if loopLength == -1:
			raise AttributeError("Error: unable to calculate length of audio loop")
		print("Scanning for anomalies...")
		anomalies = getAnomalies(deltaData, loopLength, audio.frame_rate)
		if len(anomalies) > 0:
			outputFilename = "Audio Loop Test Output.txt"
			file = open(outputFilename, "w")
			file.write(f"Filename: {filename}\n")
			file.write("Anomalies detected at the following locations:\n")
			for a in range(len(anomalies)):
				startHours = anomalies[a][0] // audio.frame_rate // 60 // 60
				startMinutes = anomalies[a][0] // audio.frame_rate // 60 % 60
				startSeconds = anomalies[a][0] // audio.frame_rate % 60 % 60
				endHours = anomalies[a][1] // audio.frame_rate // 60 // 60
				endMinutes = anomalies[a][1] // audio.frame_rate // 60 % 60
				endSeconds = anomalies[a][1] // audio.frame_rate % 60 % 60
				file.write(f"{startHours:02}:{startMinutes:02}:{startSeconds:02} -> {endHours:02}:{endMinutes:02}:{endSeconds:02}\n")
			file.write("-------------------------------------\n")
			file.close()
			print(f"Anomalies detected! Check '{outputFilename}' for details.")
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
	print("-------------------------------------")
	print("-------------------------------------")
	exitKey = input("Press any key to exit...")
	exit()
# *****/MAIN EXECUTION/*****