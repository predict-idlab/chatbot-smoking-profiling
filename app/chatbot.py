import JustOneLie.justonelie as justonelie
import StoryBuilder.storybuilder as storybuilder
import ListBuilder.listbuilder as listbuilder
import WhereAmI.whereami as whereami
import registration
import mongoconnection
import utils
import ranking
from datetime import datetime, timedelta
import random

#uvicorn chatbot:app --reload

games = ['JustOneLie', 'StoryBuilder', 'ListBuilder', 'WhereAmI']
quick_yes_no = [{"content_type":"text", "title": "Yes", "payload": "yes"}, {"content_type":"text", "title": "No", "payload": "no"}]

def update_state(col, userid, state):
    query = {"user_id": userid}
    newvalue = {"$set": {"state": state}}
    col.update_one(query, newvalue)

def create_new_user(db, userid, state):
    # create user
    new_user = {'user_id': userid, 'state': state, 'timestamp': datetime.now()}
    db.user.insert_one(new_user)
    db.profile.insert_one({'user_id': userid})

def play_game(message, game, id, db):
    # states: justonelie, listbuilder, storybuilder, whereami, charactercreator, other
    if game == "justonelie":
        return justonelie.game(message, id, db)
    elif game == "storybuilder":
        return storybuilder.game(message, id, db)
    elif game == "listbuilder":
        return listbuilder.game(message, id, db)
    elif game == "whereami":
        return whereami.game(message, id, db)

    return choose_game(db, id)
    
def choose_game(db, id):
    col = db.user
    text = "Which game do you want to play? \n"
    update_state(col, id, "choose_game")
    quick_replies = []
    random.shuffle(games)
    for i, game in enumerate(games): 
        text += f"({i+1}) {game} \n"
        quick_replies.append({"content_type": "text", "title": game, "payload": game})

    # make users choose different games
    doc = col.find_one({"user_id": id})
    start = doc['timestamp']
    now = datetime.now() + timedelta(hours=2)
    if now > (start + timedelta(days=5)):
        # check which games the player did not play yet
        l = []
        if db.justonelie.count_documents({"user_id": id}) == 0:
            l.append('JustOneLie')
        if db.listbuilder.count_documents({"user_id": id}) == 0:
            l.append('ListBuilder')
        if db.storybuilder.count_documents({"user_id": id}) == 0:
            l.append('StoryBuilder')
        else:
            feature = db.profile.find_one({"user_id": id})
            if len(feature) < 4:
                text += "\n\nYou have not yet discovered the hidden feature in StoryBuilder. Can you find it?"
        if db.whereami.count_documents({"user_id": id}) == 0:
            l.append('WhereAmI')
        
        if l != []:
            text += "\n\n"
            for el in l:
                text += f"You have not yet played: {el}.\n" 
            text += "\nTry it out!"
    return {"text": text, "quick_replies": quick_replies}

def respond(message, id, timestamp):
    db = mongoconnection.get_db()
    # check if new user
    state = ""
    user_col = db.user
    doc = user_col.find_one({"user_id": id})
    if doc == None:
        create_new_user(db, id, "start")
        state = "start"
    else:
        state = doc['state']
    
    # log user and timestamp
    if timestamp is not None:
        db.log.insert_one({"user_id": id, "timestamp": timestamp, "message": message})
    
    if message[0] == '#':
        user_col.update_one({"user_id": id}, {"$set": {"registration": "start"}})
        user_col.update_one({"user_id": id}, {"$set": {"last_state": state}})
        db.temp.update_one({"user_id": id}, {"$set": {"state": "today", 'counter': 2}})
        if message ==  '##':
            update_state(user_col, id, "registration_now")
            state = "registration_now"
        else:
            update_state(user_col, id, "registration")
            state = "registration"
    
    if message.lower().strip() == 'help':
        game = "general"
        if state == "games":
            game = doc["game"]
            state = "initiate"
            if game == "justonelie":
                db.justonelie.update_one({"user_id": id}, {"$set": {"state": state}})
            elif game == "listbuilder":
                db.listbuilder.update_one({"user_id": id}, {"$set": {"state": state}})
            elif game == "storybuilder":
                db.storybuilder.update_one({"user_id": id}, {"$set": {"state": state}})
            else:
                db.whereami.update_one({"user_id": id}, {"$set": {"state": state}})
        return utils.explanation(game)
    
    if message.lower().strip() == 'ranking':
        if state != "games":
            return {"text": ranking.get_general_ranking(id, db)}
        return {"text": ranking.get_ranking(id, db, doc["game"])}

    # select state
    if state == "start":
        update_state(user_col, id, "confirm")
        return {"text": "Hi! My name is Ota! What is your name?"}
    elif state == "confirm":
        update_state(user_col, id, "name")
        user_col.update_one({"user_id": id}, {"$set": {"name": message}})
        db.profile.update_one({"user_id": id}, {"$set": {"name": message}})
        return {"text": f"Is the name '{message}' correct?'", "quick_replies": quick_yes_no}
    elif state == "name":
        if message.lower().strip() == "yes":
            update_state(user_col, id, "explanation")
            return {"text": f"Nice to meet you, {doc['name']}!"}
        else:
            update_state(user_col, id, "confirm")
            return {"text": "Alright, what is your name?"}
    elif state == "explanation":
        update_state(user_col, id, "general")
        return utils.explanation("general")
    elif state == "general":
        return choose_game(db, id)
    elif state == "choose_game":
        game = message.lower()
        user_col.update_one({"user_id": id}, {"$set": {"game": game}})
        update_state(user_col, id, "games")
        last_message = play_game("", game, id, db)
        user_col.update_one({"user_id": id}, {"$set": {"last_message": last_message}})
        return last_message
    elif state == "games":
        doc = user_col.find_one({"user_id": id})
        last_message = play_game(message, doc["game"], id, db)
        user_col.update_one({"user_id": id}, {"$set": {"last_message": last_message}})
        return last_message
    elif state == "registration":
        return registration.register(message, id, db)
    elif state == "registration_now":
        return registration.register_now(message, id, db)
    return {'text': "I did not understand you."}