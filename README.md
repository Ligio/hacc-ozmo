# hacc-ozmo
Home Assistant Custom Component for Ecovacs Deebot Ozmo 900

With this Home Assistant Custom Component you'll be able to 
* play/pause/stop
* locate
* send to home
* clean[auto|map|area]
* set fan speed
* set water level

You can use it with this configuration (same values as for the [official integration](https://www.home-assistant.io/integrations/ecovacs/) but the integration is called *deebot* instead of *ecovacs*:

```
# required fields
deebot:
  username: YOUR_ECOVACS_USERNAME
  password: YOUR_ECOVACS_PASSWORD
  country: YOUR_TWO_LETTER_COUNTRY_CODE
  continent: YOUR_TWO_LETTER_CONTINENT_CODE
``` 

You can also customize the previous configuration with **supported_features** and/or **unsupported_features**, to add/remove vacuum features:

```
# required fields
deebot:
  username: YOUR_ECOVACS_USERNAME
  password: YOUR_ECOVACS_PASSWORD
  country: YOUR_TWO_LETTER_COUNTRY_CODE
  continent: YOUR_TWO_LETTER_CONTINENT_CODE
  supported_features:
  - start
  - pause
  - [....]
  unsupported_features:
  - clean_spot
  - fan_speed
``` 

This is the list of supported/unsupported features you can use:

```
[
    "start",
    "pause",
    "stop",
    "return_home",
    "fan_speed",
    "battery",
    "status",
    "send_command",
    "locate",
    "clean_spot",
    "turn_on",
    "turn_off"
]

```

To set the water level you should use the send_command service:

```
vacuum_script_set_water:
  alias: set vacuum water level
  sequence:
  - service: vacuum.send_command
    data:
      command: set_water_level
      entity_id: vacuum.ambrogina
      params:
        level: low|medium|high
```

Also to clean area or custom map locations (by coordinates) you should use the send_command:

```
vacuum_script_clean_area:
  alias: clean area
  sequence:
  - service: vacuum.send_command
    data:
      command: spot_area
      entity_id: vacuum.ambrogina
      params:
        area: 0,2  # multiple areas index from your ecovacs app

vacuum_script_clean_map:
  alias: clean map
  sequence:
  - service: vacuum.send_command
    data:
      command: spot_area
      entity_id: vacuum.ambrogina
      params:
        map: "1580.0,-4087.0,3833.0,-7525.0"  # x,y coords from your ecovacs app
```

To get area/map info I've installed "Packet Capture" app on my Android phone and used it with Ecovacs app to find needed info