/*
* Audio Loop Test
* 
* Description: Detects anomalies in test audio data that consists entirely of loops
* Author: Alexander Khouri
* Company: Serato Ltd
* Date: January 2023
*/
import java.io.*;
import java.util.*;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;

import javax.sound.sampled.*;

import javafx.application.Application;
import javafx.collections.FXCollections;
import javafx.concurrent.Task;
import javafx.event.ActionEvent;
import javafx.event.EventHandler;
import javafx.geometry.*;
import javafx.scene.Scene;
import javafx.scene.control.*;
import javafx.scene.image.*;
import javafx.scene.input.*;
import javafx.scene.text.*;
import javafx.scene.layout.*;
import javafx.stage.FileChooser;
import javafx.stage.FileChooser.*;
import javafx.stage.Stage;

import org.jfree.chart.*;
import org.jfree.data.*;

class AnalyseAudio extends Task<Integer> {
	public String outputText;
	public ArrayList<File> openFiles;
	public double param1;
	public double param2;
	public int typeIndex;
	public int outputIndex;
	public boolean autoLengthDetection;
	
	public AnalyseAudio(ArrayList<File> openFiles, double param1, double param2, int typeIndex, int outputIndex) {
		this.outputText = "";
		this.openFiles = openFiles;
		this.param1 = param1;
		this.param2 = param2;
		this.typeIndex = typeIndex;
		this.outputIndex = outputIndex;
		this.autoLengthDetection = (typeIndex == 2);
	}
	
	@Override
	protected Integer call() throws Exception {
		long start = System.currentTimeMillis();	// DEBUGGING
		try {
			int minLoop = -1;	// i.e. Uninitialised
			int maxLoop = -1;
			if (this.typeIndex == 0) {
				double tempo = this.param1;
				double beats = this.param2;
				minLoop = (int) Math.round((60.0 / tempo) * beats) - 2;
				maxLoop = (int) Math.round((60.0 / tempo) * beats) + 2;
			}
			else if (this.typeIndex == 1) {
				minLoop = (int) Math.floor(this.param1);
				maxLoop = (int) Math.ceil(this.param2);
			}
			int loopLength = -1;
			int loopFrameRate = -1;
			for (File file : openFiles) {
				String filePath = file.getPath();
				String fileName = file.getName();
				this.printOut("Loading audio file: " + fileName);
				AudioInputStream audioStream = AudioSystem.getAudioInputStream(file);
				AudioFormat metaData = audioStream.getFormat();
				byte[] buffer = new byte[(int) file.length()];
				audioStream.read(buffer);
				audioStream.close();
				int currentFrameRate = Math.round(metaData.getSampleRate());
				int bitRate = metaData.getSampleSizeInBits();
				int channels = metaData.getChannels();
				int frameSize = metaData.getFrameSize();
				boolean bigEndian = metaData.isBigEndian();
				ArrayList<Integer> data = getSampleList(buffer, bitRate, channels, frameSize, bigEndian);
				if (this.typeIndex == 3) {		// Continuous sine tone
					loopLength = currentFrameRate * 5;
				}
				if (loopLength == -1) {
					this.printOut("Calculating length of audio loop...");
					loopFrameRate = currentFrameRate;
					loopLength = getLoopLength(data, loopFrameRate, minLoop, maxLoop, this.autoLengthDetection);
					if (loopLength == -1) {
						throw new Exception("Error: unable to calculate length of audio loop");
					}
				}
				int currentLoopLength = Math.round(((float)currentFrameRate / (float)loopFrameRate) * (float)loopLength);
				this.printOut("Analysing audio quality...");
				ArrayList<Float> variances = getLoopVariances(currentLoopLength, data);
				this.printOut("Generating output files...");
				drawVariances(loopLength, currentFrameRate, variances, fileName, this.outputIndex);	// TBC
				this.printOut("Analysis complete!");
			}
		} catch (Exception e) {
			this.printOut(e.toString());
		}
		this.printOut("All done! Check 'ALT Output' files for analysis results.");
		this.printOut("----------------------------------------");
		System.out.println("***DEBUGGING*** Program Execution Time: " + (((double)System.currentTimeMillis() - (double)start) / 1000) + " seconds");	// DEBUGGING
		return 0;
	}

	public void printOut(Object text) {
		this.outputText = this.outputText + "" + text + "\n";
		updateMessage(this.outputText);
	}
	
	public String safePath(String path) {
		return path.replace('\\', '_').replace('/', '_').replace(':', '_').replace('*', '_').replace('?', '_').replace('"', '_').replace('<', '_').replace('>', '_').replace('|', '_').replace('.', '_'); // Remove forbidden Windows path characters
	}
	
	public double average(ArrayList<Double> items) {
		if (items.size() == 1) { return items.get(0); }
		double total = 0.0;
		for (double item : items) { total += item; }
		return Math.round(total / items.size());
	}
	public int average(int[] items) {
		if (items.length == 1) { return items[0]; }
		float total = 0.0f;
		for (int item : items) { total += item; }
		return Math.round(total / items.length);
	}

	public ArrayList<Integer> getSampleList(byte[] buffer, int bitRate, int channels, int frameSize, boolean bigEndian) {
		int channelSize = bitRate / 8;
		int start = 0, end = buffer.length - frameSize;		// Remove leading and trailing silence
		boolean silence = true;
		for (int f = start; f < buffer.length; f += frameSize) {	// Define start point after leading silence
			for (int b = 0; b < frameSize; b++) {
				if (buffer[f + b] != 0) {
					start = f;
					silence = false;
					break;
				}
			}
			if (!silence) { break; }
		}
		silence = true;
		for (int f = end; f > start; f -= frameSize) {	// Define end point before trailing silence
			for (int b = 0; b < frameSize; b++) {
				if (buffer[f + b] != 0) {
					end = f;
					silence = false;
					break;
				}
			}
			if (!silence) { break; }
		}
		ArrayList<Integer> output = new ArrayList<Integer>();	// Convert raw data bytes into integer values
		for (int f = start; f < end; f += frameSize) {			// Parse frames
			int[] frame = new int[channels];
			for (int c = 0; c < channels; c++) {				// Parse channels
				for (int b = 0; b < channelSize; b++) {			// Parse bytes
					byte currentByte = buffer[f + (c * channelSize) + b];
					if (bigEndian) {
						frame[c] |= (currentByte << ((channelSize - 1 - b) * 8));
					} else {
						frame[c] |= (currentByte << (b * 8));
					}
				}
			}
			output.add(average(frame));	// Generate mono signal by averaging all channels
		}
		return output;
	}
	
	
	public int getLoopLength(ArrayList<Integer> data, int frameRate, int minLoop, int maxLoop, boolean autoLengthDetection) {
		int loopLength = -1;
		float loopVariance = -1.0f;
		int autoTimeLimit = frameRate * 10;
		if (autoLengthDetection) {
			minLoop = frameRate;
			maxLoop = data.size() / 4;
		} else {
			minLoop = Math.max(1, minLoop) * frameRate;
			maxLoop = Math.min(data.size() / 4, maxLoop * frameRate);
		}
		for (int length = minLoop; length < maxLoop; length++) {
			ArrayList<Integer> list1 = new ArrayList<Integer>(data.subList(0, length));
			ArrayList<Integer> list2 = new ArrayList<Integer>(data.subList(length, length * 2));
			float varianceSum = 0.0f;
			for (int i = 0; i < list1.size(); i++) {
				int value1 = list1.get(i) == 0 ? list1.get(i) + 1 : list1.get(i); // Guard against zero-division below
				int value2 = list1.get(i) == 0 ? list2.get(i) + 1 : list2.get(i); // "list1.get(i) == 0" is not a typo
				varianceSum += Math.abs((value2 - value1) / value1);
			}
			float variance = varianceSum / list1.size();
			if (variance < loopVariance || loopLength == -1) {
				loopLength = length;
				loopVariance = variance;
			}
			if (autoLengthDetection && (length - loopLength) > autoTimeLimit) {
				break;	// If enough audio has been scanned since the lowest variance value was found, use that length
			}
		}
		return loopLength;
	}
	
	public ArrayList<Float> getLoopVariances(int loopLength, ArrayList<Integer> data) {
		ArrayList<Float> variances = new ArrayList<Float>();
		for (int loopStart = loopLength; loopStart <= (data.size() - loopLength); loopStart += loopLength) {
			ArrayList<Integer> prevLoop = new ArrayList<Integer>(data.subList(loopStart - loopLength, loopStart));
			ArrayList<Integer> currLoop = new ArrayList<Integer>(data.subList(loopStart, loopStart + loopLength));
			float varianceSum = 0.0f;
			for (int i = 0; i < currLoop.size(); i++) {
				int value1 = prevLoop.get(i) == 0 ? prevLoop.get(i) + 1 : prevLoop.get(i); // Safeguard against zero-division
				int value2 = prevLoop.get(i) == 0 ? currLoop.get(i) + 1 : currLoop.get(i); // "prevLoop[i] != 0 ?" is not a typo
				varianceSum += Math.abs((float)(value2 - value1) / value1);
			}
			float variance = varianceSum / currLoop.size();
			variances.add(variance);
		}
		return variances;
	}
	
	public void drawVariances(int loopLength, int frameRate, ArrayList<Float> variances, String fileName, int outputIndex) {
		
		
// 		smoothedVariances = [average(variances[max(x - 9, 0):x + 1]) for x in range(len(variances))] # 10-point average
// 		ultraSmoothedVariances = [average(variances[max(x - 19, 0):x + 1]) for x in range(len(variances))] # 20-point average
// 		timestamps = [round(x * (loopLength / frameRate)) for x in range(len(variances))] # Measured in seconds
// 		figure, axes = pyplot.subplots()
// 		pyplot.rcParams["figure.figsize"] = [5.00, 5.00]
// 		pyplot.rcParams["figure.autolayout"] = True
// 		pyplot.grid()
// 		pyplot.margins(x=0, y=0)
// 		pyplot.suptitle("Audio Loop Test Output", fontsize=12)
// 		pyplot.title(fileName, fontsize=10, pad=5)
// 		pyplot.xlabel("Time")
// 		pyplot.ylabel("Loop Variance")
// 		pyplot.plot(timestamps, variances, 'b.-', linewidth=1, markersize=1)
// 		pyplot.plot(timestamps, smoothedVariances, 'r.-', linewidth=1, markersize=1)
// 		pyplot.plot(timestamps, ultraSmoothedVariances, 'k.-', linewidth=1, markersize=1)
// 		pyplot.xlim(0, timestamps[-1] + ceil(2 * loopLength / frameRate))
// 		pyplot.ylim(0, ceil(max(variances)))
// 		pyplot.locator_params(axis='x', nbins=15)
// 		pyplot.locator_params(axis='y', nbins=13)
// 		figure.canvas.draw()
// 		xLabels = [label.get_text() for label in axes.get_xticklabels()]
// 		xLabels = [f"{int(x) // 60 // 60:02}:{int(x) // 60 % 60:02}:{int(x) % 60 % 60:02}" for x in xLabels]
// 		axes.set_xticklabels(xLabels, rotation=45, horizontalalignment='right')
// 		if outputIndex == 0:
// 			pyplot.savefig(f"[ALP Output] {safePath(fileName)}.png", bbox_inches='tight', dpi=300)
// 		elif outputIndex == 1:
// 			PdfPages.savefig(f"[ALP Output] {safePath(fileName)}.pdf", bbox_inches='tight')
	}
}

public class AudioLoopTest extends Application {
	// GUI Components
	Button buttonHelpInfo;
	TextArea textHelpInfo;
	Label labelFiles;
	TextArea textFiles;
	Button buttonOpenFile;
	FileChooser fileChooser;
	Button buttonAnalyseAudio;
	Label labelLoopType;
	ComboBox<String> boxLoopType;
	Label labelLoopParam1;
	TextField textLoopParam1;
	Label labelLoopParam2;
	TextField textLoopParam2;
	Label labelOutputType;
	ComboBox<String> boxOutputType;
	Label labelOutput;
	TextArea textOutput;
	
	// GUI Data
	String[] supportedFormats = new String[] {"flv", "mp3", "ogg", "wav"};
	String floatRegex = "((\\d*\\.)?\\d*)";
	ArrayList<File> openFiles = new ArrayList<File>();
	
	public static void main(String[] args) {
		launch(args);
	}
	
	// Helper GUI Functions
	public void refreshGUIControls() {
		if (boxLoopType.getValue() == "Tempo/Beats") {
			labelLoopParam1.setText("Tempo (BPM):");
			labelLoopParam2.setText("Number of Beats:");
			textLoopParam1.setVisible(true);
			textLoopParam2.setVisible(true);
			if (openFiles.isEmpty() || textLoopParam1.getText().isEmpty() || textLoopParam2.getText().isEmpty()) {
				buttonAnalyseAudio.setDisable(true);
			} else {
				buttonAnalyseAudio.setDisable(false);
			}
		} else if (boxLoopType.getValue() == "Time Range") {
			labelLoopParam1.setText("Minimum Time (seconds):");
			labelLoopParam2.setText("Maximum Time (seconds):");
			textLoopParam1.setVisible(true);
			textLoopParam2.setVisible(true);
			if (openFiles.isEmpty() || textLoopParam1.getText().isEmpty() || textLoopParam2.getText().isEmpty()) {
				buttonAnalyseAudio.setDisable(true);
			} else {
				buttonAnalyseAudio.setDisable(false);
			}
		} else {
			labelLoopParam1.setText("");
			labelLoopParam2.setText("");
			textLoopParam1.setVisible(false);
			textLoopParam2.setVisible(false);
			textLoopParam1.setText("");
			textLoopParam2.setText("");
			if (openFiles.isEmpty()) {
				buttonAnalyseAudio.setDisable(true);
			} else {
				buttonAnalyseAudio.setDisable(false);
			}
		}
	}
	
	@Override
    public void start(Stage stage) {
		// GUI Component Initialisation
		buttonHelpInfo = new Button("Help/Info <<");
		textHelpInfo = new TextArea("This application can be used to find undesirable artifacts (e.g. distortion) in audio files generated by digital signal processing applications. It works by analysing the signal variation across a series of repeated segments (i.e. loops), then generating a graphical representation of the variance which can subsequently be interpreted by users.\n\nTwo types of repeated audio can be used for analysis:\n    * Musical loops\n    * Continuous sine tones\n\nWhen analysing a musical loop, users must provide an estimate of the loop's time duration (specified by maximum and minimum values). Smaller ranges will result in faster execution, but this relies on more accurate knowledge of the loop length. Users can also specify the loop duration using musical metrics (i.e. tempo and number of beats), or they can let the application detect the loop length automatically without any input assistance (though this method is slow).\n\nWhen analysing a continuous sine tone, the program will use default parameters to detect the audio signal. In this scenario, the signal is effectively treated as a series of 5-second loops.\n\nIf the audio recording is split across multiple files, they can all be loaded into this application simultaneously and will be treated as a single audio stream. This application will compensate for any sampling rate fluctuations between the files.\n\nThe following input audio formats are supported:\n    " + String.join(", ", supportedFormats));
		labelFiles = new Label("Input Files:");
		textFiles = new TextArea();
		buttonOpenFile = new Button("Choose File(s)");
		fileChooser = new FileChooser();
		buttonAnalyseAudio = new Button("Analyse Audio");
		labelLoopType = new Label("Loop Definition Method:");
		boxLoopType = new ComboBox<String>();
		labelLoopParam1 = new Label("Tempo (BPM):");
		textLoopParam1 = new TextField();
		labelLoopParam2 = new Label("Number of Beats:");
		textLoopParam2 = new TextField();
		labelOutputType = new Label("Output File Type:");
		boxOutputType = new ComboBox<String>();
		labelOutput = new Label("Info:");
		textOutput = new TextArea();
		
		// GUI Component Settings
		textLoopParam1.setTextFormatter(new TextFormatter<>(change -> change.getControlNewText().matches(floatRegex) ? change : null));
		textLoopParam2.setTextFormatter(new TextFormatter<>(change -> change.getControlNewText().matches(floatRegex) ? change : null));
		ArrayList<String> loopTypes = new ArrayList<String>(Arrays.asList("Tempo/Beats", "Time Range", "Detect Automatically", "Continuous Sine Tone"));
		ArrayList<String> outputTypes = new ArrayList<String>(Arrays.asList("Image (PNG)", "Document (PDF)"));
		boxLoopType.setItems(FXCollections.observableArrayList(loopTypes));
		boxOutputType.setItems(FXCollections.observableArrayList(outputTypes));
		boxLoopType.getSelectionModel().selectFirst();
		boxOutputType.getSelectionModel().selectFirst();
		buttonAnalyseAudio.setDisable(true);
		textHelpInfo.setVisible(false);
		textHelpInfo.setEditable(false);
		textFiles.setEditable(false);
		textOutput.setEditable(false);
		textHelpInfo.setWrapText(true);
		buttonHelpInfo.setMinWidth(150);
		buttonOpenFile.setMinWidth(150);
		buttonAnalyseAudio.setMinWidth(150);
		labelLoopType.setMinWidth(250);
		boxLoopType.setMinWidth(250);
		labelLoopParam1.setMinWidth(250);
		textLoopParam1.setMinWidth(250);
		labelLoopParam2.setMinWidth(250);
		textLoopParam2.setMinWidth(250);
		labelOutputType.setMinWidth(250);
		boxOutputType.setMinWidth(250);
		textFiles.setMinHeight(150);
		textOutput.setMinHeight(150);
		labelLoopType.setAlignment(Pos.CENTER_RIGHT);
		labelLoopParam1.setAlignment(Pos.CENTER_RIGHT);
		labelLoopParam2.setAlignment(Pos.CENTER_RIGHT);
		labelOutputType.setAlignment(Pos.CENTER_RIGHT);
		fileChooser.setTitle("Open Audio File(s)");
		ArrayList<String> supportedExtensions = new ArrayList<String>(); // Used for the FileChooser extension filter
		for (String format : supportedFormats) { supportedExtensions.add("*." + format); }
		fileChooser.getExtensionFilters().addAll(new ExtensionFilter("Audio Files", supportedExtensions));
		
		// GUI Component Actions
		buttonHelpInfo.setOnAction(new EventHandler<ActionEvent>() {
            @Override
            public void handle(ActionEvent event) {
				if (textHelpInfo.isVisible()) {
					textHelpInfo.setVisible(false);
					buttonHelpInfo.setText("Help/Info <<");
					labelFiles.setVisible(true);
					textFiles.setVisible(true);
					buttonOpenFile.setVisible(true);
					buttonAnalyseAudio.setVisible(true);
					labelLoopType.setVisible(true);
					boxLoopType.setVisible(true);
					labelLoopParam1.setVisible(true);
					labelLoopParam2.setVisible(true);
					labelOutputType.setVisible(true);
					boxOutputType.setVisible(true);
					labelOutput.setVisible(true);
					textOutput.setVisible(true);
					refreshGUIControls();
				} else {
					textHelpInfo.setVisible(true);
					buttonHelpInfo.setText("Help/Info >>");
					labelFiles.setVisible(false);
					textFiles.setVisible(false);
					buttonOpenFile.setVisible(false);
					buttonAnalyseAudio.setVisible(false);
					labelLoopType.setVisible(false);
					boxLoopType.setVisible(false);
					labelLoopParam1.setVisible(false);
					textLoopParam1.setVisible(false);
					labelLoopParam2.setVisible(false);
					textLoopParam2.setVisible(false);
					labelOutputType.setVisible(false);
					boxOutputType.setVisible(false);
					labelOutput.setVisible(false);
					textOutput.setVisible(false);
				}
            }
        });
		buttonOpenFile.setOnAction(new EventHandler<ActionEvent>() {
            @Override
            public void handle(ActionEvent event) {
				List<File> openFilesList = fileChooser.showOpenMultipleDialog(stage);
				textFiles.setText("");
				openFiles.clear();
				if (openFilesList != null) {
					openFiles.addAll(openFilesList);
					for (File file : openFiles) {
						textFiles.appendText(file.getName() + "\n");
					}
				}
				refreshGUIControls();
            }
        });
		buttonAnalyseAudio.setOnAction(new EventHandler<ActionEvent>() {
			public void enableControls() {
				buttonOpenFile.setDisable(false);
				buttonAnalyseAudio.setDisable(false);
				boxLoopType.setDisable(false);
				textLoopParam1.setDisable(false);
				textLoopParam2.setDisable(false);
				boxOutputType.setDisable(false);
			}
			public void disableControls() {
				buttonOpenFile.setDisable(true);
				buttonAnalyseAudio.setDisable(true);
				boxLoopType.setDisable(true);
				textLoopParam1.setDisable(true);
				textLoopParam2.setDisable(true);
				boxOutputType.setDisable(true);
			}
            @Override
            public void handle(ActionEvent event) {
                try {
					double param1 = textLoopParam1.getText().isEmpty() ? 0.0 : Double.parseDouble(textLoopParam1.getText());
					double param2 = textLoopParam2.getText().isEmpty() ? 0.0 : Double.parseDouble(textLoopParam2.getText());
					int inputIndex = loopTypes.indexOf(boxLoopType.getValue());
					int outputIndex = outputTypes.indexOf(boxOutputType.getValue());
					AnalyseAudio task = new AnalyseAudio(openFiles, param1, param2, inputIndex, outputIndex);
					textOutput.textProperty().bind(task.messageProperty());
					task.setOnRunning((runningEvent) -> { disableControls(); });
					task.setOnCancelled((cancelledEvent) -> { enableControls(); });
					task.setOnFailed((failedEvent) -> { enableControls(); });
					task.setOnSucceeded((succeededEvent) -> { enableControls(); });
					ExecutorService executorService = Executors.newFixedThreadPool(1);
					executorService.execute(task);
					executorService.shutdown();
				} catch (Exception e) { }
            }
        });
		boxLoopType.setOnAction(new EventHandler<ActionEvent>() {
            @Override
            public void handle(ActionEvent event) {
                refreshGUIControls();
            }
        });
		textLoopParam1.setOnKeyReleased(new EventHandler<KeyEvent>() {
            @Override
            public void handle(KeyEvent event) {
                refreshGUIControls();
            }
        });
		textLoopParam2.setOnKeyReleased(new EventHandler<KeyEvent>() {
            @Override
            public void handle(KeyEvent event) {
                refreshGUIControls();
            }
        });
		
		// GUI Layout
		GridPane grid = new GridPane();
		grid.add(buttonHelpInfo, 2, 0, 1, 1);
		grid.setHalignment(buttonHelpInfo, HPos.RIGHT);
		grid.add(textHelpInfo, 0, 1, 3, 8);
		grid.add(labelFiles, 0, 0, 1, 1);
		grid.add(textFiles, 0, 1, 3, 1);
        grid.add(buttonOpenFile, 0, 2, 1, 1);
		grid.add(buttonAnalyseAudio, 0, 3, 1, 1);
		grid.add(labelLoopType, 1, 2, 1, 1);
		grid.add(labelLoopParam1, 1, 3, 1, 1);
		grid.add(labelLoopParam2, 1, 4, 1, 1);
		grid.add(labelOutputType, 1, 5, 1, 1);
		grid.add(boxLoopType, 2, 2, 1, 1);
		grid.add(textLoopParam1, 2, 3, 1, 1);
		grid.add(textLoopParam2, 2, 4, 1, 1);
		grid.add(boxOutputType, 2, 5, 1, 1);
		grid.add(labelOutput, 0, 6, 1, 1);
		grid.add(textOutput, 0, 7, 3, 1);
		grid.setHgap(10);
		grid.setVgap(10);
		grid.setPadding(new Insets(10));
        stage.setScene(new Scene(grid, 300, 250));
		
		// GUI Details
        stage.setTitle("Audio Loop Test");
		stage.getIcons().add(new Image("file:audio_loop_test.png"));
		stage.setMinWidth(710);
		stage.setMinHeight(650);
		stage.setMaxWidth(710);
		stage.setMaxHeight(650);
		
		// GUI Execution
        stage.show();
    }
}