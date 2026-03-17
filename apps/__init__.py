from apps.galaxy_app import GalaxyApp
from apps.wifi_status import WiFiStatusApp
from apps.weather_app import WeatherApp
from apps.calculator import CalculatorApp
from apps.files_app import FilesApp
from apps.mines_app import MinesApp
from apps.space_invaders_app import SpaceInvadersApp
from apps.pacman_app import PacmanApp
from apps.arkanoid_app import ArkanoidApp
from apps.tetris_app import TetrisApp
from apps.paint_app import PaintApp


def build_apps():
    return [
        GalaxyApp(),
        WiFiStatusApp(),
        WeatherApp(),
        CalculatorApp(),
        FilesApp(),
        MinesApp(),
        SpaceInvadersApp(),
        PacmanApp(),
        ArkanoidApp(),
        TetrisApp(),
        PaintApp(),
    ]
