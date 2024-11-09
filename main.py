import sys
from pynput import keyboard, mouse
from pynput.mouse import Button
from pynput.keyboard import Key
from PyQt5.QtWidgets import *
from PyQt5.QtGui import QIcon
from PyQt5 import QtCore
import time
import threading
from functools import partial
import os
import pathlib
import json

main_path = f"{pathlib.Path.home()}/BorgeBOT"
config_file = "config.json"

def create_default_folders():
    if not os.path.exists(main_path):
        os.mkdir(main_path)

def create_config_json():
    config_path = f"{main_path}/{config_file}"

    if os.path.exists(config_path):
        return

    data = {
        "AutoClicker": {
            "ClicksDelay": 0.0001,
            "ActionKey": "Key.f9"
        }
    }

    with open(config_path, 'w') as file:
        json.dump(data, file)

def load_config():
    with open(f"{main_path}/{config_file}", 'r') as file:
        config = json.load(file)
    return config

def save_config(config):
    with open(f"{main_path}/{config_file}", 'w') as file:
        json.dump(config, file, indent=4)

class RecordMacro(threading.Thread):
    def __init__(self, parent, keyboard, mouse):
        super().__init__()
        global macro_record

        self.daemon = True
        self.running = True

        self.delay = 0

        self.keyboard_active = keyboard
        self.mouse_active = mouse
        self.parent = parent

    def run(self):
        
        for i in range(3, 0, -1):
            if self.running:
                self.parent.record_button.setText(f"Recording in {i}...")
                time.sleep(1)

        if self.running:
            self.parent.record_button.setText("Recording...")

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
        if self.running:
            macro_record.append(["Delay", self.delay])
            macro_record.append(["Move", (x, y)])
            self.delay_mouse_pos = 0
            self.delay = 0

    
    def mouse_on_click(self, x, y, button, pressed):
        if self.running:
            macro_record.append(["Delay", self.delay])
            macro_record.append(["Click", (str(button), pressed)])
            self.delay = 0
        
    def mouse_on_scroll(self, x, y, dx, dy):
        #use for debug
        for item in macro_record:
            print(item)

    def kb_on_press(self, key):
        if self.running:
            macro_record.append(["Delay", self.delay])
            try:
                macro_record.append(["Press", key.char])
            except AttributeError:
                macro_record.append(["Press", key])

            self.delay = 0

    def kb_on_release(self, key):
        if self.running:
            macro_record.append(["Delay", self.delay])
            try:
                macro_record.append(["Release", key.char])
            except AttributeError:
                macro_record.append(["Release", key])

            self.delay = 0

    def stop(self):
        print("Stopping the macro recording...")
        try:
            if self.mouse_active and self.mouse_listener.is_alive():
                print("Stopping mouse listener")
                self.mouse_listener.stop()
            if self.keyboard_active and self.keyboard_listener.is_alive():
                print("Stopping keyboard listener")
                self.keyboard_listener.stop()
            if self.timer_thread and self.timer_thread.is_alive():
                self.timer_thread.stop()
        except AttributeError:
            pass
        self.delay = 0
        self.running = False

class ReplayMacro(threading.Thread):
    def __init__(self, parent, repeat):
        super().__init__()

        global threads_array
        global macro_record
        global macro_working

        self.running = True
        self.parent = parent
        self.daemon = True
        self.macro_working = True
        self.repeat = repeat

    def run(self):

        for i in range(3, 0, -1):
            self.parent.replay_button.setText(f"Recreating Macro in {i}")
            time.sleep(1)
        
        self.keyboard_controller = keyboard.Controller()
        self.mouse_controller = mouse.Controller()

        self.parent.replay_button.setText("Recreating Macro...")

        if len(threads_array) <= 0:
            self.parent.replay_button.setText("Replay")
            return
        
        for _ in range(self.repeat):
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

        self.config_json = json.load(open(f"{main_path}/{config_file}", 'r'))
        
        self.action_key = self.config_json['AutoClicker']['ActionKey']
        self.click_delay = self.config_json['AutoClicker']['ClicksDelay']

    def run(self):
        self.parent.autoclicker_button.setText(f"AutoClicker (OFF) - {str(self.action_key.replace(".", '').replace('Key', '').strip("'")).upper()}")        
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
                time.sleep(self.click_delay)
            

    def on_press(self, key):
        try:
            if key.char == eval(self.action_key):
                self.autoclicker_active = not self.autoclicker_active
        except AttributeError:
            if key == eval(self.action_key):
                self.autoclicker_active = not self.autoclicker_active

        if self.autoclicker_active:
            self.parent.autoclicker_button.setText(f"AutoClicker (ON) - {str(self.action_key.replace(".", '').replace('Key', '').strip("'")).upper()}")
        else:
            self.parent.autoclicker_button.setText(f"AutoClicker (OFF) - {str(self.action_key.replace(".", '').replace('Key', '').strip("'")).upper()}")

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

        self.edit_macro_button = QPushButton(self, text="Edit Macro")
        self.edit_macro_button.setStyleSheet(main_style)
        self.edit_macro_button.clicked.connect(self.EditMacroButton)
        self.layout.addWidget(self.edit_macro_button)

        self.replay_button = QPushButton(self, text="Replay")
        self.replay_button.setStyleSheet(main_style)
        self.replay_button.clicked.connect(self.ReplayButton)
        self.layout.addWidget(self.replay_button)
        self.cancel_replay = False

        self.test_macro = QPlainTextEdit(self)
        self.test_macro.setPlaceholderText("Try your macro here!")
        self.test_macro.setStyleSheet(main_style)
        self.test_macro.setFixedHeight(50)
        self.layout.addWidget(self.test_macro)

        self.advanced_config_button = QPushButton(self, text="Advanced Config")
        self.advanced_config_button.setStyleSheet(main_style)
        self.advanced_config_button.clicked.connect(self.ConfigButton)
        self.advanced_config_button.setFixedSize(200, 40)
        self.layout.addWidget(self.advanced_config_button)

        self.show()

    def EditMacroButton(self):
        telaedit = EditMacroWindow()
        telaedit.exec_()

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

        all_record = RecordMacro(self, keyboard_check, mouse_check)
        threads_array.append(["Macro", all_record])
        all_record.start()

    
    def ClearMacro(self):
        if len(macro_record) > 0:
            macro_record.clear()
        self.replay_button.setText("Replay")

    def ReplayButton(self):
        global macro_working
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

            if not macro_working:
                #Puxar o repeat das config avançada dps
                replay_thread = ReplayMacro(self, repeat=1)
                threads_array.append(["ThreadReplay", replay_thread])
                replay_thread.start()
        else:
            self.replay_button.setText("Replay (Empty)")
    
    def ConfigButton(self):
        tela = ConfigWindow(self)
        tela.exec_()

    def closeEvent(self, event):
        for _, thread in threads_array:
            thread.stop()
        event.accept()

class EditMacroWindow(QDialog):
    def __init__(self):
        super().__init__()

        global macro_record
        self.index_to_remove = set()
        
        self.setWindowTitle("Edit Your Macro")
        self.setWindowIcon(QIcon('autoborges.png'))
        self.setGeometry(300, 300, 400, 300)
        self.setFixedSize(1000, 600)

        self.setStyleSheet("""
            EditMacroWindow {
                background-image: url("mimosacomnarget.jpg"); 
                background-repeat: no-repeat; 
                background-position: center;
            }

            QScrollArea {
                background: transparent;
            }

            QLabel {
                font-size: 18px;
                font-weight: bold;
                padding: 8px;
                border-radius: 5px;
            }
            
            QPushButton {
                padding: 10px;
                font-size: 14px;
                background-color: #4CAF50;
                color: white;
                border: none;
                border-radius: 5px;
            }

            QPushButton:hover {
                background-color: #45a049;
            }

            #stay{
                color: #ffffff;
                background-color: #30ca44;
            }
            #remove{
                color: #ff0000;
                background-color: #007c1b;
            }

            #stay:hover{
                color: #2cd450
            }
            #remove:hover{
                color: #007a1b
            }
        """)

        layout = QVBoxLayout(self)

        scroll_area = QScrollArea(self)
        scroll_area.setWidgetResizable(True)
        scroll_area.viewport().setStyleSheet("background: transparent;")

        content_widget = QWidget()
        content_layout = QVBoxLayout(content_widget)

        for i, item in enumerate(macro_record):
            action = item[0]
            value = item[1]

            label = QLabel(f"{action}: {value}")
            label.mousePressEvent = partial(self.item_clicked, i, label)
            label.setObjectName("stay")
            content_layout.addWidget(label)

        scroll_area.setWidget(content_widget)
        layout.addWidget(scroll_area)

        self.save_button = QPushButton(self, text="Save")
        self.save_button.clicked.connect(self.saveButton)
        layout.addWidget(self.save_button)

    def saveButton(self):
        for i, index in enumerate(self.index_to_remove):
            macro_record.pop(index-i)
        self.closeWindow()

    def item_clicked(self, item, label_obj, event):
        if item in self.index_to_remove:
            label_obj.setObjectName("stay")
            self.index_to_remove.remove(item)
        else:
            label_obj.setObjectName("remove")
            self.index_to_remove.add(item)
        
        label_obj.style().unpolish(label_obj)
        label_obj.style().polish(label_obj)

    def closeWindow(self):
        self.accept()

class ConfigWindow(QDialog):
    def __init__(self, parent, aw = 500, ah = 500):
        super().__init__()

        self.aw = aw
        self.ah = ah

        self.setFixedSize(aw, ah)
        self.setGeometry(50, 50, self.aw, self.ah)
        self.setWindowIcon(QIcon('autoborges.png'))

        global threads_array

        for item in threads_array:
            if item[0] == "AutoClicker":
                parent.AutoClickerButton()

        stylesheet = """
        ConfigWindow {
            background-image: url("gedagedigedagedao.png"); 
            background-position: center;
        }

        QLabel{
            font-size: 18px;
            color: #f7f7f7;
            font-weight: bold;
            padding: 3px;
            background-color: #1e471f;
            border-radius: 15px;
        }

        QPushButton {
            background-color: #4CAF50;
            color: white;
            border: none;
            padding: 8px 16px;
            font-size: 18px;
            border-radius: 8px;
        }
        QPushButton:hover {
            background-color: #2c702f;
        }
        QPushButton:pressed {
            background-color: #163a17;
        }

        QTextEdit {
            font-size: 14px;
            color: #706464;
            background-color: #f0f0f0;
            border: 2px solid #4CAF50;
            border-radius: 10px;
            selection-background-color: #A5D6A7;
        }

        #title{
            color: #c5ffca;
        }
        """

        self.setWindowTitle("Advanced Configuration")
        self.setGeometry(100, 100, 400, 300)

        self.config_json = load_config()
        self.action_key = self.config_json['AutoClicker']['ActionKey']
        self.delay_autoclicker = self.config_json['AutoClicker']['ClicksDelay']
        self.new_key = None
        self.new_delay = None

        self.layout = QVBoxLayout()

        self.autoclickertext = QLabel(text="AutoClicker")
        self.autoclickertext.setObjectName("title")
        self.autoclickertext.setFixedSize(150, 40)
        self.autoclickertext.setAlignment(QtCore.Qt.AlignCenter)
        self.layout.addWidget(self.autoclickertext)

        h_layout = QHBoxLayout()
        
        self.action_key_autoclicker = QLabel(text="Key: " + str(self.action_key.replace(".", '').replace('Key', '').strip("'")).upper())
        self.action_key_autoclicker.setFixedSize(80, 40)
        self.action_key_autoclicker.setAlignment(QtCore.Qt.AlignCenter)
        h_layout.addWidget(self.action_key_autoclicker)

        self.change_action_key = QPushButton(text="Change Action Key")
        self.change_action_key.clicked.connect(self.ChangeActionKeyAC)
        h_layout.addWidget(self.change_action_key)

        self.layout.addLayout(h_layout)

        h_layout = QHBoxLayout()
        
        self.delay_label = QLabel(text="Clicks delay")
        h_layout.addWidget(self.delay_label)

        self.delay_range = QTextEdit()
        self.delay_range.setPlaceholderText(str(self.delay_autoclicker))
        self.delay_range.setFixedHeight(35)
        self.delay_range.setFixedWidth(200)
        h_layout.addWidget(self.delay_range)

        self.layout.addLayout(h_layout)

        self.save_button = QPushButton("Salvar", self)
        self.save_button.clicked.connect(self.save_config)
        self.layout.addWidget(self.save_button)

        self.setLayout(self.layout)

        self.setStyleSheet(stylesheet)

    def ChangeActionKeyAC(self):
        self.action_key_autoclicker.setText("...")

        self.keyboard_listener = keyboard.Listener(
                    on_press=self.kb_on_press
                )
        self.keyboard_listener.start()

    def kb_on_press(self, key):
        self.new_key = str(key)
        self.action_key_autoclicker.setText("Key: " +str(self.new_key.replace(".", '').replace('Key', '').strip("'")).upper())
        self.keyboard_listener.stop()

    def save_config(self):
        
        try:
            value = float(self.delay_range.toPlainText())
            self.new_delay = value
        except ValueError:
            pass

        if self.new_key != None:
            self.config_json["AutoClicker"]["ActionKey"] = self.new_key
        if self.new_delay != None:
            self.config_json["AutoClicker"]["ClicksDelay"] = self.new_delay

        save_config(self.config_json)
        self.accept()

if __name__ == '__main__':
    create_default_folders()
    create_config_json()
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