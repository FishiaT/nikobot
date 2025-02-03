# nikobot - MIT licensed
# for entertainment purposes (mostly)
# code is not organized at all
# no attempts have been made on making this more maintainable
# the developer is a dumbass
# work with it at your risk

import interactions
import openai

token = ''

bot_id = 0

server_ids = []

llm_settings = {
    "url": "",
    "api_key": ""
}

"""
user data structure
for reference purposes mostly

{
    "<user_id>": {
        "client": <openai client object>,
        "api": {
            "url": "<api url>",
            "api_key": "<api key>",
            "models": [<list of models in string>]
        },
        "chat": {
            "session_id": "<thread id>",
            "selected_model": "<id of choosen model>",
            "history": [
                {
                    "role": "<user | assistant>",
                    "contents": {
                        "text": "<message>",
                        "images": [
                            "<base64 encoded image>
                        ]
                    },
                    "message_id": "<origin message id>"
                }
            ]
        }
    }
}
"""

user_data = {}

bot = interactions.Client(intents=interactions.Intents.ALL)

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
        user_data[ctx.user.id]['chat'] = {}
        for model in models['data']:
            user_data[ctx.user.id]['api']['models'].append(model['id'])
        embed_description = f"""Connected to `{url}` successfully!
        
        Found {len(user_data[ctx.user.id]['api']['models'])} model(s) available for inference:
        """
        for model in user_data[ctx.user.id]['api']['models']:
            embed_description += f"\n• {model}"
        user_data[ctx.user.id]['client'] = openai.AsyncOpenAI(base_url=url, api_key=api_key)
        embed = interactions.Embed(title="Success :white_check_mark:", description=embed_description)
        await ctx.send(embed=embed)
    else:
        embed = interactions.Embed(title="Failed :x:", description=f"Unable to connect to `{url}`.\n\nPlease check the URL or the API key to see if they are correct or not. Try appending `/v1` to the API url if you are sure that the URL used is the correct one.")
        await ctx.send(embed=embed)
    client.close()
    
@interactions.slash_command(name="chat", description="Initiate a new chat session", scopes=server_ids)
async def chat_command(ctx: interactions.SlashContext):
    if not ctx.user.id in user_data.keys() or not user_data[ctx.user.id]['api']['url']:
        embed = interactions.Embed(description=":x: You have not yet connected to an LLM API. In order to start a chat session, please connect to an API by using the `/connect` command.")
        await ctx.send(embed=embed, ephemeral=True)
        return
    model_select = interactions.StringSelectMenu(user_data[ctx.user.id]['api']['models'], placeholder="Pick a model")
    message = await ctx.send(embed=interactions.Embed(description="Please choose a model to use."), components=model_select, ephemeral=True)
    result: interactions.api.events.Component = await bot.wait_for_component(messages=message, components=model_select)
    user_data[ctx.user.id]['chat']['selected_model'] = result.ctx.values[0]
    thread = await ctx.channel.create_private_thread(name=f"{ctx.user.display_name} ({ctx.user.id})'s Chat Session")
    embed = interactions.Embed(description=f"Chat session initiated, you may now start interacting with the choosen LLM model by sending messages in this thread.\n\n• Thread ID: {thread.id}\n• Selected Model: {user_data[ctx.user.id]['chat']['selected_model']}")
    user_data[ctx.user.id]['chat']['session_id'] = thread.id
    user_data[ctx.user.id]['chat']['history'] = []
    await thread.add_member(ctx.user)
    await thread.send(embed=embed)
    await message.delete(context=ctx)
    await ctx.send(embed=interactions.Embed(description=f":white_check_mark: Created a new thread ({thread.id})!"), ephemeral=True)
    
@interactions.listen(interactions.api.events.MessageCreate)
async def chat_session_handler(ctx: interactions.api.events.MessageCreate):
    if hasattr(ctx.message.channel, "owner_id") and ctx.message.channel.owner_id == bot_id:
        if ctx.message.author.id != bot_id:
            message_data = {
                "role": "user",
                "contents": {
                    "text": ctx.message.content
                },
                "message_id": ctx.message.id
            }
            if len(ctx.message.attachments) > 0:
                # TODO: add handler for attachments
                print("not implemented (attachments)")
            user_data[ctx.message.author.id]['chat']['history'].append(message_data)
            client: openai.AsyncOpenAI = user_data[ctx.message.author.id]['client']
            messages = []
            for message in user_data[ctx.message.author.id]['chat']['history']:
                data = {
                    "role": message['role'],
                    "content": ""
                }
                data['content'] = message['contents']['text']
                messages.append(data)
            chat_completion = await client.chat.completions.create(
                messages=messages,
                model=user_data[ctx.message.author.id]['chat']['selected_model'],
                stream=True
            )
            response: interactions.Message = await ctx.message.channel.send("Please wait...")
            final_response = ""
            async for chunk in chat_completion:
                final_response += chunk.choices[0].delta.content or ""
                await response.edit(content=final_response)
            message_data = {
                "role": "assistant",
                "contents": {
                    "text": final_response
                },
                "message_id": response.id
            }
            user_data[ctx.message.author.id]['chat']['history'].append(message_data)
        
bot.start(token)