import enum
import json
from typing import Annotated

import typer
from tuya_python import tuya


class SwitchState(enum.Enum):
    on = True
    off = False


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


def get_switch_command(switch_state: bool):
    return {
        "commands": [
            {
                "code": "switch_1",  # Or use the DP ID if 'switch_1' fails
                "value": switch_state,  # True for ON, False for OFF
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
            devices[device_id] = {"id": device_id, "name": info["name"]}
        else:
            _devices = tuya.cloud_connection.getdevices()
            if isinstance(_devices, list):
                print(
                    "No device_id specified, fetched entire device list. "
                    f"Found a total of {len(_devices)} device(s)"
                )
                for device in _devices:
                    devices[device["id"]] = device

        for _device_id, device in devices.items():
            print(f"Timers for device {device['name']}:")
            endpoint = f"/v2.0/cloud/timer/device/{_device_id}"
            timers = tuya.cloud_connection.cloudrequest(endpoint, "GET")
            if "result" in timers:
                for timer in timers["result"]:
                    print(f"{json.dumps(timer, indent=2)}")
                    device["timers"][timer.get("alias_name") or timer["timer_id"]] = (
                        timer
                    )
            else:
                device["timers"] = dict()
            devices[_device_id] = device
            print(f"Listed {len(timers['result'])} timer(s) for {device['name']}")
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
        local_timers = tuya.CONFIG.get("timers")
        if not local_timers:
            print("ERROR: No local timer configuration defined in the config file!")
            raise typer.Abort()

        for timer in local_timers:
            if not device_id or device_id == timer["device_id"]:
                print(json.dumps(timer, indent=2))
            if device_id == timer["device_id"]:
                return timer
        return local_timers

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
        current_timers = get_cloud_timers_list(device_id)

        # 2. We then compare between the SOT timers in the config and the cloud
        # timers. We will the reconcile the differences by creating, deleting,
        # and updating the timers in the cloud as needed
        to_create = dict()
        to_delete = dict()
        to_update = dict()

    @device_timers_app.command()
    def create(
        device_id: Annotated[str, typer.Argument(help="The device ID")],
        timer_name: Annotated[
            str, typer.Argument(help="Name of the timer. Must be unique")
        ],
        time_str: Annotated[str, typer.Argument(help="Time in HH:MM format")],
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
    ):
        endpoint = f"/v2.0/cloud/timer/device/{device_id}"
        payload = {
            "alias_name": timer_name,
            "loops": loops,
            "is_app_push": True,
            "category": "category_power",
            "timezone_id": "Asia/Ho_Chi_Minh",
            "functions": [{"code": "switch_1", "value": switch.value}],
            "time": time_str,
        }

        resp = tuya.cloud_connection.cloudrequest(endpoint, action="POST", post=payload)
        if resp["success"]:
            print("Timer successfully created!")
        print(json.dumps(resp, indent=2))
        get_cloud_timers_list(device_id)

    @device_timers_app.command()
    def modify(
        device_id: Annotated[str, typer.Argument(help="The device ID")],
        time_str: Annotated[str, typer.Argument(help="Time in HH:MM format")],
        switch: Annotated[
            SwitchState,
            typer.Argument(help="Switch the device on (True) or off (False)"),
        ],
        timer_name: Annotated[str, typer.Option(help="The name of the timer")] = "",
        timer_id: Annotated[str, typer.Option(help="The ID of the timer")] = "",
        loops: Annotated[
            str,
            typer.Option(
                help="Defines the weekdays in which the timer will run."
                " Example: 1111111 means the timer will run every day of the week"
            ),
        ] = "1111111",
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
        if not timer_name and not timer_id:
            print("Either timer_name or timer_id must be given!")
            raise typer.Abort()

        # get the timer_id by it's name
        if timer_name and not timer_id:
            timers = get_cloud_timers_list(device_id)
            for name, timer in timers[device_id]["timers"].items():
                if name == timer_name:
                    timer_id = timer["timer_id"]

        if not timer_id:
            print(f"No timer found with given name {timer_name}")
            raise typer.Abort()

        endpoint = f"/v2.0/cloud/timer/device/{device_id}"
        payload = {
            "timer_id": timer_id,
            "loops": loops,
            "category": "category_power",
            "timezone_id": "Asia/Ho_Chi_Minh",
            "functions": [{"code": "switch_1", "value": switch.value}],
            "time": time_str,
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
