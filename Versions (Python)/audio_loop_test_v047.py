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
from PyQt5.QtWidgets import *
from sys import argv
from sys import exit
from math import ceil
from math import floor
from time import time

# ***** LOGIC *****
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
	for length in range(max(1, minLoop) * frameRate, maxLoop * frameRate):
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
	pyplot.savefig(f"ALT Output [{safePath(fileName)}].png", bbox_inches='tight')
	PdfPages.savefig(f"ALT Output [{safePath(fileName)}].pdf", bbox_inches='tight')
# *****/LOGIC/*****

# ***** GUI *****
def boxLoopTypeChange(box):
	text = box.currentText()
	if text == "Tempo/Beats":
		pass
	elif text == "Time Length":
		pass
	elif text == "Default":
		pass
	else:
		pass

def buttonOpenFileClick(button):
	pass

def buttonAnalyseAudioClick(button):
	pass

def drawGUI():
	widget = QWidget()
	layout = QGridLayout()
	buttonOpenFile = QPushButton(text="Choose File(s)")
	buttonOpenFile.clicked.connect(buttonOpenFileClick)
	buttonAnalyseAudio = QPushButton(text="Analyse Audio")
	buttonAnalyseAudio.clicked.connect(buttonAnalyseAudioClick)
	boxLoopType = QComboBox()
	lineLoopParam1 = QLineEdit()
	labelLoopParam1 = QLabel(text="Tempo (BPM):", parent=lineLoopParam1)
	# labelLoopParam1.setBuddy(lineLoopParam1)
	lineLoopParam2 = QLineEdit()
	labelLoopParam2 = QLabel(text="Number of Beats:", parent=lineLoopParam2)
	# labelLoopParam2.setBuddy(lineLoopParam2)
	textOutput = QTextEdit()
	textOutput.setReadOnly(True)
	labelOutput = QLabel(text="Info:", parent=lineLoopParam1)
	textFiles = QTextEdit()
	textFiles.setReadOnly(True)
	labelFiles = QLabel(text="Input Files:", parent=lineLoopParam1)
	boxLoopType.addItems(["Tempo/Beats", "Time Length", "Default"])
	# boxLoopType.currentTextChanged.connect(boxLoopTypeChange)
	layout.addWidget(buttonOpenFile, 1, 0, 1, 2)
	layout.addWidget(buttonAnalyseAudio, 3, 0, 1, 2)
	layout.addWidget(boxLoopType, 1, 2, 1, 2)
	layout.addWidget(lineLoopParam1, 2, 2, 1, 2)
	layout.addWidget(lineLoopParam2, 3, 2, 1, 2)
	layout.addWidget(textOutput, 4, 0, 1, 4)
	layout.addWidget(textFiles, 0, 0, 1, 4)
	widget.setLayout(layout)
	widget.setWindowTitle("Audio Loop Test")
	widget.setMinimumSize(600, 400)
	return {"widget":widget, "layout":layout, "buttonOpenFile":buttonOpenFile, "buttonAnalyseAudio":buttonAnalyseAudio, "boxLoopType":boxLoopType, "lineLoopParam1":lineLoopParam1, "lineLoopParam2":lineLoopParam2, "textOutput":textOutput}
# *****/GUI/*****

# ***** MAIN EXECUTION *****
print("-------------------------------------")
print("---------- AUDIO LOOP TEST ----------")
print("-------------------------------------")
try:
	supportedFormats = ["flv", "mp3", "ogg", "wav"]
	
	# ***** GUI *****
	app = QApplication(argv)
	gui = drawGUI()
	gui["widget"].show()
	exit(app.exec_())
	raise SystemExit(0)
	# *****/GUI/*****
	
	if len(argv) < 2:
		raise IndexError(f"Error: please run this program with a valid audio file using the following command:\n\tpython ./audio_loop_test.py [YOUR AUDIO FILE NAME]\nIf you're running the executable version of this program, you must drag and drop the audio file(s) onto the executable icon.\nSupported File Formats: {', '.join(supportedFormats)}")
	print("You need to enter the length of the audio loop (or select 'Unspecified Default' if you don't know it).")
	print("How would you like to specify the loop length? (enter the number of your desired option)")
	print("\t(1) Tempo/BPM and number of beats")
	print("\t(2) Range of values that include the exact length (in seconds)")
	print("\t(3) Unspecified default (i.e. time range of 1-30 seconds)")
	minLoop = -1
	maxLoop = -1
	loopLengthType = -1
	while loopLengthType == -1:
		try:
			loopLengthType = int(input(">>> "))
			if loopLengthType == 1:
				loopTempo = -1
				loopBeats = -1
				print("Enter tempo (BPM):")
				while True:
					try:
						loopTempo = float(input(">>> "))
						if loopTempo < 1.0:
							raise ValueError()
						else:
							break
					except:
						print("INVALID INPUT - please enter a tempo >= 1")
				print("Enter number of beats:")
				while True:
					try:
						loopBeats = float(input(">>> "))
						if loopBeats < 1.0:
							raise ValueError()
						else:
							break
					except:
						print("INVALID INPUT - please enter a number of beats >= 1")
				minLoop = round((60.0 / loopTempo) * loopBeats) - 2
				maxLoop = round((60.0 / loopTempo) * loopBeats) + 2
			elif loopLengthType == 2:
				print("Enter minimum time value (seconds):")
				while True:
					try:
						minLoop = floor(float(input(">>> ")))
						if minLoop < 1:
							raise ValueError()
						else:
							break
					except:
						print("INVALID INPUT - please enter a minimum time value >= 1")
				print("Enter maximum time value (seconds):")
				while True:
					try:
						maxLoop = ceil(float(input(">>> ")))
						if maxLoop <= minLoop:
							raise ValueError()
						else:
							break
					except:
						print(f"INVALID INPUT - please enter a maximum time value > {minLoop}")
			elif loopLengthType == 3:
				minLoop = 1
				maxLoop = 30
			else:
				raise ValueError()
		except:
			loopLengthType = -1
			print("INVALID INPUT - please select one of the available options")
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
		print(f"Finished! Check 'ALT Output' files for more information.")
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
	print(f"Program terminated with exit code {error}")
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