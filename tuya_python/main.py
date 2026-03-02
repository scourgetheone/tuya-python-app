import typer
from tuya_python import device, tuya

app = typer.Typer()

device.init_app(app)
tuya.init_connection()


if __name__ == "__main__":
    app()
