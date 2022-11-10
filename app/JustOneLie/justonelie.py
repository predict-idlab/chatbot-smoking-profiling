import random
import re
import mongoconnection
from datetime import date, datetime
import JustOneLie.analysis as analysis
import utils
import ranking

questions_dic = {'What are some health effects of secondhand smoke?': 1, 
'What can you do to protect your loved ones from secondhand smoke?': 2,
'What are some health effects of smoking?': 3,
'Which improvements will follow after quitting smoking?': 4,
'What are some of the health benefits of quitting smoking over time?': 5
}

user_questions_list = ['What does your family look like?',
'What do you do in your free time?',
'What are your hobbies?',
'What makes you stressed?',
'What makes you angry?',
'What makes you sad?',
'What are daily things you do at home?',
'What are your priorities in life?',
'What are your smoking triggers?',
'Why did you start smoking?',
'What do you do when you visit a bar?',
'Why do you want to stop smoking?',
'What type of beverages do you like to drink?',
'Who among your friends do you like to meet up with the most?',
'What do you like to do with your friends?',
'If the world were coming to an end, what would you like to do one more time?',
'Who had the most impact in your life?'
]

quick_yes_no = [{"content_type":"text", "title": "Yes", "payload": "yes"}, {"content_type":"text", "title": "No", "payload": "no"}]

# get list with first two truths and then a lie
def get_justonelie_options(question):
    number = questions_dic[question]
    file_truths = open(f'JustOneLie/data/{number}_truth.txt', mode='r', encoding="utf-8")
    options = random.sample(file_truths.read().splitlines(), 2)
    file_lie = open(f'JustOneLie/data/{number}_lie.txt', mode='r', encoding="utf-8")
    return options + random.sample(file_lie.read().splitlines(), 1)

def get_justonelie_questions():
    return random.sample(list(questions_dic.keys()),3)

def initiate_user(message, id, col):
    update_state(col, id, "turn")
    return {"text": "Alright! Do you want to start with telling two truths and one lie? \n\n[Answering no on this question can lead into the hidden feature if certain conditions are met.]", "quick_replies": quick_yes_no}

def turn(message, id, db):
    col = db.justonelie
    if "yes" in message.lower():
        return user_start(id, col)
    else:
        return chatbot_start(db, id, col)

def user_start(id, col):
    update_state(col, id, "user_options")
    question = random.choice(user_questions_list)
    # save the question for the user
    col.update_one({"user_id": id}, {"$set": {"user_question": question}})
    return {"text": f"Alright. The question is: {question}"}

def chatbot_start(db, id, col):
    dif = datetime.now() - db.user.find_one({"user_id": id})["timestamp"]
    if (db.questions.count_documents({"user_id": id}) != 0) and (dif.days > 2):
        guess = random.randint(0, 3)
        if guess:
            update_state(col, id, "chatbot_question")
            return analysis.chatbot_question(db, id)
    update_state(col, id, "user_choose_question")
    questions = get_justonelie_questions()
    text = "Choose one of the following questions: \n"
    quick_replies = []
    for i, question in enumerate(questions): 
        text += f"({i+1}) {question} \n"
        quick_replies.append({"content_type": "text", "title": f"{i+1}", "payload": question})
    return {"text": text, "quick_replies": quick_replies}

def user_options(message, id, col):
    matches = re.findall(r"([0-9]+)([\.\) ]+)([a-zA-Z ]+)", message)
    if len(matches) == 3:
        lie = random.randint(1,3)
        # put matches in database
        l = []
        for i in range(3):
            l.append(matches[i-1][2].strip())
        col.update_one({"user_id": id}, {"$set": {"user_options": l}})
        # put guessed lie in database
        col.update_one({"user_id": id}, {"$set": {"user_lie": matches[lie-1][2].strip()}})
        update_state(col, id, "verify_user")
        return {"text": f'The lie is number {matches[lie-1][0]}! "{matches[lie-1][2].strip()}"', 
        "quick_replies": [{"content_type":"text", "title": "True", "payload": "true"}, {"content_type":"text", "title": "False", "payload": "false"}]}
    else:
        # check how many options the user has already given
        option = 0
        l = []
        doc = col.find_one({"user_id": id})
        if "user_options" in doc.keys():
            l = doc["user_options"]
            option = len(l)
        else:
            option = 0
        l.append(message)
        #for i in range(len(matches)):
            #l.append(matches[i+1][2].strip())
        col.update_one({"user_id": id}, {"$set": {"user_options": l}})
        if option == 2:
            lie_nr = random.randint(1,3)
            col.update_one({"user_id": id}, {"$set": {"user_lie": l[lie_nr-1]}})
            lie_text = l[lie_nr-1]
            update_state(col, id, "verify_user")
            return {"text": f'The lie is number {lie_nr}! "{lie_text}"', 
            "quick_replies": [{"content_type":"text", "title": "True", "payload": "true"}, {"content_type":"text", "title": "False", "payload": "false"}]}
        return {"text": f"{2-option} more."}

def chatbot_options(message, id, col):
    options = []
    if message in questions_dic:
        options = get_justonelie_options(message)
    else:
        update_state(col, id, "initiate")
        return {"text": "I did not understand you. Let's start again."}
    # store lie in database
    col.update_one({"user_id": id}, {"$set": {"chatbot_lie": options[2]}})
    text = "What is the lie?\n"
    quick_replies = []
    for i, option in enumerate(options):
        text += f"({i+1}) {option} \n"
        quick_replies.append({"content_type": "text", "title": f"{i+1}", "payload": option})
    update_state(col, id, "verify_chatbot")
    return {"text": text, "quick_replies": quick_replies}

def verify_user(message, id, col, db):
    if "true" in message.lower():
        return save(id, db, "Great!", 50)
    else:
        update_state(col, id, "verify_user_lie")
        text = "What was the lie? \n"
        options = col.find_one({"user_id": id})["user_options"]
        quick_replies = []
        for i, option in enumerate(options): 
            text += f"({i+1}) {option} \n"
            quick_replies.append({"content_type": "text", "title": f"{i+1}", "payload": option})
        return {"text": text, "quick_replies": quick_replies}

def verify_chatbot(message, id, db):
    lie = db.justonelie.find_one({"user_id": id})["chatbot_lie"]
    if message == lie:
        return award_points("You're right!", id, db, 100)
    else:
        return award_points(f'Wrong, the lie was "{lie}"', id, db, 0)

def verify_user_lie(message, id, col, db):
    col.update_one({"user_id": id}, {"$set": {"user_lie": message}})
    return save(id, db, "You fooled me!", 100)

def save(id, db, extra_message, points):
    # get data
    col = db.justonelie
    doc = col.find_one({"user_id": id})
    dict = {}
    dict['user_question'] = doc["user_question"]
    dict['user_options'] = doc["user_options"]
    dict['user_lie'] = doc["user_lie"]

    # insert data
    new_data = {'user_id': id, 'data': dict, 'game': 'justonelie', 'processed': False}
    db.data.insert_one(new_data)

    # delete data
    clean(id, col)
    return award_points(extra_message, id, db, points)

def award_points(extra_message, id, db, points):
    col = db.justonelie
    update_state(col, id, "again")
    doc = col.find_one({"user_id": id})
    current_total = int(doc["points"])
    new_total = current_total + points
    nr_played = doc["played"] + 1
    col.update_one({"user_id": id}, {"$set": {"points": new_total, "played": nr_played}})
    msg = f"{extra_message} You gain {points} points. You now have {new_total} points."
    msg += utils.check_streak(id, col, col.find_one({"user_id": id})["day"], new_total) 
    msg += ranking.get_ranking(id, db, 'justonelie')  
    return {"text": f"{msg} Do you want to play again?", "quick_replies": quick_yes_no}

def again(message, id, col, db):
    if "yes" in message.lower():
        doc = db.justonelie.find_one({"user_id": id})
        db.justonelie.update_one({"user_id": id}, {"$set": {"state": "initiate", 'again': doc['again']+1}})
        return initiate_user(message, id, col)
    else:
        return stop_game(id, db)

def clean(id, col):
    col.update_one({"user_id": id}, {"$set": {"user_options": []}})
    col.update_one({"user_id": id}, {"$set": {"user_question": ""}})
    col.update_one({"user_id": id}, {"$set": {"user_lie": ""}})

def stop_game(id, db):
    clean(id, db.justonelie)
    update_state(db.justonelie, id, "initiate")
    update_state(db.user, id, "choose_game")
    return {"text": "Stopped the game. Answer me if you want to play another game.\n\nSend \n'#': smoking registration \n'##': smoking registration (now) \n'ranking': leaderboard\n'help': more information"}

def create_new_game(col, userid, state):
    new_user = {'user_id': userid, 'state': state, 'points': 0, 'day': date.today().strftime("%d-%m-%Y"), 'streak': 0, 'played': 0, 'stopped':0, 'again': 0, 'all_streaks': []}
    col.insert_one(new_user)
    return utils.explanation('justonelie')

def update_state(col, userid, state):
    query = {"user_id": userid}
    newvalue = {"$set": {"state": state}}
    col.update_one(query, newvalue)

def game(message, id, db):
    #get state
    state = ""
    game_col = db.justonelie
    doc = game_col.find_one({"user_id": id})
    if doc == None:
        return create_new_game(game_col, id, "initiate")
    else:
        state = doc['state']
    
    # if message is stop, quit game
    if message.lower() == "stop":
        game_col.update_one({"user_id": id}, {"$set": {'stopped': doc['stopped']+1}})
        return stop_game(id, db)

    # states
    if state == "initiate":
        return initiate_user(message, id, game_col)
    elif state == "turn":
        return turn(message, id, db)
    elif state == "user_options":
        return user_options(message, id, game_col)
    elif state == "user_choose_question":
        return chatbot_options(message, id, game_col)
    elif state == "verify_user":
        return verify_user(message, id, game_col, db)
    elif state == "verify_chatbot":
        return verify_chatbot(message, id, db)
    elif state == "verify_user_lie":
        return verify_user_lie(message, id, game_col, db)
    elif state == "chatbot_question":
        return analysis.verify_chatbot_question(db, id, message)
    elif state == "correction":
        return analysis.correction_question(db, id, message)
    elif state == "again":
        return again(message, id, game_col, db)
    
    update_state(game_col, id, "initiate")
    return {"text": "I did not understand you. Let's start again."}