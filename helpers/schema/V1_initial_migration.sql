SET time_zone = "+00:00";

CREATE TABLE IF NOT EXISTS afk_statuses (
    user_id BIGINT PRIMARY KEY NOT NULL,
    afk_message TEXT NOT NULL,
    afk_timestamp TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS antinuke_systems (
    guild_id BIGINT PRIMARY KEY NOT NULL,
    admins JSON NOT NULL DEFAULT '[]',
    whitelist JSON NOT NULL DEFAULT '[]',
    botadd TINYINT NOT NULL DEFAULT 0,
    vanity JSON NOT NULL DEFAULT 
    '{
        "enabled": 0,
        "punishment": 3
    }' CHECK (json_valid(vanity)),
    webhook JSON NOT NULL DEFAULT 
    '{
        "enabled": 0, 
        "threshold": 4, 
        "punishment": 3
    }' CHECK (json_valid(webhook)),
    channel JSON NOT NULL DEFAULT 
    '{
        "enabled": 0, 
        "threshold": 4, 
        "punishment": 3
    }' CHECK (json_valid(channel)),
    emoji JSON NOT NULL DEFAULT 
    '{
        "enabled": 0, 
        "threshold": 4, 
        "punishment": 3
    }' CHECK (json_valid(emoji)),
    perms JSON NOT NULL DEFAULT 
    '{
        "enabled": 0, 
        "grant": [], 
        "remove": [], 
        "punishment": 3
    }' CHECK (json_valid(perms)),
    ban JSON NOT NULL DEFAULT 
    '{
        "enabled": 0, 
        "threshold": 4, 
        "punishment": 3
    }' CHECK (json_valid(ban)),
    kick JSON NOT NULL DEFAULT 
    '{
        "enabled": 0, 
        "threshold": 4, 
        "punishment": 3
    }' CHECK (json_valid(kick)),
    role JSON NOT NULL DEFAULT 
    '{
        "enabled": 0, 
        "threshold": 4, 
        "punishment": 3
    }' CHECK (json_valid(role))
);

CREATE TABLE IF NOT EXISTS ban_system (
    guild_id BIGINT PRIMARY KEY NOT NULL,
    default_history TEXT DEFAULT '0d'
);

CREATE TABLE IF NOT EXISTS deleted_messages (
    guild_id BIGINT PRIMARY KEY NOT NULL,
    message_channel_id BIGINT NOT NULL,
    author_id BIGINT NOT NULL,
    message TEXT NOT NULL,
    deleted_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    message_id BIGINT NOT NULL
);

CREATE TABLE IF NOT EXISTS edited_messages (
    guild_id BIGINT PRIMARY KEY NOT NULL,
    message_channel_id BIGINT NOT NULL,
    author_id BIGINT NOT NULL,
    message TEXT NOT NULL,
    edited_at TIMESTAMP NULL DEFAULT CURRENT_TIMESTAMP,
    message_id BIGINT NOT NULL
);

CREATE TABLE IF NOT EXISTS forced_nicknames (
  guild_id BIGINT NOT NULL,
  member_id BIGINT NOT NULL,
  member_nickname TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS guild_prefixes (
    guild_id BIGINT NOT NULL,
    guild_prefix TEXT DEFAULT NULL,
    is_set_prefix TINYINT NOT NULL
);

CREATE TABLE IF NOT EXISTS hardbans (
    guild_id BIGINT NOT NULL,
    hardbanned_users JSON NOT NULL DEFAULT '[]'
);

CREATE TABLE IF NOT EXISTS jailed_user (
    guild_id BIGINT NOT NULL,
    member_id BIGINT NOT NULL,
    is_jailed TINYINT NOT NULL
);

CREATE TABLE IF NOT EXISTS jail_system (
    guild_id BIGINT NOT NULL,
    jailed_id BIGINT NOT NULL,
    jail_channel_id BIGINT NOT NULL,
    is_jailed_setup TINYINT NOT NULL,
    jail_msg TEXT NOT NULL DEFAULT 'you have been jailed'
);

CREATE TABLE IF NOT EXISTS lockdown_system (
    guild_id BIGINT NOT NULL,
    ignored_channels JSON NOT NULL DEFAULT '[]' CHECK (json_valid(ignored_channels)),
    lock_role_id BIGINT DEFAULT NULL
);

CREATE TABLE IF NOT EXISTS muted_users (
    guild_id BIGINT NOT NULL,
    member_id BIGINT NOT NULL,
    is_muted TINYINT NOT NULL,
    is_imuted TINYINT NOT NULL,
    is_rmuted TINYINT NOT NULL
);

CREATE TABLE IF NOT EXISTS mute_system (
    guild_id BIGINT NOT NULL,
    muted_users JSON NOT NULL DEFAULT '[]' CHECK (json_valid(muted_users)),
    imuted_users JSON NOT NULL DEFAULT '[]' CHECK (json_valid(imuted_users)),
    rmuted_users JSON NOT NULL DEFAULT '[]' CHECK (json_valid(rmuted_users)),
    muted_id BIGINT NOT NULL,
    imuted_id BIGINT NOT NULL,
    rmuted_id BIGINT NOT NULL,
    is_muted_setup TINYINT NOT NULL DEFAULT 0,
);

CREATE TABLE IF NOT EXISTS removed_reactions (
    guild_id BIGINT NOT NULL,
    reaction_channel_id BIGINT NOT NULL,
    author_id BIGINT NOT NULL,
    reaction TEXT NOT NULL,
    message_id BIGINT NOT NULL,
    removed_at timestamp NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS silenced_users (
    guild_id BIGINT NOT NULL,
    member_id BIGINT NOT NULL
);

CREATE TABLE IF NOT EXISTS voicemaster_system (
    guild_id BIGINT NOT NULL,
    category_channel_ids JSON DEFAULT '[]',
    interface_channel_id BIGINT DEFAULT NULL,
    voice_channel_id BIGINT DEFAULT NULL,
    is_setup TINYINT NOT NULL,
    default_role_id BIGINT DEFAULT NULL,
    default_name VARCHAR(255) DEFAULT NULL,
    default_region VARCHAR(255) DEFAULT NULL,
    default_bitrate INT(11) DEFAULT NULL,
    custom_channels JSON NOT NULL DEFAULT '[]' CHECK (json_valid(custom_channels))
);