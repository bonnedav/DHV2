# -*- coding: utf-8 -*-
import asyncio
import datetime
import locale
import logging
import os
import random
import sys
import time
import traceback
from collections import Counter

import discord
from discord.ext import commands

from cogs.utils import commons

if os.geteuid() == 0:
    print("DON'T RUN DUCKHUNT AS ROOT! It creates an unnecessary security risk.")
    sys.exit(1)

try:
    locale.setlocale(locale.LC_ALL, 'fr_FR')
except locale.Error:
    pass

commons.init()

from cogs.utils.commons import _, credentials

description = """DuckHunt, a game about killing ducks"""

initial_extensions = ['cogs.admin', 'cogs.carbonitex', 'cogs.exp', 'cogs.meta', 'cogs.serveradmin', 'cogs.shoot']

discord_logger = logging.getLogger('discord')
discord_logger.setLevel(logging.CRITICAL)

log = logging.getLogger()
log.setLevel(logging.INFO)
handler = logging.FileHandler(filename='dh.log', encoding='utf-8', mode='w')
log.addHandler(handler)
logger = commons.logger

help_attrs = dict(hidden=True, in_help=True, name="DONOTUSE")

MINUTE = 60
HOUR = MINUTE * 60
DAY = HOUR * 24

def prefix(bot, message):
    p = prefs.getPref(message.server, "prefix")
    return ["DuckHunt", "duckhunt", "dh!", "dh"] + [p]


bot = commands.Bot(command_prefix=prefix, description=description, pm_help=None, help_attrs=help_attrs)
commons.bot = bot


@bot.event
async def on_command_error(error, ctx):
    language = prefs.getPref(ctx.message.server, "language")
    if isinstance(error, commands.NoPrivateMessage):
        await bot.send_message(ctx.message.author, _(':x: This command cannot be used in private messages.', language))
    elif isinstance(error, commands.DisabledCommand):
        await bot.send_message(ctx.message.author, _(':x: Sorry. This command is disabled and cannot be used.', language))
    elif isinstance(error, commands.CommandInvokeError):
        print('In {0.command.qualified_name}:'.format(ctx), file=sys.stderr)
        traceback.print_tb(error.original.__traceback__)
        print('{0.__class__.__name__}: {0}'.format(error.original), file=sys.stderr)

        myperms = ctx.message.channel.permissions_for(ctx.message.server.me)
        can_send = myperms.add_reactions and myperms.create_instant_invite
        if can_send:
            error_report = _("Send an error report?", language)
        else:
            error_report = _("Sadly, I need the `add_reactions` and `create_instant_invite` permissions to be able to send an error report.", language)

        msg = await comm.message_user(ctx.message, _(":x: An error (`{error}`) happened while executing `{command}`, here is the traceback: ```\n{tb}\n```\n{error_report}", language).format(**{
            "command"     : ctx.command.qualified_name,
            "error"       : error.original.__class__.__name__,
            "tb"          : "\n".join(traceback.format_tb(error.original.__traceback__, 4)),
            "error_report": error_report
        }))

        if can_send:
            yes = "\N{THUMBS UP SIGN}"
            no = "\N{THUMBS DOWN SIGN}"
            await bot.add_reaction(msg, yes)
            await bot.add_reaction(msg, no)
            res = await bot.wait_for_reaction(emoji=[yes, no], user=ctx.message.author, message=msg, timeout=120)
            if res:
                reaction, user = res
                emoji = reaction.emoji
                if emoji == yes:

                    msg = await comm.message_user(ctx.message, _(":anger_right: Creating an invite for the error report...", language))
                    support_channel = discord.utils.find(lambda c: str(c.id) == '273930986314792960', discord.utils.find(lambda s: str(s.id) == '195260081036591104', bot.servers).channels)
                    invite = await bot.create_invite(ctx.message.channel, max_uses=5)
                    invite = invite.url
                    await bot.edit_message(msg, _(":anger_right: Sending error report...", language))

                    await bot.send_message(support_channel, _(":hammer: {date} :hammer:").format(date=int(time.time())))
                    await bot.send_message(support_channel, await comm.paste(_("{cause}\n\n{tb}").format(cause=error.original.__class__.__name__,
                                                                                                         tb="\n".join(traceback.format_tb(error.original.__traceback__))), "py"))
                    await bot.send_message(support_channel, invite)
                    await bot.edit_message(msg, _(":ok: Error report sent, thanks. :)", language))
                    return
            await comm.message_user(ctx.message, _("OK, I won't send an error report.", language))

    elif isinstance(error, commands.MissingRequiredArgument):
        await comm.message_user(ctx.message, _(":x: Missing a required argument. ", language) + (("Help: \n```\n" + ctx.command.help + "\n```") if ctx.command.help else ""))
    elif isinstance(error, commands.BadArgument):
        await comm.message_user(ctx.message, _(":x: Bad argument provided. ", language) + (("Help: \n```\n" + ctx.command.help + "\n```") if ctx.command.help else ""))
        # elif isinstance(error, commands.CheckFailure):
        # await comm.message_user(ctx.message, _(":x: You are not an admin/owner, you don't have enough exp to use this command, or you are banned from the channel, so you can't use this command. ", language) + (("Help: \n```\n" + ctx.command.help + "\n```") if ctx.command.help else ""))


@bot.event
async def on_ready():
    logger.info('Logged in as:')
    logger.info('Username: ' + bot.user.name)
    logger.info('ID: ' + bot.user.id)
    await bot.change_presence(game=discord.Game(name="Killing ducks | !help"))
    if not hasattr(bot, 'uptime'):
        bot.uptime = datetime.datetime.utcnow()


@bot.event
async def on_resumed():
    logger.info('resumed...')


@bot.event
async def on_command(command, ctx):
    bot.commands_used[command.name] += 1
    await comm.logwithinfos_message(ctx.message, str(command) + " (" + ctx.message.clean_content + ") ")
    if prefs.getPref(ctx.message.server, "delete_commands") and checks.is_activated_check(ctx.message.channel):
        try:
            await bot.delete_message(ctx.message)
        except discord.Forbidden:
            await comm.logwithinfos_ctx(ctx, "Error deleting message: forbidden.")
        except discord.NotFound:
            await comm.logwithinfos_ctx(ctx, "Error deleting message: not found (normal if the purgemessages command was used).")


            # message = ctx.message
            # destination = None
            # if message.channel.is_private:
            #    destination = 'Private Message'
            # else:
            #    destination = '#{0.channel.name} ({0.server.name})'.format(message)
            #
            # log.info('{0.timestamp}: {0.author.name} in {1}: {0.content}'.format(message, destination))


@bot.event
async def on_message(message):
    commons.number_messages += 1

    if message.author.bot:
        return

    if str(message.author.id) in commons.blocked_users:
        return



    # await comm.logwithinfos_message(message, message.content)
    await bot.process_commands(message)


@bot.event
async def on_channel_delete(channel):
    await ducks.del_channel(channel)


@bot.event
async def on_server_remove(server):
    for channel in server.channels:
        await ducks.del_channel(channel)


async def mainloop():
    try:
        await bot.wait_until_ready()
        planday = 0
        last_iter = int(time.time())
        last_hour = 0
        while not bot.is_closed:
            now = int(last_iter + 1)
            thisDay = now - (now % DAY)
            seconds_left = int(DAY - (now - thisDay))
            if int((now - 1) / DAY) != planday:
                # database.giveBack(logger)
                planday = int(int(now - 1) / DAY)
                await planifie()
                last_iter = int(time.time())

            if last_hour < int(int(now / 60) / 60):
                last_hour = int(int(now / 60) / 60)

            if int(now) % 60 == 0:
                logger.debug("Current ducks: {canards}".format(**{
                    "canards": len(commons.ducks_spawned)
                }))
            thishour = int((now % DAY) / HOUR)
            for channel in list(commons.ducks_planned.keys()):
                # Ici, on est au momement ou la logique s'opere:
                # Si les canards ne dorment jamais, faire comme avant, c'est à dire
                # prendre un nombre aléatoire entre 0 et le nombre de secondes restantes avec randrange
                # et le comparer au nombre de canards restants à faire apparaitre dans la journée
                #
                # Par contre, si on est dans un serveur ou les canards peuvent dormir (==)
                # sleeping_ducks_start != sleeping_ducks_stop, alors par exemple :
                # 00:00 |-----==========---------| 23:59 (= quand les canards dorment)
                # dans ce cas, il faut juste modifier la valeur de seconds_left pour enlever le nombre d'heure
                # (en seconde) afin d'augmenter la probabilité qu'un canard apparaisse pendant le reste de la journée
                sdstart = prefs.getPref(channel.server, "sleeping_ducks_start")
                sdstop = prefs.getPref(channel.server, "sleeping_ducks_stop")
                currently_sleeping = False

                if sdstart != sdstop:  # Dans ce cas, les canards dorment peut-etre!

                    # logger.debug("This hour is {v} UTC".format(v=thishour))
                    # Bon, donc comptons le nombre d'heures / de secondes en tout ou les canards dorment
                    if sdstart < sdstop:  # 00:00 |-----==========---------| 23:59
                        if thishour < sdstop:
                            sdseconds = (sdstop - sdstart) * HOUR
                        else:
                            sdseconds = 0
                        if sdstart <= thishour < sdstop:
                            currently_sleeping = True
                    else:  # 00:00 |====--------------======| 23:59
                        sdseconds = (24 - sdstart) * HOUR  # Non, on ne compte pas les autres secondes, car elles seront passées
                        if thishour >= sdstart or thishour < sdstop:
                            currently_sleeping = True
                else:
                    sdseconds = 0

                if not currently_sleeping:
                    sseconds_left = seconds_left - sdseconds  # Don't change seconds_left, it's used for others channels
                    if sseconds_left <= 0:
                        logger.warning("Huh, sseconds_left est à {sseconds_left}... C'est problématique.\nsdstart={sdstart}, sdstop={sdstop}, thishour={thishour}, sdseconds={sdseconds}, seconds_left={seconds_left}".format(sseconds_left=sseconds_left, sdstart=sdstart, sdstop=sdstop, thishour=thishour, sdseconds=sdseconds, seconds_left=seconds_left))
                        sseconds_left = 1


                    try:
                        if random.randrange(0, sseconds_left) < commons.ducks_planned[channel]:
                            commons.ducks_planned[channel] -= 1
                            duck = {
                                "channel": channel,
                                "time"   : now
                            }
                            asyncio.ensure_future(ducks.spawn_duck(duck))
                    except KeyError:  # Race condition
                        # for channel in list(commons.ducks_planned.keys()): <= channel not deleted, so in this list
                        #    if random.randrange(0, seconds_left) < commons.ducks_planned[channel]: <= Channel had been deleted, so keyerror
                        pass

            for canard in commons.ducks_spawned:
                if int(canard["time"]) + int(prefs.getPref(canard["channel"].server, "time_before_ducks_leave")) + commons.bread[canard["channel"]] < int(now):  # Canard qui se barre
                    await comm.logwithinfos(canard["channel"], None, "Duck of {time} stayed for too long. (it's {now}, and it should have stayed until {shouldwaitto}).".format(**{
                        "time"        : canard["time"],
                        "now"         : now,
                        "shouldwaitto": str(int(canard["time"] + prefs.getPref(canard["channel"].server, "time_before_ducks_leave"))) + (" + " + str(commons.bread[canard["channel"]]) if commons.bread[canard["channel"]] != 0 else "")
                    }))
                    try:
                        asyncio.ensure_future(bot.send_message(canard["channel"], _(random.choice(commons.canards_bye), language=prefs.getPref(canard["channel"].server, "language"))))
                    except:
                        pass
                    try:
                        commons.ducks_spawned.remove(canard)
                        commons.n_ducks_flew += 1
                    except:
                        logger.warning("Oops, error when removing duck: " + str(canard))
            now = time.time()

            if last_iter + 1 <= now:
                if last_iter + 1 <= now - 5:
                    logger.warning("Running behing schedule ({s} seconds)... Server overloaded or clock changed?".format(s=str(float(float(last_iter + 1) - int(now)))))
            else:
                await asyncio.sleep(last_iter + 1 - now)

            if last_iter % 60 == 0:
                x = datetime.datetime.now().strftime('%Y-%m-%d %H:%M')
                y = str(float(float(last_iter + 1) - now))
                with open(os.path.dirname(os.path.realpath(sys.argv[0])) + "/csv/" + "latency.csv", "a") as f:
                    f.write("{x},{y}\n".format(x=x, y=y))
                logger.debug("Updating latency analytics")

            last_iter += 1

    except:
        logger.exception("")
        raise


if __name__ == '__main__':
    debug = any('debug' in arg.lower() for arg in sys.argv)
    if debug:
        bot.command_prefix = '$'
        token = credentials.get('debug_token', credentials['token'])
    else:
        token = credentials['token']

    bot.client_id = credentials['client_id']
    bot.commands_used = Counter()
    bot.bots_key = credentials['bots_key']
    bot.discord_bots_org_key = credentials['discord_bots_org_key']

    ## POST INIT IMPORTS ##

    from cogs.utils.ducks import planifie, allCanardsGo
    from cogs.utils.analytics import analytics_loop
    from cogs.utils import prefs, comm
    from cogs.utils import ducks
    from cogs.utils import checks

    for extension in initial_extensions:
        try:
            bot.load_extension(extension)
        except Exception as e:
            logger.exception('Failed to load extension {}\n{}: {}'.format(extension, type(e).__name__, e))
    bot.loop.create_task(mainloop())
    bot.loop.create_task(analytics_loop())

    # noinspection PyBroadException
    try:
        # bot.loop.create_task(api.apcom.kyk.start(port=5566))
        bot.loop.set_debug(True)
        bot.loop.run_until_complete(bot.start(token))
    except KeyboardInterrupt:
        logger.warning("Shutdown in progress")
    except:
        logger.exception("Unknown error, restarting")  # No pls no no no
    finally:
        # noinspection PyBroadException
        try:
            bot.loop.run_until_complete(allCanardsGo())
        except:
            pass
        handlers = log.handlers[:]
        for hdlr in handlers:
            hdlr.close()
            log.removeHandler(hdlr)
        bot.loop.run_until_complete(bot.logout())

    asyncio.sleep(3)
    bot.loop.close()
