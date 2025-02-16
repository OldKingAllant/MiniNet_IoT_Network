import sys
import random
import datetime
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from PyQt5.QtCore import QTimer, Qt, QSize
from PyQt5.QtGui import QIcon, QFont
from PyQt5.QtWidgets import QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QSizePolicy, QScrollArea, QDialog, QLineEdit, QListWidget, QListWidgetItem, QAbstractItemView

from app_detail.server_requests import *

import typing

class Box(QWidget):
    def __init__(self, text: str, heater: typing.Optional[typing.Tuple[str, str]], server_url: str):
        super().__init__()
        self.text = text
        self.values = []
        self.timestamps = []
        self.graph_visible = True
        self.heater = heater
        self.server_url = server_url
        self.initUI()

    def initUI(self):
        self.layout = QVBoxLayout()
        self.setLayout(self.layout)
        
        top_layout = QHBoxLayout()
        self.label = QLabel(self.text)

        font = QFont("Verdana", 60, QFont.Bold)
        self.label.setFont(font)
        self.label.setAlignment(Qt.AlignCenter)

        button1 = QPushButton()
        button1.setStyleSheet("background-color: white;")
        button1.setIcon(QIcon("./assets/pulonof.png"))
        button1.setIconSize(QSize(100,100))
        button1.clicked.connect(self.toggle_graph) 

        button_size = 150

        if self.heater:
            self.button2 = QPushButton()
            self.button2.setStyleSheet("background-color: darkRed;")
            self.button2.setIcon(QIcon("./assets/termos.png"))
            self.button2.setIconSize(QSize(200,200))
            self.button2.clicked.connect(self.switch_heater_status)
            self.button2.setFixedSize(button_size, button_size)
            self.heater_on = False

        
        button1.setFixedSize(button_size, button_size)
        top_layout.addWidget(button1)
        top_layout.addWidget(self.label)

        if self.heater:
            top_layout.addWidget(self.button2)
        
        top_widget = QWidget()
        top_widget.setLayout(top_layout)
        top_widget.setFixedHeight(200)
        
        self.layout.addWidget(top_widget)
        
        self.fig, self.ax = plt.subplots()
        self.canvas = FigureCanvas(self.fig)
        self.layout.addWidget(self.canvas)
        
        self.setFixedHeight(800)
        self.update_plot()

    def toggle_graph(self):
        self.graph_visible = not self.graph_visible
        self.canvas.setVisible(self.graph_visible)
        if hasattr(self, 'button2'):
            self.button2.setVisible(self.graph_visible)
            self.button2.setStyleSheet("background-color: darkRed;")

    def update_heater_status(self, is_on: bool):
        if self.heater_on == is_on:
            return 
        self.change_button2_color()
        self.heater_on = is_on

    def switch_heater_status(self):
        self.heater_on = not self.heater_on
        if self.heater_on:
            start_actuator(self.server_url, self.heater[0], self.heater[1])
        else:
            stop_actuator(self.server_url, self.heater[0], self.heater[1])
        self.change_button2_color()

    def change_button2_color(self):
        if not hasattr(self, 'button2'):
            return
        current_color = self.button2.styleSheet()
        if "darkRed" in current_color:
            self.button2.setStyleSheet("background-color: darkGreen;")
        else:
            self.button2.setStyleSheet("background-color: darkRed;")

    def update_plot(self):
        self.ax.clear()
        if self.timestamps:
            self.ax.plot(self.timestamps, self.values)
        self.ax.set_ylim(5, 30)
        self.canvas.draw()

    def add_value(self, value):
        current_time = datetime.datetime.now().strftime("%H:%M:%S")
        self.values.append(value)
        self.timestamps.append(current_time)
        if len(self.values) > 10:
            self.values.pop(0)
            self.timestamps.pop(0)
        self.update_plot()

    def add_values(self, values: typing.List):
        values = values[-10:]
        self.values.extend([value['new_temp'] for value in values])
        self.timestamps.extend([datetime.datetime.fromtimestamp(value['timestamp']).strftime("%H:%M:%S") for value in values])
        if len(self.values) > 10:
            self.values = self.values[-10:]
            self.timestamps = self.timestamps[-10:]
        self.update_plot()
        return

class TransparentBoxWithButton(QWidget):
    def __init__(self, text, main_window):
        super().__init__()
        self.main_window = main_window
        self.initUI(text)

    def initUI(self, text):
        layout = QVBoxLayout()
        self.setLayout(layout)
        label = QLabel(text)
        layout.addWidget(label)
        self.setFixedHeight(600)
        self.setStyleSheet("border: none;")

        add_box_button = QPushButton()
        add_box_button.setFixedSize(200, 200)
        add_box_button.setStyleSheet("""
            QPushButton {
                border: 3px solid black;
                border-radius: 10px;
                background-color: #f0f0f0;
            }
            QPushButton:hover {
                background-color: #e0e0e0;
            }
            QPushButton:pressed {
                background-color: #d0d0d0;
            }
        """)

        button_label = QLabel("Add")
        button_label.setAlignment(Qt.AlignCenter)
        button_label.setFont(QFont("Verdana", 35, QFont.Bold))
        button_label.setWordWrap(True)
        button_label.setStyleSheet("color: black;")

        button_layout = QVBoxLayout(add_box_button)
        button_layout.addWidget(button_label)
        button_layout.setContentsMargins(0, 0, 0, 0)
        button_layout.setAlignment(Qt.AlignCenter)

        add_box_button.clicked.connect(self.main_window.open_add_box_dialog)
        layout.addWidget(add_box_button, alignment=Qt.AlignCenter)

class TransparentBox(QWidget):
    def __init__(self, text):
        super().__init__()
        self.initUI(text)

    def initUI(self, text):
        layout = QVBoxLayout()
        self.setLayout(layout)
        label = QLabel(text)
        layout.addWidget(label)
        self.setFixedHeight(600)
        self.setStyleSheet("border: none;")

class AddBoxDialog(QDialog):
    def __init__(self, sensors: typing.List[typing.Tuple[str, str]]):
        super().__init__()
        self.setWindowTitle("Add New Box")
        self.setFixedSize(300, 400)
        
        layout = QVBoxLayout()
        self.setLayout(layout)
        
        self.sensor_list = QListWidget()
        self.sensor_list.setSelectionMode(QAbstractItemView.SingleSelection)
        for sensor in sensors:
            item = QListWidgetItem(f'{sensor[0]}/{sensor[1]}')
            self.sensor_list.addItem(item)
        
        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("Enter box name")
        self.name_input.setStyleSheet("""
            QLineEdit {
                border: 2px solid black;
                border-radius: 5px;
                padding: 5px;
                font-size: 14px;
            }
        """)
        
        add_button = QPushButton("Add Box")
        add_button.setStyleSheet("""
            QPushButton {
                border: 3px solid black;
                border-radius: 10px;
                background-color: #f0f0f0;
                font-size: 16px;
                font-weight: bold;
                color: black;
            }
            QPushButton:hover {
                background-color: #e0e0e0;
            }
            QPushButton:pressed {
                background-color: #d0d0d0;
            }
        """)
        add_button.clicked.connect(self.accept)
        
        layout.addWidget(self.sensor_list)
        layout.addWidget(self.name_input)
        layout.addWidget(add_button)
    
    def get_name(self):
        return self.name_input.text()
    
    def get_selected_sensor(self):
        selected_items = self.sensor_list.selectedItems()
        if selected_items:
            return selected_items[0].text()
        return None

class MainWindow(QMainWindow):
    def __init__(self, 
                sensor_list: typing.List[typing.Tuple[str, str]], 
                open_sensors: typing.List[int],
                heaters: typing.List[typing.Tuple[str, str]],
                connection_list: typing.List[typing.Tuple[int, int]],
                server_url: str):
        super().__init__()
        self.sensors = sensor_list
        self.all_sensors = sensor_list.copy()
        self.heaters = heaters
        self.server_url = server_url

        for sensor, heater in connection_list:
            if sensor >= len(self.all_sensors) or heater >= len(self.heaters):
                raise ValueError("Found invalid connection")

        self.connections = connection_list
        self.initUI(open_sensors)

    def initUI(self, open_sensors: typing.List[int]):
        self.setWindowTitle('Main Window')

        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        central_widget_layout = QVBoxLayout(central_widget)
        central_widget_layout.addWidget(scroll_area)

        scroll_content = QWidget()
        scroll_area.setWidget(scroll_content)

        self.layout: QVBoxLayout = QVBoxLayout(scroll_content)

        self.boxes: typing.List[typing.Tuple[typing.Tuple[str, str], Box]] = []
        self.row_widgets: typing.List[QWidget] = []

        num_rows = (len(open_sensors) + 1) // 2

        for i in range(num_rows):
            row_widget = QWidget()
            row_layout = QHBoxLayout(row_widget)
            row_layout.setContentsMargins(0, 0, 0, 0)
            row_layout.setSpacing(0)

            sensor_index_indirect = open_sensors[i * 2]
            sensor1 = self.all_sensors[sensor_index_indirect]

            heater_list = list(filter(lambda conn: conn[0] == sensor_index_indirect, self.connections))
            heater = None
            if len(heater_list) > 0:
                heater = self.heaters[heater_list[0][1]]

            box1 = Box(f'{sensor1[0]}/{sensor1[1]}', heater=heater, server_url=self.server_url)
            row_layout.addWidget(box1)
            self.boxes.append((sensor1, box1))
            self.sensors.remove(sensor1)

            if i*2 + 1 < len(open_sensors):
                sensor_index_indirect = open_sensors[i * 2 + 1]
                heater_list = list(filter(lambda conn: conn[0] == sensor_index_indirect, self.connections))
                heater = None
                if len(heater_list) > 0:
                    heater = self.heaters[heater_list[0][1]]
                sensor2 = self.all_sensors[sensor_index_indirect]
                box2 = Box(f'{sensor2[0]}/{sensor2[1]}', heater=heater, server_url=self.server_url)
                row_layout.addWidget(box2)
                self.boxes.append((sensor2, box2))
                self.sensors.remove(sensor2)
            else:
                self.transparent_box_with_button = TransparentBoxWithButton('', self)
                row_layout.addWidget(self.transparent_box_with_button)

            self.row_widgets.append(row_widget)
            self.layout.addWidget(row_widget)

        if len(open_sensors) % 2 == 0:
            self.transparent_box_with_button = TransparentBoxWithButton('', self)
            self.layout.addWidget(self.transparent_box_with_button)

        self.showMaximized()
        
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_values)
        self.timer.start(10000)  

        self.update_values()

    def update_values(self):
        for sensor, box in self.boxes:
            if self.server_url == '':
                new_value = random.randint(5, 30)
                box.add_value(new_value)
            else:
                values = get_sensor_data(self.server_url, sensor[0], sensor[1])
                if values != None:
                    print(f'{sensor[0]}/{sensor[1]} {values}')
                    box.add_values(values)
                if box.heater != None:
                    status = get_actuator_status(self.server_url, box.heater[0], box.heater[1])
                    if status != None:
                        print(f'{box.heater[0]}/{box.heater[1]} {status}')
                        box.update_heater_status(status['is_on'])

    def open_add_box_dialog(self):
        dialog = AddBoxDialog(self.sensors)
        if dialog.exec_():
            new_box_name = dialog.get_name()
            selected_sensor = dialog.get_selected_sensor()
            if new_box_name and selected_sensor:
                sensor_parts = selected_sensor.split('/')
                sensor_entry: typing.Tuple[str, str] = (sensor_parts[0], sensor_parts[1])
                sensor_index = self.all_sensors.index(sensor_entry)

                heater_list = list(filter(lambda conn: conn[0] == sensor_index, self.connections))
                heater = None
                if len(heater_list) > 0:
                    heater = self.heaters[heater_list[0][1]]

                new_box = Box(new_box_name, heater=heater, server_url=self.server_url)
                
                self.sensors.remove(sensor_entry)
                
                self.remove_all_transparent_boxes()
                
                last_row_layout = self.row_widgets[-1].layout()
                if last_row_layout.count() >= 2:
                    row_widget = QWidget()
                    row_layout = QHBoxLayout(row_widget)
                    row_layout.setContentsMargins(0, 0, 0, 0)
                    row_layout.setSpacing(0)
                    row_layout.addWidget(new_box)
                    self.row_widgets.append(row_widget)
                    self.layout.addWidget(row_widget)
                    last_row_layout = row_layout
                else:
                    last_row_layout.addWidget(new_box)

                self.boxes.append((sensor_entry, new_box))

                self.transparent_box_with_button = TransparentBoxWithButton('', self)
                if len(self.boxes) % 2 == 1:
                    last_row_layout.addWidget(self.transparent_box_with_button)
                else:
                    row_widget = QWidget()
                    row_layout = QHBoxLayout(row_widget)
                    row_layout.setContentsMargins(0, 0, 0, 0)
                    row_layout.setSpacing(0)
                    row_layout.addWidget(self.transparent_box_with_button)
                    additional_transparent_box = TransparentBox('')
                    row_layout.addWidget(additional_transparent_box)
                    self.row_widgets.append(row_widget)
                    self.layout.addWidget(row_widget)

    def remove_all_transparent_boxes(self):
        if self.transparent_box_with_button != None:
            self.layout.removeWidget(self.transparent_box_with_button)
            self.transparent_box_with_button.destroy()
            self.transparent_box_with_button = None

        for row_widget in self.row_widgets:
            row_layout = row_widget.layout()
            for i in reversed(range(row_layout.count())):
                widget = row_layout.itemAt(i).widget()
                if isinstance(widget, TransparentBox) or isinstance(widget, TransparentBoxWithButton):
                    row_layout.takeAt(i).widget().destroy()
                    row_layout.removeWidget(widget)

def main():
    app = QApplication(sys.argv)
    sensors = [('H1', 'temp_sensor'), ('H2', 'temp_sensor'), ('H3', 'temp_sensor')]
    heaters = [('H1', 'heater'), ('H3', 'heater')]
    connection_list = [(0, 0), (2, 1)]
    window = MainWindow(sensor_list=sensors, 
                        open_sensors=[0], 
                        heaters=heaters, 
                        connection_list=connection_list,
                        server_url='')
    window.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()