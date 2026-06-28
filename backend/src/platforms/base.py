# platforms/base.py
from abc import ABC, abstractmethod

class ChessPlatform(ABC):
    def __init__(self, username):
        self.username = username

    @abstractmethod
    def fetch_games(self) -> list:
        pass