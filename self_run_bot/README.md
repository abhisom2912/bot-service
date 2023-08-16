# Self Run Bot - Scarlett

## 1. Brief Introduction
This repo allows you to run your own Discord bot (Scarlett) to answer the queries asked by your community. You can also extend the scope of this repo and add code to allow people to ask question from other sources, for eg. Telegram (refer to bot_service/wip/telegram_bot_openai.py) or via API calls. In the background, Scarlett uses OpenAI to match the query against your documentation and fetch the best possible answer to it.

What sets Scarlett apart from other AI chatbots is its ability to provide high-quality, objective answers with the proper context. Instead of indexing information from the entire internet, Scarlett is trained with your project’s documentation from GitBook, Docusaurus, Medium, and PDF documents like whitepapers, among other things. This ensures that Scarlett maintains the latest information on your project. Whenever anyone asks Scarlett for any information related to your project, it will provide a concise response along with relevant links where the user can get more information about the question asked.

## 2. How Does Scarlett Work?
**Step 1)** You can train Scarlett with various documents, including but not limited to your technical documentation, blog posts, and product explainers. To do so, you only need to provide the relevant links to your documents, and Scarlett will accomplish the rest. 

**Step 2)** Once Scarlett is trained with information about your project, it can be deployed on Discord. By building on the code given in this repository, you can also run a widget-like chatbot that can be added directly to your website.

**Step 3)** Your community members can ask Scarlett for any information about your project and it will respond instantly.


## 3. How to Run Your Bot?
**Step 1)** Get your OpenAI API key from [OpenAI's official website](https://platform.openai.com/account/api-keys).

**Step 2)** Create a Discord bot and get its Discord token by following the steps given [here](https://discordpy.readthedocs.io/en/latest/discord.html#discord-intro).

**Step 3)** Create a `.env` file using the `.env.example` file and specify your environment variables.

**Step 4)** Install the python prerequisites:
```bash 
pip3 install -r requirements.txt
```

**Step 5)** Go to the `./mongo_service` directory and run the following command to host the API:
```bash
python3 -m uvicorn mongo_server:app --reload
```

**Step 6)** After running the mongo server using the command given above, you can check out the Swagger generated API docs here: http://127.0.0.1:8000/docs#/ or the FastAPI generated API docs here: http://127.0.0.1:8000/redoc 

**Step 7)** Run the python script after running the mongo server (in a separate terminal). To do so, run the following command in the `self_run_bot` directory:
```bash
python3 all_bot_openai_py310.py
```

Voila! Scarlett is now ready to answer all queries on your Discord server.


**Note:** If you have any doubts, kindly create an issue on Github. We'll try to go through them at the earliest. Alternatively, you can reach out to us at [scarlettai.official@gmail.com](mailto:scarlettai.official@gmail.com).