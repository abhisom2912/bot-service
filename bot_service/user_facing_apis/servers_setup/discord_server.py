import discord
from asgiref.sync import sync_to_async
from ..utilities.utility_functions import *
from dotenv import dotenv_values
import requests
import json

config = dotenv_values("bot_service/.env")
list_of_exempted_server_ids = config['EXEMPTED_SERVER_IDS'].split(',') if \
    'EXEMPTED_SERVER_IDS' in config.keys() is not None else []


def get_answer(question, server_id, questioner_id):
    rate_limit_error_message = 'You have already asked the maximum number of questions for the day on this server. Please contact admin for further questions or you can increase your quota by visiting our website.'
    usage_exceeded_message = 'Usage has exceeded the credits allocated to Scarlett for this protocol . Please contact admin to top-up Scarlett for continuing the services.'
    protocol_not_found_message = 'We couldn\'t find any active protocol docs for this server. Please contact admin to onboard Scarlett on this server.'
    unknown_error_message = 'Unknown error occurred. Please try again or report to admin.'
    query_params = "discord/" +  server_id + "/" + questioner_id + "?question=" + question
    if server_id in list_of_exempted_server_ids:
        response = requests.get(config['BASE_API_URL'] + "question/masterApi/getAnswerFromAnyProtocol?question=" + question)
    else:
        response = requests.get(config['BASE_API_URL'] + "question/" + query_params)

    if response.status_code == 200:
        response_json = json.loads(response.content.decode('utf-8'))
        return response_json['question_answered'], response_json['answer'], response_json['links']
    elif response.status_code == 403:
        return False, rate_limit_error_message, []
    elif response.status_code == 404:
        return False, protocol_not_found_message, []
    elif response.status_code == 424:
        return False, usage_exceeded_message, []
    else:
        return False, unknown_error_message, []


def update_mod_response(question, response, server_id):
    # clean_question = question.replace("?", '').replace('&', 'and')
    body = {
        "server_type": "discord",
        "server_id": server_id,
        "question": question,
        "response": response
    }
    requests.put(config['BASE_API_URL'] + "protocol/addResponse", json.dumps(body))


def start_discord_bot():
    intents = discord.Intents.default()
    intents.message_content = True
    client = discord.Client(intents=intents)

    @client.event
    async def on_ready():
        print('We have logged in as {0.user}'.format(client))

    @client.event
    async def on_message(message):
        print(message.content)
        if message.author == client.user:
            return

        if message.content.lower().find('@1072338244085227623'.lower()) != -1 or message.clean_content.lower().find('@scarlett') != -1:
            question = message.clean_content.replace('@scarlett', '').strip()
            title = "Q: " + question
            question_answered, answer, links = await sync_to_async(get_answer)(question, str(message.guild.id), str(message.author.id))
            link_number = 1
            link_text = ''
            for link in links:
                if link_number == 1:
                    link_text = ' [Link' + str(link_number) + '](' + link + ')'
                else:
                    link_text += ', [Link' + str(link_number) + '](' + link + ')'
                link_number += 1
            embed_var = discord.Embed(title=title, description="A: " + answer, color=0x4bd4d6)
            embed_var.set_author(name=message.author.display_name + " asked:", url="",
                                 icon_url=message.author.display_avatar)
            if link_text != '' and question_answered:
                embed_var.add_field(name="Relevant links",
                                    value="To read more, check out the following links -" + link_text, inline=False)
            # await message.reply(embed = embed_var)
            await message.channel.send(embed=embed_var)

        elif message.reference and (message.author.guild_permissions.ban_members or
                                    message.author.guild_permissions.kick_members or
                                    message.author.guild_permissions.moderate_members or
                                    message.author.guild_permissions.mute_members):
            if 'gif' not in message.clean_content and check_if_question(message.reference.resolved.clean_content):
                question = " ".join(filter(lambda x:x[0]!='@', message.reference.resolved.clean_content.split()))
                response = " ".join(filter(lambda x:x[0]!='@', message.clean_content.split()))
                print(question + '-> ' + response)
                await sync_to_async(update_mod_response)(question, response, str(message.guild.id))

    client.run(config['DISCORD_TOKEN'])


if __name__ == '__main__':
    start_discord_bot()
