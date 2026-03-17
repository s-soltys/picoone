from apps.games.arkanoid_app import ArkanoidApp
from apps.games.mines_app import MinesApp
from apps.games.pacman_app import PacmanApp
from apps.games.space_invaders_app import SpaceInvadersApp
from apps.games.tetris_app import TetrisApp


def build_games():
    return [
        MinesApp(),
        SpaceInvadersApp(),
        PacmanApp(),
        ArkanoidApp(),
        TetrisApp(),
    ]
