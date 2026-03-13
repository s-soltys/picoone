from apps.galaxy_app import GalaxyApp
from apps.wifi_status import WiFiStatusApp
from apps.calculator import CalculatorApp
from apps.files_app import FilesApp
from apps.mines_app import MinesApp
from apps.rage_app import RageApp
from apps.space_invaders_app import SpaceInvadersApp
from apps.pacman_app import PacmanApp
from apps.arkanoid_app import ArkanoidApp
from apps.tetris_app import TetrisApp
from apps.paint_app import PaintApp


def build_apps():
    return [
        GalaxyApp(),
        WiFiStatusApp(),
        CalculatorApp(),
        FilesApp(),
        MinesApp(),
        RageApp(),
        SpaceInvadersApp(),
        PacmanApp(),
        ArkanoidApp(),
        TetrisApp(),
        PaintApp(),
    ]
