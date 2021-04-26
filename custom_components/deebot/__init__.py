"""Support for Ecovacs Deebot vacuums with advanced features"""
import logging
import random
import string

import voluptuous as vol

from homeassistant.const import CONF_PASSWORD, CONF_USERNAME, EVENT_HOMEASSISTANT_STOP
from homeassistant.helpers import discovery
import homeassistant.helpers.config_validation as cv
from homeassistant.components.vacuum import (
    SUPPORT_BATTERY,
    SUPPORT_CLEAN_SPOT,
    SUPPORT_FAN_SPEED,
    SUPPORT_LOCATE,
    SUPPORT_RETURN_HOME,
    SUPPORT_SEND_COMMAND,
    SUPPORT_STATE,
    SUPPORT_STATUS,
    SUPPORT_STOP,
    SUPPORT_TURN_OFF,
    SUPPORT_TURN_ON,
    SUPPORT_START,
    SUPPORT_PAUSE
)

_LOGGER = logging.getLogger(__name__)

DOMAIN = "deebot"

CONF_COUNTRY = "country"
CONF_CONTINENT = "continent"
CONF_SUPPORTED_FEATURES = "supported_features"
CONF_UNSUPPORTED_FEATURES = "unsupported_features"

SERVICE_TO_STRING = {
    SUPPORT_START: "start",
    SUPPORT_PAUSE: "pause",
    SUPPORT_STOP: "stop",
    SUPPORT_RETURN_HOME: "return_home",
    SUPPORT_FAN_SPEED: "fan_speed",
    SUPPORT_BATTERY: "battery",
    SUPPORT_STATE: "state",
    SUPPORT_STATUS: "status",
    SUPPORT_SEND_COMMAND: "send_command",
    SUPPORT_LOCATE: "locate",
    SUPPORT_CLEAN_SPOT: "clean_spot",
    SUPPORT_TURN_ON: "turn_on",
    SUPPORT_TURN_OFF: "turn_off"
}

STRING_TO_SERVICE = {v: k for k, v in SERVICE_TO_STRING.items()}

CONFIG_SCHEMA = vol.Schema(
    {
        DOMAIN: vol.Schema(
            {
                vol.Required(CONF_USERNAME): cv.string,
                vol.Required(CONF_PASSWORD): cv.string,
                vol.Required(CONF_COUNTRY): vol.All(vol.Lower, cv.string),
                vol.Required(CONF_CONTINENT): vol.All(vol.Lower, cv.string),
                vol.Optional(
                    CONF_SUPPORTED_FEATURES, default=[]
                ): vol.All(cv.ensure_list, [vol.In(STRING_TO_SERVICE.keys())]),
                vol.Optional(
                    CONF_UNSUPPORTED_FEATURES, default=[]
                ): vol.All(cv.ensure_list, [vol.In(STRING_TO_SERVICE.keys())]),
            }
        )
    },
    extra=vol.ALLOW_EXTRA,
)

ECOVACS_DEVICES = "ecovacs_devices"
ECOVACS_CONFIG = "ecovacs_config"

# Generate a random device ID on each bootup
ECOVACS_API_DEVICEID = "".join(
    random.choice(string.ascii_uppercase + string.digits) for _ in range(8)
)


def setup(hass, config):
    """Set up the Ecovacs component."""
    _LOGGER.debug("Creating new Ecovacs component")

    hass.data[ECOVACS_DEVICES] = []
    hass.data[ECOVACS_CONFIG] = []

    from ozmo import EcoVacsAPI, VacBot

    ecovacs_api = EcoVacsAPI(
        ECOVACS_API_DEVICEID,
        config[DOMAIN].get(CONF_USERNAME),
        EcoVacsAPI.md5(config[DOMAIN].get(CONF_PASSWORD)),
        config[DOMAIN].get(CONF_COUNTRY),
        config[DOMAIN].get(CONF_CONTINENT),
    )

    devices = ecovacs_api.devices()
    _LOGGER.debug("Ecobot devices: %s", devices)

    for device in devices:
        _LOGGER.info(
            "Discovered Ecovacs device on account: %s with nickname %s",
            device["did"],
            device["nick"],
        )
        vacbot = VacBot(
            ecovacs_api.uid,
            ecovacs_api.REALM,
            ecovacs_api.resource,
            ecovacs_api.user_access_token,
            device,
            config[DOMAIN].get(CONF_CONTINENT).lower(),
            monitor=True,
        )
        hass.data[ECOVACS_DEVICES].append(vacbot)

    def stop(event: object) -> None:
        """Shut down open connections to Ecovacs XMPP server."""
        for device in hass.data[ECOVACS_DEVICES]:
            _LOGGER.info(
                "Shutting down connection to Ecovacs device %s", device.vacuum["did"]
            )
            device.disconnect()

    # Listen for HA stop to disconnect.
    hass.bus.listen_once(EVENT_HOMEASSISTANT_STOP, stop)

    if hass.data[ECOVACS_DEVICES]:
        _LOGGER.debug("Starting vacuum components")

        dconfig = config[DOMAIN]

        if len(dconfig.get(CONF_SUPPORTED_FEATURES)) == 0:
            dconfig[CONF_SUPPORTED_FEATURES] = STRING_TO_SERVICE.keys()

        if CONF_UNSUPPORTED_FEATURES in dconfig:
            filtered_features = []
            for supported_feature in dconfig.get(CONF_SUPPORTED_FEATURES):
                if supported_feature not in dconfig.get(CONF_UNSUPPORTED_FEATURES):
                    filtered_features.append(supported_feature)
            dconfig[CONF_SUPPORTED_FEATURES] = filtered_features

        _LOGGER.debug("SUPPORTED FEATURES")
        _LOGGER.debug(dconfig.get(CONF_SUPPORTED_FEATURES))

        deebot_config = {
            CONF_SUPPORTED_FEATURES: strings_to_services(dconfig.get(CONF_SUPPORTED_FEATURES), STRING_TO_SERVICE)
        }

        hass.data[ECOVACS_CONFIG].append(deebot_config)

        _LOGGER.debug(hass.data[ECOVACS_CONFIG])

        discovery.load_platform(hass, "vacuum", DOMAIN, {}, config)

    return True

def services_to_strings(services, service_to_string):
    """Convert SUPPORT_* service bitmask to list of service strings."""
    strings = []
    for service in service_to_string:
        if service & services:
            strings.append(service_to_string[service])
    return strings


def strings_to_services(strings, string_to_service):
    """Convert service strings to SUPPORT_* service bitmask."""
    services = 0
    for string in strings:
        services |= string_to_service[string]
    return services
