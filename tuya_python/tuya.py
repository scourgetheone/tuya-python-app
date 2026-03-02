import os
from pathlib import Path

import tinytuya
import tomlkit
import typer

CONFIG = {}
APPLICATION_DATA_PATH = typer.get_app_dir("tuya-python")
cloud_connection = None


def load_config_file():
    """
    The config file is called 'config.toml' and it is located in the
    APPLICATION_DATA_PATH directory. This function loads the config file
    and saves it to the module variable CONFIG


    """
    global CONFIG, APPLICATION_DATA_PATH

    # Create application folder if not exist
    Path(os.path.expanduser(APPLICATION_DATA_PATH)).mkdir(parents=True, exist_ok=True)

    # Opens a file for both reading and writing, see https://stackoverflow.com/a/15976014
    with open(
        os.path.expanduser(os.path.join(APPLICATION_DATA_PATH, "config.toml")),
        "a+",
    ) as config_file:
        config_file.seek(0)
        config_content = config_file.read()
        config = tomlkit.parse(config_content)
        CONFIG = config


def init_connection():
    load_config_file()
    global cloud_connection, CONFIG

    cloud_connection = tinytuya.Cloud(
        apiRegion=CONFIG["api_region"],
        apiKey=CONFIG["api_key"],
        apiSecret=CONFIG["api_secret"],
    )
