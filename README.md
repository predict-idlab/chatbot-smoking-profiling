# Smoking Trigger Detection with a Chatbot
Repository for the paper "Design of a social chatbot with gamification for user profiling and smoking trigger detection". This repository contains the server side. In this project the webhook of Facebook was used for the frontend. Facebook Messenger provided the interface to the chatbot. Moreover, this repository also contains the questionnaire that was used to evaluate the project with participants.

## Project Structure
De app folder contains the chatbot, while the trigger-detection folder contains the module that checks the database for new potential smoking triggers and contstructs messages for the hidden feature games. De docker-compose file takes care of launching these two modules, and also launches a container with a mongoDB database.

## Build and Run Project
To setup the server, first docker needs to be installed. After this, run:

```
docker compose build .
```

To start the containers, run:

```
docker compose up
```

## Webhook with Facebook
The webhook endpoint at the side of the server can be found in `app/App.py`. At Facebook's side a Facebook Page is needed. Instructions for configuring the webhook can be found [here](https://developers.facebook.com/docs/pages/webhooks/).