import random
import spacy
import string
from datetime import date, datetime, timedelta
from transformers import AutoTokenizer, AutoModelForSequenceClassification
from transformers import pipeline
import utils
import ranking

tokenizer = AutoTokenizer.from_pretrained("bhadresh-savani/distilbert-base-uncased-emotion")
model = AutoModelForSequenceClassification.from_pretrained("bhadresh-savani/distilbert-base-uncased-emotion")

placeholders = ["I see (a) %s.", "There is (a) %s.", "There is (a) %s here.", "I see (a) %s over there.", "In this place, there is (a) %s."]

quick_yes_no = [{"content_type":"text", "title": "Yes", "payload": "yes"}, {"content_type":"text", "title": "No", "payload": "no"}]

def create_new_game(col, userid, state):
    new_user = {'user_id': userid, 'state': state, 'points': 0, 'guesses': 0, "place": "", "already_guessed": [], "hints": [], 'day': date.today().strftime("%d-%m-%Y"), 'streak': 0, 'played': 0, "stopped": 0, "again": 0, 'all_streaks': []}
    col.insert_one(new_user)
    return utils.explanation('whereami')

def update_state(col, userid, state):
    query = {"user_id": userid}
    newvalue = {"$set": {"state": state}}
    col.update_one(query, newvalue)

def stop_game(id, db):
    clean(id, db.whereami)
    update_state(db.whereami, id, "initiate")
    update_state(db.user, id, "choose_game")
    return {"text": "Stopped the game. Answer me if you want to play another game.\n\nSend \n'#': smoking registration \n'##': smoking registration (now) \n'ranking': leaderboard\n'help': more information"}

def get_place():
    file = f'WhereAmI/data/places.txt'
    l = open(file).readlines()
    places = [x.split('\t')[0] for x in l]
    descriptions = [x.split('\t')[1] for x in l]
    nr = random.randint(0, len(places)-1)
    place = places[nr].strip()
    description = descriptions[nr].strip().split(', ')
    return place, description

def initiate_user(message, id, col):
    update_state(col, id, "turn")
    return {"text": "Alright! Do you want to start with the description?", "quick_replies": quick_yes_no}

def turn(message, id, col):
    if "yes" in message.lower():
        return user_start(id, col)
    else:
        return chatbot_start(id, col)

def chatbot_start(id, col):
    update_state(col, id, "check")
    place, descriptions = get_place()
    col.update_one({"user_id": id}, {"$set": {"place": place}})
    col.update_one({"user_id": id}, {"$set": {"descriptions": descriptions}})
    description = generate_description(id, col, descriptions)["text"]
    return {"text": f"[If you don't know any guesses anymore, or you want to stop playing, send 'stop'. Answer with one or two words.]\n\n {description}"}

def generate_description(id, col, descriptions):
    description = random.choice(descriptions)
    descriptions.remove(description)
    col.update_one({"user_id": id}, {"$set": {"descriptions": descriptions}})
    text = random.choice(placeholders) % description
    return {"text": text}

def check(message, id, db):
    col = db.whereami
    doc = col.find_one({"user_id": id})
    place = doc["place"]
    guesses = doc["guesses"]+1
    if place == message.lower().strip():
        em = "Congratulations! You guessed the place."
        points = 100 - guesses*10
        if points < 0:
            points = 0
        clean(id, col)
        return award_points(id, db, points, em)
    col.update_one({"user_id": id}, {"$set": {"guesses": guesses}})
    descriptions = doc["descriptions"]
    if len(descriptions) <= 1:
        em = f"You failed to guess the place. The place was {place}."
        points = 0
        clean(id, col)
        return award_points(id, db, points, em)
    return generate_description(id, col, descriptions)

def user_start(id, col):
    update_state(col, id, "guess")
    return {"text": "So, where are you? What do you see around you?"}

def get_guess(hints, already_guessed):
    nlp = spacy.load("en_core_web_lg")
    file = f'WhereAmI/data/places.txt'
    l = open(file).readlines()
    places = [x.split('\t')[0] for x in l]
    descriptions = [x.split('\t')[1] for x in l]
    descriptions = [x.strip().split(', ') for x in descriptions]
    labels = {}
    
    for i, place in enumerate(places):
        if place not in already_guessed:
            labels[place] = 0
            for hint in hints:
                doc_before = nlp(hint)
                doc1 = nlp((' '.join([str(t) for t in doc_before if not t.is_stop])).translate(str.maketrans('','',string.punctuation)))    
                value = 0
                for item in descriptions[i]:
                    item_uncleaned = nlp(item)
                    doc2 = nlp(' '.join([str(t) for t in item_uncleaned if not t.is_stop]))
                    #print(doc1, "<->", doc2, doc1.similarity(doc2))
                    sim = doc1.similarity(doc2)
                    if value < sim:
                        value = sim
                
                labels[place] += value
    
    guess = max(labels, key=labels.get)
    if labels[guess] < len(hints)*0.5:
        return None

    return guess

def guess(message, id, col, db):
    doc = col.find_one({"user_id": id})
    already_guessed = doc["already_guessed"]
    hints = doc["hints"]
    if len(already_guessed) > 4 or len(hints) > 6:
        update_state(col, id, "confirm")
        return {"text": "I can't guess where you are... Where are you?"}
    hints.append(message)
    guess = get_guess(hints, already_guessed)
    col.update_one({"user_id": id}, {"$set": {"hints": hints}})
    if guess == None:
        return {"text": "I don't know. Give me another hint."}
    already_guessed.append(guess)
    col.update_one({"user_id": id}, {"$set": {"already_guessed": already_guessed}})
    update_state(col, id, "guess_check")
    return {"text": f"Is it a {guess}?", 
    "quick_replies": [{"content_type":"text", "title": "True", "payload": "true"}, {"content_type":"text", "title": "False", "payload": "false"}]}

def guess_check(message, id, col, db):
    doc = col.find_one({"user_id": id})
    hints = doc["hints"]
    if message == 'true':
        em = "I guessed it."
        points = 50 + len(hints)*20
        save(id, db)
        return award_points(id, db, points, em)
    update_state(col, id, "guess")
    return {"text": "Okay, give me another hint."}

def confirm(message, id, col, db):
    doc = col.find_one({"user_id": id})
    already_guessed = doc["already_guessed"]
    already_guessed.append(message.lower().strip())
    hints = doc["hints"]
    col.update_one({"user_id": id}, {"$set": {"already_guessed": already_guessed}})
    em = "I could not deduce the place."
    points = 100 + len(hints)*20
    save(id, db)
    return award_points(id, db, points, em)

def award_points(id, db, points, em):
    col = db.whereami
    update_state(col, id, "again")
    doc = col.find_one({"user_id": id})
    total_points = doc["points"]+points
    nr_played = doc["played"] + 1
    col.update_one({"user_id": id}, {"$set": {"points": total_points, "played": nr_played}})
    msg = f"{em} You gain {points} points. You now have {total_points} points."
    msg += utils.check_streak(id, col, col.find_one({"user_id": id})["day"], total_points) 
    msg += ranking.get_ranking(id, db, "whereami")  
    return {"text": f"{msg} Do you want to play again?", "quick_replies": quick_yes_no}

def again(message, id, col, db):
    if "yes" in message.lower():
        doc = db.whereami.find_one({"user_id": id})
        db.whereami.update_one({"user_id": id}, {"$set": {"state": "initiate", 'again': doc['again']+1}})
        return initiate_user(message, id, col)
    else:
        return stop_game(id, db)

def save(id, db):
    # get data
    col = db.whereami
    doc = col.find_one({"user_id": id})
    dic = {}
    dic['user_location'] = doc["already_guessed"][-1]
    dic['time'] = datetime.now() + timedelta(hours=2)

    # insert data
    new_data = {'user_id': id, 'data': dic, 'game': 'whereami', 'processed': False}
    db.data.insert_one(new_data)

    # delete data
    clean(id, col)

def clean(id, col):
    col.update_one({"user_id": id}, {"$set": {'guesses': 0}})
    col.update_one({"user_id": id}, {"$set": {"place": ""}})
    col.update_one({"user_id": id}, {"$set": {"already_guessed": []}})
    col.update_one({"user_id": id}, {"$set": {"hints": []}})

def game(message, id, db):
    #get state
    state = ""
    game_col = db.whereami
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
        return turn(message, id, game_col)
    elif state == "check":
        return check(message, id, db)
    elif state == "guess":
        return guess(message, id, game_col, db)
    elif state == "guess_check":
        return guess_check(message, id, game_col, db)
    elif state == "confirm":
        return confirm(message, id, game_col, db)
    elif state == "again":
        return again(message, id, game_col, db)
    
    update_state(game_col, id, "initiate")
    return {"text": "I did not understand you. Let's start again."}