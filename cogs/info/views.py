from discord.ext.menus import ListPageSource, PageSource
from discord import (
	Embed, Member, Role, Color
)

from helpers import Context, SparkyPages

class MembersPageSource(ListPageSource):
	def __init__(self, entries: list[Member], role: Role):
		super().__init__(entries=entries, per_page=10)
		self.title: str = f'Members in {role.name}'
		self.description: str = f''

	async def format_page(self, menu: SparkyPages, members: list[Member]):
		embed = Embed(title=self.title, colour=Color(0xFFFFFF))
		member_entries = ''
		for member in members:
			member_entry = f"`{menu.current_page*10 + members.index(member) + 1}` **{member}**"
			member_entries += member_entry + "\n"

		embed.description = member_entries
		author = menu.ctx.author
		embed.set_author(name=author.display_name, icon_url=author.display_avatar.url)

		maximum = self.get_max_pages()

		if maximum > 1:
			embed.set_footer(text=f'Page {menu.current_page + 1}/{maximum} ({len(self.entries)} members)')
		return embed

class MemberMenu(SparkyPages):
	def __init__(self, source: PageSource, ctx: Context):
		super().__init__(source, ctx=ctx, compact='compact')
  