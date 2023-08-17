# Bot Service - Scarlett

## 1. Brief Introduction
This subdirectory contains code that allows you to run an AI bot as a service. The code includes an AI-powered bot that can learn about a protocol/product/company from a variety of sources including Github repositories, Gitbook documentation, Google sheets, PDF documents, and Medium articles. The bot's primary function is to efficiently answer questions related to the protocol based on its knowledge of the protocol. 

We built this codebase to launch on our own. However, due to time constraints, we were not able to do justice to it. However, you can use this code to launch your own servcice. Our codebase is far ahead of the incumbents in terms of the features it offers: 

## 2. Features

- Comprehensive Learning: The bot is designed to absorb information from diverse sources, enabling it to quickly grasp the nuances of a given protocol.

- Efficient Question Answering: With its extensive learning capabilities, the bot can answer questions accurately and swiftly, saving time for both users and administrators.

- Rate Limiting: To maintain a healthy interaction environment, the service includes built-in rate limiting for questions from users on various communication platforms like Discord and Telegram.

- Question History: The bot keeps track of previously asked questions and their answers, allowing it to respond to repeat inquiries using stored knowledge rather than generating new answers from scratch.

- Flexible Payment Options: The service allows for a pay-as-you-go model, ensuring flexibility in payment. Payments can be made using cryptocurrency, making transactions seamless and secure.

- Training via Moderator Responses: In cases where the bot encounters questions it cannot answer, administrators/moderators can step in. The bot can learn from these responses, constantly improving its capabilities and reducing repetitive tasks for administrators.

## 3. Folder Structure

### `user_facing_apis`
This is the main folder that includes all the code to run Scarlett (AI bot service). 

- All the files with the `_routes.py` suffix interface with our Mongo database.
- `server.py` includes the code to connect with the Mongo server.
- `models.py` includes the schema to define input structure, and streamline data storage. 
- JSON files inside `/user_facing_apis/resources` contains config that helps in the payment process. Currently, only crypto payments are supported. `accepted_payment_methods.json` defines which tokens are accepted and on which chains. 
- `/user_facing_apis/servers_setup` folder contains the script to run a Discord bot for the user
- `/user_facing_apis/utilities` folder includes utilities that are essential for the bot's functioning. `mod_response_training.py` contains code to train bot with the responses from Discord moderators. `fetch_data.py` includes code to fetch data from the links provided by the user and converting it into iterable outputs and embeddings. It uses the scrapers included in the `/user_facing_apis/utilities/scrapers` to scrape data from different data sources, example `gitbook_scraper.py` to scrape Gitbook documentation,  `medium_parser.py` to scrape data from Medium articles, and so on.

### `wip`
This folder contains scripts/functions that we wrote to explore new features. Some of these features were completed and added to our main code (refer to the `user_facing_apis` folder). However, some of these scripts/functions we stopped developing halfway. For more details on the wip scripts, kindly check out this [link](./wip/README.md).


## 4. Important Notes

- Throughout this subdirectory, we refer to `you` as someone who's using the code to run their own service, `user` as someone using that service, and `questioner` as someone asking queries on the user's Discord/TG channel. This is in contrast to `../self_run_bot` where we refer to `user` as someone who's running the bot. 

- The service works on a pay-as-you-go model that allows users to recharge the bot with any amount above a specified minimum amount ($1). Amount added by the user reflects in the database as that user's `credits` while their usage is tracked using a `usage` parameter.


## 5. How to Run this Service?
**Step 1)** Get your OpenAI API key from [OpenAI's official website](https://platform.openai.com/account/api-keys).

**Step 2)** Create a Discord bot and get its Discord token by following the steps given [here](https://discordpy.readthedocs.io/en/latest/discord.html#discord-intro).

**Step 3)** Create a `.env` file using the `.env.example` file and specify your environment variables.

**Step 4)** Install the python prerequisites:
```bash 
pip3 install -r requirements.txt
```

**Step 5)** Go to the `./user_facing_apis` directory and run the following command to host the API:
```bash
python3 -m uvicorn server:app --reload
```

**Step 6)** After running the Mongo server using the command given above, you can check out the Swagger generated API docs here: http://127.0.0.1:8000/docs#/ or the FastAPI generated API docs here: http://127.0.0.1:8000/redoc 

**Step 7)** Run the bot after running the mongo server (in a separate terminal). To do so, run the following command in the `./user_facing_apis/servers_setup` directory:
```bash
python3 discord_server.py
```

Voila! Your AI bot service is now ready.



**Note:** If you have any doubts, kindly create an issue on Github. We'll try to go through them at the earliest. Alternatively, you can reach out to us at [scarlettai.official@gmail.com](mailto:scarlettai.official@gmail.com).