from apps.galaxy_app import GalaxyApp
from apps.wifi_status import WiFiStatusApp
from apps.calculator import CalculatorApp
from apps.files_app import FilesApp
from apps.mines_app import MinesApp
from apps.rage_app import RageApp


def build_apps():
    return [
        GalaxyApp(),
        WiFiStatusApp(),
        CalculatorApp(),
        FilesApp(),
        MinesApp(),
        RageApp(),
    ]
