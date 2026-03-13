from apps.galaxy_app import GalaxyApp
from apps.wifi_status import WiFiStatusApp
from apps.calculator import CalculatorApp
from apps.files_app import FilesApp


def build_apps():
    return [
        GalaxyApp(),
        WiFiStatusApp(),
        CalculatorApp(),
        FilesApp(),
    ]
