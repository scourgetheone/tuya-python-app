import json

import tinytuya

# 1. Setup Cloud Connection
c = tinytuya.Cloud(
    apiRegion="sg",
    apiKey="8rj3k9ck3fd5atj3rreh",
    apiSecret="eed6ce998c6b486faf2786dafdc9ae94",
)

# 2. Define the command
# Most switches use 'switch_1' as the standard code.
# For DP Instruction Mode, you'd use the DP ID (e.g., '1')
commands = {
    "commands": [
        {
            "code": "switch_1",  # Or use the DP ID if 'switch_1' fails
            "value": True,  # True for ON, False for OFF
        }
    ]
}

# Fetch the list of all devices
print("Fetching devices list: ")
devices = c.getdevices()

# Print the results in a readable way
if isinstance(devices, list):
    for device in devices:
        print(f"Name: {device['name']}")
        device_id = device["id"]
        print(f"id: {device_id}")
        status = c.getstatus(device_id)
        print(f"{json.dumps(status, indent=2)}")
        functions = c.getfunctions(device_id)
        print(f"functions: {json.dumps(functions['result'], indent=2)}")
        endpoint = f"/v1.0/devices/{device_id}/timers"
        timers = c.cloudrequest(endpoint, "GET")
        if "result" in timers:
            for timer in timers["result"]:
                print(f"{json.dumps(timer, indent=2)}")

        print("Sending command...")
        result = c.sendcommand(device["id"], commands)
        print("Response from Cloud:", result)
