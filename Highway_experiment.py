import sys
import random
from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt5.QtCore import Qt

# Глобальные параметры
TIMER_INTERVAL = 1
DT = TIMER_INTERVAL / 1000.0
SCALE = 8
SCENE_WIDTH = 1200
SCENE_HEIGHT = 200
REMOVAL_THRESHOLD = SCENE_WIDTH / SCALE
CAR_WIDTH = 5
CAR_HEIGHT = 20
SPEED_SCALE = 2
CRASH_DURATION = 1000
NEXT_CRASH_DURATION = CRASH_DURATION + 200
NEEDED_SPACE = 15


# координата машины - позиция заднего бампера, длина машины - константа 5
class Car:
    def __init__(self, cur_experiment, initial_speed, next_car=None):
        self.cur_experiment = cur_experiment
        self.status = 'constant'
        self.initial_speed = float(initial_speed) / SPEED_SCALE
        self.cur_speed = float(initial_speed) / SPEED_SCALE
        self.need_speed = float(initial_speed) / SPEED_SCALE
        self.coef_acceleration = self.cur_experiment.coef_acceleration
        self.coef_slowdown = self.cur_experiment.coef_slowdown
        self.slowness_duration = 0
        self.position = 0.0
        self.length = CAR_WIDTH
        self.next_car = next_car
        self.crash_timer = 0

    def step(self, dt):
        if self.status == 'crash':
            if self.crash_timer > 0:
                self.crash_timer -= 1
            else:
                if (self.next_car and self.next_car.status != 'crash') or not self.next_car:
                    if self.next_car and (self.position + self.length) < self.next_car.position or not self.next_car:
                        self.cur_speed = 0
                        self.status = 'acceleration'
                        self.crash_timer = 0
            return
        if self.slowness_duration > 0:
            self.cur_speed = 0
            self.slowness_duration -= 1
            self.status = 'slowdown'
        else:
            if self.next_car:
                car_length = self.length
                distance_to_next = self.next_car.position - (self.position + car_length)
                safe_distance = 3.0 * car_length  # три корпуса
                if distance_to_next < safe_distance:
                    self.need_speed = self.next_car.cur_speed
                    if self.cur_speed > self.need_speed:
                        new_speed = self.cur_speed - self.coef_slowdown * dt
                        self.cur_speed = max(new_speed, self.need_speed)
                        self.status = 'slowdown'
                    elif self.cur_speed < self.need_speed:
                        new_speed = self.cur_speed + (self.coef_acceleration / 2) * dt
                        self.cur_speed = min(new_speed, self.need_speed)
                        self.status = 'acceleration'
                    else:
                        self.status = 'constant'
                else:
                    if self.cur_speed < self.initial_speed:
                        new_speed = self.cur_speed + self.coef_acceleration * dt
                        self.cur_speed = min(new_speed, self.initial_speed)
                        self.status = 'acceleration'
                    else:
                        self.cur_speed = self.initial_speed
                        self.status = 'constant'
            else:
                if self.cur_speed < self.initial_speed:
                    new_speed = self.cur_speed + self.coef_acceleration * dt
                    self.cur_speed = min(new_speed, self.initial_speed)
                    self.status = 'acceleration'
                else:
                    self.status = 'constant'

            if self.next_car and (self.position + self.length) > self.next_car.position:
                self.crash(delay=CRASH_DURATION)
                if self.next_car.status != 'crash':
                    self.next_car.crash(delay=NEXT_CRASH_DURATION)
                return

        self.compute_next_coord(dt)

    def crash(self, delay):
        self.status = 'crash'
        self.cur_speed = 0.0
        self.crash_timer = delay

    def delay(self, ticks):
        self.need_speed = 0
        self.slowness_duration = ticks

    def get_coord(self):
        return self.position

    def get_speed(self):
        return self.cur_speed

    def get_status(self):
        return self.status

    def compute_next_coord(self, dt):
        self.position += self.cur_speed * dt


class Highway:
    def __init__(self, cur_experiment):
        self.cur_experiment = cur_experiment
        self.cars = []

    def step(self, dt):
        for i, car in enumerate(self.cars):
            if i < len(self.cars) - 1:
                car.next_car = self.cars[i + 1]
            else:
                car.next_car = None
            car.step(dt)
        if self.cur_experiment.time_to_next_car <= 0:
            if self.is_highway_free():
                init_speed = random.uniform(self.cur_experiment.min_speed, self.cur_experiment.max_speed)
                self.add_car(init_speed, self.cur_experiment.coef_acceleration, self.cur_experiment.coef_slowdown)

        self.cars = [car for car in self.cars if car.position < REMOVAL_THRESHOLD]

    def add_car(self, init_speed, coef_acc, coef_slow):
        if self.is_highway_free():
            new_car = Car(self.cur_experiment, init_speed, None)
            new_car.position = -15.0
            self.cars.insert(0, new_car)

    def is_highway_free(self):
        if not self.cars:
            return True
        first_car = min(self.cars, key=lambda car: car.position)
        return first_car.position > NEEDED_SPACE

    def clear_highway(self):
        self.cars = []

    def get_all_cars(self):
        return self.cars


class Experiment:
    def __init__(self):
        self.cur_highway = Highway(self)
        self.time_to_next_car = 0
        self.min_speed = 30
        self.max_speed = 50
        self.min_time_spawn = 2
        self.max_time_spawn = 4
        self.coef_acceleration = 10
        self.coef_slowdown = 10

    def step(self, dt=DT):
        self.time_to_next_car -= 1
        self.cur_highway.step(dt)
        if self.time_to_next_car <= 0:
            self.time_to_next_car = random.randint(self.min_time_spawn, self.max_time_spawn)


    def set_params(self, min_speed, max_speed, min_time, max_time, coef_acc, coef_slow):
        self.min_speed = min_speed
        self.max_speed = max_speed
        self.min_time_spawn = min_time * 10
        self.max_time_spawn = max_time * 10
        self.coef_acceleration = coef_acc
        self.coef_slowdown = coef_slow

    def get_highway(self):
        return self.cur_highway


class CarItem(QtWidgets.QGraphicsRectItem):
    def __init__(self, car, parent=None):
        self.car = car
        width_px = CAR_WIDTH * SCALE
        height_px = CAR_HEIGHT
        super().__init__(0, 0, width_px, height_px, parent)
        self.setFlag(QtWidgets.QGraphicsItem.ItemIsSelectable, True)
        self.body_brush = QtGui.QBrush(Qt.blue)

    def setBrush(self, brush):
        self.body_brush = brush

    def paint(self, painter, option, widget=None):
        painter.setBrush(self.body_brush)
        painter.drawRect(self.rect())

        rect_w = self.rect().width()
        rect_h = self.rect().height()

        # лобовое стекло
        cabin_w = rect_w * 0.25
        cabin_h = rect_h * 0.9
        cabin_x = (rect_w - cabin_w) * 0.6
        cabin_y = (rect_h - cabin_h) * 0.5
        painter.setBrush(QtGui.QBrush(QtCore.Qt.black))
        painter.drawRect(QtCore.QRectF(cabin_x, cabin_y, cabin_w, cabin_h))

        # заднее стекло
        rear_w = rect_w * 0.05
        rear_h = rect_h * 0.9
        rear_x = (rect_w - rear_w) * 0.15
        rear_y = (rect_h - rear_h) * 0.5
        painter.setBrush(QtGui.QBrush(QtCore.Qt.black))
        painter.drawRect(QtCore.QRectF(rear_x, rear_y, rear_w, rear_h))

        # передние фары
        painter.setBrush(QtGui.QBrush(QtCore.Qt.yellow))
        r = rect_h * 0.15
        top_headlight_x = rect_w - r * 0.7
        top_headlight_y = rect_h * 0.05
        painter.drawEllipse(QtCore.QRectF(top_headlight_x, top_headlight_y, r, r))
        bottom_headlight_x = rect_w - r * 0.7
        bottom_headlight_y = rect_h - r * 1.05
        painter.drawEllipse(QtCore.QRectF(bottom_headlight_x, bottom_headlight_y, r, r))

        # задние фары
        painter.setBrush(QtGui.QBrush(QtCore.Qt.red))
        r_tail = r * 0.7
        top_tail_x = 0 + r_tail * 0.05
        top_tail_y = rect_h * 0.1
        painter.drawEllipse(QtCore.QRectF(top_tail_x, top_tail_y, r_tail, r_tail))
        bottom_tail_x = 0 + r_tail * 0.05
        bottom_tail_y = rect_h - r_tail * 1.1
        painter.drawEllipse(QtCore.QRectF(bottom_tail_x, bottom_tail_y, r_tail, r_tail))

    def mousePressEvent(self, event):
        super().mousePressEvent(event)
        self.show_dialog()

    def show_dialog(self):
        dialog = CarDialog(self.car)
        dialog.exec_()



class CarDialog(QtWidgets.QDialog):
    def __init__(self, car):
        super().__init__()
        self.car = car
        self.label_ticks = QtWidgets.QLabel("Количество секунд задержки:")
        self.edit_ticks = QtWidgets.QLineEdit("5")
        self.init_ui()

    def init_ui(self):
        self.setWindowTitle("Параметры автомобиля")
        layout = QtWidgets.QVBoxLayout()
        layout.addWidget(self.label_ticks)
        layout.addWidget(self.edit_ticks)
        button_box = QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel)
        button_box.accepted.connect(self.apply_changes)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)
        self.setLayout(layout)

    def apply_changes(self):
        delay = self.edit_ticks.text()
        if not delay.isdigit():
            QtWidgets.QMessageBox.warning(
                self,
                "Ошибка параметров",
                "Введите число!"
            )
            return -1
        ticks = 1000 * int(delay)
        self.car.delay(ticks)
        self.accept()


class HighwayView(QtWidgets.QGraphicsView):
    def __init__(self, experiment, parent=None):
        super().__init__(parent)
        self.experiment = experiment
        self.scene = QtWidgets.QGraphicsScene(self)
        self.setScene(self.scene)
        self.scene.setSceneRect(0, 0, SCENE_WIDTH, SCENE_HEIGHT)
        self.scene.setBackgroundBrush(QtGui.QBrush(Qt.green))
        self.highway_height = 80
        self.highway_y = (SCENE_HEIGHT - self.highway_height) / 2
        self.highway_item = self.scene.addRect(
            0, self.highway_y, SCENE_WIDTH, self.highway_height,
            pen=QtGui.QPen(Qt.NoPen), brush=QtGui.QBrush(Qt.gray)
        )

    def update_scene(self):
        for item in self.scene.items():
            if isinstance(item, CarItem):
                self.scene.removeItem(item)
        cars = self.experiment.get_highway().get_all_cars()
        for car in cars:
            item = CarItem(car)
            x = car.get_coord() * SCALE
            y = self.highway_y + (self.highway_height - 10) / 2
            item.setPos(x, y)
            status = car.get_status()
            if status == 'crash':
                color = Qt.red
            elif status == 'acceleration':
                color = Qt.green
            elif status == 'slowdown':
                color = Qt.yellow
            else:
                color = Qt.blue
            item.setBrush(QtGui.QBrush(color))
            self.scene.addItem(item)


class MainWindow(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Моделирование движения автомобилей")
        self.experiment = Experiment()
        self.timer = QtCore.QTimer()
        self.timer.timeout.connect(self.simulation_step)
        self.simulation_started = False

        central_widget = QtWidgets.QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QtWidgets.QVBoxLayout(central_widget)

        params_layout = QtWidgets.QGridLayout()
        params_layout.setSpacing(10)

        self.label_min_speed = QtWidgets.QLabel(f"Мин. скорость: {self.experiment.min_speed}")
        self.slider_min_speed = QtWidgets.QSlider(Qt.Horizontal)
        self.slider_min_speed.setRange(10, 100)
        self.slider_min_speed.setValue(self.experiment.min_speed)
        self.slider_min_speed.valueChanged.connect(self.on_min_speed_changed)
        vbox_min_speed = QtWidgets.QVBoxLayout()
        vbox_min_speed.addWidget(self.label_min_speed)
        vbox_min_speed.addWidget(self.slider_min_speed)

        self.label_max_speed = QtWidgets.QLabel(f"Макс. скорость: {self.experiment.max_speed}")
        self.slider_max_speed = QtWidgets.QSlider(Qt.Horizontal)
        self.slider_max_speed.setRange(10, 100)
        self.slider_max_speed.setValue(self.experiment.max_speed)
        self.slider_max_speed.valueChanged.connect(self.on_max_speed_changed)
        vbox_max_speed = QtWidgets.QVBoxLayout()
        vbox_max_speed.addWidget(self.label_max_speed)
        vbox_max_speed.addWidget(self.slider_max_speed)

        self.label_min_time = QtWidgets.QLabel(f"Мин. интервал: {self.experiment.min_time_spawn}")
        self.slider_min_time = QtWidgets.QSlider(Qt.Horizontal)
        self.slider_min_time.setRange(1, 100)
        self.slider_min_time.setValue(self.experiment.min_time_spawn)
        self.slider_min_time.valueChanged.connect(self.on_min_time_changed)
        vbox_min_time = QtWidgets.QVBoxLayout()
        vbox_min_time.addWidget(self.label_min_time)
        vbox_min_time.addWidget(self.slider_min_time)

        self.label_max_time = QtWidgets.QLabel(f"Макс. интервал: {self.experiment.max_time_spawn}")
        self.slider_max_time = QtWidgets.QSlider(Qt.Horizontal)
        self.slider_max_time.setRange(1, 100)
        self.slider_max_time.setValue(self.experiment.max_time_spawn)
        self.slider_max_time.valueChanged.connect(self.on_max_time_changed)
        vbox_max_time = QtWidgets.QVBoxLayout()
        vbox_max_time.addWidget(self.label_max_time)
        vbox_max_time.addWidget(self.slider_max_time)

        self.label_acc = QtWidgets.QLabel(f"Ускорение: {self.experiment.coef_acceleration:.1f}")
        self.slider_acc = QtWidgets.QSlider(Qt.Horizontal)
        self.slider_acc.setRange(1, 1000)
        self.slider_acc.setValue(int(self.experiment.coef_acceleration * 10))
        self.slider_acc.valueChanged.connect(self.on_acc_changed)
        vbox_acc = QtWidgets.QVBoxLayout()
        vbox_acc.addWidget(self.label_acc)
        vbox_acc.addWidget(self.slider_acc)

        self.label_slow = QtWidgets.QLabel(f"Замедление: {self.experiment.coef_slowdown:.1f}")
        self.slider_slow = QtWidgets.QSlider(Qt.Horizontal)
        self.slider_slow.setRange(1, 1000)
        self.slider_slow.setValue(int(self.experiment.coef_slowdown * 10))
        self.slider_slow.valueChanged.connect(self.on_slow_changed)
        vbox_slow = QtWidgets.QVBoxLayout()
        vbox_slow.addWidget(self.label_slow)
        vbox_slow.addWidget(self.slider_slow)

        params_layout.addLayout(vbox_min_speed, 0, 0)
        params_layout.addLayout(vbox_max_speed, 1, 0)
        params_layout.addLayout(vbox_min_time, 0, 1)
        params_layout.addLayout(vbox_max_time, 1, 1)
        params_layout.addLayout(vbox_acc, 0, 2)
        params_layout.addLayout(vbox_slow, 1, 2)

        main_layout.addLayout(params_layout)

        self.highway_view = HighwayView(self.experiment)
        self.highway_view.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.highway_view.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.highway_view.setFixedSize(SCENE_WIDTH, SCENE_HEIGHT)

        main_layout.addWidget(self.highway_view, alignment=Qt.AlignCenter)


        bottom_layout = QtWidgets.QHBoxLayout()
        bottom_layout.setSpacing(75)

        self.start_button = QtWidgets.QPushButton("Начать")
        self.start_button.clicked.connect(self.start_simulation)
        bottom_layout.addWidget(self.start_button)

        self.pause_button = QtWidgets.QPushButton("Пауза")
        self.pause_button.clicked.connect(self.pause_simulation)
        bottom_layout.addWidget(self.pause_button)

        self.resume_button = QtWidgets.QPushButton("Продолжить")
        self.resume_button.clicked.connect(self.resume_simulation)
        bottom_layout.addWidget(self.resume_button)

        self.clear_button = QtWidgets.QPushButton("Очистить дорогу")
        self.clear_button.clicked.connect(self.clear_highway)
        bottom_layout.addWidget(self.clear_button)

        self.exit_button = QtWidgets.QPushButton("Выход")
        self.exit_button.clicked.connect(self.close)
        bottom_layout.addWidget(self.exit_button)

        main_layout.addLayout(bottom_layout)

        self.resize(SCENE_WIDTH, 400)
        self.setFixedSize(self.size())
        self.highway_view.update_scene()

    # Обработчики слайдеров
    def on_min_speed_changed(self, value):
        self.label_min_speed.setText(f"Мин. скорость: {value}")

    def on_max_speed_changed(self, value):
        self.label_max_speed.setText(f"Макс. скорость: {value}")

    def on_min_time_changed(self, value):
        self.label_min_time.setText(f"Мин. интервал: {value}")

    def on_max_time_changed(self, value):
        self.label_max_time.setText(f"Макс. интервал: {value}")

    def on_acc_changed(self, value):
        real_acc = value / 10
        self.label_acc.setText(f"Ускорение: {real_acc:.1f}")

    def on_slow_changed(self, value):
        real_slow = value / 10
        self.label_slow.setText(f"Замедление: {real_slow:.1f}")

    # Кнопки
    def start_simulation(self):
        error = self.update_params()
        self.simulation_started = True
        if not error:
            self.timer.start(TIMER_INTERVAL)

    def pause_simulation(self):
        self.timer.stop()

    def resume_simulation(self):
        if self.simulation_started:
            self.timer.start(TIMER_INTERVAL)

    def clear_highway(self):
        self.simulation_started = False
        self.experiment.get_highway().clear_highway()
        self.pause_simulation()
        self.highway_view.update_scene()

    def update_params(self):
        min_speed = self.slider_min_speed.value()
        max_speed = self.slider_max_speed.value()
        min_time = self.slider_min_time.value()
        max_time = self.slider_max_time.value()
        acc = self.slider_acc.value() / 10
        slow = self.slider_slow.value() / 10
        if min_speed > max_speed or min_time > max_time:
            QtWidgets.QMessageBox.warning(
                self,
                "Ошибка параметров",
                "Минимальное значение должно быть меньше или равно максимальному. Исправьте настройки."
            )
            return -1
        self.experiment.set_params(min_speed, max_speed, min_time, max_time, acc, slow)
        return 0

    def simulation_step(self):
        self.experiment.step(DT)
        self.highway_view.update_scene()



app = QtWidgets.QApplication([])
window = MainWindow()
window.show()
sys.exit(app.exec_())
