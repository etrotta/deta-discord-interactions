class INTEGRATION_TYPE:
    GUILD_INSTALL = 0  # App is installable to servers
    USER_INSTALL = 1  # App is installable to users

class CONTEXT_TYPE:
    GUILD = 0  # Interaction can be used within servers
    BOT_DM = 1  # Interaction can be used within DMs with the app's bot user
    PRIVATE_CHANNEL = 2  # Interaction can be used within Group DMs and DMs other than the app's bot user
