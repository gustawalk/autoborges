import sys
from pynput import keyboard, mouse
from pynput.mouse import Button
from pynput.keyboard import Key
from PyQt5.QtWidgets import *
from PyQt5.QtGui import QIcon
import time
import threading

class RecordMacro(threading.Thread):
    def __init__(self, keyboard, mouse):
        super().__init__()
        global macro_record

        self.daemon = True
        self.running = True

        self.delay = 0
        self.delay_mouse_pos = 0

        self.keyboard_active = keyboard
        self.mouse_active = mouse
        
        self.key_pressed = set()

    def run(self):
        print(f"Starting record macro thread with kb: {self.keyboard_active} - mouse: {self.mouse_active}")
        if self.mouse_active:
            self.mouse_listener = mouse.Listener(
                on_move=self.mouse_on_move,
                on_click=self.mouse_on_click,
                on_scroll=self.mouse_on_scroll
            )
            self.mouse_listener.start()

        if self.keyboard_active:
            self.keyboard_listener = keyboard.Listener(
                on_press=self.kb_on_press,
                on_release=self.kb_on_release
            )
            self.keyboard_listener.start()

        self.timer_thread = threading.Thread(target=self.delay_timer, daemon=True).start()

    def delay_timer(self):
        while self.running:
            self.delay += 1
            time.sleep(0.001)

    def mouse_on_move(self, x, y):
        if self.delay_mouse_pos <= 2:
            self.delay_mouse_pos += 1
            return

        macro_record.append(["Delay", self.delay])
        macro_record.append(["Move", (x, y)])
        self.delay_mouse_pos = 0
        self.delay = 0

    
    def mouse_on_click(self, x, y, button, pressed):
        
        macro_record.append(["Delay", self.delay])
        macro_record.append(["Click", (str(button), pressed)])
        self.delay = 0
    
    def mouse_on_scroll(self, x, y, dx, dy):
        for item in macro_record:
            print(item)

    def kb_on_press(self, key):

        if key not in self.key_pressed:
            macro_record.append(["Delay", self.delay])
            try:
                macro_record.append(["Press", key.char])
            except AttributeError:
                macro_record.append(["Press", key])

            self.delay = 0
            self.key_pressed.add(key)

    def kb_on_release(self, key):

        if key in self.key_pressed:
            macro_record.append(["Delay", self.delay])
            try:
                macro_record.append(["Release", key.char])
            except AttributeError:
                macro_record.append(["Release", key])

            self.delay = 0
            self.key_pressed.remove(key)

    def stop(self):
        print("Stopping the macro recording...")
        if self.mouse_active and self.mouse_listener.is_alive():
            print("Stopping mouse listener")
            for i in range(1, 4, 1):
                macro_record.pop(len(macro_record)-i)
            self.mouse_listener.stop()
        if self.keyboard_active and self.keyboard_listener.is_alive():
            print("Stopping keyboard listener")
            self.keyboard_listener.stop()
        if self.timer_thread and self.timer_thread.is_alive():
            self.timer_thread.stop()
        self.delay = 0
        self.running = False

class ReplayMacro(threading.Thread):
    def __init__(self, parent):
        super().__init__()

        global threads_array
        global macro_record

        self.running = True
        self.parent = parent
        self.daemon = True

    def run(self):

        self.keyboard_controller = keyboard.Controller()
        self.mouse_controller = mouse.Controller()

        for i in range(3, 0, -1):
            self.parent.replay_button.setText(f"Recreating Macro in {i}")
            time.sleep(1)

        self.parent.replay_button.setText("Recreating Macro...")

        if len(threads_array) <= 0:
            self.parent.replay_button.setText("Replay")
            return
        
        for item in macro_record:
            action = item[0]
            value = item[1]

            if action == "Delay":
                time.sleep(value/1_000)
            elif action == "Press":
                self.keyboard_controller.press(value)
            elif action == "Release":
                self.keyboard_controller.release(value)
            elif action == "Move":
                x = value[0]
                y = value[1]
                self.mouse_controller.position = (x, y)
            elif action == "Click":
                button = value[0]
                press = value[1]

                if button == "Button.left":
                    button = Button.left
                elif button == "Button.right":
                    button = Button.right

                if press:
                    self.mouse_controller.press(button)
                else:
                    self.mouse_controller.release(button)

        self.stop()

    def stop(self):
        print("stopping replay")
        global macro_working
        macro_working = False

        self.running = False

        self.parent.replay_button.setText("Replay")
        self.parent.cancel_replay = False

        threads_array.clear()

class AutoClicker(threading.Thread):
    def __init__(self, parent):
        super().__init__()
        self.autoclicker_active = False
        self.listener = None
        self.parent = parent
        self.running = True
        self.daemon = True

    def run(self):
        self.parent.autoclicker_button.setText("AutoClicker (OFF) - F9")        
        self.listener = keyboard.Listener(
            on_press=self.on_press,
            on_release=self.on_release
        )
        self.listener.start()
        threading.Thread(target=self.autoclicker, daemon=True).start()

    def autoclicker(self):
        mouse_controller = mouse.Controller()
        while self.running:
            while self.autoclicker_active:
                mouse_controller.click(Button.left)
                time.sleep(0.0001)
            

    def on_press(self, key):
        if key == Key.f9:
            self.autoclicker_active = not self.autoclicker_active

            if self.autoclicker_active:
                self.parent.autoclicker_button.setText("AutoClicker (ON) - F9")
            else:
                self.parent.autoclicker_button.setText("AutoClicker (OFF) - F9")         

    def on_release(self, key):
        return
    
    def stop(self):
        self.listener.stop()
        self.listener = None
        self.running = False
        self.autoclicker_active = False

class MainWindow(QMainWindow):
    def __init__(self, aw=420, ah=420):
        super().__init__()
        global threads_array
        global macro_record

        self.aw = aw
        self.ah = ah

        self.setFixedSize(aw, ah)
        self.setGeometry(50, 50, self.aw, self.ah)
        self.setWindowTitle("AutoBorges")
        self.setWindowIcon(QIcon('autoborges.png'))

        self.checkboxs = []

        main_style = """
            QPushButton {
                background-color: #4CAF50;
                color: white;
                border: none;
                padding: 8px 16px;
                font-size: 18px;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #2c702f;
            }
            QPushButton:pressed {
                background-color: #163a17;
            }
            QPlainTextEdit {
                background-color: #c6ccc8;
                color: #00180e;
                font-size: 14px;
                border: 2px solid #2d412d;
                border-radius: 8px;
            }

            QCheckBox {
                color: #ffffff;
                font-size: 18px;
                font-weight: 500;
                background-color: #4CAF50;
                padding: 5px;
                border-radius: 4px;
                text-align: center;
            }
            QCheckBox::hover{
                color: #275f29;
            }
            QCheckBox::indicator {
                width: 20px;
                height: 20px;
            }
            QCheckBox::indicator:unchecked {
                border: 2px solid #ffffff;
                background-color: #a31010;
                border-radius: 4px;
            }
            QCheckBox::indicator:checked {
                border: 2px solid #ffffff;
                background-color: #275f29;
                border-radius: 4px;
            }
        """

        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        self.layout = QVBoxLayout(central_widget)

        self.autoclicker_button = QPushButton(self, text="AutoClicker")
        self.autoclicker_button.setStyleSheet(main_style)
        self.autoclicker_button.clicked.connect(self.AutoClickerButton)
        self.layout.addWidget(self.autoclicker_button)
        
        self.record_button = QPushButton(self, text="Record")
        self.record_button.setStyleSheet(main_style)
        self.record_button.clicked.connect(self.RecordButton)
        self.layout.addWidget(self.record_button)
        self.is_recording = False

        checkbox_layout = QHBoxLayout()
        possible_records = ['Keyboard', 'Mouse']
        for record in possible_records:
            item = QCheckBox(record)
            item.setStyleSheet(main_style)
            item.setChecked(True)
            self.checkboxs.append([record, item])
            checkbox_layout.addWidget(item)

        self.layout.addLayout(checkbox_layout)

        self.clear_macro_button = QPushButton(self, text="Clear Macro")
        self.clear_macro_button.setStyleSheet(main_style)
        self.clear_macro_button.clicked.connect(self.ClearMacro)
        self.layout.addWidget(self.clear_macro_button)

        self.replay_button = QPushButton(self, text="Replay")
        self.replay_button.setStyleSheet(main_style)
        self.replay_button.clicked.connect(self.ReplayButton)
        self.layout.addWidget(self.replay_button)
        self.cancel_replay = False

        self.test_macro = QPlainTextEdit(self)
        self.test_macro.setPlaceholderText("Try your macro here!")
        self.test_macro.setStyleSheet(main_style)
        self.test_macro.setFixedHeight(100)
        self.layout.addWidget(self.test_macro)

        self.show()

    def AutoClickerButton(self):
        for i, item in enumerate(threads_array):
            if item[0] == "AutoClicker":
                self.autoclicker_button.setText("AutoClicker")
                thread = item[1]
                thread.stop()
                threads_array.pop(i)
                return

        autoclicker_thread = AutoClicker(self)
        threads_array.append(["AutoClicker", autoclicker_thread])
        autoclicker_thread.start()

    def RecordButton(self):
        mouse_check = False
        keyboard_check = False

        for i, item in enumerate(threads_array):
            thread = item[1]
            thread.stop()

        if len(threads_array) > 0:
            threads_array.clear()
            self.record_button.setText("Record")
            return
        
        self.record_button.setText("Recording...")
        self.replay_button.setText("Replay")

        for checkbox in self.checkboxs:
            code = checkbox[0]
            id_checkbox = checkbox[1]

            if code == "Keyboard" and id_checkbox.isChecked():
                print("kb true")
                keyboard_check = True
            elif code == "Mouse" and id_checkbox.isChecked():
                print("mouse true")
                mouse_check = True

        all_record = RecordMacro(keyboard_check, mouse_check)
        threads_array.append(["Macro", all_record])
        all_record.start()

    
    def ClearMacro(self):
        if len(macro_record) > 0:
            macro_record.clear()
        self.replay_button.setText("Replay")

    def ReplayButton(self):
        if len(macro_record) > 0:
            for i, item in enumerate(threads_array):
                if item[0] == "ThreadReplay":
                    if not self.cancel_replay:
                        self.replay_button.setText("Click Again To Cancel")
                        self.cancel_replay = True
                    else:
                        thread = item[1]
                        thread.stop()
                        self.replay_button.setText("Replay")
                        self.cancel_replay = False
                    return
                
            replay_thread = ReplayMacro(self)
            threads_array.append(["ThreadReplay", replay_thread])
            replay_thread.start()
        else:
            self.replay_button.setText("Replay (Empty)")

    def closeEvent(self, event):
        for _, thread in threads_array:
            thread.stop()
        event.accept()

if __name__ == '__main__':
    stylesheet = """
    MainWindow {
        background-image: url("autoborges.png"); 
        background-repeat: no-repeat; 
        background-position: center;
    }
    """

    threads_array = []
    macro_record = []
    macro_working = False

    app = QApplication(sys.argv)
    app.setStyleSheet(stylesheet)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())