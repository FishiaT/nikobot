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
    "indexes": {
        "<session id>": "<user id>"
    },
    "terminated": [
        "<terminated session ids>"
    ]
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

user_data = {
    "indexes": {},
    "terminated": []
}

# TODO: only use necessary intents
# until i stop being a lazyass this should suffice
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
    try:
        models = client.models.list().to_dict()
    except openai.AuthenticationError:
        embed = interactions.Embed(title="Failed :x:", description=f"Unable to connect to `{url}`. Invalid or no API key specified.")
        await ctx.send(embed=embed)
        client.close()
        return
    except openai.APIConnectionError:
        embed = interactions.Embed(title="Failed :x:", description=f"Unable to connect to `{url}`. Please check if the provided URL is correct.")
        await ctx.send(embed=embed)
        client.close()
        return
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
        
        {len(user_data[ctx.user.id]['api']['models'])} model(s) is available for selection.
        """
        user_data[ctx.user.id]['client'] = openai.AsyncOpenAI(base_url=url, api_key=api_key)
        embed = interactions.Embed(title="Success :white_check_mark:", description=embed_description)
        await ctx.send(embed=embed)
    else:
        embed = interactions.Embed(title="Failed :x:", description=f"Unable to connect to `{url}`. Failed to fetch models.")
        await ctx.send(embed=embed)
    client.close()
    
@interactions.slash_command(name="chat", description="Initiate a new chat session", scopes=server_ids)
async def chat_command(ctx: interactions.SlashContext):
    if hasattr(ctx.channel, "owner_id") and ctx.channel.owner_id == bot_id:
        embed = interactions.Embed(description=":x: This command cannot be ran in a chat session.")
        await ctx.send(embed=embed, ephemeral=True)
        return
    if not ctx.user.id in user_data.keys() or not user_data[ctx.user.id]['api']['url']:
        embed = interactions.Embed(description=":x: You have not yet connected to an LLM API. In order to start a chat session, please connect to an API by using the `/connect` command.")
        await ctx.send(embed=embed, ephemeral=True)
        return
    model_select = interactions.StringSelectMenu(user_data[ctx.user.id]['api']['models'], placeholder="Pick a model")
    message: interactions.Message = await ctx.send(embed=interactions.Embed(description="Please choose a model to use.\n\nAfter choosing a model, it may take a while before the session is created. A new message will be sent to notify you once that's done."), components=model_select, ephemeral=True)
    result: interactions.api.events.Component = await bot.wait_for_component(messages=message, components=model_select)
    await message.delete(context=ctx)
    status_message = await ctx.send(embed=interactions.Embed(description=":watch: Setting things up, please wait..."), ephemeral=True)
    thread = await ctx.channel.create_private_thread(name="New Session")
    user_data[ctx.user.id]['chat'][thread.id] = {}
    user_data[ctx.user.id]['chat'][thread.id]['selected_model'] = result.ctx.values[0]
    user_data[ctx.user.id]['chat'][thread.id]['support_vision'] = True
    user_data[ctx.user.id]['chat'][thread.id]['system_prompt'] = ""
    user_data[ctx.user.id]['chat'][thread.id]['parameters'] = {
        "stream": False,
        "temperature": 0.8,
        "seed": -1
    }
    user_data[ctx.user.id]['chat'][thread.id]['history'] = []
    user_data[ctx.user.id]['chat'][thread.id]['indexes'] = []
    user_data['indexes'][thread.id] = ctx.user.id
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
    except openai.BadRequestError as e:
        if "must be a string" in e.body:
            # assume no image or other file type
            user_data[ctx.user.id]['chat'][thread.id]['support_vision'] = False
        else:
            # TODO: handle non-instruct models (e.g. whisper)
            print(f"{e.body} not implemented")
    await thread.add_member(ctx.user)
    embed = interactions.Embed(description=f"Chat session initiated, you may now start interacting with the choosen LLM model by sending messages in this thread.\n\nWhile you are in this thread, you may also use special commands to change the inference parameters, modify the system prompt, and terminate this session!\n\n• Selected Model: {user_data[ctx.user.id]['chat'][thread.id]['selected_model']}\n• Support image attachments: {user_data[ctx.user.id]['chat'][thread.id]['support_vision']}")
    await thread.send(embed=embed)
    await status_message.delete(context=ctx)
    await ctx.send(embed=interactions.Embed(description=f":white_check_mark: Chat session created!"), ephemeral=True)
    
@interactions.slash_command(name="terminate", description="Terminate current chat session", scopes=server_ids)
async def terminate_command(ctx: interactions.SlashContext):
    if hasattr(ctx.channel, "owner_id") and ctx.channel.owner_id == bot_id and ctx.channel_id in user_data['indexes'].keys() and ctx.user.id == user_data['indexes'][ctx.channel.id]:
        user_data['indexes'].pop(ctx.channel_id)
        user_data[ctx.user.id]['chat'].pop(ctx.channel_id)
        user_data['terminated'].append(ctx.channel_id)
        await ctx.send(embed=interactions.Embed(description=":white_check_mark: Terminated current session."))
        await ctx.channel.archive(locked=True)
    else:
        await ctx.send(embed=interactions.Embed(description=":x: You are not in a chat thread or are not the creator of this thread!"), ephemeral=True)
        
@interactions.slash_command(name="system_prompt", description="Change the system prompt of the current session", scopes=server_ids)
async def system_prompt_command(ctx: interactions.SlashContext):
    if hasattr(ctx.channel, "owner_id") and ctx.channel.owner_id == bot_id and ctx.channel_id in user_data['indexes'].keys() and ctx.user.id == user_data['indexes'][ctx.channel.id]:
        modal = interactions.Modal(
            interactions.ParagraphText(
                required=False,
                custom_id="system_prompt",
                label="System Prompt",
                placeholder="You are a helpful AI assistant.",
                value=user_data[ctx.user.id]['chat'][ctx.channel_id]['system_prompt']
            ),
            title="System Prompt"
        )
        await ctx.send_modal(modal)
        modal_ctx: interactions.ModalContext = await bot.wait_for_modal(modal)
        user_data[ctx.user.id]['chat'][ctx.channel.id]['system_prompt'] = modal_ctx.responses['system_prompt']
        await modal_ctx.send(embed=interactions.Embed(description=":white_check_mark: Changed the system prompt!"), delete_after=10)
    else:
        await ctx.send(embed=interactions.Embed(description=":x: You are not in a chat thread or are not the creator of this thread!"), ephemeral=True)
        
@interactions.slash_command(name="inference_parameters", description="Change inference parameters", scopes=server_ids)
@interactions.slash_option(
    name="stream",
    description="Update response in real time (NOT OPTIMIZED)",
    opt_type=interactions.OptionType.BOOLEAN
)
@interactions.slash_option(
    name="temperature",
    description="Randomness of response (higher increases creativity and vice versa)",
    opt_type=interactions.OptionType.NUMBER
)
@interactions.slash_option(
    name="seed",
    description="Seed for the Random Number Generator",
    opt_type=interactions.OptionType.INTEGER
)
async def inference_parameters_command(ctx: interactions.SlashContext, stream: bool = False, temp: float = 0.8, seed: int = -1):
    if hasattr(ctx.channel, "owner_id") and ctx.channel.owner_id == bot_id and ctx.channel_id in user_data['indexes'].keys() and ctx.user.id == user_data['indexes'][ctx.channel.id]:
        user_data[ctx.user.id]['chat'][ctx.channel.id]['parameters']['stream'] = stream
        user_data[ctx.user.id]['chat'][ctx.channel.id]['parameters']['temperature'] = temp
        user_data[ctx.user.id]['chat'][ctx.channel.id]['parameters']['seed'] = seed
        await ctx.send(embed=interactions.Embed(description=":white_check_mark: Updated inference parameters!"), delete_after=10)
    else:
        await ctx.send(embed=interactions.Embed(description=":x: You are not in a chat thread or are not the creator of this thread!"), ephemeral=True)
    
@interactions.listen(interactions.api.events.MessageCreate)
async def chat_session_handler(ctx: interactions.api.events.MessageCreate):
    if hasattr(ctx.message.channel, "owner_id") and ctx.message.channel.owner_id == bot_id:
        if ctx.message.author.id != bot_id and ctx.message.author.id == user_data['indexes'][ctx.message.channel.id] and not ctx.message.channel.id in user_data['terminated']:
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
            response: interactions.Message = await ctx.message.channel.send(":watch: Please wait, this may take a while...")
            messages = []
            if user_data[ctx.message.author.id]['chat'][ctx.message.channel.id]['system_prompt']:
                messages.append({
                    "role": "system",
                    "content": user_data[ctx.message.author.id]['chat'][ctx.message.channel.id]['system_prompt']
                })
            for message in user_data[ctx.message.author.id]['chat'][ctx.message.channel.id]['history']:
                data = {
                    "role": message['role']
                }
                match(message['role']):
                    case "user":
                        data['content'] = []
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
                    case "assistant":
                        data['content'] = message['contents']['text']
                messages.append(data)
            chat_completion = await client.chat.completions.create(
                messages=messages,
                model=user_data[ctx.message.author.id]['chat'][ctx.message.channel.id]['selected_model'],
                stream=True,
                temperature=user_data[ctx.message.author.id]['chat'][ctx.message.channel.id]['parameters']['temperature'],
                seed=user_data[ctx.message.author.id]['chat'][ctx.message.channel.id]['parameters']['seed']
            )
            final_response = ""
            async for chunk in chat_completion:
                final_response += chunk.choices[0].delta.content or ""
                if user_data[ctx.message.author.id]['chat'][ctx.message.channel.id]['parameters']['stream']:
                    await response.edit(content=final_response)
            await response.edit(content=final_response)
            message_data = {
                "role": "assistant",
                "contents": {
                    "text": final_response,
                    "images": []
                },
                "message_id": response.id
            }
            user_data[ctx.message.author.id]['chat'][ctx.message.channel.id]['history'].append(message_data)
            user_data[ctx.message.author.id]['chat'][ctx.message.channel.id]['indexes'].append(response.id)
            
@interactions.listen(interactions.api.events.MessageDelete)
async def message_deletion_handler(ctx: interactions.api.events.MessageDelete):
    if hasattr(ctx.message.channel, "owner_id") and ctx.message.channel.owner_id == bot_id:
        if ctx.message.channel.id in user_data['indexes'].keys():
            user_id = user_data['indexes'][ctx.message.channel.id]
            message_index = user_data[user_id]['chat'][ctx.message.channel.id]['indexes'].index(ctx.message.id)
            user_data[user_id]['chat'][ctx.message.channel.id]['indexes'].pop(message_index)
            user_data[user_id]['chat'][ctx.message.channel.id]['history'].pop(message_index)
        
bot.start(token)