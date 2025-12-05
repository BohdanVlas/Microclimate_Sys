"""
Проста симуляція вбудованої системи контролю мікроклімату.
- Працює на стандартній бібліотеці
- Асинхронні сенсори + контролер + логування в CSV
- Локальний інтерфейс
"""

import asyncio
import csv
import datetime
import math
import random
import threading
from dataclasses import dataclass, field
from typing import Dict, Optional

SENSOR_PERIOD = 1.0
CONTROL_PERIOD = 1.0
LOG_PERIOD = 5.0
DEFAULT_SETPOINTS = {
    "temperature": 22.0,
    "humidity": 50.0,
    "co2": 800.0
}
HYSTERESIS = {
    "temperature": 0.7,
    "humidity": 3.0,
    "co2": 50.0
}
CSV_LOGFILE = "microclimate_log.csv"


@dataclass
class SensorReadings:
    temperature: float
    humidity: float
    co2: float
    timestamp: datetime.datetime = field(default_factory=datetime.datetime.utcnow)


@dataclass
class ActuatorState:
    heater_on: bool = False
    cooler_on: bool = False
    humidifier_on: bool = False
    fan_on: bool = False


class SensorSimulator:

    def __init__(self,
                 initial_temp: float = 20.0,
                 initial_humidity: float = 45.0,
                 initial_co2: float = 600.0):
        self._temp = initial_temp
        self._humidity = initial_humidity
        self._co2 = initial_co2
        self._outside_temp = 5.0
        self._heater_power = 0.8
        self._cooler_power = 1.0
        self._humidifier_power = 2.0
        self._fan_exchange = 0.3

    def step(self, actuators: ActuatorState, dt: float = 1.0):
        loss = (self._outside_temp - self._temp) * 0.01 * dt
        self._temp += loss

        if actuators.heater_on:
            self._temp += self._heater_power * dt
        if actuators.cooler_on:
            self._temp -= self._cooler_power * dt

        self._humidity += (40.0 - self._humidity) * 0.005 * dt
        if actuators.humidifier_on:
            self._humidity += self._humidifier_power * dt
        self._humidity = max(0.0, min(100.0, self._humidity))

        self._co2 += 2.0 * dt
        if actuators.fan_on:
            self._co2 += (400.0 - self._co2) * self._fan_exchange * dt
        self._temp += random.uniform(-0.05, 0.05) * dt
        self._humidity += random.uniform(-0.1, 0.1) * dt
        self._co2 += random.uniform(-1.0, 1.0) * dt

    def read(self) -> SensorReadings:
        noise_temp = random.gauss(0.0, 0.05)
        noise_hum = random.gauss(0.0, 0.2)
        noise_co2 = random.gauss(0.0, 2.0)
        return SensorReadings(
            temperature=round(self._temp + noise_temp, 2),
            humidity=round(self._humidity + noise_hum, 2),
            co2=round(self._co2 + noise_co2, 1),
        )


class MicroclimateController:

    def __init__(self, setpoints: Dict[str, float], hysteresis: Dict[str, float]):
        self.setpoints = dict(setpoints)
        self.hysteresis = dict(hysteresis)
        self.actuators = ActuatorState()
        self.last_action: Dict[str, Optional[datetime.datetime]] = {}

    def update(self, readings: SensorReadings):
        t_sp = self.setpoints["temperature"]
        t_h = self.hysteresis["temperature"]
        if readings.temperature < t_sp - t_h:
            self.actuators.heater_on = True
            self.actuators.cooler_on = False
        elif readings.temperature > t_sp + t_h:
            self.actuators.cooler_on = True
            self.actuators.heater_on = False
        else:
            self.actuators.heater_on = False
            self.actuators.cooler_on = False

        h_sp = self.setpoints["humidity"]
        h_h = self.hysteresis["humidity"]
        if readings.humidity < h_sp - h_h:
            self.actuators.humidifier_on = True
        elif readings.humidity > h_sp + h_h:
            self.actuators.humidifier_on = False
        co2_sp = self.setpoints["co2"]
        co2_h = self.hysteresis["co2"]
        if readings.co2 > co2_sp + co2_h:
            self.actuators.fan_on = True
        elif readings.co2 < co2_sp - co2_h:
            self.actuators.fan_on = False

    def set_setpoint(self, name: str, value: float):
        if name in self.setpoints:
            self.setpoints[name] = value
        else:
            raise KeyError(f"No such setpoint: {name}")

    def get_status(self) -> Dict:
        return {
            "setpoints": dict(self.setpoints),
            "hysteresis": dict(self.hysteresis),
            "actuators": self.actuators,
        }


class CSVLogger:
    def __init__(self, filename: str = CSV_LOGFILE):
        self.filename = filename
        # write header
        with open(self.filename, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow([
                "timestamp", "temperature", "humidity", "co2",
                "heater", "cooler", "humidifier", "fan"
            ])

    def log(self, readings: SensorReadings, actuators: ActuatorState):
        with open(self.filename, "a", newline="") as f:
            writer = csv.writer(f)
            writer.writerow([
                readings.timestamp.isoformat(),
                readings.temperature,
                readings.humidity,
                readings.co2,
                int(actuators.heater_on),
                int(actuators.cooler_on),
                int(actuators.humidifier_on),
                int(actuators.fan_on),
            ])


def start_cli(controller: MicroclimateController, stop_event: threading.Event):
    """
    Підтримувані команди:
      status
      set <temperature|humidity|co2> <value>
      actuators
      help
      exit
    """
    print("CLI запущено. Введіть 'help' для списку команд.")
    while not stop_event.is_set():
        try:
            raw = input("> ").strip()
        except EOFError:
            break
        if not raw:
            continue
        parts = raw.split()
        cmd = parts[0].lower()
        if cmd == "help":
            print("Команди: status, set <param> <value>, actuators, help, exit, savecsv")
            print("Параметри для set: temperature, humidity, co2")
        elif cmd == "status":
            st = controller.get_status()
            print("Setpoints:", st["setpoints"])
            print("Hysteresis:", st["hysteresis"])
            print("Actuators:", st["actuators"])
        elif cmd == "set" and len(parts) == 3:
            param = parts[1].lower()
            try:
                val = float(parts[2])
                controller.set_setpoint(param, val)
                print(f"Setpoint {param} = {val}")
            except Exception as e:
                print("Помилка:", e)
        elif cmd == "actuators":
            print(controller.actuators)
        elif cmd == "savecsv":
            print(f"Логи зберігаються у {CSV_LOGFILE}")
        elif cmd == "exit":
            print("Завершення симуляції...")
            stop_event.set()
            break
        else:
            print("Невідома команда. help -> довідка.")


async def sensor_task(sim: SensorSimulator, controller: MicroclimateController,
                      readings_queue: asyncio.Queue, stop_event: threading.Event):
    while not stop_event.is_set():
        sim.step(controller.actuators, dt=SENSOR_PERIOD)
        r = sim.read()
        r.timestamp = datetime.datetime.utcnow()
        await readings_queue.put(r)
        await asyncio.sleep(SENSOR_PERIOD)


async def controller_task(controller: MicroclimateController,
                          readings_queue: asyncio.Queue,
                          log_queue: asyncio.Queue,
                          stop_event: threading.Event):
    while not stop_event.is_set():
        try:
            r = await asyncio.wait_for(readings_queue.get(), timeout=CONTROL_PERIOD)
            controller.update(r)
            await log_queue.put((r, controller.actuators))
        except asyncio.TimeoutError:
            await asyncio.sleep(0.01)


async def logger_task(csv_logger: CSVLogger, log_queue: asyncio.Queue, stop_event: threading.Event):
    last_written = datetime.datetime.utcnow()
    buffer = []
    while not stop_event.is_set() or not log_queue.empty():
        try:
            item = await asyncio.wait_for(log_queue.get(), timeout=1.0)
            buffer.append(item)
        except asyncio.TimeoutError:
            item = None
        if (datetime.datetime.utcnow() - last_written).total_seconds() >= LOG_PERIOD and buffer:
            for r, act in buffer:
                csv_logger.log(r, act)
            buffer.clear()
            last_written = datetime.datetime.utcnow()
        await asyncio.sleep(0.01)
    for r, act in buffer:
        csv_logger.log(r, act)


async def status_printer(readings_queue: asyncio.Queue, controller: MicroclimateController,
                         stop_event: threading.Event):
    last_reading: Optional[SensorReadings] = None
    while not stop_event.is_set():
        try:
            last_reading = readings_queue.get_nowait()
            readings_queue.put_nowait(last_reading)
        except asyncio.QueueEmpty:
            pass
        if last_reading:
            ts = last_reading.timestamp.isoformat()
            print(f"[{ts}] T={last_reading.temperature}°C H={last_reading.humidity}% CO2={last_reading.co2}ppm -> Actuators: {controller.actuators}")
        await asyncio.sleep(5.0)


def run_simulation(run_seconds: Optional[int] = None):
    sim = SensorSimulator(initial_temp=19.5, initial_humidity=45.0, initial_co2=650.0)
    controller = MicroclimateController(setpoints=DEFAULT_SETPOINTS, hysteresis=HYSTERESIS)
    csv_logger = CSVLogger(CSV_LOGFILE)

    stop_event = threading.Event()
    readings_queue: asyncio.Queue = asyncio.Queue(maxsize=10)
    log_queue: asyncio.Queue = asyncio.Queue(maxsize=100)

    cli_thread = threading.Thread(target=start_cli, args=(controller, stop_event), daemon=True)
    cli_thread.start()

    async def main_loop():
        tasks = [
            asyncio.create_task(sensor_task(sim, controller, readings_queue, stop_event)),
            asyncio.create_task(controller_task(controller, readings_queue, log_queue, stop_event)),
            asyncio.create_task(logger_task(csv_logger, log_queue, stop_event)),
            asyncio.create_task(status_printer(readings_queue, controller, stop_event)),
        ]
        if run_seconds is not None:
            await asyncio.sleep(run_seconds)
            stop_event.set()
        await asyncio.gather(*tasks, return_exceptions=True)

    try:
        asyncio.run(main_loop())
    except KeyboardInterrupt:
        stop_event.set()
    finally:
        print("Симуляція завершена.")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Microclimate controller simulator")
    parser.add_argument("--run-seconds", type=int, default=None, help="Run simulation for N seconds then exit")
    parser.add_argument("--logfile", type=str, default=CSV_LOGFILE, help="CSV logfile path")
    args = parser.parse_args()

    CSV_LOGFILE = args.logfile
    run_simulation(run_seconds=args.run_seconds)
