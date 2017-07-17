# -*- coding: utf-8 -*-
import asyncio
import copy
import inspect
import random
import string
import time

import discord
from discord.ext import commands
from prettytable import PrettyTable

from cogs.utils import comm, commons, prefs
from cogs.utils.commons import _
from cogs.utils.prefs import JSONloadFromDisk
from .utils import checks


class Admin:
    """Admin-only commands that make the bot dynamic."""

    def __init__(self, bot):
        self.bot = bot

    @commands.command(hidden=True)
    @checks.is_owner()
    async def load(self, ctx, *, module: str):
        """Loads a module."""
        try:
            self.bot.load_extension(module)
        except Exception as e:
            await ctx.send('\N{PISTOL}')
            await ctx.send('{}: {}'.format(type(e).__name__, e))
        else:
            await ctx.send('\N{OK HAND SIGN}')

    @commands.command(hidden=True)
    @checks.is_owner()
    async def unload(self, ctx, *, module: str):
        """Unloads a module."""
        try:
            self.bot.unload_extension(module)
        except Exception as e:
            await ctx.send('\N{PISTOL}')
            await ctx.send('{}: {}'.format(type(e).__name__, e))
        else:
            await ctx.send('\N{OK HAND SIGN}')

    @commands.command(name='reload_cog', hidden=True)
    @checks.is_owner()
    async def _reload(self, ctx, *, module: str):
        """Reloads a module."""
        try:
            self.bot.unload_extension(module)
            self.bot.load_extension(module)
        except Exception as e:
            await ctx.send('\N{PISTOL}')
            await ctx.send('{}: {}'.format(type(e).__name__, e))
        else:
            await ctx.send('\N{OK HAND SIGN}')

    @commands.command(pass_context=True, hidden=True)
    @checks.is_owner()
    async def debug(self, ctx, *, code: str):
        """Evaluates code."""
        code = code.strip('` ')
        python = '```py\n{}\n```'
        result = None

        env = {
            'bot'    : self.bot,
            'ctx'    : ctx,
            'message': ctx.message,
            'server' : ctx.message.guild,
            'channel': ctx.message.channel,
            'author' : ctx.message.author
        }

        env.update(globals())

        try:
            result = eval(code, env)
            if inspect.isawaitable(result):
                result = await result
        except Exception as e:
            await ctx.message.channel.send(python.format(type(e).__name__ + ': ' + str(e)))
            return

        await comm.message_user(ctx.message, python.format(result))

    @commands.command(pass_context=True, hidden=True)
    @checks.is_owner()
    async def do(self, ctx, times: int, *, command):
        """Repeats a command a specified number of times."""
        msg = copy.copy(ctx.message)
        msg.content = command
        for i in range(times):
            await self.bot.process_commands(msg)

    @commands.command(pass_context=True)
    @checks.is_owner()
    async def dbtable(self, ctx):
        if not prefs.getPref(ctx.message.guild, "global_scores"):
            await comm.message_user(ctx.message, str(ctx.message.guild.id) + "-" + str(ctx.message.channel.id))
        else:
            await comm.message_user(ctx.message, str(ctx.message.guild.id))

    @commands.command(pass_context=True)
    @checks.is_owner()
    async def serverlist(self, ctx, passed_prefs: str = "", maxservs: int = None):
        language = prefs.getPref(ctx.message.guild, "language")

        x = PrettyTable()
        args_ = passed_prefs.split(" ")
        x._set_field_names([_("Name", language), _("Invitation", language), _("Server ID", language), _("Number of enabled channels", language), _("Number of connected users", language), _("Ducks per day", language), _("Number of unneeded permissions", language), _("Number of needed permissions", language)])
        x.reversesort = True

        tmp = await ctx.message.channel.send(str(ctx.message.author.mention) + _(" > En cours", language))
        servers = JSONloadFromDisk("channels.json")


        i = 0
        lu = 0

        slist = sorted(list(self.bot.guilds), key=lambda s: int(s.member_count), reverse=True)[:maxservs]
        total = len(slist)

        for server in list(slist):
            i += 1
            if time.time() - lu >= 5 or i == total:
                lu = time.time()
                try:
                    await tmp.edit(content=str(ctx.message.author.mention) + _(" > Processing servers ({done}/{total})", language).format(**{
                        "done" : i,
                        "total": total
                    }))
                except:
                    pass
            invite = None

            permissionsToHave = ["change_nicknames", "connect", "create_instant_invite", "embed_links", "manage_messages", "mention_everyone", "read_messages", "send_messages", "send_tts_messages"]

            permEnMoins = 0
            permEnPlus = 0
            channel = server.default_channel
            for permission, value in channel.permissions_for(server.me):
                if not value and permission in permissionsToHave:
                    permEnMoins += 1
                elif value and not permission in permissionsToHave:
                    permEnPlus += 1

            if "invitations" in args_:
                for channel in server.channels:
                    permissions = channel.permissions_for(server.me)
                    if permissions.create_instant_invite:
                        try:
                            invite = await channel.create_invite(max_age=120 * 60)
                            invite = invite.url
                        except:
                            invite = ""
                    else:
                        invite = ""
            try:
                channels = str(len(servers[server.id]["channels"]))
            except KeyError:  # Pas de channels ou une autre merde dans le genre ?
                channels = "0"

            x.add_row([server.name, invite, str(server.id), channels + "/" + str(len(server.channels)), server.member_count, prefs.getPref(server, "ducks_per_day"), permEnPlus, permEnMoins])

        await comm.message_user(ctx.message, "```\n" + x.get_string(sortby=_("Number of connected users", language)) + "\n```")

    @commands.command(pass_context=True)
    @checks.is_owner()
    async def cleanup_servers(self, ctx):
        language = prefs.getPref(ctx.message.guild, "language")

        await comm.message_user(ctx.message, _("Serching for servers to leave", language))
        to_clean = []
        total_members_lost = 0
        servers = JSONloadFromDisk("channels.json")

        for server in list(self.bot.guilds):

            try:
                if len(servers[server.id]["channels"]) == 0:
                    to_clean.append(server)
                    total_members_lost += server.member_count

            except KeyError:  # Pas de channels ou une autre merde dans le genre ?
                to_clean.append(server)
                total_members_lost += server.member_count

        def id_generator(size=6, chars=string.ascii_uppercase + string.digits):
            return ''.join(random.choice(chars) for _ in range(size))

        random_str = id_generator()

        await comm.message_user(ctx.message, _("Cleaning {servers} unused servers (accounting for {members} members in total)", language).format(servers=len(to_clean), members=total_members_lost))
        await comm.message_user(ctx.message, _("To confirm, please type {random_str} now.", language).format(random_str=random_str))

        def is_good_message(m):
            return m.author == ctx.message.author and m.content == random_str

        try:
            guess = await self.bot.wait_for('message', check=is_good_message, timeout=10)
        except asyncio.TimeoutError:
            guess = None

        if guess is None:
            await comm.message_user(ctx.message, _(":x: Operation canceled, you took too long to answer.", language).format(random_str=random_str))

        else:
            failed = 0
            for server in to_clean:
                try:
                    await server.send(":warning: I'll now leave the server, as you have not configured me... Join https://discord.gg/2BksEkV the duckhunt server for help about the setup and actions you have to take to bring me back, or check https://api-d.com for more help.")
                except:
                    failed += 1
                    pass
                try:
                    await server.leave()  # Good Bye :'(
                except:
                    commons.logger.exception("")

            await comm.message_user(ctx.message, _(":ok: Finished, failed for {failed} servers.", language).format(failed=failed))

            # await self.bot.leave_server(server)

    @commands.command(pass_context=True)
    @checks.is_owner()
    async def broadcast(self, ctx, *, bc: str):
        """!broadcast [message]"""
        language = prefs.getPref(ctx.message.guild, "language")
        await comm.message_user(ctx.message, _("Starting the broadcast", language))
        await comm.logwithinfos_ctx(ctx, "Broadcast started")
        for channel in list(commons.ducks_planned.keys()):
            try:
                await channel.send(bc)
            except:
                await comm.logwithinfos_ctx(ctx, "Error broadcasting to " + str(channel.name))
                pass
        await comm.logwithinfos_ctx(ctx, "Broadcast ended")
        await comm.message_user(ctx.message, _("Broadcast finished", language))

    @commands.command(pass_context=True)
    @checks.is_owner()
    async def send_message(self, ctx, server_name: str, channel_name: str, *, message: str):
        language = prefs.getPref(ctx.message.guild, "language")

        await discord.utils.find(lambda m: m.name == channel_name, discord.utils.find(lambda m: m.name == server_name or str(m.id) == str(server_name), self.bot.guilds).channels).send(message)
        await comm.message_user(ctx.message, _("Message ({message}) sent to {server} #{channel} ", language).format(message=message, server=server_name, channel=channel_name))

    @commands.command(pass_context=True)
    @checks.is_owner()
    async def say(self, ctx, *, message: str):

        await ctx.message.channel.send(message)

    @commands.command(pass_context=True)
    @checks.is_owner()
    async def bug(self, ctx):

        raise RuntimeError("May the gods be upon you!")


def setup(bot):
    bot.add_cog(Admin(bot))
