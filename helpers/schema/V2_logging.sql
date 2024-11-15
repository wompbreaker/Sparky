CREATE TABLE IF NOT EXISTS logging (
	guild_id BIGINT PRIMARY KEY,
	channels JSON NOT NULL DEFAULT '{"messages": [], "members": [], "roles": [], "channels": [], "invites": [], "emojis": [], "voice": []}' CHECK (json_valid(channels)),
	ignored_channels JSON NOT NULL DEFAULT '[]' CHECK (json_valid(ignored_channels)),
	ignored_members JSON NOT NULL DEFAULT '[]' CHECK (json_valid(ignored_members))
);