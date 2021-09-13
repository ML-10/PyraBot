from replit import db
import asyncio
import functools
import itertools
import math
import os
import random
import typing
import json
import base64
import requests
import time
import aiohttp
from decimal import Decimal

import psutil
import discord
import qrcode
import youtube_dl
from async_timeout import timeout
from bs4 import BeautifulSoup
from discord.ext import commands, wizards, tasks
from googletrans import LANGCODES, Translator
from pretty_help import PrettyHelp
from keepalive import keepalive
from PIL import Image
import PIL.ImageFont as IFont
import PIL.ImageDraw as IDraw
from owotext import OwO
from lyricsgenius import Genius
from dislash import slash_commands
import emoji
import unicodedata

genius = Genius()

translator = Translator()


intents = discord.Intents.all()

token = os.getenv('BOT_TOKEN')
prefix = 'p '
bot = commands.Bot(prefix,
                   help_command=PrettyHelp(color=discord.Colour.red()),
                   intents=intents)

slash = slash_commands.SlashClient(bot)

drip = Image.open('drip.jpg')

uwu = OwO()



# string defs
empty = 'Empty queue.'
no = 'Nothing being played at the moment.'
dm = 'This command can\'t be used in DM channels.'
error = 'An error occurred: {}'
noaccount = 'You do not have an account! Run {}register to register.'

currency_unit = '₱'

youtube_dl.utils.bug_reports_message = lambda: ''

# checks

@bot.check
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

with open('filter.txt') as f:
    messagefilter = f.read().split(', ')
    messagefilter[-1] = messagefilter[-1][:7]

bot.counter = int(db['counter'])
try:
    lastcounted = db['lastcounted']
except IndexError:
    lastcounted = 0

@bot.event
async def on_message(message: discord.Message):
    if not message.guild:
        await bot.process_commands(message)
    if message.author == bot.user:
        return

    global lastcounted
    try:
        if message.channel.id == 843250290249695233 and str(int(eval(message.content))) == str(bot.counter):
            if message.author.id != lastcounted:
                await message.add_reaction('✅')
                bot.counter += 1
                lastcounted = message.author.id
                db['counter'] = str(bot.counter)
                db['lastcounted'] = str(lastcounted)
                await message.channel.edit(topic=f'Counting with PyraBot! Current number: {bot.counter}')
            else:
                await message.reply(f'you can\'t count two numbers in a row! the next number is {bot.counter}')
    except:
        pass
    message_content = message.content.strip().lower()
    if message.guild.id in [82739460435345345979324]:
        for bad_word in messagefilter:
            if bad_word in message_content:
                await message.channel.send(
                    "{}, your message has been censored.".format(
                        message.author.mention))
                await message.delete()

    await bot.process_commands(message)

snipe_message_author = {}
snipe_message_content = {}

@bot.event
async def on_message_delete(message: discord.Message):
    snipe_message_author[message.channel.id] = f"**{message.author}** [{message.author.display_name}]"
    snipe_message_content[message.channel.id] = message.content
    await asyncio.sleep(3600)
    del snipe_message_author[message.channel.id]
    del snipe_message_content[message.channel.id]


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
        'before_options':
        '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
        'options': '-vn',
    }

    ytdl = youtube_dl.YoutubeDL(YTDL_OPTIONS)
    ytdl.cache.remove()

    def __init__(self,
                 ctx: commands.Context,
                 source: discord.FFmpegPCMAudio,
                 *,
                 data: dict,
                 volume: float = 0.5):
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
    async def create_source(cls,
                            ctx: commands.Context,
                            search: str,
                            *,
                            loop: asyncio.BaseEventLoop = None):
        loop = loop or asyncio.get_event_loop()

        partial = functools.partial(cls.ytdl.extract_info,
                                    search,
                                    download=False,
                                    process=False)
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
        partial = functools.partial(cls.ytdl.extract_info,
                                    webpage_url,
                                    download=False)
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
                        'Couldn\'t retrieve any matches for `{}`'.format(
                            webpage_url))

        return cls(ctx,
                   discord.FFmpegPCMAudio(info['url'], **cls.FFMPEG_OPTIONS),
                   data=info)

    @classmethod
    async def search_source(self,
                            ctx: commands.Context,
                            search: str,
                            *,
                            loop: asyncio.BaseEventLoop = None,
                            bot):
        self.bot = bot
        channel = ctx.channel
        loop = loop or asyncio.get_event_loop()

        self.search_query = '%s%s:%s' % ('ytsearch', 10, ''.join(search))

        partial = functools.partial(self.ytdl.extract_info,
                                    self.search_query,
                                    download=False,
                                    process=False)
        info = await loop.run_in_executor(None, partial)

        self.search = {}
        self.search["title"] = f'Search results for:\n**{search}**'
        self.search["type"] = 'rich'
        self.search["color"] = 7506394
        self.search["author"] = {
            'name': f'{ctx.author.name}',
            'url': f'{ctx.author.avatar_url}',
            'icon_url': f'{ctx.author.avatar_url}'
        }

        lst = []
        count = 0
        e_list = []
        for e in info['entries']:
            # lst.append(f'`{info["entries"].index(e) + 1}.` {e.get("title")} **[{YTDLSource.parse_duration(int(e.get("duration")))}]**\n')
            VId = e.get('id')
            VUrl = 'https://www.youtube.com/watch?v=%s' % (VId)
            lst.append(f'`{count + 1}.` [{e.get("title")}]({VUrl})\n')
            count += 1
            e_list.append(e)

        lst.append(
            '\n**Type a number to make a choice, Type `cancel` to exit**')
        self.search["description"] = "\n".join(lst)

        em = discord.Embed.from_dict(self.search)
        await ctx.send(embed=em, delete_after=45.0)

        def check(msg):
            return msg.content.isdigit(
            ) == True and msg.channel == channel or msg.content == 'cancel' or msg.content == 'Cancel'

        try:
            m = await self.bot.wait_for('message', check=check, timeout=45.0)

        except asyncio.TimeoutError:
            rtrn = 'timeout'

        else:
            if m.content.isdigit() == True:
                sel = int(m.content)
                if 0 < sel <= 10:
                    for key, value in info.items():
                        if key == 'entries':
                            """data = value[sel - 1]"""
                            VId = e_list[sel - 1]['id']
                            VUrl = 'https://www.youtube.com/watch?v=%s' % (VId)
                            partial = functools.partial(self.ytdl.extract_info,
                                                        VUrl,
                                                        download=False)
                            data = await loop.run_in_executor(None, partial)
                    rtrn = self(ctx,
                                discord.FFmpegPCMAudio(data['url'],
                                                       **self.FFMPEG_OPTIONS),
                                data=data)
                else:
                    rtrn = 'sel_invalid'
            elif m.content == 'cancel':
                rtrn = 'cancel'
            else:
                rtrn = 'sel_invalid'

        return rtrn

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
        embed = (discord.Embed(
            title='Now playing',
            description='```css\n{0.source.title}\n```'.format(self),
            colour=discord.Colour.red()).add_field(
                name='Duration', value=self.source.duration).add_field(
                    name='Requested by',
                    value=self.requester.mention).add_field(
                        name='Uploader',
                        value='[{0.source.uploader}]({0.source.uploader_url})'.
                        format(self)).add_field(
                            name='URL',
                            value='[Click]({0.source.url})'.format(self)).
                 set_thumbnail(url=self.source.thumbnail))

        return embed


class SongQueue(asyncio.Queue):
    def __getitem__(self, item):
        if isinstance(item, slice):
            return list(
                itertools.islice(self._queue, item.start, item.stop,
                                 item.step))
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

        self.exists = True

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
            self.now = None

            if self.loop == False:
                # Try to get the next song within 3 minutes.
                # If no song will be added to the queue in time,
                # the player will disconnect due to performance
                # reasons.
                try:
                    async with timeout(180):  # 3 minutes
                        self.current = await self.songs.get()
                except asyncio.TimeoutError:
                    self.bot.loop.create_task(self.stop())
                    self.exists = False
                    self.voice.leave()
                    return

                self.current.source.volume = self._volume
                self.voice.play(self.current.source, after=self.play_next_song)
                await self.current.source.channel.send(
                    embed=self.current.create_embed())

            #If the song is looped
            elif self.loop == True:
                self.now = discord.FFmpegPCMAudio(
                    self.current.source.stream_url,
                    **YTDLSource.FFMPEG_OPTIONS)
                self.voice.play(self.now, after=self.play_next_song)

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

class EmbedBuilderWizard(wizards.Wizard):
    def __init__(self):
        self.result = {}
        super().__init__(cleanup_after=False, timeout=30.0)

    # register an action, so users can type "stop" or "cancel" to stop
    # the wizard
    @wizards.action("stop", "cancel")
    async def cancel_wizard(self, message):
        await self.send("Wizard Cancelled.")
        await self.stop(wizards.StopReason.CANCELLED)

    @wizards.step(
        "What should the embed title be?",
        position=1
    )
    async def embed_title(self, message):
        self.result["title"] = message.content

    @wizards.step(
        "What should the embed description be?",
        timeout=180.0,  # override the default timeout of 30
        position=2,
    )
    async def embed_description(self, message):
        length = len(message.content)
        if length > 2000:
            await self.send(
                f"That description is {length} chars, but the maximum is 2000."
            )
            return await self.do_step(self.embed_description)  # redo the step
        self.result["description"] = message.content

    @wizards.step(
        "Type 1 to add a field, or 2 to move on.",
        position=3,
    )
    async def embed_fields(self, message):
        self.result.setdefault("fields", [])
        if message.content == "2":
            pass  # move on to the next step
        elif message.content == "1":
            field_name = await self.do_step(self.embed_field_name)
            field_value = await self.do_step(self.embed_field_value)
            field_inline = await self.do_step(self.embed_field_inline)
            self.result["fields"].append(
                (field_name, field_value, field_inline)
            )

            # repeat the step, so users can add multiple fields
            return await self.do_step(self.embed_fields)
        else:
            await self.send("Please choose 1 or 2.")
            return await self.do_step(self.embed_fields)

    @wizards.step(
        "What should the field name be?",
        call_internally=False,
    )
    async def embed_field_name(self, message):
        return message.content

    @wizards.step(
        "What should the field description be?",
        call_internally=False,
    )
    async def embed_field_value(self, message):
        return message.content

    @wizards.step(
        "Should the field be inline?",
        call_internally=False,
    )
    async def embed_field_inline(self, message):
        if message.content.lower().startswith("y"):
            return True
        elif message.content.lower().startswith("n"):
            return False
        else:
            await self.send("Please choose yes or no.")
            return await self.do_step(self.embed_field_inline)


class Music(commands.Cog):
    """A category for commands related to playing music."""
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.voice_states = {}

    def get_voice_state(self, ctx: commands.Context):
        state = self.voice_states.get(ctx.guild.id)
        if not state or not state.exists:
            state = VoiceState(self.bot, ctx)
            self.voice_states[ctx.guild.id] = state

        return state

    def cog_unload(self):
        for state in self.voice_states.values():
            self.bot.loop.create_task(state.stop())

    async def cog_before_invoke(self, ctx: commands.Context):
        ctx.voice_state = self.get_voice_state(ctx)

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
    async def _summon(self,
                      ctx: commands.Context,
                      *,
                      channel: discord.VoiceChannel = None):
        """Summons the bot to a voice channel.
        If no channel was specified, it joins your channel.
        """

        if not channel and not ctx.author.voice:
            raise VoiceError(
                'You are neither connected to a voice channel nor specified a channel to join.'
            )

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
        ctx.voice_state.current.source.volume = volume / 100
        await ctx.send('Volume of the player set to {}%'.format(volume))

    @commands.command(name='now', aliases=['current'])
    async def _now(self, ctx: commands.Context):
        """Displays the currently playing song."""

        await ctx.send(embed=ctx.voice_state.current.create_embed())

    @commands.command(name='pause')
    @commands.has_permissions(manage_guild=True)
    async def _pause(self, ctx: commands.Context):
        """Pauses the currently playing song."""
        if ctx.voice_state.voice.is_playing():
            ctx.voice_state.voice.pause()
            await ctx.message.add_reaction('⏯')

    @commands.command(name='resume')
    @commands.has_permissions(manage_guild=True)
    async def _resume(self, ctx: commands.Context):
        """Resumes a currently paused song."""

        if ctx.voice_state.voice.is_paused():
            ctx.voice_state.voice.resume()
            await ctx.message.add_reaction('⏯')

    @commands.command(name='stop')
    @commands.has_permissions(manage_guild=True)
    async def _stop(self, ctx: commands.Context):
        """Stops playing song and clears the queue."""

        ctx.voice_state.songs.clear()

        if ctx.voice_state.is_playing:
            ctx.voice_state.loop = False
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
            ctx.voice_state.loop = False
            await ctx.message.add_reaction('⏭')
            ctx.voice_state.skip()

        elif voter.id not in ctx.voice_state.skip_votes:
            ctx.voice_state.skip_votes.add(voter.id)
            total_votes = len(ctx.voice_state.skip_votes)

            if total_votes >= 3:
                await ctx.message.add_reaction('⏭')
                ctx.voice_state.skip()
            else:
                await ctx.send('Skip vote added, currently at **{}/3**'.format(
                    total_votes))

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
        for i, song in enumerate(ctx.voice_state.songs[start:end],
                                 start=start):
            queue += '`{0}.` [**{1.source.title}**]({1.source.url})\n'.format(
                i + 1, song)

        embed = (discord.Embed(description='**{} tracks:**\n\n{}'.format(
            len(ctx.voice_state.songs), queue)).set_footer(
                text='Viewing page {}/{}'.format(page, pages)))
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
        await ctx.send(f'Loop is now {ctx.voice_state.loop} for current song.')

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

        await ctx.send('Loading song...')

        async with ctx.typing():
            try:
                source = await YTDLSource.create_source(ctx,
                                                        search,
                                                        loop=self.bot.loop)
            except YTDLError as e:
                await ctx.send(
                    'An error occurred while processing this request: {}'.
                    format(str(e)))
            else:
                song = Song(source)

                await ctx.voice_state.songs.put(song)
                await ctx.send('Enqueued {}'.format(str(source)))

    @commands.command(name='search')
    async def _search(self, ctx: commands.Context, *, search: str):
        """Searches Youtube.
        It returns an embed of the first 10 results collected from Youtube.
        Then the user can choose one of the titles by typing a number in chat or they can cancel by typing "cancel" in chat.
        Each title in the list can be clicked as a link.
        """
        async with ctx.typing():
            try:
                source = await YTDLSource.search_source(ctx,
                                                        search,
                                                        loop=self.bot.loop,
                                                        bot=self.bot)
            except YTDLError as e:
                await ctx.send(
                    'An error occurred while processing this request: {}'.
                    format(str(e)))
            else:
                if source == 'sel_invalid':
                    await ctx.send('Invalid selection')
                elif source == 'cancel':
                    await ctx.send(':white_check_mark:')
                elif source == 'timeout':
                    await ctx.send(':alarm_clock: **Timed out**')
                else:
                    if not ctx.voice_state.voice:
                        await ctx.invoke(self._join)

                    song = Song(source)
                    await ctx.voice_state.songs.put(song)
                    await ctx.send('Enqueued {}'.format(str(source)))

    @commands.command()
    async def lyrics(self, ctx: commands.Context, *, query: str):
        '''Searches Genius for lyrics.'''
        lyrics = genius.search_song(title=query).lyrics
        for chunk in [lyrics[i:i + 2000] for i in range(0, len(lyrics), 2000)]:
            await ctx.send(embed=discord.Embed(
                title=query, description=chunk, colour=discord.Colour.red()))

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
        self.guild_count.start()

    @commands.Cog.listener()
    async def on_command_error(self, ctx: commands.Context, error):
        if isinstance(error, commands.CommandOnCooldown):
            await ctx.message.reply(f'That command is on cooldown for {error.retry_after:.2f}s!')
            return

        base64_error = base64.b64encode(str(error).encode('ascii')).decode('ascii')
        await ctx.message.reply(f'There was an error running that command!\n`{str(error)}`\nError code: `{base64_error}`')

    def cog_unload(self):
        self.guild_count.cancel()

    @commands.command()
    async def hello(self, ctx: commands.Context, *args):
        '''Say hello.'''
        await ctx.message.reply(
            'Hello {0.author.mention}! Did you know that @circles.png is my creator?'
            .format(ctx.message))
        
    @commands.command(aliases=['tr', 'trans'])
    async def translate(self, ctx: commands.Context, source: str,
                        destination: str, *, text: str):
        """Translates text to another language."""
        try:
            await ctx.send(embed=discord.Embed(
                title=f'Translated from {source} to {destination}', 
                description=translator.translate(text,
                                     dest=LANGCODES[destination.lower()],
                                     src=LANGCODES[source.lower()]).text,
                footer='powered by Google Translate',
                colour=discord.Colour.red()
                ))
               
        except KeyError as k:
            await ctx.send(f'Language not found: ({k})')

    @commands.command(aliases=['th', 'transhelp', 'thelp'])
    async def translatehelp(self, ctx: commands.context):
        "Returns all languages availiable to translate."

        await ctx.send(str(LANGCODES.keys()))

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
    async def playing(self, ctx: commands.Context, *, game):
        "Changes bot's playing status."
        await bot.change_presence(activity=discord.Game(name=game))
        await ctx.message.add_reaction('✅')

    @commands.is_owner()
    @commands.command()
    async def streaming(self, ctx: commands.Context, *, stream):
        "Changes bot's streaming status."
        await bot.change_presence(
            activity=discord.Streaming(name=stream, url=""))
        await ctx.message.add_reaction('✅')

    @commands.is_owner()
    @commands.command()
    async def listening(self, ctx: commands.Context, *, song):
        "Changes bot's listening status."
        await bot.change_presence(activity=discord.Activity(
            type=discord.ActivityType.listening, name=song))
        await ctx.message.add_reaction('✅')

    @commands.is_owner()
    @commands.command()
    async def watching(self, ctx: commands.Context, *, movie):
        "Changes bot's watching status."
        await bot.change_presence(activity=discord.Activity(
            type=discord.ActivityType.watching, name=movie))
        await ctx.message.add_reaction('✅')

    @commands.command()
    @commands.check(checkforavraaj)
    async def warn(self,
                   ctx,
                   member: discord.Member,
                   reason: typing.Optional[str] = 'breaking the rules'):
        'Warns a member with an optional reason.'
        await member.send(member.mention +
                          ' YOU HAVE BEEN WARNED FROM guild "' +
                          member.guild.name + '" FOR ' + reason)

    @commands.command()
    async def ping(self, ctx: commands.Context):
        "Returns the bot's latency in milliseconds."
        await ctx.message.reply(f'Pong! {round(bot.latency * 1000, abs(Decimal(bot.latency * 1000).adjusted())+1)}ms')

    @slash.command(
        name="ping",
        description="Returns the bot's latency in milliseconds.",
    )
    async def _ping(self, inter):
        "Returns the bot's latency in milliseconds."
        await inter.reply('Pong! {0}ms'.format(round(bot.latency, 5) * 1000))

    @commands.command(aliases=['vote'])
    async def poll(self, ctx: commands.Context, *, inp: str):
        "Starts a poll with emojis and a topic."
        inp = list(inp)
        emojis = ''
        for i, char in enumerate(inp):
            if char in emoji.UNICODE_EMOJI['en']:
                emojis += char
                inp.pop(i)

        statement = ''.join(inp).strip()

        embed = discord.Embed(
            title="Vote! [" + statement + "]",
            description=statement,
            colour=discord.Colour.red()
        )
        embed.set_author(name=ctx.author.display_name, icon_url=ctx.author.avatar_url)
        message = await ctx.send(embed=embed)
        for r in emoji.emojize(emojis).replace(' ', '').strip():
            try:
                await message.add_reaction(r)
            except discord.HTTPException:
                await ctx.send(f'Emoji not found: {unicodedata.name(r)} (\\u{hex(ord(r))})')

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

        for chunk in list(element[i:i + 2000]
                          for i in range(0, len(element), 2000)):
            await ctx.send(chunk)

    @commands.command()
    async def qrcode(self, ctx: commands.Context, *, data: str):
        "Generates a QR code given some data."
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
        """Generates a random roast."""
        with open('roasts.txt') as f:
            await ctx.send(random.choice(f.readlines()))

    @commands.command()
    async def drip(self, ctx: commands.Context):
        '''Makes an image of you with drip.'''
        await ctx.author.avatar_url.save('avatar.png')
        avatar = Image.open('avatar.png')
        avatar = avatar.resize((150, 150))
        drip.paste(avatar, box=(180, 50))
        drip.save('result.png')
        await ctx.send(file=discord.File('result.png'))

    @commands.command(aliases=['owo', 'uwu', 'uwuify'])
    async def owoify(self, ctx: commands.Context, *, text: str):
        '''OwOifies text.'''
        await ctx.send(
            embed=discord.Embed(
                title='uwu',
                description=uwu.whatsthis(text),
                colour=discord.Colour.red(),
                footer='powered by owotext'
            ).set_author(name=ctx.author.display_name, icon_url=ctx.author.avatar_url)
        )

    @commands.command()
    async def b(self, ctx: commands.Context, *, text: str):
        ''':b:ifies your text.'''
        t = text.strip().split(' ')
        for i, word in enumerate(t):
            word = list(word)
            word[0] = ':b:'
            t[i] = ''.join(word)

        await ctx.send(embed=discord.Embed(
            title=':b:', description=' '.join(t), colour=discord.Colour.red()))

    @slash.command(
        name="dice",
        description="Rolls a dice with a given number of sides.",
    )
    async def dice(self, ctx: commands.Context, number: int):
        "Rolls a dice with a given number of sides."
        await ctx.send(f'Rolled dice with {number} sides: **{random.randint(1, number)}**')

    @commands.command()
    async def invite(self, ctx: commands.Context):
        "Generates a link to invite the bot to your own server!"
        await ctx.send(embed=discord.Embed(title='Invite link!', description='https://discord.com/api/oauth2/authorize?client_id=575622700001918976&permissions=8&scope=bot%20applications.commands'))

    @commands.command(aliases=['cb', 'chat'])
    async def chatbot(self, ctx: commands.Context):
        "Talk to an AI!"

        url = "http://api.brainshop.ai/get"
        headers = {'x-rapidapi-host': 'acobot-brainshop-ai-v1.p.rapidapi.com'}

        def check(message):
            return message.channel == ctx.message.channel and message.author == ctx.author

        await ctx.message.reply('Hi! Talk about anything, or say \'quit\' to quit.')

        text = ''
        while text != 'quit':
            query = await bot.wait_for('message', check=check)
            text = query.content.strip()
            querystring = {"bid":"157380","key": os.getenv('BRAINSHOP_KEY'), "uid":str(ctx.author.display_name), "msg": text}
            response = requests.request("GET", url, headers=headers, params=querystring) 
            await query.reply(json.loads(response.text)['cnt'])

        await ctx.message.reply('Anyways, bye!')

    @commands.command(aliases=['createembed', 'emb'])
    async def embed(self, ctx: commands.Context):
        "Build an embed using a wizard."
        wizard = EmbedBuilderWizard()
        await wizard.start(ctx)
        result = wizard.result

        embed = discord.Embed(
            title=result["title"],
            description=result["description"],
        )
        for name, value, inline in result["fields"]:
            embed.add_field(name=name, value=value, inline=inline)

        await ctx.send(embed=embed)

    @commands.command(aliases=['corona', 'coronavirus', 'covid19'])
    async def covid(self, ctx: commands.Context, country: str):
        'COVID-19 stats for a given country.'
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"https://corona.lmao.ninja/v2/countries/{country}") as resp:
                    data = await resp.json()
        except Exception:
            return None

        tme = round(time.time())
        tme -= data['updated']
        hrs = int(tme / 3600)
        tme = tme % 3600
        min = int(tme / 60)
        tme = tme % 60
        hrs = max(hrs, 0)
        min = max(min, 0)
        update = f"Updated {hrs} hours {min} minutes and {tme} seconds ago"
        embed = discord.Embed(colour=discord.Colour.red())
        embed.set_author(name=f"Data for the country {country}", icon_url=data['countryInfo']['flag'])
        embed.set_thumbnail(url=data['countryInfo']['flag'])
        embed.add_field(name="Total Cases", value=f"{data['cases']} (+{data['todayCases']})", inline=False)
        embed.add_field(name="Total Deaths", value=f"{data['deaths']} (+{data['todayDeaths']})", inline=False)
        embed.add_field(name="Total Recoveries", value=f"{data['recovered']}", inline=False)
        embed.add_field(name="Active", value=str(data['active']), inline=True)
        embed.add_field(name="Critical", value=str(data['critical']), inline=True)
        embed.add_field(name="Tests Conducted", value=str(data['tests']), inline=True)
        embed.set_footer(text=update)

        await ctx.send(embed=embed)

    @commands.command()
    async def snipe(self, ctx: commands.Context):
        "Shows the last deleted message in the last 1 hour."
        channel = ctx.channel
        try:
            emb = discord.Embed(
                title = snipe_message_author[channel.id],
                description = snipe_message_content[channel.id],
                colour = discord.Colour.red()
            )
            emb.set_author(name=ctx.author.display_name, icon_url=ctx.author.avatar_url)
            await ctx.send(embed=emb)
        except:
            await ctx.send(f"No deleted messages in the last 1 hour in **#{channel.name}**!")

    @commands.command()
    async def stats(self, ctx: commands.Context):
        "psutil stats for PyraBot."
        embed = discord.Embed(
            title = 'Stats for PyraBot',
            description = '\n',
            colour = discord.Colour.red()
        )

        embed.set_author(name=ctx.author.display_name, icon_url=ctx.author.avatar_url)
        embed.add_field(name='CPU', value=psutil.cpu_percent(interval=1), inline=True)
        embed.add_field(name='Memory', value=f'{round(psutil.virtual_memory().available / (1024 ** 3), 2)} of {round(psutil.virtual_memory().total / (1024 ** 3), 2)}GB ({100 - psutil.virtual_memory().percent}%)', inline=True)
        embed.add_field(name='Servers', value=len(bot.guilds), inline=True)
        embed.add_field(name='Latency', value=f'{round(bot.latency * 1000, abs(Decimal(bot.latency * 1000).adjusted())+1)}ms', inline=True)
        embed.set_footer(text='Updated now')
        await ctx.send(embed=embed)

    @commands.command()
    async def meme(self, ctx: commands.Context, top: str, bottom: str):
        "Creates a meme with top text, bottom text, and an image."
        await ctx.message.attachments[0].save('meme.png')
                
        with Image.open('meme.png') as img:
            size = img.size
            fontSize = int(size[1] / 5)
            font = IFont.truetype("impact.ttf", fontSize)

            edit = IDraw.Draw(img)

            # find biggest font size that works

            topTextSize = font.getsize(top)
            bottomTextSize = font.getsize(bottom)
            while topTextSize[0] > size[0] - 20 or bottomTextSize[0] > size[0] - 20:
                fontSize = fontSize - 1
                font = IFont.truetype("impact.ttf", fontSize)
                topTextSize = font.getsize(top)
                bottomTextSize = font.getsize(bottom)

            # find top centered position for top text
            topTextPositionX = (size[0] / 2) - (topTextSize[0] / 2)
            topTextPositionY = 0
            topTextPosition = (topTextPositionX, topTextPositionY)

            # find bottom centered position for bottom text
            bottomTextPositionX = (size[0] / 2) - (bottomTextSize[0] / 2)
            bottomTextPositionY = size[1] - bottomTextSize[1] - 10
            bottomTextPosition = (bottomTextPositionX, bottomTextPositionY)

            # draw outlines
            # there may be a better way
            outlineRange = int(fontSize / 15)
            for x in range(-outlineRange, outlineRange + 1):
                for y in range(-outlineRange, outlineRange + 1):
                    edit.text((topTextPosition[0] + x,
                    topTextPosition[1] + y), top, (0, 0, 0), font=font)
                    edit.text((bottomTextPosition[0] + x,
                    bottomTextPosition[1] + y), bottom, (0, 0, 0), font=font)

            edit.text(topTextPosition, top, (255, 255, 255), font=font)
            edit.text(bottomTextPosition, bottom, (255, 255, 255), font=font)
            img.save('meme.png')

        await ctx.message.reply(file=discord.File('meme.png'))
            
    @commands.command()
    async def ban(self, ctx: commands.Context):
        await ctx.author.ban(reason='pingspoofing')

    @commands.command()
    async def kick(self, ctx: commands.Context):
        await ctx.author.ban(reason='pingspoofing')

    @commands.command()
    async def unban(self, ctx: commands.Context):
        await ctx.author.ban(reason='pingspoofing')

    @tasks.loop(hours=2.0)
    async def guild_count(self):
        await bot.change_presence(activity=discord.Activity(
            type=discord.ActivityType.watching, name=f'p help in {len(bot.guilds)} servers'))

    @guild_count.before_loop
    async def before_guild_count(self):
        print('Waiting for bot to ready...')
        await self.bot.wait_until_ready()

bot.add_cog(Music(bot))
bot.add_cog(General(bot))
bot.load_extension("jishaku")
bot.load_extension("cogs.tictactoe")
bot.load_extension("cogs.battleships")

keepalive()
bot.run(token)
