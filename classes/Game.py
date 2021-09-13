class Game:

    occupied_channels = []

    def __init__(self, name: str, max_players: int, minimum_players: int):
        self.name = name
        self.max = max_players
        self.minimum = minimum_players