import enum
from typing import Annotated

import typer
from tuya_python import tuya


class SwitchState(enum.Enum):
    on = "on"
    off = "off"


def get_device_state(status):
    # Get the switch state
    for state in status["result"]:
        if state["code"] == "switch_1":
            if state["value"]:
                return SwitchState.on.value
            else:
                return SwitchState.off.value


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
                print(f"State: {get_device_state(status)}")
                print("------")

    @device_app.command()
    def switch(
        device_id: Annotated[str, typer.Argument(help="The device ID")],
        state: Annotated[SwitchState, typer.Argument(help="Set the switch's state")],
    ):
        if state == SwitchState.on:
            command = get_switch_command(True)
        if state == SwitchState.off:
            command = get_switch_command(False)

        print(f"Sending command {state.value}")
        tuya.cloud_connection.sendcommand(device_id, command)
        status = tuya.cloud_connection.getstatus(device_id)

        print(
            f"Command sent successfully! Current device state: {get_device_state(status)}"
        )
