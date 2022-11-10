from datetime import date, datetime, timedelta

explanations = {"justonelie": """This game is JustOneLie. One of the players tells two truths and one lie, while the other guesses what the lie is.\n
If you want to start with telling two truths and one lie, I will give you a few topics. You have to tell two truths and one lie that have something to do with this topic. When I asks you to give your statements, send them to me one by one, separately. For example:
you: option1
you: option2
you: option3\n
After sending your statements, I will guess what your lie is. After that, you will confirm whether I was right or wrong.\n
If you don't want to start, you can choose between a few topics my statements should be about. When you have chosen that, I will present you with my statements. You select my lie, and I will confirm if your guess was right or wrong.\n
You will gain points according to whether I guessed your lie or not, or whether you guessed my lie or not. \n
There are a few hidden parts of the game that will present themselves after you've played some of the games. Try to unlock these features. Good luck!\n
If you want to see the rankings of this game, send 'ranking'. Send 'help' in the game if you want to hear the rules again.""",
"storybuilder": """This game is StoryBuilder. One of the players starts with a prompt, and then each player continues the story in turns.\n
First you choose the genre of the story after which you or I start with a prompt, and then the story is build in turns. If you have reached the ending of the story you wanted to write, you send 'done' to me and you'll get your points. You gain points according to how many additions you do to the story. If you want to stop the game at any time, you can send 'stop' to me. However, you won't gain any points.\n
A few features are locked until I have gathered enough data about you. To unlock these features, play the different games.\n
If you want to see the rankings of this game, send 'ranking'. Send 'help' in the game if you want to hear the rules again.""",
"listbuilder": """This game is ListBuilder. Two players try to build a list of words according to a topic. The rule is that your word (or group of words) begins with what the other player has ended.
For example (with as topic 'hobbies'):
me: read
you: drawing
me: gaming\n
First, you choose the topic around which we will build a list, and then you'll start with the first word. I'll continue your list with my own addition, and then it's your turn again.
The game stops when I don't know any words anymore, or when you send a word that does not begin with the end of my last word. You gain points according to how many additions to the list you have made. If you want to stop the game at any moment, you can type 'stop' and the game will stop. You'll gain no points however if you quit this way.\n
It's important that you answer each topic truthfully and that your answers relate to you.\n
If you want to see the rankings of this game, send 'ranking'. Send 'help' in the game if you want to hear the rules again.""",
"whereami":"""This game is WhereAmI. One player tries to guess the whereabouts of the other player. This player gives hints of what he sees, and the first player can guess once per hint.\n
First of all, you choose of you want to start with giving hint to your location, or if you want to guess the place I have in mind. If you guess my place, you'll gain points. However if you can't guess the place, you send 'stop'. You'll gain no points however. If you're the one giving hints, you'll gain more points the longer it takes me to guess the place. If it takes me too long to guess the place or I have no idea, I'll give up and you'll get points.\n
So, whenever you change location, a quick game of WhereAmI can give you lots of points.\n
If you want to see the rankings of this game, send 'ranking'. Send 'help' in the game if you want to hear the rules again.""",
"general": """Let me first give you a quick overview of my capabilities.\n 
There are four games from which you can choose, and these can be selected by talking to me. I'll give you the options when you talk to me.\n 
If you are in a game and you want to switch back to the options menu, finish the game or send 'stop'. However, if you use the 'stop' method, no points will be given to you.\n
Each game has a streak feature, so if you play a game every day, your points will quickly accumulate the longer you keep up the streak.\n
If you want to register a smoking event, type the symbol '#' and you will be guided through the smoking event registration. If you want to stop the registration at any moment, send 'stop'. If you want to restart the registration, send '#' again. If you don't want to go through all the steps every time and just want to register a smoking event that happened just now, send '##'.\n
Sometimes I'll give you multiple options from which you can choose and if you're on a phone, you may have to swipe to the right to see all the options.\n
Rankings of the accumulated amount of points are kept for every seperate game. Moreover, there is even a ranking for all the games in total. If you want to see where you stand in these rankings, send 'ranking'.\n
Now, answer this message and let's select a game."""}

def explanation(game):
    return {"text": explanations[game]}

def check_streak(id, col, day, total_points):
    if date.today().strftime("%d-%m-%Y") != day:
        doc = col.find_one({"user_id": id})
        if date.today() == (datetime.strptime(day, "%d-%m-%Y") + timedelta(days=1)).date():
            points = 0
            streak = doc["streak"]+1
            msg = f" You now have a streak of {streak} day(s)."
            if streak%7 == 0:
                points += int(100*(streak/7))
                msg += f" This comes down to {int(streak/7)} week(s), which results to {int(1000*(streak/7))} additional points."
            points += int(streak*30)
            total_points += points
            msg += f" You gained {int(streak*30)} points for your streak. This comes down to {total_points} points."
            col.update_one({"user_id": id}, {"$set": {"points": total_points, "streak": streak, "day": date.today().strftime("%d-%m-%Y")}})
            return msg
        else:
            streak = doc["streak"]+1
            all_streaks = doc['all_streaks']
            all_streaks.append(streak)
            col.update_one({"user_id": id}, {"$set": {"streak": 0, "day": date.today().strftime("%d-%m-%Y"), "all_streaks": all_streaks}})
            return f" You have lost your streak of {streak} day(s)."
    else:
        return ""