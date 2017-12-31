# -*- coding: utf-8 -*-
import discord.utils
from discord.ext import commands

from cogs.utils import comm, commons, prefs, scores
from cogs.utils.commons import _


def is_owner_check(message):
    owner = message.author.id in ['138751484517941259', '94822638991454208', '270061265156702208']
    # bot.loop.create_task(comm.logwithinfos_message(message, "Check owner: " + str(owner)))
    return owner  # Owner of the bot


def is_banned_check(message):
    banned = not scores.getStat(message.channel, message.author, "banned", default=False)
    # bot.loop.create_task(comm.logwithinfos_message(message, "Check not banned: " + str(banned)))
    return banned  # Inverse d'un banissement


def is_admin_check(message):
    servers = prefs.JSONloadFromDisk("channels.json")

    try:
        admin = message.author.id in servers[message.server.id]["admins"]
    except KeyError:
        admin = False
    # bot.loop.create_task(comm.logwithinfos_message(message, "Check admin: " + str(admin)))

    return admin  # Dans la liste des admins d'un serveur (fichier json)


def is_player_check(member, channel=None):
    if isinstance(member, discord.Member):
        try:
            member = scores.getChannelPlayers(channel, columns=['shoots_fired'], match_id=member.id)[0]
        except IndexError:
            return False

    return member.get('shoots_fired', 0) or 0


def is_activated_check(channel):
    servers = prefs.JSONloadFromDisk("channels.json")

    try:
        if channel.id in servers[channel.server.id]["channels"]:
            activated = True
        else:
            activated = False
    except KeyError:
        activated = False

    # bot.loop.create_task(comm.logwithinfos_message(message, "Check activated here: " + str(activated)))
    return activated


def have_exp_check(message, exp):
    return scores.getStat(message.channel, message.author, "exp") >= exp


def have_exp(exp, warn=True):
    def check(ctx, exp, warn):
        exp_ = have_exp_check(ctx.message, exp)
        if not exp_ and warn:
            commons.bot.loop.create_task(comm.message_user(ctx.message, _(":x: You can't use this command, you need at least {exp} exp points!", prefs.getPref(ctx.message.server, "language")).format(**{
                "exp": exp
            })))
        return exp_

    exp_ = commands.check(lambda ctx: check(ctx, exp, warn))
    return exp_


def is_owner(warn=True):
    def check(ctx, warn):
        owner = is_owner_check(ctx.message)
        if not owner and warn:
            commons.bot.loop.create_task(comm.message_user(ctx.message, _(":x: You can't use this command, you're not the bot owner!", prefs.getPref(ctx.message.server, "language"))))
        return owner

    owner = commands.check(lambda ctx: check(ctx, warn))
    return owner


def is_not_banned():
    return commands.check(lambda ctx: is_banned_check(ctx.message) or is_admin_check(ctx.message) or is_owner_check(ctx.message))


def is_admin(warn=True):
    def check(ctx, warn):
        admin = is_owner_check(ctx.message) or is_admin_check(ctx.message)
        if not admin and warn:
            commons.bot.loop.create_task(comm.message_user(ctx.message, _(":x: You can't use this command, you're not an admin on this server!", prefs.getPref(ctx.message.server, "language"))))
        return admin

    admin = commands.check(lambda ctx: check(ctx, warn))
    return admin


def is_activated_here():
    return commands.check(lambda ctx: is_activated_check(ctx.message.channel))


def check_permissions(ctx, perms):
    msg = ctx.message
    if is_owner_check(msg):
        return True

    ch = msg.channel
    author = msg.author
    resolved = ch.permissions_for(author)
    return all(getattr(resolved, name, None) == value for name, value in perms.items())


def role_or_permissions(ctx, check, **perms):
    if check_permissions(ctx, perms):
        return True

    ch = ctx.message.channel
    author = ctx.message.author
    if ch.is_private:
        return False  # can't have roles in PMs

    role = discord.utils.find(check, author.roles)
    return role is not None


def admin_or_permissions(**perms):
    def predicate(ctx):
        return role_or_permissions(ctx, lambda r: r.name == 'Bot Admin', **perms)

    return commands.check(predicate)


def is_in_servers(*server_ids):
    def predicate(ctx):
        server = ctx.message.server
        if server is None:
            return False
        return server.id in server_ids

    return commands.check(predicate)
