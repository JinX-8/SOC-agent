import sys
import threading
import asyncio
import os
from PyQt5.QtWidgets import (QApplication, QMainWindow, QTextEdit, QLineEdit,
                             QPushButton, QVBoxLayout, QHBoxLayout, QWidget, QLabel,
                             QSizePolicy, QSpacerItem)
from PyQt5.QtCore import pyqtSignal, QObject, QThread, Qt, QSize, QMetaObject, Q_ARG
from PyQt5.QtGui import QFont, QPixmap, QMovie, QIcon

# --- Dynamically Adjust Import Path ---
script_dir = os.path.dirname(os.path.abspath(__file__)) # Frontend folder
project_root = os.path.dirname(script_dir) # Kobe folder
sys.path.insert(0, project_root)

# --- Import Backend Functions ---
try:
    from Backend.Model import FirstLayerDMM
    from Backend.Chatbot import Chatbot
    from Backend.realtimeSearchEngine import RealtimeSearchEngine
    from Backend.Automation import Automation # Async function
    from Backend.TexTtoSpeech import manageTTS
    from Backend.ImageGeneration import generate_image_task # <-- IMPORT IMAGE GEN FUNCTION
    # from Backend.SpeechToText import listen_function # Placeholder for STT
except ImportError as e:
    print(f"[ERROR] Critical Import Error: {e}")
    print("Ensure backend files exist in the 'Backend' folder with correct function names.")
    sys.exit(1) # Can't run without backend

# --- Path to Graphics Folder ---
GRAPHICS_PATH = "Graphics"

# --- Worker Thread (Handles Backend Logic) ---
class WorkerSignals(QObject):
    finished = pyqtSignal()
    error = pyqtSignal(tuple)
    result = pyqtSignal(str)
    status = pyqtSignal(str)

class BackendWorker(QThread):
    def __init__(self, query):
        super().__init__()
        self.query = query
        self.signals = WorkerSignals()
        self._is_running = True # Flag to stop TTS/loops if needed

    def run(self):
        """Processes the query by calling appropriate backend functions."""
        try:
            self.signals.status.emit("Analyzing request...")
            # 1. Get Task(s) from Decision Model
            tasks = FirstLayerDMM(self.query)
            print(f"DMM Tasks: {tasks}") # Debug output

            if not tasks:
                self.signals.result.emit("I couldn't quite understand that. Please rephrase.")
                return

            response_text = ""
            automation_tasks = [] # Collect tasks for the async Automation function

            # 2. Process Each Task from the Decision Model
            for task_str in tasks:
                task_lower = task_str.lower().strip()

                if task_lower.startswith("general"):
                    query_text = task_str.removeprefix("general").strip().strip('()')
                    self.signals.status.emit(f"Thinking about: {query_text}...")
                    response = Chatbot(query_text)
                    response_text += response + "\n"

                elif task_lower.startswith("realtime"):
                    query_text = task_str.removeprefix("realtime").strip().strip('()')
                    self.signals.status.emit(f"Searching online for: {query_text}...")
                    response = RealtimeSearchEngine(query_text)
                    response_text += response + "\n"

                elif task_lower.startswith("generate image"): # <-- HANDLE IMAGE GENERATION
                    prompt = task_str.removeprefix("generate image").strip().strip('()')
                    self.signals.status.emit(f"Starting image generation for: '{prompt}'...")
                    try:
                        # Run image generation in a separate thread to avoid freezing GUI
                        img_thread = threading.Thread(target=generate_image_task, args=(prompt,), daemon=True)
                        img_thread.start()
                        response_text += f"Okay, generating an image for '{prompt}'. This might take a moment...\n"
                        # Note: We don't wait for completion here. The image generation
                        # function itself should handle opening/displaying the image.
                    except Exception as img_e:
                        print(f"[ERROR] Image generation thread failed to start: {img_e}")
                        self.signals.error.emit((type(img_e), img_e, img_e.__traceback__))
                        response_text += f"Sorry, I couldn't start the image generation: {img_e}\n"

                elif task_lower == "exit":
                    response_text += "Goodbye!\n"
                    # Consider adding app.quit() via signal if exit should close GUI
                    break # Stop processing further tasks

                else: # Assume it's an automation task for the Automation() function
                    automation_tasks.append(task_str)

            # 3. Execute Automation Tasks (if any collected)
            if automation_tasks:
                self.signals.status.emit(f"Executing automation: {', '.join(automation_tasks)}...")
                try:
                    # Get or create an asyncio event loop for the current thread
                    try:
                        loop = asyncio.get_running_loop()
                    except RuntimeError: # 'RuntimeError: There is no current event loop...'
                        loop = asyncio.new_event_loop()
                        asyncio.set_event_loop(loop)

                    success = loop.run_until_complete(Automation(automation_tasks))
                    if not success:
                        response_text += f"Sorry, I encountered an issue executing automation tasks.\n"
                    # else: # Optional success message for automation
                    #    response_text += f"Completed: {', '.join(automation_tasks)}\n"
                except Exception as auto_e:
                    print(f"[ERROR] Automation execution failed: {auto_e}")
                    self.signals.error.emit((type(auto_e), auto_e, auto_e.__traceback__))
                    response_text += f"Sorry, automation failed: {auto_e}\n"


            # 4. Send Final Text Response and Trigger TTS
            final_response = response_text.strip()
            if final_response:
                self.signals.result.emit(final_response)
                # Run TTS in its own thread so it doesn't block the GUI update
                tts_thread = threading.Thread(target=manageTTS, args=(final_response, lambda r=None: self._is_running), daemon=True)
                tts_thread.start()

        except Exception as e:
            # Catch-all for unexpected errors during the process
            print(f"[ERROR] Major error in BackendWorker: {e}")
            self.signals.error.emit((type(e), e, e.__traceback__))
            self.signals.result.emit(f"A critical error occurred: {e}") # Send error to GUI
        finally:
            self.signals.finished.emit() # Signal that processing is complete

    def stop(self):
        """Sets a flag to stop ongoing TTS or other loops if necessary."""
        self._is_running = False

# --- Main GUI Window (Clean & Modern Style) ---
class AssistantWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Kobe AI Assistant")
        self.setGeometry(100, 100, 650, 750)

        # --- Load Graphics ---
        self.kobe_gif_path = os.path.join(GRAPHICS_PATH, "Kobe.gif")
        self.mic_on_icon = QIcon(os.path.join(GRAPHICS_PATH, "Mic_On.png"))
        self.mic_off_icon = QIcon(os.path.join(GRAPHICS_PATH, "Mic_Off.png"))
        self.minimize_icon = QIcon(os.path.join(GRAPHICS_PATH, "minimize2.png"))
        self.close_icon = QIcon(os.path.join(GRAPHICS_PATH, "Close.png"))

        self.is_listening = False # State for mic button

        # --- Modern Styling ---
        self.setStyleSheet("""
            QMainWindow { background-color: #1F1F1F; }
            QWidget#mainWidget { background-color: #2B2B2B; border-radius: 8px; }
            QLabel#gifLabel { background-color: transparent; padding: 5px; }
            QTextEdit#chatDisplay { background-color: #333333; color: #EAEAEA; border: none; border-radius: 5px; font-family: 'Segoe UI', Arial, sans-serif; font-size: 11pt; padding: 10px; }
            QLineEdit#inputLine { background-color: #3A3A3A; color: #EAEAEA; border: 1px solid #4A4A4A; border-radius: 15px; padding: 10px 15px; font-family: 'Segoe UI', Arial, sans-serif; font-size: 11pt; }
            QPushButton#sendButton { background-color: #4A4A4A; color: white; border: none; border-radius: 15px; padding: 10px 20px; font-family: 'Segoe UI', Arial, sans-serif; font-size: 10pt; font-weight: bold; min-width: 60px; }
            QPushButton#sendButton:hover { background-color: #5A5A5A; }
            QPushButton#sendButton:pressed { background-color: #3A3A3A; }
            QPushButton#micButton { background-color: transparent; border: none; padding: 0px 5px; }
            QPushButton#controlButton { background-color: transparent; border: none; padding: 2px; min-width: 25px; max-width: 25px; min-height: 25px; max-height: 25px; border-radius: 12px; }
            QPushButton#controlButton:hover { background-color: #4A4A4A; }
            QPushButton#controlButton:pressed { background-color: #5A5A5A; }
        """)

        # --- Main Widget and Layout ---
        main_widget = QWidget(self)
        main_widget.setObjectName("mainWidget")
        self.setCentralWidget(main_widget)
        main_layout = QVBoxLayout(main_widget)
        main_layout.setContentsMargins(10, 5, 10, 10)

        # --- Window Control Buttons ---
        control_layout = QHBoxLayout()
        control_layout.addStretch()
        minimize_button = QPushButton()
        minimize_button.setObjectName("controlButton")
        minimize_button.setIcon(self.minimize_icon)
        minimize_button.setIconSize(QSize(16, 16))
        minimize_button.setFlat(True)
        minimize_button.clicked.connect(self.showMinimized)
        control_layout.addWidget(minimize_button)
        close_button = QPushButton()
        close_button.setObjectName("controlButton")
        close_button.setIcon(self.close_icon)
        close_button.setIconSize(QSize(16, 16))
        close_button.setFlat(True)
        close_button.clicked.connect(self.close)
        control_layout.addWidget(close_button)
        main_layout.addLayout(control_layout)

        # --- GIF Display ---
        self.gif_label = QLabel()
        self.gif_label.setObjectName("gifLabel")
        if os.path.exists(self.kobe_gif_path):
            self.gif_movie = QMovie(self.kobe_gif_path)
            # Make GIF slightly larger for visibility
            self.gif_movie.setScaledSize(QSize(180, 180))
            self.gif_label.setMovie(self.gif_movie)
            self.gif_movie.start()
        else:
            self.gif_label.setText("Kobe.gif not found")
            print(f"[Warning] GIF not found at: {self.kobe_gif_path}")
        self.gif_label.setAlignment(Qt.AlignCenter)
        self.gif_label.setFixedHeight(190) # Adjust height for larger GIF
        main_layout.addWidget(self.gif_label)

        # --- Chat Display ---
        self.chat_display = QTextEdit()
        self.chat_display.setObjectName("chatDisplay")
        self.chat_display.setReadOnly(True)
        main_layout.addWidget(self.chat_display)

        # --- Input Area Layout ---
        input_layout = QHBoxLayout()
        input_layout.setSpacing(10)
        self.input_line = QLineEdit()
        self.input_line.setObjectName("inputLine")
        self.input_line.setPlaceholderText("Ask Kobe anything...")
        self.input_line.returnPressed.connect(self.send_query)
        input_layout.addWidget(self.input_line)
        self.mic_button = QPushButton()
        self.mic_button.setObjectName("micButton")
        self.mic_button.setIcon(self.mic_off_icon)
        self.mic_button.setIconSize(QSize(28, 28))
        self.mic_button.setFlat(True)
        self.mic_button.setToolTip("Toggle Voice Input (STT Not Implemented)")
        self.mic_button.clicked.connect(self.toggle_listening)
        input_layout.addWidget(self.mic_button)
        self.send_button = QPushButton("Send")
        self.send_button.setObjectName("sendButton")
        self.send_button.clicked.connect(self.send_query)
        input_layout.addWidget(self.send_button)
        main_layout.addLayout(input_layout)

        self.worker_thread = None

        # Optional: Make window frameless
        # self.setWindowFlag(Qt.FramelessWindowHint)
        # self.setAttribute(Qt.WA_TranslucentBackground)

    def toggle_listening(self):
        """Handles the microphone button click."""
        self.is_listening = not self.is_listening
        if self.is_listening:
            self.mic_button.setIcon(self.mic_on_icon)
            self.display_status("Listening... (STT not implemented)")
            # --- TODO: Start STT in a separate thread ---
            # try:
            #     stt_thread = threading.Thread(target=self.run_stt, daemon=True)
            #     stt_thread.start()
            # except NameError: # Handle if listen_function isn't imported
            #     self.handle_error(("Config Error", "SpeechToText function not available.", None))
            #     self.reset_mic_button()
            # except Exception as e:
            #     self.handle_error(("STT Error", e, None))
            #     self.reset_mic_button()
        else:
            self.mic_button.setIcon(self.mic_off_icon)
            self.display_status("Stopped listening.")
            # --- TODO: Add logic to stop/cancel STT if running ---

    # --- Placeholder function to call STT ---
    # def run_stt(self):
    #     """Runs the STT function and updates GUI safely."""
    #     try:
    #         # IMPORTANT: Replace 'listen_function' with your actual imported STT function name
    #         recognized_text = listen_function()
    #         if recognized_text:
    #             # Safely update GUI elements from this thread using invokeMethod
    #             QMetaObject.invokeMethod(self.input_line, "setText", Qt.QueuedConnection, Q_ARG(str, recognized_text))
    #             QMetaObject.invokeMethod(self, "send_query", Qt.QueuedConnection) # Optionally auto-send
    #     except Exception as e:
    #          QMetaObject.invokeMethod(self, "handle_error", Qt.QueuedConnection, Q_ARG(tuple, ("STT Error", e, None)))
    #     finally:
    #         # Ensure the mic button is reset regardless of success/failure
    #         QMetaObject.invokeMethod(self, "reset_mic_button", Qt.QueuedConnection)

    def reset_mic_button(self):
         """Safely resets mic button state and icon from any thread."""
         self.is_listening = False
         self.mic_button.setIcon(self.mic_off_icon)
         # Re-enable button if it was disabled during STT
         if not self.input_line.isEnabled(): # Check if processing is ongoing
              self.mic_button.setEnabled(True)

    def send_query(self):
        """Sends the text query to the backend worker thread."""
        query = self.input_line.text().strip()
        # Prevent sending empty queries or sending while processing
        if not query or (self.worker_thread and self.worker_thread.isRunning()):
            return

        self.add_message("You:", query)
        self.input_line.clear()

        # Disable input fields during processing
        self.input_line.setEnabled(False)
        self.send_button.setEnabled(False)
        self.mic_button.setEnabled(False) # Disable mic while processing text input

        # Stop previous worker if any (e.g., if user sends new query quickly)
        if self.worker_thread:
             self.worker_thread.stop() # Set flag to stop TTS
             # self.worker_thread.quit() # Ask thread to exit gracefully
             # self.worker_thread.wait() # Optionally wait

        # Start new backend processing
        self.worker_thread = BackendWorker(query)
        # Connect signals from worker to GUI slots
        self.worker_thread.signals.result.connect(self.display_result)
        self.worker_thread.signals.status.connect(self.display_status)
        self.worker_thread.signals.error.connect(self.handle_error)
        self.worker_thread.signals.finished.connect(self.on_processing_finished)
        self.worker_thread.start() # Start the thread's run() method

    def add_message(self, sender, message):
        """Adds a formatted message to the chat display."""
        sender_color = "#87CEEB" if sender == "Kobe:" else "#E0E0E0" # Light blue for Kobe
        sender_html = f"<span style='color:{sender_color}; font-weight:bold;'>{sender}</span>"
        # Escape HTML characters in the message to prevent rendering issues
        message_html = message.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;').replace('\n', '<br>')
        self.chat_display.append(f"{sender_html}<br>{message_html}<br>")
        self.chat_display.ensureCursorVisible() # Auto-scroll to bottom

    def display_result(self, result_text):
        """Displays the final text result from the backend."""
        self.add_message("Kobe:", result_text)

    def display_status(self, status_text):
        """Displays status messages (e.g., 'Processing...')"""
        self.add_message("System:", f"<i>{status_text}</i>")

    def handle_error(self, error_tuple):
        """Displays errors from the backend thread."""
        print(f"[ERROR] Error in backend thread: Type={error_tuple[0]}, Msg={error_tuple[1]}")
        # Consider logging the full traceback (error_tuple[2]) to a file
        self.add_message("System:", f"<span style='color:#FF6B6B;'>Error: {error_tuple[1]}</span>") # Red error text

    def on_processing_finished(self):
        """Re-enables input fields after backend processing is complete."""
        self.input_line.setEnabled(True)
        self.send_button.setEnabled(True)
        self.mic_button.setEnabled(True) # Re-enable mic button
        self.input_line.setFocus() # Put cursor back in input box
        self.worker_thread = None # Clear the reference to the finished thread

        # If mic was active before sending text, reset its state
        if self.is_listening:
             self.reset_mic_button()

    def closeEvent(self, event):
        """Ensures threads are stopped cleanly when the window is closed."""
        if self.worker_thread and self.worker_thread.isRunning():
            print("Stopping backend worker on close...")
            self.worker_thread.stop()
            self.worker_thread.quit() # Ask thread to terminate
            if not self.worker_thread.wait(1000): # Wait up to 1 second
                print("[Warning] Backend thread did not stop gracefully.")
        event.accept()

# --- Application Entry Point ---
if __name__ == '__main__':
    app = QApplication(sys.argv)
    # Apply a modern Fusion style if available (optional)
    # app.setStyle("Fusion")
    window = AssistantWindow()
    window.show()
    sys.exit(app.exec_())