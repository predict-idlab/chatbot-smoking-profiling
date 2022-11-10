import random
from datetime import date
import utils
import ranking

subjects = {'hobbies': 1,
'stress factors': 2,
'smoking triggers': 3,
'family': 4
}

quick_yes_no = [{"content_type":"text", "title": "Yes", "payload": "yes"}, {"content_type":"text", "title": "No", "payload": "no"}]

def create_new_game(col, userid, state):
    new_user = {'user_id': userid, 'state': state, 'points': 0, "words": [], "user_answers": [], 'day': date.today().strftime("%d-%m-%Y"), 'streak': 0, 'played': 0, 'stopped': 0, 'again': 0, 'all_streaks': []}
    col.insert_one(new_user)
    return utils.explanation('listbuilder')

def update_state(col, userid, state):
    query = {"user_id": userid}
    newvalue = {"$set": {"state": state}}
    col.update_one(query, newvalue)

def stop_game(id, db):
    clean(id, db.listbuilder)
    update_state(db.listbuilder, id, "initiate")
    update_state(db.user, id, "choose_game")
    return {"text": "Stopped the game. Answer me if you want to play another game.\n\nSend \n'#': smoking registration \n'##': smoking registration (now) \n'ranking': leaderboard\n'help': more information"}

def get_next_word(letter, subject):
    nr = subjects[subject]
    file = f'ListBuilder/data/{nr}.txt'
    l = [x.split('\t')[ord(letter)-97] for x in open(file).readlines()]
    l = list(filter(None, map(lambda s: s.strip(), l)))
    if l == []:
        return None
    return random.sample(l, 1)[0].strip()

def initiate_user(message, id, col):
    update_state(col, id, "start")
    text = "Alright! Which subject do you want? \n"
    quick_replies = []
    for i, subject in enumerate(subjects.keys()): 
        text += f"({i+1}) {subject} \n"
        quick_replies.append({"content_type": "text", "title": subject, "payload": subject})
    return {"text": text, "quick_replies": quick_replies}

def start(message, id, col):
    if message in subjects.keys():
        update_state(col, id, "generate")
        col.update_one({"user_id": id}, {"$set": {"subject": message}})
        turns = random.randint(1, 6)
        col.update_one({"user_id": id}, {"$set": {"nr_of_turns": turns}})
        col.update_one({"user_id": id}, {"$set": {"nr_of_turns_left": turns}})
        return {"text": f"Type 'done' if you do not know any words anymore that relate to you. Alright, tell me about your {message}."}
    update_state(col, id, "initiate")
    return {"text": "I did not understand you. Let's start again."}

def word_generator(message, id, col, db):
    letter = message.lower().strip()[-1]
    # check if an acceptable letter
    nr = ord(letter)-97
    if nr < 0 or nr > 25:
        return {"text": "I do not recognize your last letter, can you repeat that?"}
    doc = col.find_one({"user_id": id})
    subject = doc["subject"]
    l = doc["words"]
    answers = doc["user_answers"]
    nr_turns = doc["nr_of_turns_left"]
    # check if 'done' is sent
    if message.lower() == "done":
        save(id, db)
        total_turns = doc["nr_of_turns"] - doc["nr_of_turns_left"]
        em = f"You ran out of options. You lost, but you gave {total_turns} correct words!"
        points = total_turns * 10
        return award_points(id, db, points, em)
    # check if first letter is same as last letter
    if l != []:
        if l[-1][-1] != message.lower().strip()[0]:
            save(id, db)
            total_turns = doc["nr_of_turns"] - doc["nr_of_turns_left"]
            em = f"Your last word did not start with the last letter of mine. You lost, but you gave {total_turns} correct words!"
            points = total_turns * 10
            return award_points(id, db, points, em)
    l.append(message.lower().strip())
    answers.append(message.lower().strip())
    col.update_one({"user_id": id}, {"$set": {"user_answers": answers}})
    if nr_turns == 0:
        save(id, db)
        total_turns = doc["nr_of_turns"]+1
        em = f"I don't know any more {subject}! You've won! You gave {total_turns} correct words."
        points = total_turns * 10 + 50
        return award_points(id, db, points, em)
    word = get_next_word(letter, subject)
    for i in range(10):
        if word not in l:
            break
        word = get_next_word(letter, subject)
    if word in l or word is None:
        save(id, db)
        total_turns = doc["nr_of_turns"]+1
        em = f"I don't know any more {subject} ! You've won! You gave {total_turns} correct words."
        points = total_turns * 10 + 50
        return award_points(id, db, points, em)
    l.append(word)
    col.update_one({"user_id": id}, {"$set": {"words": l, "nr_of_turns_left": nr_turns-1}})
    return {"text": word}

def award_points(id, db, points, em):
    col = db.listbuilder
    update_state(col, id, "again")
    doc = col.find_one({"user_id": id})
    total_points = doc["points"]+points
    nr_played = doc["played"] + 1
    col.update_one({"user_id": id}, {"$set": {"points": total_points, "played": nr_played}})
    msg = f"{em} You gain {points} points. You now have {total_points} points."
    msg += utils.check_streak(id, col, col.find_one({"user_id": id})["day"], total_points)
    msg += ranking.get_ranking(id, db, "listbuilder")
    return {"text": f"{msg} Do you want to play again?", "quick_replies": quick_yes_no}

def save(id, db):
    # get data
    col = db.listbuilder
    doc = col.find_one({"user_id": id})
    dict = {}
    dict['subject'] = doc["subject"]
    dict['user_answers'] = doc["user_answers"]

    # insert data
    new_data = {'user_id': id, 'data': dict, 'game': 'listbuilder', 'processed': False}
    db.data.insert_one(new_data)

    # delete data
    clean(id, col)

def clean(id, col):
    col.update_one({"user_id": id}, {"$set": {"words": []}})
    col.update_one({"user_id": id}, {"$set": {"user_answers": []}})
    col.update_one({"user_id": id}, {"$set": {"nr_of_turns": 0}})
    col.update_one({"user_id": id}, {"$set": {"nr_of_turns_left": 0}})

def again(message, id, col, db):
    if "yes" in message.lower():
        doc = db.listbuilder.find_one({"user_id": id})
        db.listbuilder.update_one({"user_id": id}, {"$set": {"state": "initiate", 'again': doc['again']+1}})
        return initiate_user(message, id, col)
    else:
        return stop_game(id, db)

def game(message, id, db):
    #get state
    state = ""
    game_col = db.listbuilder
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
    elif state == "start":
        return start(message, id, game_col)
    elif state == "generate":
        return word_generator(message, id, game_col, db)
    elif state == "again":
        return again(message, id, game_col, db)
    
    update_state(game_col, id, "initiate")
    return {"text": "I did not understand you. Let's start again."}