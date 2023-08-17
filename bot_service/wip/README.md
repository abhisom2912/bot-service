# Work in Progress (WIP) Scripts/Functions

We started writing these scripts/functions to explore new features. Some of these features were completed and added to our main code (refer to the "user_facing_apis" folder). However, some of these scripts/functions we stopped developing halfway. 

**Note:** Some code snippets in this folder might break. 

## Understanding the Files in this Folder
1. `all_bot_openai_py310_cmd.py`
- A sample discord bot which which can be setup via command line parameters. You can train this bot with various type of data including a link to your Github docs, Gitbook docs, or from a PDF document.
- This bot can also read data from a Google sheet. The Google sheet should contain Title, Heading (topic), Content (details about the topic), Uploaded (boolean value which tells if this conent is already uploaded to avoid reuploads)

2. `alternate_pdf_parse_font_style.py`
- Sample code for parsing a PDF file
- This particular code looks at the font styles to figure out the headings and the content within the headings
- We explored this technique to parse PDF, however, we are using a different PDF parsing methodology in our main code

3. `fuzzy_match.py`
- Sample python code to perform fuzzy match
- This feature can be used to fetch answers to queries that have been asked previously
- This feature can help make the service more cost effective

4. `telegram_bot_openai.py`
- A sample TG bot that can be trained with various type of data including a link to your Github docs, Gitbook docs, or from a PDF document.
- This bot can answer questions from your community on Telegram.
