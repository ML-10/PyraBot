from discord.ext import commands
from discord.ext.commands import Context, Bot
from discord import User, Embed, Colour
import classes.games.TicTacToe as tic
from classes.Game import Game
from classes.Player import Player
from main import prefix
from time import time
import asyncio
from typing import Dict


class TicTacToe(commands.Cog):
    _channel_to_game: Dict[str, tic.TicTacToeGame] = {}

    def __init__(self, bot: Bot):
        self.bot: Bot = bot

    @commands.group(aliases=['ttt'])
    async def tictactoe(self, ctx: Context):
        "The root command for TicTacToe."

    @commands.cooldown(1, 5, commands.BucketType.user)
    @commands.command(parent=tictactoe, aliases=['c'])
    async def challenge(self, ctx: Context, user: User):
        "Challenges someone for a game of TicTacToe."
        if ctx.guild is None:
            await ctx.reply(
                "**You cannot challenge someone outside of a server**")
            return

        if ctx.author.id == user.id:
            await ctx.reply("**You cannot challenge yourself!**")
            return

        if ctx.channel.id in Game.occupied_channels:
            await ctx.reply("**This channel is occupied, by another game!**")
            return

        if ctx.author.id in Player.occupied_players:
            await ctx.reply("**You are already in a game!**")
            return

        if user.id in Player.occupied_players:
            await ctx.reply(f"**{user.mention} is in another game!**")
            return

        embed = Embed(title="TicTacToe In-Game Commands📝", color=Colour.red())

        embed.add_field(
            name="In-Game Commands ⚙️",
            value=
            f"**{prefix}ttt c @user** (challenge a user to a game of TicTacToe)\n"
            f"**{prefix}ttt p pos** (place your symbol at pos, a number from 0-8\n"
            f"**{prefix}ttt s** (forfeit the game)\n"
            f"**{prefix}ttt time** (win, if the opponent hasn't played in 100 seconds)\n"
            f"**{prefix}ttt t** (propose a tie to your opponent)\n")

        message = await ctx.send(
            content=
            f"**{ctx.author.mention} has challenged {user.mention} to a game of TicTacToe,"
            f" will they accept?**",
            embed=embed)

        reactions = ["✅", "❌"]
        accepted = False

        for reaction in reactions:
            await message.add_reaction(reaction)

        def check(react, author):
            return author == user and str(react.emoji) in reactions

        while True:
            try:
                reaction, user = await self.bot.wait_for(
                    "reaction_add", 
                    timeout=30,
                    check=check
                )

                if str(reaction.emoji) == "✅":
                    accepted = True
                    break

                elif str(reaction.emoji) == "❌":
                    break

            except asyncio.TimeoutError:
                break

        if accepted:

            if ctx.channel.id in Game.occupied_channels:

                await ctx.reply(
                    "**This channel was occupied, before the challenge was accepted!**"
                )
                return

            if ctx.author.id in Player.occupied_players:

                await ctx.reply(
                    "**You joined a game, before the challenge was accepted!**"
                )
                return

            if user.id in Player.occupied_players:

                await ctx.reply(
                    f"**{user.mention} joined a game, before the challenge was accepted!**"
                )
                return

            players = [ctx.author.id, user.id]

            game = tic.TicTacToeGame(players)

            Game.occupied_channels.append(ctx.channel.id)
            self._channel_to_game[str(ctx.channel.id)] = game

            for player in players:

                Player.occupied_players.append(player)

            await ctx.send(
                content=f"**{ctx.author.mention} ⚔️ {user.mention}\n"
                f"-------------------------\n"
                f"{game.get_player_by_id(ctx.author.id).emoji}{ctx.author.mention}\n"
                f"{game.get_player_by_id(user.id).emoji}{user.mention}**")

            await asyncio.sleep(1)

            game.timer = time()
            game.ongoing = True

            await self.display(ctx, game)  # send the first message

        else:

            await ctx.reply(
                f"**{user.mention} turned down/did not respond the challenge!**"
            )

    @commands.command(parent=tictactoe, aliases=['p'])
    async def place(self, ctx: Context, pos: int):
        "Places a marker on the board."
        try:

            game = self._channel_to_game[str(ctx.channel.id)]

            if ctx.author.id not in game.player_ids:

                await ctx.reply("**You are not part of this TicTacToe game!**")
                return

        except KeyError:

            await ctx.reply(
                "**There is no TicTacToe game running in this channel!**")
            return

        if pos not in range(0, 9):

            await ctx.reply("**Number must be between 0-8!**")
            return

        if game.current_round_player.discord_id != ctx.author.id:

            await ctx.reply("**It's not your turn!**")
            return

        success = game.board.place(game.current_round_player.symbol, pos)

        if success:

            if game.board.check_win(game.current_round_player.symbol):

                winner = game.current_round_player
                loser = game.next_player()

                await ctx.send(
                    f"**{winner.emoji}<@!{winner.discord_id}> defeated "
                    f"{loser.emoji}<@!{loser.discord_id}> in a game of TicTacToe!**"
                )

                self.delete_game(ctx, game)

            else:

                game.next_round()
                await self.display(ctx, game)

        else:

            await ctx.reply(f"**Spot #{pos} is occupied!**")

    @commands.command(parent=tictactoe, aliases=['resign', 'giveup', 'forfeit', 's'])
    async def surrender(self, ctx: Context):
        "Surrenders to the opponent."
        try:

            game = self._channel_to_game[str(ctx.channel.id)]

            if ctx.author.id not in game.player_ids:

                await ctx.reply("**You are not part of this TicTacToe game!**")
                return

        except KeyError:

            await ctx.reply(
                "**There is no TicTacToe game running in this channel!**")
            return

        loser = game.get_player_by_id(ctx.author.id)
        winner = [x for x in game.players
                  if x.discord_id != loser.discord_id][0]

        await ctx.send(
            f"**{loser.emoji}<@!{loser.discord_id}> surrendered to {winner.emoji}<@!{winner.discord_id}>!**"
        )

        self.delete_game(ctx, game)

    @commands.command(parent=tictactoe, aliases=['t'])
    async def tie(self, ctx: Context):
        'Proposes a tie to the opponent.'
        try:

            game = self._channel_to_game[str(ctx.channel.id)]

            if ctx.author.id not in game.player_ids:

                await ctx.reply("**You are not part of this TicTacToe game!**")
                return

        except KeyError:

            await ctx.reply(
                "**There is no TicTacToe game running in this channel!**")
            return

        thisplayer = game.get_player_by_id(ctx.author.id)
        otherplayer = [
            x for x in game.players if x.discord_id != thisplayer.discord_id
        ][0]

        thisplayer.proposed_tie = True

        if thisplayer.proposed_tie and otherplayer.proposed_tie:

            await ctx.send(
                f"**{thisplayer.emoji}<@!{thisplayer.discord_id}> and {otherplayer.emoji}<@!{otherplayer.discord_id}>"
                f"agreed to a tie!**")

            self.delete_game(ctx, game)

        else:

            await ctx.send(
                f"**{thisplayer.emoji}<@!{thisplayer.discord_id}> proposed a tie"
                f" to {otherplayer.emoji}<@!{otherplayer.discord_id}>!**")

    @commands.command(parent=tictactoe, aliases=['to', 'time'])
    async def timeout(self, ctx: Context):
        'Wins the game if the opponent has not responded for more than 100 seconds.'
        try:

            game = self._channel_to_game[str(ctx.channel.id)]

            if ctx.author.id not in game.player_ids:
                await ctx.reply("**You are not part of this TicTacToe game!**")
                return

        except KeyError:

            await ctx.reply(
                "**There is no TicTacToe game running in this channel!**")
            return

        if time() - game.timer > game.TIMEOUT:

            game.current_round_player = game.next_player()

            winner = game.current_round_player
            loser = game.next_player()

            await ctx.send(
                f"**{winner.emoji}<@!{winner.discord_id}> defeated "
                f"{loser.emoji}<@!{loser.discord_id}> due to the inactivity of the latter**"
            )

            self.delete_game(ctx, game)

        else:

            await ctx.reply(
                f"**<@!{game.next_player().discord_id}> has still ~{game.TIMEOUT - (time() - game.timer)}"
                f" seconds to play!**")

    @classmethod
    async def display(cls, ctx: Context, game: tic.TicTacToeGame):
        txt = game.board.display()

        await ctx.send(f"**It is <@!{game.current_round_player.discord_id}>'s "
                       f"turn ({game.current_round_player.emoji})**\n")

        # these 2 messages are split, because discord will make emojis smaller when they are combined with normal text

        await ctx.send('**Board:**\n' + txt)

    @classmethod
    def delete_game(cls, ctx: Context, game: tic.TicTacToeGame):

        Game.occupied_channels.remove(ctx.channel.id)
        del cls._channel_to_game[str(ctx.channel.id)]

        for player_id in game.player_ids:

            Player.occupied_players.remove(player_id)

        del game

    @challenge.error
    async def challenge_error(self, ctx: Context, error: Exception):

        if isinstance(error, commands.MissingRequiredArgument):

            await ctx.reply("**You need to specify the user!\n"
                            f"Example: {prefix}ttt c @user**")

        elif isinstance(error, commands.UserNotFound):

            await ctx.reply("**User does not exist or could not be found!\n"
                            f"Example: {prefix}ttt c @user**")

    @place.error
    async def p_error(self, ctx: Context, error: Exception):

        if isinstance(error, commands.MissingRequiredArgument):

            await ctx.reply("**You need to specify the coordinates!\n"
                            f"Example: {prefix}ttt p 4**")


def setup(bot):
    bot.add_cog(TicTacToe(bot))
