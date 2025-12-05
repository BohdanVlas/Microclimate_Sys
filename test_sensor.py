import random
from Microclimate_sim import SensorSimulator, ActuatorState

def test_sensor_step_temperature_and_humidity_direction():
    random.seed(0)
    sim = SensorSimulator(initial_temp=10.0, initial_humidity=20.0, initial_co2=500.0)
    actuators = ActuatorState(heater_on=True, cooler_on=False, humidifier_on=True, fan_on=False)
    sim.step(actuators, dt=1.0)
    r = sim.read()
    assert r.temperature > 10.0 - 1.0
    assert r.humidity >= 20.0
