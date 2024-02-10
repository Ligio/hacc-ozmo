"""Support for Ecovacs Deebot Vacuums with Spot Area cleaning."""
import logging
from functools import partial

from homeassistant.components.vacuum import (
    ATTR_STATUS,
    STATE_CLEANING,
    STATE_DOCKED,
    STATE_ERROR,
    STATE_IDLE,
    STATE_PAUSED,
    STATE_RETURNING,
    SUPPORT_FAN_SPEED,
)

try:
    from homeassistant.components.vacuum import StateVacuumEntity
except ImportError:
    from homeassistant.components.vacuum import StateVacuumDevice as StateVacuumEntity

from homeassistant.helpers.icon import icon_for_battery_level

from . import ECOVACS_DEVICES, CONF_SUPPORTED_FEATURES, ECOVACS_CONFIG

_LOGGER = logging.getLogger(__name__)

ATTR_ERROR = "error"
ATTR_COMPONENT_PREFIX = "component_"

STATE_MAP = {
    "cleaning": STATE_CLEANING,
    "auto": STATE_CLEANING,
    "spot_area": STATE_CLEANING,
    "charging": STATE_DOCKED,
    "idle": STATE_DOCKED,
    "pause": STATE_PAUSED,
    "returning": STATE_RETURNING,
    "stop": STATE_IDLE,
}

def setup_platform(hass, config, add_entities, discovery_info=None):
    """Set up the Ecovacs vacuums."""
    vacuums = []
    for device in hass.data[ECOVACS_DEVICES]:
        vacuums.append(EcovacsDeebotVacuum(device, hass.data[ECOVACS_CONFIG][0]))
    _LOGGER.debug("Adding Ecovacs Deebot Vacuums to Hass: %s", vacuums)
    add_entities(vacuums, True)


class EcovacsDeebotVacuum(StateVacuumEntity):
    """Ecovacs Vacuums such as Deebot."""

    def __init__(self, device, config):
        _LOGGER.debug("CONFIG: %s", str(config))

        """Initialize the Ecovacs Vacuum."""
        self.device = device
        self.device.connect_and_wait_until_ready()
        if self.device.vacuum.get("nick", None) is not None:
            self._name = "{}".format(self.device.vacuum["nick"])
        else:
            # In case there is no nickname defined, use the device id
            self._name = "{}".format(self.device.vacuum["did"])

        self.clean_mode = 'auto'
        self._fan_speed = 'normal'
        self._error = None
        self._supported_features = config[CONF_SUPPORTED_FEATURES]
        _LOGGER.debug("Vacuum initialized: %s with features: %d", self.name, self._supported_features)

    async def async_added_to_hass(self) -> None:
        """Set up the event listeners now that hass is ready."""
        self.device.statusEvents.subscribe(lambda _: self.schedule_update_ha_state())
        self.device.batteryEvents.subscribe(lambda _: self.schedule_update_ha_state())
        self.device.lifespanEvents.subscribe(lambda _: self.schedule_update_ha_state())
        self.device.fanEvents.subscribe(self.on_fan_change)
        self.device.errorEvents.subscribe(self.on_error)

    def on_error(self, error):
        """Handle an error event from the robot.

        This will not change the entity's state. If the error caused the state
        to change, that will come through as a separate on_status event
        """
        if error == "no_error":
            self._error = None
        else:
            self._error = error

        self.hass.bus.fire(
            "ecovacs_error", {"entity_id": self.entity_id, "error": error}
        )
        self.schedule_update_ha_state()

    def on_fan_change(self, fan_speed):
        self._fan_speed = fan_speed
        self.schedule_update_ha_state()

    @property
    def should_poll(self) -> bool:
        """Return True if entity has to be polled for state."""
        return False

    @property
    def unique_id(self) -> str:
        """Return an unique ID."""
        return self.device.vacuum.get("did", None)

    @property
    def is_on(self):
        """Return true if vacuum is currently cleaning."""
        return self.device.is_cleaning

    @property
    def is_charging(self):
        """Return true if vacuum is currently charging."""
        return self.device.is_charging

    @property
    def name(self):
        """Return the name of the device."""
        return self._name

    @property
    def supported_features(self):
        """Flag vacuum cleaner robot features that are supported."""
        return self._supported_features

    @property
    def state(self):
        try:
            return STATE_MAP[self.device.vacuum_status]
        except KeyError:
            return STATE_ERROR

    @property
    def status(self):
        """Return the status of the vacuum cleaner."""
        return self.device.vacuum_status

    def return_to_base(self, **kwargs):
        """Set the vacuum cleaner to return to the dock."""
        from ozmo import Charge

        self.device.run(Charge())
	
    @property
    def battery_icon(self):
        """Return the battery icon for the vacuum cleaner."""
        return icon_for_battery_level(
            battery_level=self.battery_level, charging=self.is_charging
        )

    @property
    def battery_level(self):
        """Return the battery level of the vacuum cleaner."""
        if self.device.battery_status is not None:
            return self.device.battery_status * 100

        return super().battery_level

    @property
    def fan_speed(self):
        """Return the fan speed of the vacuum cleaner."""
        if bool(self.supported_features & SUPPORT_FAN_SPEED):
            return self._fan_speed
        return 'normal'

    def set_fan_speed(self, fan_speed, **kwargs):
        """Set fan speed."""
        from ozmo import SetCleanSpeed

        self.device.run(SetCleanSpeed(fan_speed))
        self._fan_speed = fan_speed

    async def async_set_fan_speed(self, fan_speed, **kwargs):
        await self.hass.async_add_executor_job(partial(self.set_fan_speed, fan_speed))

    @property
    def fan_speed_list(self):
        """Get the list of available fan speed steps of the vacuum cleaner."""
        from ozmo import FAN_SPEED_NORMAL, FAN_SPEED_HIGH

        return [FAN_SPEED_NORMAL, FAN_SPEED_HIGH]

    def turn_on(self, **kwargs):
        """Turn the vacuum on and start cleaning."""
        from ozmo import Clean, SpotArea

        self.clean_mode = 'auto'
        self.device.run(Clean(mode=self.clean_mode, speed=self.fan_speed, action='start'))

    def start(self):
        self.turn_on()

    def turn_off(self, **kwargs):
        """Turn the vacuum off stopping the cleaning and returning home."""
        self.clean_mode = None
        self.return_to_base()

    def stop(self, **kwargs):
        """Stop the vacuum cleaner."""
        from ozmo import Clean

        self.device.run(Clean(mode=self.clean_mode, speed=self.fan_speed, action='stop'))

    def pause(self, **kwargs):
        """Stop the vacuum cleaner."""
        from ozmo import Clean

        self.device.run(Clean(mode=self.clean_mode, speed=self.fan_speed, action='pause'))

    def resume(self, **kwargs):
        """Stop the vacuum cleaner."""
        from ozmo import Clean

        self.device.run(Clean(mode=self.clean_mode, speed=self.fan_speed, action='resume'))

    def start_pause(self, **kwargs):
        """Start, pause or resume the cleaning task."""
        if self.device.vacuum_status == 'pause':
            self.resume()
        elif self.device.vacuum_status != 'pause':
            self.pause()

    async def async_start_pause(self, **kwargs):
        """Start, pause or resume the cleaning task."""
        await self.hass.async_add_executor_job(self.start_pause)

    def clean_spot(self, **kwargs):
        """Perform a spot clean-up."""
        from ozmo import Clean

        self.clean_mode = 'spot'
        self.device.run(Clean(mode=self.clean_mode, speed=self.fan_speed, action='start'))

    def locate(self, **kwargs):
        """Locate the vacuum cleaner."""
        from ozmo import PlaySound

        self.device.run(PlaySound())

    def send_command(self, command, params=None, **kwargs):
        """Send a command to a vacuum cleaner."""

        """
        {
          "entity_id": "vacuum.<ID>",
          "command": "spot_area",
          "params" : {
            "area": "0,2"
          }
        }

        or

        {
          "entity_id": "vacuum.<ID>",
          "command": "spot_area",
          "params" : {
            "map": "1580.0,-4087.0,3833.0,-7525.0"
          }
        }

		or

        Send command to edge clean.

        {
          "entity_id": "vacuum.<ID>",
          "command": "clean_edge",
        }
        """

        from ozmo import VacBotCommand, Edge

        if command == 'clean_edge':
            self.device.run(Edge())

        if command == 'spot_area':
            if 'area' in params:
                return self.clean_area(params['area'])
            elif 'map' in params:
                return self.clean_map(params['map'])

        if command == 'set_water_level':
            return self.set_water_level(params['level'])

        self.device.run(VacBotCommand(command, params))

    def clean_map(self, map):
        from ozmo import Clean, SpotArea

        if not map:
            self.clean_mode = 'auto'
            self.device.run(Clean(mode=self.clean_mode, speed=self.fan_speed, action='start'))
        else:
            self.clean_mode = 'spot_area'
            self.device.run(SpotArea(map_position=map, speed=self.fan_speed, action='start'))

    def clean_area(self, area):
        from ozmo import Clean, SpotArea

        if not area:
            self.clean_mode = 'auto'
            self.device.run(Clean(mode=self.clean_mode, speed=self.fan_speed, action='start'))
        else:
            self.clean_mode = 'spot_area'
            self.device.run(SpotArea(area=area, speed=self.fan_speed, action='start'))

    def set_water_level(self, level):
        from ozmo import SetWaterLevel

        self.device.run(SetWaterLevel(level=level))

    @property
    def extra_state_attributes(self):
        """Return the device-specific state attributes of this vacuum."""
        data = {}
        data[ATTR_ERROR] = self._error

        for key, val in self.device.components.items():
            attr_name = ATTR_COMPONENT_PREFIX + key
            data[attr_name] = int(val * 100)

        data["clean_mode"] = self.clean_mode
        data[ATTR_STATUS] = self.state

        return data
