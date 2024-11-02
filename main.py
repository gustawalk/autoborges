import sys
from pynput import keyboard, mouse
from pynput.mouse import Button
from pynput.keyboard import Key
from PyQt5.QtWidgets import *
from PyQt5.QtGui import QIcon
import time
import threading

class RecordMouse(threading.Thread):
    def __init__(self):
        super().__init__()
        global macro_mouse
        global macro_working

        self.daemon = True
        self.timer = 0
        self.running = True
        self.subtimer = 0

    def run(self):
        print("Starting mouse thread")
        self.timer_thread = threading.Thread(target=self.timer_delay, daemon=True)
        self.timer_thread.start()

        self.listener = mouse.Listener(
            on_move=self.on_move,
            on_click=self.on_click,
            on_scroll=self.on_scroll
        )
        self.listener.start()
    
    def on_move(self, x, y):
        if not macro_working and self.running:
            if self.subtimer <= 5:
                self.subtimer += 1
                return
            macro_mouse.append(["Delay", self.timer])
            macro_mouse.append(['Move', (x, y)])
            self.timer = 0
            self.subtimer = 0

    def on_click(self, x, y, button, pressed):
        if not macro_working and self.running:
            macro_mouse.append(["Delay", self.timer])
            macro_mouse.append(["Click", (str(button), pressed)])
            self.timer = 0
            
    def on_scroll(self, x, y, dx, dy):
        return
    
    def timer_delay(self):
        while self.running:
            self.timer += 1
            time.sleep(0.01)
    
    def stop(self):
        print("Parando a gravação do mouse")
        for i in range(3): #removendo o ultimo click para evitar loop
            print(f"Removing {macro_mouse[len(macro_mouse)-1]}")
            macro_mouse.pop(len(macro_mouse)-1)
        self.running = False
        self.listener.stop()
        self.listener = None
        self.timer = 0

class RecordKeyboard(threading.Thread):
    def __init__(self):
        super().__init__()
        global macro_keyboard
        global macro_working
        self.daemon = True
        self.timer = 0
        self.couting = True
        self.key_pressed = set()

    def run(self):
        print("Starting keyboard thread")
        self.timer_thread = threading.Thread(target=self.timer_delay, daemon=True)
        self.timer_thread.start()

        self.listener = keyboard.Listener(
            on_press=self.on_press,
            on_release=self.on_release
        )
        self.listener.start()

    def timer_delay(self):
        while self.couting:
            self.timer += 1
            time.sleep(0.01)

    def on_press(self, key):
        if not macro_working:
            if key not in self.key_pressed:
                macro_keyboard.append(["Delay", self.timer])
                self.timer = 0
                try:
                    macro_keyboard.append(["Press", key.char])
                except AttributeError:
                    macro_keyboard.append(["Press", key])
                    
                self.key_pressed.add(key)
            
                print(key)
                print(self.key_pressed)

    def on_release(self, key):
        if not macro_working:
            if key in self.key_pressed:
                macro_keyboard.append(["Delay", self.timer])
                self.timer = 0
                try:
                    macro_keyboard.append(["Release", key.char])
                except AttributeError:
                    macro_keyboard.append(["Release", key])
                self.key_pressed.remove(key)

                print(key)

    def stop(self):
        print("Foi pra fechar aqui")
        self.listener.stop()
        self.couting = False
        self.timer = 0

class ReplayMacro(threading.Thread):
    def __init__(self, macrokb, macroms, parent):
        super().__init__()

        global threads_array

        self.macrokb = macrokb
        self.macromouse = macroms
        self.running = True
        self.parent = parent
        self.daemon = True
        self.count =  0

        print(macrokb)
        print(macroms)

    def run(self):
        global macro_working

        self.keyboard_controller = keyboard.Controller()
        self.mouse_controller = mouse.Controller()

        for i in range(3, 0, -1):
            self.parent.replay_button.setText(f"Recreating Macro in {i}")
            time.sleep(1)

        self.parent.replay_button.setText("Recreating Macro...")

        if len(self.macrokb) == 0 and len(self.macromouse) == 0:
            self.parent.replay_button.setText("Replay")
            return

        if len(self.macrokb) > 0:
            self.count += 1
            threading.Thread(target=self.run_macro_kb, daemon=True).start()
        if len(self.macromouse) > 0:
            print("started mouse")
            self.count  += 1
            threading.Thread(target=self.run_macro_mouse, daemon=True).start()

        
        threading.Thread(target=self.check_finish, daemon=True).start()


    def run_macro_kb(self):
        global macro_working

        for item in macro_keyboard:
            if self.running:
                macro_working = True
                action = item[0]
                value = item[1]

                if action == "Delay":
                    if value/100 > 0.1:
                        time.sleep(value/100)
                elif action == "Press":
                    self.keyboard_controller.press(value)
                elif action == "Release":
                    self.keyboard_controller.release(value)

                print(action, value)
        
        self.count -= 1
        print("Acabou teclado")
    
    def run_macro_mouse(self):
        global macro_working

        for item in macro_mouse:
            if self.running:
                macro_working = True
                action = item[0]
                value = item[1]

                if action == "Delay":
                    if value/100 > 0.1:
                        time.sleep(value/1000)
                        print(f"delay {value/100}")
                elif action == "Move":
                    x = value[0]
                    y = value[1]
                    self.mouse_controller.position = (x, y)
                    print("moving")
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

                    print("clicking")
        
        print("Acabou mouse")
        self.count -= 1

    def check_finish(self):
        while self.running:
            if self.count == 0:
                self.stop()
                print("Cout = 0")

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
        global macro_keyboard

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
        print(threads_array)

        for i, item in enumerate(threads_array):
            print(item)
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
                macro_kbthread = RecordKeyboard()
                threads_array.append(["ThreadKB", macro_kbthread])
                macro_kbthread.start()
            if code == "Mouse" and id_checkbox.isChecked():
                macro_mousethread = RecordMouse()
                threads_array.append(["ThreadMouse", macro_mousethread])
                macro_mousethread.start()

        return
    
    def ClearMacro(self):
        if len(macro_keyboard) != 0:
            macro_keyboard.clear()
        if len(macro_mouse) != 0:
            macro_mouse.clear()
        self.replay_button.setText("Replay")

    def ReplayButton(self):
        global macro_mouse, macro_keyboard

        if len(macro_keyboard) != 0 or len(macro_mouse) != 0:
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
                
            replay_thread = ReplayMacro(macro_keyboard, macro_mouse, self)
            threads_array.append(["ThreadReplay", replay_thread])
            replay_thread.start()
        else:
            print(len(macro_mouse))
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
    macro_keyboard = []
    macro_mouse = []
    macro_working = False

    app = QApplication(sys.argv)
    app.setStyleSheet(stylesheet)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())