import discord
from discord.ext import commands
import logging
from bot import Sparky
from cogs.fun.fun import Fun
from helpers import Emojis
logger = logging.getLogger(__name__)

class TestView(discord.ui.View):
    def __init__(self, ctx: commands.Context):
        super().__init__(timeout=20.0)
        self.ctx = ctx

    @discord.ui.button(label="Execute Action", style=discord.ButtonStyle.green)
    async def execute_action_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        await self.execute_action()

    async def execute_action(self):
        # Common logic that will be executed by both the command and the button click
        await self.ctx.send(f"Testing the command!")

class Test(commands.Cog):
    """Test cog"""
    
    def __init__(self, bot: Sparky):
        try:
            self.bot: Sparky = bot
            logger.info(f"{self.qualified_name} initialized successfully!")
        except Exception as e:
            logger.error(f"Failed to initialize {self.qualified_name}: {e}")

    @commands.command(
        name="testview",
        aliases=["tv"],
        usage="Syntax: testview\nExample: testview"
    )
    async def test_view(self, ctx: commands.Context):
        """Test view command"""
        view = TestView(ctx=ctx)
        embed = discord.Embed(
            title="Test view",
            description="Click the button to execute the action!",
            color=discord.Color.green()
        )
        await ctx.send(embed, view=view)

    @commands.command(
        name="test",
        aliases=["t"],
        usage="Syntax: test\nExample: test"
    )
    async def test(self, ctx: commands.Context):
        """Test command"""
        view = TestView(ctx=ctx)
        await view.execute_action()

    @commands.command(name="readembed", aliases=["re"], usage="Syntax: readembed")
    @commands.is_owner()
    async def read_embed(self, ctx: commands.Context):
        """Read embed command"""
        # get message reference and its embeds
        if ctx.message.reference is not None:
            original_message = ctx.message.reference.cached_message
            if original_message is None:
                original_message_id = ctx.message.reference.message_id
                original_message = await ctx.channel.fetch_message(original_message_id)
            embeds = original_message.embeds
            if len(embeds) == 0:
                await ctx.send("No embeds found in the referenced message.")
                return
            for embed in embeds:
                # steal emojis from the embed fields
                for field in embed.fields:
                    if field.value:
                        message_content = field.value
                        fun_cog: Fun = self.bot.get_cog("Fun")
                        await fun_cog.steal_emojis(ctx, message_content)
        else:
            await ctx.send("Please reply to a message with embeds.")

    @commands.command(name="scanembed", aliases=["se"], usage="Syntax: scanembed")
    @commands.is_owner()
    async def scan_embed(self, ctx: commands.Context):
        """Scan embed command"""
        # get message reference and its embeds
        if ctx.message.reference is not None:
            original_message = ctx.message.reference.cached_message
            if original_message is None:
                original_message_id = ctx.message.reference.message_id
                original_message = await ctx.channel.fetch_message(original_message_id)
            embeds = original_message.embeds
            if len(embeds) == 0:
                await ctx.send("No embeds found in the referenced message.")
                return
            for embed in embeds:
                # list all embed elements
                embed_elements = []
                try:
                    embed_elements.append(f"Title: {embed.title}")
                    embed_elements.append(f"Description: {embed.description}")
                    embed_elements.append(f"URL: {embed.url}")
                    embed_elements.append(f"Type: {embed.type}")
                    embed_elements.append(f"Color: {embed.color}")
                    embed_elements.append(f"Image: {embed.image}")
                    embed_elements.append(f"Thumbnail: {embed.thumbnail}")
                    embed_elements.append(f"Fields: {embed.fields}")
                    embed_elements.append(f"Author Icon URL: {embed.author.icon_url}")
                    embed_elements.append(f"Image URL: {embed.image.url}")
                    embed_elements.append(f"Thumbnail URL: {embed.thumbnail.url}")
                    embed_elements.append(f"Author Name: {embed.author.name}")
                    embed_elements.append(f"Fields: {embed.fields}")
                    # send the embed elements as a message
                    embed_elements_message = "\n".join(embed_elements)
                    # send the embed elements as a text document
                    with open("embed_elements.txt", "w") as file:
                        file.write(embed_elements_message)
                    with open("embed_elements.txt", "rb") as file:
                        await ctx.send(file=discord.File(file, "embed_elements.txt"))
                except Exception as e:
                    logger.error(f"Failed to scan embed: {e}")
        else:
            await ctx.send("Please reply to a message with embeds.")

    @commands.command(name='purgeemojis', aliases=['pe'], usage='Syntax: purgeemojis')
    @commands.is_owner()
    async def purge_emojis(self, ctx: commands.Context):
        """Purge emojis command"""
        guild = ctx.guild
        emojis = guild.emojis
        for emoji in emojis:
            if emoji.guild.id == guild.id:
                await emoji.delete()
        await ctx.send("All emojis have been purged!")

    @commands.command(name='unicode', aliases=['uni'], usage='Syntax: unicode <unicode>')
    @commands.is_owner()
    async def unicode(self, ctx: commands.Context, unicode: str):
        """Unicode command"""
        emoji = Emojis().get_emoji(unicode)
        await ctx.send(f"{emoji}")
