from Microclimate_sim import MicroclimateController, SensorReadings, HYSTERESIS, DEFAULT_SETPOINTS

def test_controller_turns_on_heater_and_off_cooler():
    controller = MicroclimateController(setpoints=DEFAULT_SETPOINTS, hysteresis=HYSTERESIS)
    r = SensorReadings(temperature=15.0, humidity=50.0, co2=500.0)
    controller.update(r)
    assert controller.actuators.heater_on is True
    assert controller.actuators.cooler_on is False

def test_controller_turns_on_fan_for_high_co2():
    controller = MicroclimateController(setpoints=DEFAULT_SETPOINTS, hysteresis=HYSTERESIS)
    r = SensorReadings(temperature=22.0, humidity=50.0, co2=2000.0)
    controller.update(r)
    assert controller.actuators.fan_on is True
