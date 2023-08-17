# Scarlett

This repository contains two subdirectories:

### 1. `self_run_bot`
This subdirectory contains code that allows you to run your own Discord bot (Scarlett) to answer the queries asked within your community. You can also extend the scope of this repo and add code to allow people to ask question from other sources. In the background, Scarlett uses OpenAI to match the query against your documentation and fetch the best possible answer to it.

This is targeted towards users who want to run their own AI bot for community management. To run the code in this subdirectory, you don't need a lot of programming experience. Check out this [link](./self_run_bot/README.md) for more details.


### 2. `bot_service`
This subdirectory contains code that allows you to run an AI bot as a service. The code includes an AI-powered bot that can learn about a protocol/product/company from a variety of sources including Github repositories, Google sheets, Gitbook documentation, PDF documents, and Medium articles. The bot's primary function is to efficiently answer questions related to the protocol based on its knowledge of the protocol. 

We built this codebase to launch on our own. However, due to time constraints, we were not able to do justice to it. However, you can use this code to launch your own servcice. Our codebase is far ahead of the incumbents in terms of the features it offers: 

**Features**

- Comprehensive Learning: The bot is designed to absorb information from diverse sources, enabling it to quickly grasp the nuances of a given protocol.

- Efficient Question Answering: With its extensive learning capabilities, the bot can answer questions accurately and swiftly, saving time for both users and administrators.

- Rate Limiting: To maintain a healthy interaction environment, the service includes built-in rate limiting for questions from users on various communication platforms like Discord and Telegram.

- Question History: The bot keeps track of previously asked questions and their answers, allowing it to respond to repeat inquiries using stored knowledge rather than generating new answers from scratch.

- Flexible Payment Options: The service allows for a pay-as-you-go model, ensuring flexibility in payment. Payments can be made using cryptocurrency, making transactions seamless and secure.

- Training via Moderator Responses: In cases where the bot encounters questions it cannot answer, administrators/moderators can step in. The bot can learn from these responses, constantly improving its capabilities and reducing repetitive tasks for administrators.


To know more about this service, including how to run it, check out this [link](./bot_service/README.md).


## Contributing
We welcome contributions to enhance and expand the capabilities of this repository. If you have ideas for new features, improvements, or bug fixes, please feel free to fork this repository, make your changes, and submit a pull request.

## Support
If you encounter any issues or have questions about setting up or using this repository, please reach out to us at [scarlettai.official@gmail.com](mailto:scarlettai.official@gmail.com).

## License
This project is licensed under the MIT License, allowing you to use, modify, and distribute the code as per the terms mentioned.




