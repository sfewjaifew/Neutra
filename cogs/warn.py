import discord

from discord.ext import commands

from core import OWNERS
from utilities import permissions, picker



def setup(bot):
    bot.add_cog(Warnings(bot))

class Warnings(commands.Cog):
    """
    Manage the server's warning system.
    """

    def __init__(self, bot):
        self.bot = bot
        self.cxn = bot.connection

      ###################
     ## WARN COMMANDS ##
    ###################

    @commands.command()
    @commands.guild_only()
    @permissions.has_permissions(kick_members=True)
    async def warn(self, ctx, targets: commands.Greedy[discord.Member], *, reason: str = None):
        if not len(targets): return await ctx.send(f"Usage: `{ctx.prefix}warn <target> [target]... [reason]`")
        warned = []
        for target in targets:
            if target.id in OWNERS: return await ctx.send('You cannot warn my master.')
            if target.id == ctx.author.id: return await ctx.send('I don\'t think you really want to warn yourself...')
            if target.id == self.bot.user.id: return await ctx.send('I don\'t think I want to warn myself...')
            if target.guild_permissions.manage_messages and ctx.author.id not in OWNERS: return await ctx.send('You cannot punish other staff members.')
            if ctx.guild.me.top_role.position > target.top_role.position and not target.guild_permissions.administrator:
                try:
                    warnings = await self.cxn.fetchrow("SELECT warnings FROM warn WHERE id = $1 AND server_id = $2", target.id, ctx.guild.id) or (None)
                    if warnings is None: 
                        warnings = 0
                        await self.cxn.execute("INSERT INTO warn VALUES ($1, $2, $3)", target.id, ctx.guild.id, int(warnings) + 1)
                        warned.append(f"{target.name}#{target.discriminator}")
                    else:
                        warnings = int(warnings[0])
                        try:
                            await self.cxn.execute("UPDATE warn SET warnings = warnings + 1 WHERE server_id = $1 AND id = $2", ctx.guild.id, target.id)
                            warned.append(f"{target.name}#{target.discriminator}")
                        except Exception: raise

                except Exception as e: return await ctx.send(e)
                if reason:
                    try:
                        await target.send(f"<:announce:807097933916405760> You have been warned in **{ctx.guild.name}** `{reason}`.")
                    except: return
            else: return await ctx.send('<:fail:816521503554273320> `{0}` could not be warned.'.format(target))
        if warned:
            await ctx.send(f'<:checkmark:816534984676081705> Warned `{", ".join(warned)}`')


    @commands.command()
    @commands.guild_only()
    async def listwarns(self, ctx, *, target: discord.Member =None):
        if target is None:
            target = ctx.author

        try:
            warnings = await self.cxn.fetchrow("SELECT warnings FROM warn WHERE id = $1 AND server_id = $2", target.id, ctx.guild.id) or None
            if warnings is None: return await ctx.send(f"<:checkmark:816534984676081705> User `{target}` has no warnings.")
            warnings = int(warnings[0])
            await ctx.send(f"<:announce:807097933916405760> User `{target}` currently has **{warnings}** warning{'' if int(warnings) == 1 else 's'} in this server.")
        except Exception as e: return await ctx.send(e)


    @commands.command(aliases = ['deletewarnings','removewarns','removewarnings','deletewarns','clearwarnings'])
    @commands.guild_only()
    @permissions.has_permissions(kick_members = True)
    async def clearwarns(self, ctx, *, target: discord.Member = None):
        if target is None: return await ctx.send(f"Usage: `{ctx.prefix}deletewarn <target>`")
        try:
            warnings = await self.cxn.fetchrow("SELECT warnings FROM warn WHERE id = $1 AND server_id = $2", target.id, ctx.guild.id) or None
            if warnings is None: return await ctx.send(f"<:checkmark:816534984676081705> User `{target}` has no warnings.")
            warnings = int(warnings[0])
            await self.cxn.execute("DELETE FROM warn WHERE id = $1 and server_id = $2", target.id, ctx.guild.id)
            await ctx.send(f"<:checkmark:816534984676081705> Cleared all warnings for `{target}` in this server.")
            try:
                await target.send(f"<:announce:807097933916405760> All your warnings have been cleared in **{ctx.guild.name}**.")
            except: return
        except Exception as e: return await ctx.send(e)


    @commands.command(aliases=['revokewarning','undowarning','undowarn'])
    @commands.guild_only()
    @permissions.has_permissions(kick_members = True)
    async def revokewarn(self, ctx, *, target: discord.Member = None):
        if target is None: return await ctx.send(f"Usage: `{ctx.prefix}revokewarn <target>`")
        try:
            warnings = await self.cxn.fetchrow("SELECT warnings FROM warn WHERE id = $1 AND server_id = $2", target.id, ctx.guild.id) or None
            if warnings is None: return await ctx.send(f"<:checkmark:816534984676081705> User `{target}` has no warnings to revoke.")
            warnings = int(warnings[0])
            if int(warnings) == 1: 
                await self.cxn.execute("DELETE FROM warn WHERE id = $1 and server_id = $2", target.id, ctx.guild.id)
                await ctx.send(f"<:checkmark:816534984676081705> Cleared all warnings for `{target}` in this server.")
            else:
                await self.cxn.execute("UPDATE warn SET warnings = warnings - 1 WHERE server_id = $1 AND id = $2", ctx.guild.id, target.id)
                await ctx.send(f"<:checkmark:816534984676081705> Revoked a warning for `{target}` in this server.")
            try:
                await target.send(f"<:announce:807097933916405760> You last warning has been revoked in **{ctx.guild.name}**.")
            except: return
        except Exception as e: return await ctx.send(e)


    @commands.command(brief="Display the server warnlist.", aliases=["warns"])
    @commands.guild_only()
    @permissions.has_permissions(manage_messages=True)
    async def serverwarns(self, ctx):
        """
        Usage: -serverwarns
        Alias: -warns
        Output: Embed of all warned members in the server
        Permission: Manage Messages
        """
        query = '''SELECT COUNT(*) FROM warn'''
        count = await self.cxn.fetchrow(query)
        query = '''SELECT id, warnings FROM warn ORDER BY warnings DESC'''
        records = await self.cxn.fetch(query)

        warn_list = []
        for i in records:
            warn_list.append(
                {
                    "name": str(ctx.guild.get_member(i[0])),
                    "value":"{}".format(i[1]),
                }
            )
        return await picker.PagePicker(title="{} Warn List ({:,} total)".format(ctx.guild.name, int(count[0])),
        ctx=ctx, list=[{"name":"{}. {}".format(y+1,x["name"]), 
        "value":"Warnings: " + x["value"]} for y, x in enumerate(warn_list)]).pick()