import asyncio
import ctypes
import functools
import itertools
import json
import logging
import math
import os
import random
import re
import sys
import typing

import aioconsole
import discord
import qrcode
import requests
import SimpleEconomy as Seco
import youtube_dl
from async_timeout import timeout
from bs4 import BeautifulSoup
from discord.ext import commands
from discord.voice_client import VoiceClient
from googletrans import LANGCODES, Translator
from pretty_help import PrettyHelp

translator = Translator()

# Logging
logger = logging.getLogger('discord')
logger.setLevel(logging.INFO)
handler = logging.FileHandler(
    filename='log.log', encoding='utf-8', mode='w')
handler.setFormatter(logging.Formatter(
    '%(asctime)s:%(levelname)s:%(name)s: %(message)s'))
logger.addHandler(handler)

token = os.getenv('BOT_TOKEN')
prefix = '!'
bot = commands.Bot(prefix, help_command=PrettyHelp(
    color=discord.Color.orange()))

Seco.Database_dir = "C:\\Users\\sophi\\Desktop\\bot\\discord-py-meowbot\\economy-db\\"
Seco.default_balance = 1000

# string defs
empty = 'Empty queue.'
no = 'Nothing being played at the moment.'
dm = 'This command can\'t be used in DM channels.'
error = 'An error occurred: {}'
noaccount = 'You do not have an account! Run {}register to register.'

currency_unit = '₱'

youtube_dl.utils.bug_reports_message = lambda: ''


with open('amounts.json', 'r') as f:
    amounts = json.load(f)

# checks


def checkforavraaj(ctx: commands.Context):
    """A check for the user AVRAAJ.

    Args:
        ctx (commands.Context): The context of the command.

    Returns:
        bool: True if the user is AVRAAJ.
    """
    return not ctx.author.id == 682859915181817886


def checkml(ctx):
    """A check for the user circles.png.

    Args:
        ctx (commands.Context): The context of the command.

    Returns:
        bool: True if the user is circles.png.
    """
    return ctx.author.id == 262120465525506049


def checkadmin(ctx):
    return discord.abc.GuildChannel.permissions_for(ctx.message.author)


async def on_ready():
    print('Ready')


@bot.event
async def on_message(message: discord.Message):
    bad = False
    if message.author == bot.user:
        return

    no = '''
    with open('filter.txt') as f:
        messagefilter = f.read().split(', ')
        messagefilter[-1] = messagefilter[-1][:7]
    '''

    await bot.process_commands(message)


class VoiceError(Exception):
    pass


class YTDLError(Exception):
    pass


class YTDLSource(discord.PCMVolumeTransformer):
    YTDL_OPTIONS = {
        'format': 'bestaudio/best',
        'extractaudio': True,
        'audioformat': 'mp3',
        'outtmpl': '%(extractor)s-%(id)s-%(title)s.%(ext)s',
        'restrictfilenames': True,
        'noplaylist': True,
        'nocheckcertificate': True,
        'ignoreerrors': False,
        'logtostderr': False,
        'quiet': True,
        'no_warnings': True,
        'default_search': 'auto',
        'source_address': '0.0.0.0',
    }

    FFMPEG_OPTIONS = {
        'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
        'options': '-vn',
    }

    ytdl = youtube_dl.YoutubeDL(YTDL_OPTIONS)

    def __init__(self, ctx: commands.Context, source: discord.FFmpegPCMAudio, *, data: dict, volume: float = 0.5):
        super().__init__(source, volume)

        self.requester = ctx.author
        self.channel = ctx.channel
        self.data = data

        self.uploader = data.get('uploader')
        self.uploader_url = data.get('uploader_url')
        date = data.get('upload_date')
        self.upload_date = date[6:8] + '.' + date[4:6] + '.' + date[0:4]
        self.title = data.get('title')
        self.thumbnail = data.get('thumbnail')
        self.description = data.get('description')
        self.duration = self.parse_duration(int(data.get('duration')))
        self.tags = data.get('tags')
        self.url = data.get('webpage_url')
        self.views = data.get('view_count')
        self.likes = data.get('like_count')
        self.dislikes = data.get('dislike_count')
        self.stream_url = data.get('url')

    def __str__(self):
        return '**{0.title}** by **{0.uploader}**'.format(self)

    @classmethod
    async def create_source(cls, ctx: commands.Context, search: str, *, loop: asyncio.BaseEventLoop = None):
        loop = loop or asyncio.get_event_loop()

        partial = functools.partial(
            cls.ytdl.extract_info, search, download=False, process=False)
        data = await loop.run_in_executor(None, partial)

        if data is None:
            raise YTDLError(
                'Couldn\'t find anything that matches `{}`'.format(search))

        if 'entries' not in data:
            process_info = data
        else:
            process_info = None
            for entry in data['entries']:
                if entry:
                    process_info = entry
                    break

            if process_info is None:
                raise YTDLError(
                    'Couldn\'t find anything that matches `{}`'.format(search))

        webpage_url = process_info['webpage_url']
        partial = functools.partial(
            cls.ytdl.extract_info, webpage_url, download=False)
        processed_info = await loop.run_in_executor(None, partial)

        if processed_info is None:
            raise YTDLError('Couldn\'t fetch `{}`'.format(webpage_url))

        if 'entries' not in processed_info:
            info = processed_info
        else:
            info = None
            while info is None:
                try:
                    info = processed_info['entries'].pop(0)
                except IndexError:
                    raise YTDLError(
                        'Couldn\'t retrieve any matches for `{}`'.format(webpage_url))

        return cls(ctx, discord.FFmpegPCMAudio(info['url'], **cls.FFMPEG_OPTIONS), data=info)

    @staticmethod
    def parse_duration(duration: int):
        minutes, seconds = divmod(duration, 60)
        hours, minutes = divmod(minutes, 60)
        days, hours = divmod(hours, 24)

        duration = []
        if days > 0:
            duration.append('{} days'.format(days))
        if hours > 0:
            duration.append('{} hours'.format(hours))
        if minutes > 0:
            duration.append('{} minutes'.format(minutes))
        if seconds > 0:
            duration.append('{} seconds'.format(seconds))

        return ', '.join(duration)


class Song:
    __slots__ = ('source', 'requester')

    def __init__(self, source: YTDLSource):
        self.source = source
        self.requester = source.requester

    def create_embed(self):
        embed = (discord.Embed(title='Now playing',
                               description='```css\n{0.source.title}\n```'.format(
                                   self),
                               color=discord.Color.blurple())
                 .add_field(name='Duration', value=self.source.duration)
                 .add_field(name='Requested by', value=self.requester.mention)
                 .add_field(name='Uploader', value='[{0.source.uploader}]({0.source.uploader_url})'.format(self))
                 .add_field(name='URL', value='[Click]({0.source.url})'.format(self))
                 .set_thumbnail(url=self.source.thumbnail))

        return embed


class SongQueue(asyncio.Queue):
    def __getitem__(self, item):
        if isinstance(item, slice):
            return list(itertools.islice(self._queue, item.start, item.stop, item.step))
        else:
            return self._queue[item]

    def __iter__(self):
        return self._queue.__iter__()

    def __len__(self):
        return self.qsize()

    def clear(self):
        self._queue.clear()

    def shuffle(self):
        random.shuffle(self._queue)

    def remove(self, index: int):
        del self._queue[index]


class VoiceState:
    def __init__(self, bot: commands.Bot, ctx: commands.Context):
        self.bot = bot
        self._ctx = ctx

        self.current = None
        self.voice = None
        self.next = asyncio.Event()
        self.songs = SongQueue()

        self._loop = False
        self._volume = 0.5
        self.skip_votes = set()

        self.audio_player = bot.loop.create_task(self.audio_player_task())

    def __del__(self):
        self.audio_player.cancel()

    @property
    def loop(self):
        return self._loop

    @loop.setter
    def loop(self, value: bool):
        self._loop = value

    @property
    def volume(self):
        return self._volume

    @volume.setter
    def volume(self, value: float):
        self._volume = value

    @property
    def is_playing(self):
        return self.voice and self.current

    async def audio_player_task(self):
        while True:
            self.next.clear()

            if not self.loop:
                # Try to get the next song within 3 minutes.
                # If no song will be added to the queue in time,
                # the player will disconnect due to performance
                # reasons.
                try:
                    async with timeout(180):  # 3 minutes
                        self.current = await self.songs.get()
                except asyncio.TimeoutError:
                    self.bot.loop.create_task(self.stop())
                    return

            self.current.source.volume = self._volume
            self.voice.play(self.current.source, after=self.play_next_song)
            await self.current.source.channel.send(embed=self.current.create_embed())

            await self.next.wait()

    def play_next_song(self, error=None):
        if error:
            raise VoiceError(str(error))

        self.next.set()

    def skip(self):
        self.skip_votes.clear()

        if self.is_playing:
            self.voice.stop()

    async def stop(self):
        self.songs.clear()

        if self.voice:
            await self.voice.disconnect()
            self.voice = None


class Music(commands.Cog):
    """A category for commands related to playing music."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.voice_states = {}

    def get_voice_state(self, ctx: commands.Context):
        state = self.voice_states.get(ctx.guild.id)
        if not state:
            state = VoiceState(self.bot, ctx)
            self.voice_states[ctx.guild.id] = state

        return state

    def cog_unload(self):
        for state in self.voice_states.values():
            self.bot.loop.create_task(state.stop())

    def cog_check(self, ctx: commands.Context):
        if not ctx.guild:
            raise commands.NoPrivateMessage(
                'This command can\'t be used in DM channels.')
        return True

    async def cog_before_invoke(self, ctx: commands.Context):
        ctx.voice_state = self.get_voice_state(ctx)

    async def cog_command_error(self, ctx: commands.Context, error: commands.CommandError):
        await ctx.send('An error occurred: {}'.format(str(error)))

    @commands.command(name='join', invoke_without_subcommand=True)
    async def _join(self, ctx: commands.Context):
        """Joins a voice channel."""

        destination = ctx.author.voice.channel
        if ctx.voice_state.voice:
            await ctx.voice_state.voice.move_to(destination)
            return

        ctx.voice_state.voice = await destination.connect()

    @commands.command(name='summon')
    @commands.has_permissions(manage_guild=True)
    async def _summon(self, ctx: commands.Context, *, channel: discord.VoiceChannel = None):
        """Summons the bot to a voice channel.
        If no channel was specified, it joins your channel.
        """

        if not channel and not ctx.author.voice:
            raise VoiceError(
                'You are neither connected to a voice channel nor specified a channel to join.')

        destination = channel or ctx.author.voice.channel
        if ctx.voice_state.voice:
            await ctx.voice_state.voice.move_to(destination)
            return

        ctx.voice_state.voice = await destination.connect()

    @commands.command(name='leave', aliases=['disconnect'])
    @commands.has_permissions(manage_guild=True)
    async def _leave(self, ctx: commands.Context):
        """Clears the queue and leaves the voice channel."""

        if not ctx.voice_state.voice:
            return await ctx.send('Not connected to any voice channel.')

        await ctx.voice_state.stop()
        del self.voice_states[ctx.guild.id]

    @commands.command(name='volume')
    async def _volume(self, ctx: commands.Context, *, volume: int):
        """Sets the volume of the player."""

        if not ctx.voice_state.is_playing:
            return await ctx.send('Nothing being played at the moment.')
        ctx.voice_state.volume = volume / 100
        await ctx.send('Volume of the player set to {}%'.format(volume))

    @commands.command(name='now', aliases=['current'])
    async def _now(self, ctx: commands.Context):
        """Displays the currently playing song."""

        await ctx.send(embed=ctx.voice_state.current.create_embed())

    @commands.command(name='pause')
    @commands.has_permissions(manage_guild=True)
    async def _pause(self, ctx: commands.Context):
        """Pauses the currently playing song."""

        if not ctx.voice_state.is_playing and ctx.voice_state.voice.is_playing():
            ctx.voice_state.voice.pause()
            await ctx.message.add_reaction('⏯')

    @commands.command(name='resume')
    @commands.has_permissions(manage_guild=True)
    async def _resume(self, ctx: commands.Context):
        """Resumes a currently paused song."""

        if not ctx.voice_state.is_playing and ctx.voice_state.voice.is_paused():
            ctx.voice_state.voice.resume()
            await ctx.message.add_reaction('⏯')

    @commands.command(name='stop')
    @commands.has_permissions(manage_guild=True)
    async def _stop(self, ctx: commands.Context):
        """Stops playing song and clears the queue."""

        ctx.voice_state.songs.clear()

        if not ctx.voice_state.is_playing:
            ctx.voice_state.voice.stop()
            await ctx.message.add_reaction('⏹')

    @commands.command(name='skip')
    async def _skip(self, ctx: commands.Context):
        """Vote to skip a song. The requester can automatically skip.
        3 skip votes are needed for the song to be skipped.
        """

        if not ctx.voice_state.is_playing:
            return await ctx.send('Not playing any music right now...')

        voter = ctx.message.author
        if voter == ctx.voice_state.current.requester:
            await ctx.message.add_reaction('⏭')
            ctx.voice_state.skip()

        elif voter.id not in ctx.voice_state.skip_votes:
            ctx.voice_state.skip_votes.add(voter.id)
            total_votes = len(ctx.voice_state.skip_votes)

            if total_votes >= 3:
                await ctx.message.add_reaction('⏭')
                ctx.voice_state.skip()
            else:
                await ctx.send('Skip vote added, currently at **{}/3**'.format(total_votes))

        else:
            await ctx.send('You have already voted to skip this song.')

    @commands.command(name='queue')
    async def _queue(self, ctx: commands.Context, *, page: int = 1):
        """Shows the player's queue.
        You can optionally specify the page to show. Each page contains 10 elements.
        """

        if len(ctx.voice_state.songs) == 0:
            return await ctx.send('Empty queue.')

        items_per_page = 10
        pages = math.ceil(len(ctx.voice_state.songs) / items_per_page)

        start = (page - 1) * items_per_page
        end = start + items_per_page

        queue = ''
        for i, song in enumerate(ctx.voice_state.songs[start:end], start=start):
            queue += '`{0}.` [**{1.source.title}**]({1.source.url})\n'.format(
                i + 1, song)

        embed = (discord.Embed(description='**{} tracks:**\n\n{}'.format(len(ctx.voice_state.songs), queue))
                 .set_footer(text='Viewing page {}/{}'.format(page, pages)))
        await ctx.send(embed=embed)

    @commands.command(name='shuffle')
    async def _shuffle(self, ctx: commands.Context):
        """Shuffles the queue."""

        if len(ctx.voice_state.songs) == 0:
            return await ctx.send('Empty queue.')

        ctx.voice_state.songs.shuffle()
        await ctx.message.add_reaction('✅')

    @commands.command(name='remove')
    async def _remove(self, ctx: commands.Context, index: int):
        """Removes a song from the queue at a given index."""

        if len(ctx.voice_state.songs) == 0:
            return await ctx.send('Empty queue.')

        ctx.voice_state.songs.remove(index - 1)
        await ctx.message.add_reaction('✅')

    @commands.command(name='loop')
    async def _loop(self, ctx: commands.Context):
        """Loops the currently playing song.
        Invoke this command again to unloop the song.
        """

        if not ctx.voice_state.is_playing:
            return await ctx.send('Nothing being played at the moment.')

        # Inverse boolean value to loop and unloop.
        ctx.voice_state.loop = not ctx.voice_state.loop
        await ctx.message.add_reaction('✅')

    @commands.command(name='play')
    async def _play(self, ctx: commands.Context, *, search: str):
        """Plays a song.
        If there are songs in the queue, this will be queued until the
        other songs finished playing.
        This command automatically searches from various sites if no URL is provided.
        A list of these sites can be found here: https://rg3.github.io/youtube-dl/supportedsites.html
        """

        if not ctx.voice_state.voice:
            await ctx.invoke(self._join)

        async with ctx.typing():
            try:
                source = await YTDLSource.create_source(ctx, search, loop=self.bot.loop)
            except YTDLError as e:
                await ctx.send('An error occurred while processing this request: {}'.format(str(e)))
            else:
                song = Song(source)

                await ctx.voice_state.songs.put(song)
                await ctx.send('Enqueued {}'.format(str(source)))

    @_join.before_invoke
    @_play.before_invoke
    async def ensure_voice_state(self, ctx: commands.Context):
        if not ctx.author.voice or not ctx.author.voice.channel:
            raise commands.CommandError(
                'You are not connected to any voice channel.')

        if ctx.voice_client and ctx.voice_client.channel != ctx.author.voice.channel:
            raise commands.CommandError('Bot is already in a voice channel.')


class General(commands.Cog):
    """A category for commands that don't fit into the other categories."""

    def __init__(self, bot):
        self.bot = bot

    async def cog_command_error(self, ctx: commands.Context, error: commands.CommandError):
        await ctx.send(error.format(str(error)))

    def cog_check(self, ctx: commands.Context):
        if not ctx.guild:
            raise commands.NoPrivateMessage(dm)
        return True

    @commands.command()
    async def hello(self, ctx: commands.Context, *args):
        '''Say hello.'''
        await ctx.message.channel.send('Hello {0.author.mention}! Did you know that @ML-10 is my creator?'.format(ctx.message))

    @commands.command()
    async def solve(self, ctx: commands.Context, equation):
        '''Evaluate a Python expression.'''
        await ctx.message.channel.send('The answer to: "' + equation + '" is ' + str(eval(equation)))

    @commands.command()
    async def translate(self, ctx: commands.Context, text: str, lang: str):
        """Detects language and translates text to another language."""
        await ctx.send('Translated: '+translator.translate(text, dest=LANGCODES[lang.lower()]).text)

    @commands.command()
    async def translatehelp(self, ctx):
        "Returns all languages availiable to translate."

        await ctx.send(str(LANGCODES))

    @commands.command()
    async def drunk(self, ctx: commands.Context, *, text: str):
        "Randomizes capitalization."
        text = list(text)
        for letter in text:
            if random.randint(0, 1) == 0:
                text[text.index(letter)] = \
                    text[text.index(letter)].upper() \
                    if text[text.index(letter)].islower() \
                    else text[text.index(letter)].lower()
        await ctx.send('Drunk: "' + ''.join(text) + '"')

    @commands.is_owner()
    @commands.command()
    async def restart(self, ctx: commands.Context):
        """Restarts the bot. (can only be stopped by <@262120465525506049>)"""
        await ctx.send('Logging out...')
        await bot.logout()
        await ctx.send('Logging in...')
        await bot.login(token)

    @commands.is_owner()
    @commands.command()
    async def playing(self, ctx: commands.Context, *, game):
        "Changes bot's playing status."
        await bot.change_presence(activity=discord.Game(name=game))
        await ctx.message.add_reaction('✅')

    @commands.is_owner()
    @commands.command()
    async def streaming(self, ctx: commands.Context, *, stream):
        "Changes bot's streaming status."
        await bot.change_presence(activity=discord.Streaming(name=stream, url=""))
        await ctx.message.add_reaction('✅')

    @commands.is_owner()
    @commands.command()
    async def listening(self, ctx: commands.Context, *, song):
        "Changes bot's listening status."
        await bot.change_presence(activity=discord.Activity(type=discord.ActivityType.listening, name=song))
        await ctx.message.add_reaction('✅')

    @commands.is_owner()
    @commands.command()
    async def watching(self, ctx: commands.Context, *, movie):
        "Changes bot's watching status."
        await bot.change_presence(activity=discord.Activity(type=discord.ActivityType.watching, name=movie))
        await ctx.message.add_reaction('✅')

    @commands.command()
    @commands.check(checkforavraaj)
    async def warn(self, ctx, member: discord.Member, reason: typing.Optional[str] = 'breaking the rules'):
        'Warns a member with an optional reason.'
        await member.send(member.mention + ' YOU HAVE BEEN WARNED FROM guild "' + member.guild.name + '" FOR ' + reason)

    @commands.command()
    async def ping(self, ctx):
        "Returns the bot's latency in milliseconds."
        await ctx.send('Pong! {0}ms'.format(round(bot.latency, 5) * 1000))

    @commands.command(aliases=['vote'])
    async def poll(self, ctx: commands.Context, *, statement):
        "Starts a poll."
        embed = discord.Embed(
            title="Vote! ["+statement+"]",
            description=statement,
            color=discord.Colour.blurple())
        embed.set_footer(text="from PyraBot")
        message = await ctx.send(embed=embed)
        await message.add_reaction('👍')
        await message.add_reaction('👎')
        await ctx.message.delete()

    @commands.command()
    async def scp(self, ctx):
        "Finds a random scp from www.scpwiki.com."
        page = requests.get('http://www.scpwiki.com/random:random-scp')
        soup = BeautifulSoup(page.text, 'html.parser')

        element = soup.find(id='page-content')

        page = requests.get(element.div.div.p.iframe['src'].split('#')[-1])
        soup = BeautifulSoup(page.text, 'html.parser')

        element = soup.find('div', id='page-content')
        element = element.text.strip()

        for chunk in list(element[i:i+2000] for i in range(0, len(element), 2000)):
            await ctx.send(chunk)

    @commands.command()
    async def spam(self, ctx: commands.Context):
        for i in range(10):
            await bot.get_channel(767488243263864842).send('spam'*10)

    @commands.command()
    async def qrcode(self, ctx: commands.Context, *, data: str):
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_H,
            box_size=10,
            border=4,
        )
        qr.add_data(data)
        qr.make(fit=True)

        img = qr.make_image(fill_color="black", back_color="white")
        img.save('code.png')

        await ctx.send(file=discord.File('code.png'))

        os.remove("code.png")

    @commands.command()
    async def roast(self, ctx: commands.Context):
        """Generates a random roast, from https://parade.com/1105374/marynliles/good-comebacks/"""
        with open('roasts.txt') as f:
            await ctx.send(random.choice(f.readlines()))

    @commands.command()
    async def cbt(self, ctx: commands.Context):
        """Prints the whole CBT article on Wikipedia."""
        text = requests.get(
            'https://en.wikipedia.org/wiki/Cock_and_ball_torture')
        soup = BeautifulSoup(text.content, 'html.parser')

        for chunk in [soup.text[i:i+2000] for i in range(0, len(soup.text), 2000)]:
            await ctx.send(chunk)


class Currency(commands.Cog):
    @commands.command()
    async def top(self, ctx: commands.Context):
        '''Shows the top people on the leaderboard.'''
        leaderboard = await Seco.get_leaderboard('balance')
        send_text = ""
        for person in leaderboard:
            userid = person['userid']
            balance = person['balance']
            place = leaderboard.index(person) + 1
            send_text += f'#{place}: {bot.get_user(userid).display_name}: {balance}{currency_unit}\n'
        await ctx.send(embed=discord.Embed(title=f"Top users in {ctx.author.guild.name}", description=send_text, color=discord.Colour.red()))

    @commands.command()
    async def register(self, ctx: commands.Context):
        '''Registers you into the PyraBot currency system.'''
        await Seco.user_check(ctx.author.id)
        await ctx.send(f'Registered! Use {prefix}help to learn more.')

    @commands.command(aliases=['balance'])
    async def bal(self, ctx: commands.Context):
        '''Shows your current balance.'''
        await Seco.user_check(ctx.author.id)
        balance = await Seco.get_balance(ctx.author.id)
        await ctx.send(f'Your balance is {str(balance)}{currency_unit}.')

    @commands.command()
    async def give(self, ctx: commands.Context, member: discord.Member, amount: int):
        await Seco.transfer_balance(from_userid=ctx.author.id, to_userid=member.id, amount=amount)
        await ctx.send(f'Added {amount} to {member.display_name}\'s balance')


async def background_task():
    await bot.wait_until_ready()
    while not bot.is_closed():
        try:
            console_input = await aioconsole.ainput("shell> ")
            args = console_input.split(' ')
            if args[0] == 'exec':
                exec(args[1])
            elif args[0] == 'say':
                await discord.utils.get(bot.get_guild(int(args[1])).text_channels, name=args[2]).send(' '.join(args[3:]))
            else:
                print('Command not found')
        except Exception as e:
            print(e)

bot.loop.create_task(background_task())
bot.add_cog(Music(bot))
bot.add_cog(General(bot))
bot.add_cog(Currency(bot))
bot.load_extension("jishaku")

bot.run(token)
