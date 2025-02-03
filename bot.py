import interactions
import openai

token = ''

server_ids = []

llm_settings = {
    "url": "",
    "api_key": ""
}

"""
user data structure

{
    "<user_id>": {
        "api": {
            "url": "<api url>",
            "api_key": "<api key>",
            "models": [<list of models in string>]
        }
    }
}
"""

user_data = {}

bot = interactions.Client(intents=interactions.Intents.DEFAULT)

@interactions.listen()
async def on_ready():
    print("Niko's ready to serve!")
    
@interactions.slash_command(name="about", description="About Niko", scopes=server_ids)
async def about_command(ctx: interactions.SlashContext):
    embed = interactions.Embed(title="Hello :hugging:", description="Niko is an experimental bot for interacting with LLMs over OpenAI-compatible APIs directly on Discord!\n\n**It is not designed for serious or otherwise professional use.**\n\nThe bot is written in Python using the [interactions.py](https://github.com/interactions-py/interactions.py) library, the [official OpenAI](https://github.com/openai/openai-python) library, and parts of the [ayalib](https://github.com/FishiaT/ayalib) library.")
    await ctx.send(embed=embed, ephemeral=True)
    
@interactions.slash_command(name="connect", description="Connect to an LLM", scopes=server_ids)
@interactions.slash_option(
    name="url",
    description="URL of the API",
    required=True,
    opt_type=interactions.OptionType.STRING
)
@interactions.slash_option(
    name="api_key",
    description="API key of the API (optional)",
    required=False,
    opt_type=interactions.OptionType.STRING
)
async def connect_command(ctx: interactions.SlashContext, url: str, api_key: str = "NO_API_KEY"):
    await ctx.defer(ephemeral=True)
    client = openai.Client(base_url=url, api_key=api_key)
    models = client.models.list().to_dict()
    if "data" in models.keys() and len(models['data']) > 0:
        user_data[ctx.user.id] = {}
        user_data[ctx.user.id]['api'] = llm_settings.copy()
        user_data[ctx.user.id]['api']['url'] = url
        user_data[ctx.user.id]['api']['api_key'] = api_key
        user_data[ctx.user.id]['api']['models'] = []
        for model in models['data']:
            user_data[ctx.user.id]['api']['models'].append(model['id'])
        embed_description = f"""Connected to `{url}` successfully!
        
        Found {len(user_data[ctx.user.id]['api']['models'])} model(s) available for inference:
        """
        for model in user_data[ctx.user.id]['api']['models']:
            embed_description += f"\n• {model}"
        embed = interactions.Embed(title="Success :white_check_mark:", description=embed_description)
        await ctx.send(embed=embed)
    else:
        embed = interactions.Embed(title="Failed :x:", description=f"Unable to connect to `{url}`.\n\nPlease check the URL or the API key to see if they are correct or not. Try appending `/v1` to the API url if you are sure that the URL used is the correct one.")
        await ctx.send(embed=embed)
    client.close()    
        
bot.start(token)