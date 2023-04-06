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
from PyQt5.QtCore import *
from PyQt5.QtGui import *
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
	pyplot.savefig(f"Audio Loop Test Output/{safePath(fileName)}.png", bbox_inches='tight')
	PdfPages.savefig(f"Audio Loop Test Output/{safePath(fileName)}.pdf", bbox_inches='tight')
# *****/LOGIC/*****

# ***** GUI *****
def boxLoopTypeChange(box, label1, label2, field1, field2, output):
	if box.currentIndex() == 0:
		field1.setText("")
		field2.setText("")
		field1.setReadOnly(False)
		field2.setReadOnly(False)
		field1.setStyleSheet("background-color: rgb(255,255,255);")
		field2.setStyleSheet("background-color: rgb(255,255,255);")
		label1.setText("Tempo (BPM):")
		label2.setText("Number of Beats:")
	elif box.currentIndex() == 1:
		field1.setText("")
		field2.setText("")
		field1.setReadOnly(False)
		field2.setReadOnly(False)
		field1.setStyleSheet("background-color: rgb(255,255,255);")
		field2.setStyleSheet("background-color: white;")
		label1.setText("Minimum Time (seconds):")
		label2.setText("Maximum Time (seconds):")
	elif box.currentIndex() == 2:
		field1.setText("1")
		field2.setText("30")
		field1.setReadOnly(True)
		field2.setReadOnly(True)
		field1.setStyleSheet("background-color: rgb(224,224,224);")
		field2.setStyleSheet("background-color: rgb(224,224,224);")
		label1.setText("Minimum Time (seconds):")
		label2.setText("Maximum Time (seconds):")

def buttonOpenFileClick(window, filePaths, supportedFormats):
	filePaths.clear()
	dialog = QFileDialog()
	filePaths.extend(dialog.getOpenFileNames(filter=f"Audio Files ({' '.join([f'*.{x}' for x in supportedFormats])})")[0])
	window.setText("\n".join([f.replace('\\', '/').split('/')[-1] for f in filePaths]))

def buttonAnalyseAudioClick(filePaths, param1, param2, typeIndex, output):
	try:
		minLoop = float(param1)
		maxLoop = float(param2)
		if typeIndex == 0: # minLoop = Tempo, maxLoop = Number of Beats
			minLoop = round((60.0 / minLoop) * maxLoop) - 2
			maxLoop = round((60.0 / minLoop) * maxLoop) + 2
		loopLength = -1
		for f in range(len(filePaths)):
			filePath = filePaths[f]
			fileName = filePath.replace('\\', '/').split('/')[-1]
			output.append(f"Loading audio file: {fileName}")
			audio = AudioSegment.from_file(filePath)
			data = list(audio.set_channels(1).get_array_of_samples())
			output.append("Removing leading and trailing silence...")
			data = trimSilence(data)
			if loopLength == -1:
				output.append("Calculating length of audio loop...")
				loopLength = getLoopLength(data, audio.frame_rate, minLoop, maxLoop)
				if loopLength == -1:
					raise AttributeError("Error: unable to calculate length of audio loop")
			output.append("Analysing loop variance...")
			variances = getLoopVariances(data, audio.frame_rate, loopLength)
			drawVariances(variances, loopLength, audio.frame_rate, filePath, fileName)
			output.append(f"Finished! Check the 'Audio Loop Test Output' folder for results.")
	except IndexError as error:
		output.append(error)
	except TypeError as error:
		output.append(error)
	except AttributeError as error:
		output.append(error)
	except Exception as error:
		output.append(error)
	except SystemExit as error:
		output.append(f"Program terminated with exit code {error}")
	except KeyboardInterrupt as error:
		output.append(error)
	except:
		output.append("Error with program execution!")
	finally:
		output.append("-------------------------------------")

def runWidget(supportedFormats):
	widget = QWidget()
	layout = QGridLayout()
	buttonOpenFile = QPushButton(text="Choose File(s)")
	buttonAnalyseAudio = QPushButton(text="Analyse Audio")
	boxLoopType = QComboBox()
	labelLoopType = QLabel(text="Loop Definition Method:")
	lineLoopParam1 = QLineEdit()
	lineLoopParam1.setValidator(QDoubleValidator(bottom=1.0))
	labelLoopParam1 = QLabel(text="Tempo (BPM):")
	lineLoopParam2 = QLineEdit()
	lineLoopParam2.setValidator(QDoubleValidator(bottom=1.0))
	labelLoopParam2 = QLabel(text="Number of Beats:")
	textFiles = QTextEdit()
	textFiles.setReadOnly(True)
	textFiles.setStyleSheet("background-color: rgb(224,224,224);")
	labelFiles = QLabel(text="Input Files:")
	textOutput = QTextEdit()
	textOutput.setReadOnly(True)
	textOutput.setStyleSheet("background-color: rgb(224,224,224);")
	labelOutput = QLabel(text="Info:")
	boxLoopType.addItems(["Tempo/Beats", "Time Range", "Default"])
	filePaths = []
	boxLoopType.currentTextChanged.connect(lambda: boxLoopTypeChange(boxLoopType, labelLoopParam1, labelLoopParam2, lineLoopParam1, lineLoopParam2))
	buttonOpenFile.clicked.connect(lambda: buttonOpenFileClick(textFiles, filePaths, supportedFormats))
	buttonAnalyseAudio.clicked.connect(lambda: buttonAnalyseAudioClick(filePaths, lineLoopParam1.text(), lineLoopParam2.text(), boxLoopType.currentIndex(), textOutput))
	layout.addWidget(textFiles, 1, 0, 1, 5)
	layout.addWidget(labelFiles, 0, 0, 1, 2)
	layout.addWidget(buttonOpenFile, 2, 0, 1, 1)
	layout.addWidget(buttonAnalyseAudio, 4, 0, 1, 1)
	layout.addWidget(labelLoopType, 2, 1, 1, 2, alignment=Qt.AlignRight)
	layout.addWidget(labelLoopParam1, 3, 1, 1, 2, alignment=Qt.AlignRight)
	layout.addWidget(labelLoopParam2, 4, 1, 1, 2, alignment=Qt.AlignRight)
	layout.addWidget(boxLoopType, 2, 3, 1, 2)
	layout.addWidget(lineLoopParam1, 3, 3, 1, 2)
	layout.addWidget(lineLoopParam2, 4, 3, 1, 2)
	layout.addWidget(textOutput, 6, 0, 1, 5)
	layout.addWidget(labelOutput, 5, 0, 1, 2)
	widget.setLayout(layout)
	widget.setWindowTitle("Audio Loop Test")
	widget.setMinimumSize(600, 400)
	return widget
# *****/GUI/*****

# ***** MAIN EXECUTION *****
supportedFormats = ["flv", "mp3", "ogg", "wav"]
app = QApplication(argv)
widget = runWidget(supportedFormats)
widget.show()
exit(app.exec())
# *****/MAIN EXECUTION/*****