from apps.browser_app import BrowserApp
from apps.calculator import CalculatorApp
from apps.device_status import DeviceStatusApp
from apps.galaxy_app import GalaxyApp
from apps.games import build_games
from apps.games_folder_app import GamesFolderApp
from apps.mtg_life_app import MTGLifeCounterApp
from apps.paint_app import PaintApp
from apps.pipboy_app import PipBoyApp
from apps.server_app import ServerApp
from apps.weather_app import WeatherApp
from apps.wifi_status import WiFiStatusApp


def build_apps():
    games = build_games()
    desktop = [
        GalaxyApp(),
        PipBoyApp(),
        BrowserApp(),
        ServerApp(),
        WeatherApp(),
        CalculatorApp(),
        DeviceStatusApp(),
        MTGLifeCounterApp(),
        PaintApp(),
        GamesFolderApp(games),
    ]
    return {
        "desktop": desktop,
        "menu": {
            "wifi": WiFiStatusApp(),
        },
        "games": games,
    }
