"""
Audio Loop Test

Description: Detects anomalies in test audio data that consists entirely of loops
Author: Alexander Khouri
Company: Serato Ltd
Date: October 2022
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
from math import ceil
from math import floor
from sys import argv
from sys import exit
from time import time

# ***** LOGIC *****
def safeInt(value, default):
	try:
		return int(value)
	except:
		return default

def safePath(path):
	return path.replace('\\', '_').replace('/', '_').replace(':', '_').replace('*', '_').replace('?', '_').replace('"', '_').replace('<', '_').replace('>', '_').replace('|', '_').replace('.', '_') # Remove forbidden Windows path characters

def average(items):
	if len(items) > 0:
		return sum(items) / len(items)
	else:
		return 0.0

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
	for length in range(max(1, minLoop) * frameRate, min(len(data) // 4, maxLoop * frameRate)):
		if length % 500 == 0:
			print() # Worker thread progress signal hack (due to incompabitility between pyqt and njit)
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
def getLoopVariances(loopLength, data):
	variances = []
	for loopStart in range(loopLength, len(data) - loopLength + 1, loopLength):
		if len(variances) % 500 == 0:
			print() # Worker thread progress signal hack (due to incompabitility between pyqt and njit)
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

def drawVariances(loopLength, frameRate, variances, fileName, outputIndex):
	smoothedVariances = [average(variances[max(x - 9, 0):x + 1]) for x in range(len(variances))] # 10-point average
	ultraSmoothedVariances = [average(variances[max(x - 19, 0):x + 1]) for x in range(len(variances))] # 20-point average
	timestamps = [round(x * (loopLength / frameRate)) for x in range(len(variances))] # Measured in seconds
	figure, axes = pyplot.subplots()
	pyplot.rcParams["figure.figsize"] = [5.00, 5.00]
	pyplot.rcParams["figure.autolayout"] = True
	pyplot.grid()
	pyplot.margins(x=0, y=0)
	pyplot.suptitle("Audio Loop Test Output", fontsize=12)
	pyplot.title(fileName, fontsize=10, pad=5)
	pyplot.xlabel("Time")
	pyplot.ylabel("Loop Variance")
	pyplot.plot(timestamps, variances, 'b.-', linewidth=1, markersize=1)
	pyplot.plot(timestamps, smoothedVariances, 'r.-', linewidth=1, markersize=1)
	pyplot.plot(timestamps, ultraSmoothedVariances, 'k.-', linewidth=1, markersize=1)
	pyplot.xlim(0, timestamps[-1] + ceil(2 * loopLength / frameRate))
	pyplot.ylim(0, ceil(max(variances)))
	pyplot.locator_params(axis='x', nbins=15)
	pyplot.locator_params(axis='y', nbins=13)
	figure.canvas.draw()
	xLabels = [label.get_text() for label in axes.get_xticklabels()]
	xLabels = [f"{int(x) // 60 // 60:02}:{int(x) // 60 % 60:02}:{int(x) % 60 % 60:02}" for x in xLabels]
	axes.set_xticklabels(xLabels, rotation=45, horizontalalignment='right')
	if outputIndex == 0:
		pyplot.savefig(f"[ALP Output] {safePath(fileName)}.png", bbox_inches='tight', dpi=300)
	elif outputIndex == 1:
		PdfPages.savefig(f"[ALP Output] {safePath(fileName)}.pdf", bbox_inches='tight')
# *****/LOGIC/*****

# ***** MULTI-THREADING *****
class AnalyseAudioWorker(QObject):
	finished = pyqtSignal()
	progress = pyqtSignal(str)
	
	def __init__(self, filePaths, param1, param2, typeIndex, outputIndex, output):
		super().__init__()	
		self.filePaths = filePaths
		self.param1 = param1
		self.param2 = param2
		self.typeIndex = typeIndex
		self.outputIndex = outputIndex
		self.output = output
	
	def printOut(self, text):
		self.progress.emit(text)

	def run(self):
		minLoop = float(self.param1)
		maxLoop = float(self.param2)
		if self.typeIndex == 0:
			tempo = minLoop
			beats = maxLoop
			minLoop = round((60.0 / tempo) * beats) - 2
			maxLoop = round((60.0 / tempo) * beats) + 2
		elif self.typeIndex == 1 or self.typeIndex == 2:
			minLoop = floor(minLoop)
			maxLoop = ceil(maxLoop)
		loopLength = -1
		loopFrameRate = -1
		for f in range(len(self.filePaths)):
			filePath = self.filePaths[f]
			fileName = filePath.replace('\\', '/').split('/')[-1]
			self.printOut(f"Loading audio file: {fileName}")
			audio = AudioSegment.from_file(filePath)
			currentFrameRate = audio.frame_rate
			self.printOut("") # Internal worker thread progress signal
			data = list(audio.set_channels(1).get_array_of_samples())
			self.printOut("Removing leading and trailing silence...")
			data = trimSilence(data)
			if self.typeIndex == 3:
				loopLength = currentFrameRate * 5
			if loopLength == -1:
				self.printOut("Calculating length of audio loop...")
				loopFrameRate = currentFrameRate
				loopLength = getLoopLength(data, loopFrameRate, minLoop, maxLoop)
				if loopLength == -1:
					raise AttributeError("Error: unable to calculate length of audio loop")
			currentLoopLength = round((currentFrameRate / loopFrameRate) * loopLength)
			self.printOut("Analysing audio quality...")
			variances = getLoopVariances(currentLoopLength, data)
			self.printOut("Generating output files...")
			drawVariances(currentLoopLength, currentFrameRate, variances, fileName, self.outputIndex)
			self.printOut(f"Analysis complete!")
		self.printOut(f"All done! Check 'ALT Output' files for analysis results.")
		self.printOut("----------------------------------------")
		self.finished.emit()
# *****/MULTI-THREADING/*****

# ***** GUI *****
class AppGUI():
	def __init__(self):
		self.supportedFormats = ["flv", "mp3", "ogg", "wav"]
		self.filePaths = []
		self.widget = QWidget()
		self.layout = QGridLayout()
		self.buttonOpenFile = QPushButton(text="Choose File(s)")
		self.buttonAnalyseAudio = QPushButton(text="Analyse Audio")
		self.buttonHelpInfo = QPushButton(text="Help/Info <<")
		self.boxLoopType = QComboBox()
		self.labelLoopType = QLabel(text="Loop Definition Method:")
		self.lineLoopParam1 = QLineEdit()
		self.lineLoopParam1.setValidator(QDoubleValidator(bottom=1.0))
		self.labelLoopParam1 = QLabel(text="Tempo (BPM):")
		self.lineLoopParam2 = QLineEdit()
		self.lineLoopParam2.setValidator(QDoubleValidator(bottom=1.0))
		self.labelLoopParam2 = QLabel(text="Number of Beats:")
		self.boxOutputType = QComboBox()
		self.labelOutputType = QLabel(text="Output File Type:")
		self.textFiles = QTextEdit()
		self.textFiles.setReadOnly(True)
		self.textFiles.setStyleSheet("background-color: rgb(224,224,224);")
		self.labelFiles = QLabel(text="Input Files:")
		self.textOutput = QTextEdit()
		self.textOutput.setReadOnly(True)
		self.textOutput.setStyleSheet("background-color: rgb(224,224,224);")
		self.labelOutput = QLabel(text="Info:")
		self.textHelpInfo = QTextEdit()
		self.textHelpInfo.setReadOnly(True)
		self.textHelpInfo.setStyleSheet("background-color: rgb(224,224,224);")
		self.textHelpInfo.setText(f"This application can be used to find undesirable artifacts (e.g. distortion) in audio files generated by digital signal processing applications. It works by analysing the signal variation across a series of repeated segments (i.e. loops), then generating a graphical representation of the variance which can subsequently be interpreted by users.\n\nTwo types of repeated audio can be used for analysis:\n    * Musical loops\n    * Continuous sine tones\n\nWhen analysing a musical loop, users must provide an estimate of the loop's time duration (specified by maximum and minimum values). Smaller estimated ranges will result in faster execution times, but this obviously relies on more accurate knowledge of the loop length. Alternatively, users can specify the time duration using musical metrics (i.e. tempo and number of beats).\n\nWhen analysing a continuous sine tone, the program will use default parameters to detect the audio signal. In this scenario, the signal is effectively treated as a series of 5-second loops.\n\nIf the audio recording is split across multiple files, they can all be loaded into this application simultaneously and will be treated as a single audio stream. This application will compensate for any sampling rate fluctuations between the files.\n\nThe following input audio formats are supported:\n    {', '.join(self.supportedFormats)}")
		self.textHelpInfo.setVisible(False)
		self.boxLoopType.addItems(["Tempo/Beats", "Custom Time Range", "Default Time Range", "Continuous Sine Tone"])
		self.boxLoopType.currentTextChanged.connect(self.boxLoopTypeChange)
		self.boxOutputType.addItems(["PNG (Image)", "PDF (Document)"])
		self.buttonOpenFile.clicked.connect(self.buttonOpenFileClick)
		self.buttonAnalyseAudio.clicked.connect(self.buttonAnalyseAudioClick)
		self.buttonHelpInfo.clicked.connect(self.buttonHelpInfoClick)
		self.lineLoopParam1.textChanged.connect(self.setAnalyseAudioButtonStatus)
		self.lineLoopParam2.textChanged.connect(self.setAnalyseAudioButtonStatus)
		self.buttonAnalyseAudio.setEnabled(False)
		self.layout.addWidget(self.labelFiles, 0, 0, 1, 2)
		self.layout.addWidget(self.textFiles, 1, 0, 1, 5)
		self.layout.addWidget(self.buttonHelpInfo, 0, 4, 1, 1)
		self.layout.addWidget(self.textHelpInfo, 1, 5, 7, 1)
		self.layout.addWidget(self.buttonOpenFile, 2, 0, 1, 1)
		self.layout.addWidget(self.buttonAnalyseAudio, 5, 0, 1, 1)
		self.layout.addWidget(self.labelLoopType, 2, 1, 1, 2, alignment=Qt.AlignRight)
		self.layout.addWidget(self.labelLoopParam1, 3, 1, 1, 2, alignment=Qt.AlignRight)
		self.layout.addWidget(self.labelLoopParam2, 4, 1, 1, 2, alignment=Qt.AlignRight)
		self.layout.addWidget(self.labelOutputType, 5, 1, 1, 2, alignment=Qt.AlignRight)
		self.layout.addWidget(self.boxLoopType, 2, 3, 1, 2)
		self.layout.addWidget(self.lineLoopParam1, 3, 3, 1, 2)
		self.layout.addWidget(self.lineLoopParam2, 4, 3, 1, 2)
		self.layout.addWidget(self.boxOutputType, 5, 3, 1, 2)
		self.layout.addWidget(self.labelOutput, 6, 0, 1, 2)
		self.layout.addWidget(self.textOutput, 7, 0, 1, 5)
		self.widget.setLayout(self.layout)
		self.widget.setWindowTitle("Audio Loop Test")
		self.widget.setWindowIcon(QIcon("audio_loop_test.png"))
		self.widget.setMinimumSize(600, 400)

	def enableControls(self):
		self.buttonOpenFile.setEnabled(True)
		self.buttonAnalyseAudio.setEnabled(True)
		self.boxLoopType.setEnabled(True)
		self.boxOutputType.setEnabled(True)
		if self.boxLoopType.currentIndex() != 2:
			self.lineLoopParam1.setEnabled(True)
			self.lineLoopParam2.setEnabled(True)

	def disableControls(self):
		self.buttonOpenFile.setEnabled(False)
		self.buttonAnalyseAudio.setEnabled(False)
		self.boxLoopType.setEnabled(False)
		self.boxOutputType.setEnabled(False)
		self.lineLoopParam1.setEnabled(False)
		self.lineLoopParam2.setEnabled(False)

	def setAnalyseAudioButtonStatus(self):
		if self.lineLoopParam1.text() != "" and self.lineLoopParam2.text() != "":
			self.buttonAnalyseAudio.setEnabled(True)
		else:
			self.buttonAnalyseAudio.setEnabled(False)

	def boxLoopTypeChange(self):
		if self.boxLoopType.currentIndex() == 0:
			self.lineLoopParam1.setText("")
			self.lineLoopParam2.setText("")
			self.lineLoopParam1.setEnabled(True)
			self.lineLoopParam2.setEnabled(True)
			self.lineLoopParam1.setVisible(True)
			self.lineLoopParam2.setVisible(True)
			self.labelLoopParam1.setText("Tempo (BPM):")
			self.labelLoopParam2.setText("Number of Beats:")
		elif self.boxLoopType.currentIndex() == 1:
			self.lineLoopParam1.setText("")
			self.lineLoopParam2.setText("")
			self.lineLoopParam1.setEnabled(True)
			self.lineLoopParam2.setEnabled(True)
			self.lineLoopParam1.setVisible(True)
			self.lineLoopParam2.setVisible(True)
			self.labelLoopParam1.setText("Minimum Time (seconds):")
			self.labelLoopParam2.setText("Maximum Time (seconds):")
		elif self.boxLoopType.currentIndex() == 2:
			self.lineLoopParam1.setText("1")
			self.lineLoopParam2.setText("30")
			self.lineLoopParam1.setEnabled(False)
			self.lineLoopParam2.setEnabled(False)
			self.lineLoopParam1.setVisible(True)
			self.lineLoopParam2.setVisible(True)
			self.labelLoopParam1.setText("Minimum Time (seconds):")
			self.labelLoopParam2.setText("Maximum Time (seconds):")
		elif self.boxLoopType.currentIndex() == 3:
			self.lineLoopParam1.setText("")
			self.lineLoopParam2.setText("")
			self.lineLoopParam1.setEnabled(False)
			self.lineLoopParam2.setEnabled(False)
			self.lineLoopParam1.setVisible(False)
			self.lineLoopParam2.setVisible(False)
			self.labelLoopParam1.setText("")
			self.labelLoopParam2.setText("")

	def buttonOpenFileClick(self):
		dialog = QFileDialog()
		self.filePaths.clear()
		self.filePaths.extend(dialog.getOpenFileNames(filter=f"Audio Files ({' '.join([f'*.{x}' for x in self.supportedFormats])})")[0])
		self.textFiles.setText("\n".join([f.replace('\\', '/').split('/')[-1] for f in self.filePaths]))

	def buttonAnalyseAudioClick(self):
		self.textOutput.setText("")
		self.thread = QThread()
		self.worker = AnalyseAudioWorker(self.filePaths, self.lineLoopParam1.text(), self.lineLoopParam2.text(), self.boxLoopType.currentIndex(), self.boxOutputType.currentIndex(), self.textOutput)
		self.worker.moveToThread(self.thread)
		self.thread.started.connect(self.worker.run)
		self.worker.finished.connect(self.thread.quit)
		self.worker.finished.connect(self.worker.deleteLater)
		self.thread.finished.connect(self.thread.deleteLater)
		self.worker.progress.connect(self.printOut)
		self.thread.start()
		self.disableControls()
		self.thread.finished.connect(self.enableControls)

	def buttonHelpInfoClick(self):
		if self.buttonHelpInfo.text() == "Help/Info <<":
			# self.widget.resize(QSize(self.widget.size().width() + 300, self.widget.size().height()))
			self.buttonOpenFile.setVisible(False)
			self.buttonAnalyseAudio.setVisible(False)
			self.boxLoopType.setVisible(False)
			self.labelLoopType.setVisible(False)
			self.lineLoopParam1.setVisible(False)
			self.labelLoopParam1.setVisible(False)
			self.lineLoopParam2.setVisible(False)
			self.labelLoopParam2.setVisible(False)
			self.boxOutputType.setVisible(False)
			self.labelOutputType.setVisible(False)
			self.textFiles.setVisible(False)
			self.labelFiles.setVisible(False)
			self.textOutput.setVisible(False)
			self.labelOutput.setVisible(False)
			self.buttonHelpInfo.setText("Help/Info >>")
			self.textHelpInfo.setVisible(True)
		else:
			# self.widget.resize(QSize(self.widget.size().width() - 300, self.widget.size().height()))
			self.buttonOpenFile.setVisible(True)
			self.buttonAnalyseAudio.setVisible(True)
			self.boxLoopType.setVisible(True)
			self.labelLoopType.setVisible(True)
			self.lineLoopParam1.setVisible(True)
			self.labelLoopParam1.setVisible(True)
			self.lineLoopParam2.setVisible(True)
			self.labelLoopParam2.setVisible(True)
			self.boxOutputType.setVisible(True)
			self.labelOutputType.setVisible(True)
			self.textFiles.setVisible(True)
			self.labelFiles.setVisible(True)
			self.textOutput.setVisible(True)
			self.labelOutput.setVisible(True)
			self.buttonHelpInfo.setText("Help/Info <<")
			self.textHelpInfo.setVisible(False)

	def getWidget(self):
		return self.widget

	def printOut(self, text):
		if text != "":
			self.textOutput.append(text)
# *****/GUI/*****

# ***** MAIN EXECUTION *****
app = QApplication(argv)
try:
	gui = AppGUI()
	widget = gui.getWidget()
	widget.show()
except IndexError as error:
	self.printOut(error)
except TypeError as error:
	self.printOut(error)
except AttributeError as error:
	self.printOut(error)
except Exception as error:
	self.printOut(error)
except SystemExit as error:
	self.printOut(f"Program terminated with exit code {error}")
except KeyboardInterrupt as error:
	self.printOut(error)
except:
	self.printOut("Error with program execution!")
finally:
	exit(app.exec())
# *****/MAIN EXECUTION/*****