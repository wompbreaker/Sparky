from discord.app_commands import CheckFailure, check
from aiomysql import DictCursor
from discord import Interaction

class AntinukeFailure(CheckFailure):
    pass

class NotGuildOwner(CheckFailure):
    pass

def check_antinuke_admin():
    """Check if the user is an antinuke admin"""
    async def predicate(interaction: Interaction):
        if interaction.user == interaction.guild.owner:
            return True
        async with interaction.client.pool.acquire() as conn:
            async with conn.cursor(DictCursor) as cur:
                await cur.execute(
                    "SELECT * FROM antinuke_system WHERE guild_id = %s;",
                    (interaction.guild.id,)
                )
                result = await cur.fetchone()
        if not result:
            raise AntinukeFailure("This server does not have an antinuke system enabled.")
        if str(interaction.user.id) in result['admins']:
            return True
        raise AntinukeFailure("You are not an antinuke admin.")
    
    return check(predicate)

def check_guild_owner():
    """Check if the user is the guild owner"""
    def predicate(interaction: Interaction) -> bool:
        if interaction.user == interaction.guild.owner:
            return True
        raise NotGuildOwner("You are not the guild owner.")
    
    return check(predicate)
        