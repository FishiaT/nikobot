# nikobot - MIT licensed
# for entertainment purposes (mostly)
# code is not organized at all
# no attempts have been made on making this more maintainable
# the developer is a dumbass
# work with it at your risk

import interactions
import openai
import httpx
import base64

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
            "<session_id>": {
                "selected_model": "<id of choosen model>",
                "support_vision": true | false,
                "system_prompt": "<optional system prompt>",
                "parameters": {}
                "history": [
                    {
                        "role": "<user | assistant>",
                        "contents": {
                            "text": "<message>",
                            "images": [
                                {
                                    "type": "<content type>",
                                    "data": "<base64 encoded image data>"
                                }
                            ]
                        },
                        "message_id": "<origin message id>"
                    }
                ],
                "indexes": [
                    <message ids>
                ]
            }
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
    await ctx.defer(ephemeral=True)
    if not ctx.user.id in user_data.keys() or not user_data[ctx.user.id]['api']['url']:
        embed = interactions.Embed(description=":x: You have not yet connected to an LLM API. In order to start a chat session, please connect to an API by using the `/connect` command.")
        await ctx.send(embed=embed, ephemeral=True)
        return
    model_select = interactions.StringSelectMenu(user_data[ctx.user.id]['api']['models'], placeholder="Pick a model")
    message = await ctx.send(embed=interactions.Embed(description="Please choose a model to use.\n\nAfter choosing a model, it may take a while before the session is created. A new message will be sent to notify you once that's done."), components=model_select)
    result: interactions.api.events.Component = await bot.wait_for_component(messages=message, components=model_select)
    thread = await ctx.channel.create_private_thread(name=f"{ctx.user.display_name}'s Chat Session")
    user_data[ctx.user.id]['chat'][thread.id] = {}
    user_data[ctx.user.id]['chat'][thread.id]['selected_model'] = result.ctx.values[0]
    user_data[ctx.user.id]['chat'][thread.id]['support_vision'] = True
    user_data[ctx.user.id]['chat'][thread.id]['history'] = []
    user_data[ctx.user.id]['chat'][thread.id]['indexes'] = []
    client: openai.AsyncOpenAI = user_data[ctx.user.id]['client']    
    test_image_data = "iVBORw0KGgoAAAANSUhEUgAAACAAAAAgCAYAAABzenr0AAAAAXNSR0IArs4c6QAAAARnQU1BAACxjwv8YQUAAAAJcEhZcwAAEnQAABJ0Ad5mH3gAAAEHSURBVFhH1ZIBDsMwCAPz/09vYhoVcbEJUddqJ2UNGIKXdrweZmDibsYYw36m9RVOOZbHHC7FoWIhxg7LGysDkS0DTDOUliENsGustA5bBiKoYVwhDTCUOYwrtgwY2XDPd5AG2L9kdGqdXnVBd7jR7xD83MDOFVe0TrvCAH5b5UeIcVanwB6slwayZ7avzGF9ZDIQG7J9rI37zADGLD9VZEOxIdat7NFcjD/r6IAmzEWYjoNQT+MpSJqwYRV2Fp6XGrgCH5YZmNbU9QD/bwCvOaI0R6qn90UOUzrLO1zZgA1ieYMr5AbkYURjeYMrG7BBLG9wpQm7HZZ3uNIgG7Lyygyt3sDjBt5XTrYB+/P3qwAAAABJRU5ErkJggg=="
    try:
        test_request = await client.chat.completions.create(
            model=user_data[ctx.user.id]['chat'][thread.id]['selected_model'],
            messages=[
                {
                   "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": "What's being shown in this image?"
                        },
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/png;base64,{test_image_data}"
                            }
                        }
                    ]
                }
            ]
        )
    except openai.BadRequestError:
        user_data[ctx.user.id]['chat'][thread.id]['support_vision'] = False
    await thread.add_member(ctx.user)
    embed = interactions.Embed(description=f"Chat session initiated, you may now start interacting with the choosen LLM model by sending messages in this thread.\n\n• Thread ID: {thread.id}\n• Selected Model: {user_data[ctx.user.id]['chat'][thread.id]['selected_model']}\n• Support image attachments: {user_data[ctx.user.id]['chat'][thread.id]['support_vision']}")
    await thread.send(embed=embed)
    await message.delete(context=ctx)
    await ctx.send(embed=interactions.Embed(description=f":white_check_mark: Created a new thread ({thread.id})!"))
    
@interactions.listen(interactions.api.events.MessageCreate)
async def chat_session_handler(ctx: interactions.api.events.MessageCreate):
    if hasattr(ctx.message.channel, "owner_id") and ctx.message.channel.owner_id == bot_id:
        if ctx.message.author.id != bot_id:
            message_data = {
                "role": "user",
                "contents": {
                    "text": ctx.message.content,
                    "images": []
                },
                "message_id": ctx.message.id
            }
            if user_data[ctx.message.author.id]['chat'][ctx.message.channel.id]['support_vision'] and len(ctx.message.attachments) > 0:
                for a in ctx.message.attachments:
                    if "image" in a.content_type:
                        image_data = {
                            "type": a.content_type,
                            "data": base64.b64encode(httpx.get(a.url).content).decode('utf-8')
                        }
                        message_data['contents']['images'].append(image_data)
                    else:
                        # TODO: support docs/txt files
                        # maybe some RAG-based solutions could be implemented here
                        print(f"{a.content_type} not implemented")
            user_data[ctx.message.author.id]['chat'][ctx.message.channel.id]['history'].append(message_data)
            user_data[ctx.message.author.id]['chat'][ctx.message.channel.id]['indexes'].append(ctx.message.id)
            client: openai.AsyncOpenAI = user_data[ctx.message.author.id]['client']
            response: interactions.Message = await ctx.message.channel.send(":watch: Please wait...")
            messages = []
            for message in user_data[ctx.message.author.id]['chat'][ctx.message.channel.id]['history']:
                data = {
                    "role": message['role'],
                    "content": []
                }
                data['content'].append({
                    "type": "text",
                    "text": message['contents']['text']
                })
                if len(message['contents']['images']) > 0:
                    for image in message['contents']['images']:
                        data['content'].append({
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:{image['type']};base64,{image['data']}"
                            }
                        })
                messages.append(data)
            chat_completion = await client.chat.completions.create(
                messages=messages,
                model=user_data[ctx.message.author.id]['chat'][ctx.message.channel.id]['selected_model'],
                stream=True
            )
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
            user_data[ctx.message.author.id]['chat'][ctx.message.channel.id]['history'].append(message_data)
            user_data[ctx.message.author.id]['chat'][ctx.message.channel.id]['indexes'].append(response.id)
        
bot.start(token)