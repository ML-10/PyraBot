class Player:

    occupied_players = []

    def __init__(self, discord_id: int):
        self.discord_id: int = discord_id