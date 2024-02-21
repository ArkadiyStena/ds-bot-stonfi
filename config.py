import dotenv
import os

dotenv.load_dotenv('./.env')

BOT_TOKEN = os.environ["BOT_TOKEN"]
COMMAND_PREFIX = "/"

ROLE_IDS = {
    "Wallet Connect": 1209568880905814026,
    "DEX user": 1110615192838090853
}

GUILD_ID = 974592621706117120

MIN_TRADED_VOLUME = 100
PTON_ADDRESS = "EQCM3B12QK1e4yZSf8GtBRT0aLMNyEsBc_DhVfRRtOEffLez"
TONCONNECT_MANIFEST_URL = "https://app.ston.fi/tonconnect-manifest.json"

COOLDOWN_TIME = 3