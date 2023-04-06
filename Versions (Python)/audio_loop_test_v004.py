import warnings
warnings.simplefilter("ignore", RuntimeWarning)

from pydub import AudioSegment
from sys import argv
from sys import exit


# ***** HELPER FUNCTIONS *****
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
		if abs(1 - (value1 / value2)) > deltaThreshold:
			return False
	return True

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
	filenames = []
	for arg in range(1, len(argv)):
		filenames.append(argv[arg])
	for filename in filenames:	
		print(f"Loading audio file: {filename}")
		if not filename.split('.')[-1].lower() in supportedFormats:
			raise TypeError(f"Error: please run the program with a valid audio file (supported formats: {', '.join(supportedFormats)})")
		audio = AudioSegment.from_file(filename)
		data = list(audio.set_channels(1).get_array_of_samples())
		print("Removing leading and trailing silence...")
		data = trimSilence(data)
		print("Calculating length of audio loop...")
		loopLength = getLoopLength(data, audio.frame_rate)
		if loopLength == -1:
			raise AttributeError("Error: unable to calculate length of audio loop")
		print("Scanning for anomalies...")
		anomalies = getAnomalies(data, loopLength, audio.frame_rate)
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
except IndexError as e:
	print(f"{e}")
except TypeError as e:
	print(f"{e}")
except AttributeError as e:
	print(f"{e}")
except Exception as e:
	print(f"Error: {e}")
except:
	print("Error during program execution!")
finally:
	print("-------------------------------------")
	print("-------------------------------------")
	exitKey = input("Press any key to exit...")
	exit()
# *****/MAIN EXECUTION/*****