import datetime
import enum
import json
from typing import Annotated

import requests
import typer
from tuya_python import tuya


class SwitchState(enum.Enum):
    on = "on"
    off = "off"


class TimerType(enum.Enum):
    normal = "normal"
    sunset = "sunset"
    sunrise = "sunrise"


def get_device_switch_state(status):
    # Get the switch state
    for state in status["result"]:
        if state["code"] == "switch_1":
            if state["value"]:
                return SwitchState.on.name
            else:
                return SwitchState.off.name


def get_device_info(device_id):
    devices = tuya.cloud_connection.getdevices()
    if isinstance(devices, list):
        for device in devices:
            if device["id"] == device_id:
                return device
    return None


def get_switch_command(switch_state: SwitchState):
    return {
        "commands": [
            {
                "code": "switch_1",  # Or use the DP ID if 'switch_1' fails
                "value": True
                if switch_state == SwitchState.on
                else False,  # True for ON, False for OFF
            }
        ]
    }


def init_app(app: typer.Typer):
    device_app = typer.Typer()
    app.add_typer(device_app, name="device")

    @device_app.command("list")
    def _list():
        """
        Lists all the devices of the Tuya Cloud project
        """

        # Fetch the list of all devices
        print("Fetching devices list: ")
        devices = tuya.cloud_connection.getdevices()

        # Print the results in a readable way
        if isinstance(devices, list):
            print(f"Found a total of {len(devices)} device(s)")
            for device in devices:
                print("------")
                print(f"Name: {device['name']}")
                device_id = device["id"]
                print(f"id: {device_id}")
                status = tuya.cloud_connection.getstatus(device_id)
                print(f"State: {get_device_switch_state(status)}")
                print("------")

    @device_app.command()
    def switch(
        device_id: Annotated[str, typer.Argument(help="The device ID")],
        state: Annotated[SwitchState, typer.Argument(help="Set the switch's state")],
    ):
        command = get_switch_command(state.value)
        device = get_device_info(device_id)
        print(f"Sending command {state.value} to device {device['name']}")
        tuya.cloud_connection.sendcommand(device_id, command)
        status = tuya.cloud_connection.getstatus(device_id)
        print(
            f"Command sent successfully! Current device state: {get_device_switch_state(status)}"
        )

    @device_app.command()
    def info(
        device_id: Annotated[str, typer.Argument(help="The device ID")],
    ):
        """
        Gets the info of a device from Tuya Cloud API
        """
        status = tuya.cloud_connection.getconnectstatus(device_id)
        device = get_device_info(device_id)
        device["online"] = status
        print(json.dumps(device, indent=2))

    """
    ###################
    TIMER FUNCTIONALITY
    ###################
    """
    device_timers_app = typer.Typer()
    device_app.add_typer(device_timers_app, name="timer")

    @device_timers_app.command("list")
    def get_cloud_timers_list(
        device_id: Annotated[str, typer.Argument(help="The device ID")] = "",
    ):
        """
        Lists the timers of a device fetched from Tuya Cloud
        """
        devices = dict()
        if device_id:
            info = get_device_info(device_id)
            if not info:
                print(f"No device found with ID {device_id}")
                raise typer.Abort()
            devices[device_id] = dict()
        else:
            _devices = tuya.cloud_connection.getdevices()
            if isinstance(_devices, list):
                print(
                    "No device_id specified, fetched entire device list. "
                    f"Found a total of {len(_devices)} device(s)"
                )
                for device in _devices:
                    devices[device["id"]] = dict()

        for _device_id, device in devices.items():
            print(f"Timers for device {_device_id}:")
            endpoint = f"/v2.0/cloud/timer/device/{_device_id}"
            timers = tuya.cloud_connection.cloudrequest(endpoint, "GET")
            if "result" in timers:
                for timer in timers["result"]:
                    print(f"{json.dumps(timer, indent=2)}")
                    devices[_device_id][
                        timer.get("alias_name") or timer["timer_id"]
                    ] = timer

            print(f"Listed {len(timers['result'])} timer(s) for {_device_id}")
            print("------------")

        return devices

    @device_timers_app.command("list-local")
    def get_local_timers_list(
        device_id: Annotated[str, typer.Argument(help="The device ID")] = "",
    ):
        """
        Lists the timers of a device as defined in the config file

        Returns:
            A list of device dictionaries, in the format of:
            [{"device_id": "ID", "timers": "12:12-on", "15:30-off"}]
        """
        print("Listing local timer configuration")
        local_timers = tuya.CONFIG.get("device_timers")
        if not local_timers:
            print("ERROR: No local timer configuration defined in the config file!")
            raise typer.Abort()

        timers = dict()

        for device_timers in local_timers:
            _device_id = device_timers["device_id"]
            if _device_id not in timers:
                timers[_device_id] = dict()
            # If device_id is given, then only fetch timers from that device,
            # otherwise fetch timers of all devices found in the config
            if not device_id or device_id == _device_id:
                print(json.dumps(device_timers, indent=2))
                for timer in device_timers["timers"]:
                    timers[_device_id][timer["name"]] = timer

        return timers

    def timer_diff_check(local_timer: dict, cloud_timer: dict):
        """
        Checks for differences between the local timer and cloud timer

        Args:
            local_timer: the timer as defined in the config file
            cloud_timer: the timer fetched from the cloud

        Returns:
            dictionary of keys that have differing values
        """
        keys_to_check = ("time", "loops")
        diff = dict()
        for key in keys_to_check:
            cloud = cloud_timer[key]
            local = local_timer[key]
            if key == "time" and TimerType[local_timer["type"]] != TimerType.normal:
                local = get_astronomical_time(local_timer[key], local_timer["type"])
            if cloud != local:
                print(
                    f"Diff found for timer {local_timer['name']}: cloud_timer[{key}] ({cloud}) != local_timer[{key}] ({local})"
                )
                diff[key] = {"cloud": cloud, "local": local}
        return diff

    @device_timers_app.command()
    def apply(
        device_id: Annotated[str, typer.Argument(help="The device ID")] = "",
    ):
        """
        Apply our local timer configuration to Tuya cloud.

        This means that we compare between the source-of-truth (SOT) configuration
        file, the saved state of the cloud timers (if it exists), and the actual
        state of the cloud timers. When there are discrepancies between the
        states, new timers may be created, non-existent timers (in the cloud)
        may be deleted, and timers updated to reflect the updated configuration.

        Note that we will *never* delete or touch any cloud timers of devices
        that are not managed (defined) in the configuration file.
        """
        # 1. Get the various timer states, first being our SOT timer
        # configuration from the TOML config file
        local_timers = get_local_timers_list(device_id)
        # The current state of the timers from the cloud
        cloud_timers = get_cloud_timers_list(device_id)

        # 2. We then compare between the SOT timers in the config and the cloud
        # timers. We will the reconcile the differences by creating, deleting,
        # and updating the timers in the cloud as needed
        to_create = dict()
        to_delete = dict()
        to_update = dict()

        # Create locally defined timers in the cloud that does not exist yet
        for device_id in local_timers.keys():
            if device_id not in cloud_timers:
                print(
                    f"Device {device_id} does not exist in the cloud! Please"
                    " double-check the device ID as it may be incorrect, or you"
                    " have not added the device to the Tuya Cloud project."
                )
                continue

            for name, local_timer in local_timers[device_id].items():
                if name not in cloud_timers[device_id]:
                    print(
                        f"{name} does not exist in the cloud! Adding to to_create list"
                    )
                    if device_id not in to_create:
                        to_create[device_id] = dict()
                    to_create[device_id][name] = local_timer
                else:
                    # Check for differences and update cloud timer if needed
                    diff = timer_diff_check(local_timer, cloud_timers[device_id][name])
                    if diff:
                        if device_id not in to_update:
                            to_update[device_id] = dict()
                        # Save the timer_id so we can update the timer later
                        local_timer["timer_id"] = cloud_timers[device_id][name][
                            "timer_id"
                        ]
                        to_update[device_id][name] = local_timer

        # Delete cloud timers not defined in the local timer config
        for device_id in cloud_timers.keys():
            if device_id not in local_timers:
                print(
                    f"Device {device_id} is not defined in the config! Will not do"
                    " anything with this device."
                )
                continue

            for name, cloud_timer in cloud_timers[device_id].items():
                if name not in local_timers[device_id]:
                    print(
                        f"Timer {name} is not defined locally for device"
                        f" {device_id}! Adding to to_delete list"
                    )
                    if device_id not in to_delete:
                        to_delete[device_id] = dict()
                    to_delete[device_id][name] = cloud_timer

        if to_delete:
            for device_id, timers in to_delete.items():
                print(f"Now deleting {len(timers.keys())} timers from {device_id}")
                timer_ids = list()
                for timer in timers.values():
                    timer_ids.append(timer["timer_id"])
                delete(device_id, timer_ids)

        if to_create:
            for device_id, timers in to_create.items():
                print(f"Now creating {len(timers.keys())} timers from {device_id}")
                for timer in timers.values():
                    create(
                        device_id,
                        **timer,
                    )

        if to_update:
            for device_id, timers in to_update.items():
                print(f"Now updating {len(timers.keys())} timers from {device_id}")
                for timer in timers.values():
                    modify(
                        device_id,
                        **timer,
                    )

    def get_astronomical_time(time: str, type: TimerType) -> str:
        """
        Gets sunrise and sunset times from OpenMeteo

        Args:
            time: the time offset given in the format: "+5" where the first
                character tells if the time offset should add "+" or subtract "-"
                from the sunset/sunrise rimes. After the offset character is the
                time offset expressed in minutes
            type: the type of timer. Valid values are TimerType.sunset and
                TimerType.sunrise
        """
        weather_data = requests.get(
            "https://api.open-meteo.com/v1/forecast?latitude=21.7229&longitude=104.9113&hourly=temperature_2m,precipitation_probability,precipitation,cloud_cover&daily=sunrise,sunset&timezone=Asia%2FBangkok&forecast_days=1"
        ).json()
        suntime = datetime.datetime.fromisoformat(weather_data["daily"][type.value][0])

        time = float(time)
        time_obj = suntime + datetime.timedelta(minutes=time)

        return time_obj.strftime("%H:%M")

    @device_timers_app.command()
    def create(
        device_id: Annotated[str, typer.Argument(help="The device ID")],
        name: Annotated[str, typer.Argument(help="Name of the timer. Must be unique")],
        time: Annotated[str, typer.Argument(help="Time in HH:MM format")],
        switch: Annotated[
            SwitchState,
            typer.Argument(help="Switch the device on (True) or off (False)"),
        ],
        loops: Annotated[
            str,
            typer.Option(
                help="Defines the weekdays in which the timer will run."
                " Example: 1111111 means the timer will run every day of the week"
            ),
        ] = "1111111",
        type: Annotated[
            TimerType, typer.Option(help="Type of timer")
        ] = TimerType.normal,
    ):
        endpoint = f"/v2.0/cloud/timer/device/{device_id}"
        if isinstance(type, str):
            type = TimerType[type]
        if type != TimerType.normal:
            time = get_astronomical_time(time, type)
        payload = {
            "alias_name": name,
            "loops": loops,
            "is_app_push": True,
            "category": "category_power",
            "timezone_id": "Asia/Ho_Chi_Minh",
            "functions": [
                {"code": "switch_1", "value": True if switch == "on" else False}
            ],
            "time": time,
        }

        resp = tuya.cloud_connection.cloudrequest(endpoint, action="POST", post=payload)
        if resp["success"]:
            print("Timer successfully created!")
        print(json.dumps(resp, indent=2))

    @device_timers_app.command()
    def modify(
        device_id: Annotated[str, typer.Argument(help="The device ID")],
        time: Annotated[str, typer.Argument(help="Time in HH:MM format")],
        switch: Annotated[
            SwitchState,
            typer.Argument(help="Switch the device on (True) or off (False)"),
        ],
        name: Annotated[str, typer.Option(help="The name of the timer")] = "",
        timer_id: Annotated[str, typer.Option(help="The ID of the timer")] = "",
        loops: Annotated[
            str,
            typer.Option(
                help="Defines the weekdays in which the timer will run."
                " Example: 1111111 means the timer will run every day of the week"
            ),
        ] = "1111111",
        type: Annotated[
            TimerType, typer.Option(help="Type of timer")
        ] = TimerType.normal,
    ):
        """
        Modify an existing timer. At least one of the timer identifiers,
        timer_name or timer_id, must be specified.

        Args:
            device_id: the ID of the device whose timer we want to modify
            time_str: set the time of the timer in HH:MM format, e.g "12:35"
            switch: turn the switch on (True) or off (False)
            timer_name: the name of the timer we want to modify
            timer_id: the id of the timer we want to modify
        """
        if isinstance(type, str):
            type = TimerType[type]
        if type != TimerType.normal:
            time = get_astronomical_time(time, type)
        if not name and not timer_id:
            print("Either timer_name or timer_id must be given!")
            raise typer.Abort()

        # get the timer_id by it's name
        if name and not timer_id:
            timers = get_cloud_timers_list(device_id)
            for _name, timer in timers[device_id].items():
                if _name == name:
                    timer_id = timer["timer_id"]

        if not timer_id:
            print(f"No timer found with given name {name}")
            raise typer.Abort()

        endpoint = f"/v2.0/cloud/timer/device/{device_id}"
        payload = {
            "timer_id": timer_id,
            "loops": loops,
            "category": "category_power",
            "timezone_id": "Asia/Ho_Chi_Minh",
            "functions": [{"code": "switch_1", "value": switch.value}],
            "time": time,
        }

        resp = tuya.cloud_connection.cloudrequest(
            endpoint,
            action="PUT",
            post=payload,
        )
        print(resp)
        if resp["success"]:
            print(f"Successfully modified timer {timer_id} from device {device_id}")

    @device_timers_app.command()
    def delete(
        device_id: Annotated[str, typer.Argument(help="The device ID")],
        timer_ids: Annotated[
            list[str], typer.Argument(help="List of timer IDs to delete")
        ] = [],
        all: Annotated[bool, typer.Option(help="Delete all timers")] = False,
    ):
        if all:
            endpoint = f"/v2.0/cloud/timer/device/{device_id}"
            resp = tuya.cloud_connection.cloudrequest(endpoint, action="DELETE")
            print(resp)
            if resp["success"]:
                print(f"Successfully deleted all timers from device {device_id}")
            return

        if not timer_ids:
            print("No timer IDs specified, and --all not given. Aborting...")
            raise typer.Abort()

        endpoint = f"/v2.0/cloud/timer/device/{device_id}/batch"
        query = {"timer_ids": ",".join(timer_ids)}
        resp = tuya.cloud_connection.cloudrequest(
            endpoint, action="DELETE", post=query, query=query
        )
        print(resp)
        if resp["success"]:
            print(
                f"Successfully deleted timers {' '.join(timer_ids)} from device {device_id}"
            )
