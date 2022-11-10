from transformers import AutoTokenizer, AutoModelWithLMHead, pipeline
import re
import random
from datetime import date
import StoryBuilder.script as script
import utils
import ranking
  
tokenizer = AutoTokenizer.from_pretrained("pranavpsv/genre-story-generator-v2")

model = AutoModelWithLMHead.from_pretrained("pranavpsv/genre-story-generator-v2")

story_gen = pipeline("text-generation", "pranavpsv/genre-story-generator-v2")

list_genres = ['superhero', 'action', 'drama', 'horror', 'thriller', 'sci_fi']

quick_yes_no = [{"content_type":"text", "title": "Yes", "payload": "yes"}, {"content_type":"text", "title": "No", "payload": "no"}]

def generate_story(message, id, db):
    col = db.storybuilder
    doc = col.find_one({"user_id": id})
    story = ""
    counter = doc["counter"] + 1
    if message.lower() == "done":
        points = (counter-1)*10+30
        col.update_one({"user_id": id}, {"$set": {"counter": 0}})
        if counter > 0:
            return award_points(id, db, points, f"You have given {int(counter-1)} additions to the story.")
        else:
            points = 0
            return award_points(id, db, points, f"You have given {int(counter-1)} additions to the story, so you gain no points.")

    story = doc["story"] + " " + message.strip()
    story = story[-300:].replace("[", " ").replace("]", " ")
    genre = col.find_one({"user_id": id})['genre']
    raw = story_gen(f"<BOS> <{genre}> {story.strip()}")[0]['generated_text']
    clean = re.sub(r'\<BOS\> \<.+\> ', '', raw).strip()
    new = re.sub(story.strip(),'',clean).strip()
    response = ' '.join(new.split()[:50])

    col.update_one({"user_id": id}, {"$set": {"story": f"{message.strip()} {response}", "counter": counter}})
    return {"text": response}

def start_script(id, db, subject, data):
    em = "[Be aware! You entered a partly scripted story. When it is your turn to add something to the story, answer with facts about yourself. You're the character in this story.]\n\n"
    genre = db.storybuilder.find_one({"user_id": id})['genre']
    l = script.begin_script(db, id, genre, subject, data)
    (s, qr, l) = script.script_story("", id, db, l)
    db.storybuilder.update_one({"user_id": id}, {"$set": {"script":l}})
    if qr == []:
        return {"text": em+s}
    return {"text": em+s, "quick_replies": qr}

def run_script(message, id, db):
    doc = db.storybuilder.find_one({"user_id": id})
    l = doc["script"]
    counter = doc["counter"] + 1
    (s, qr, l) = script.script_story(message, id, db, l)
    if l == None:
        update_state(db.storybuilder, id, "game")
        db.storybuilder.update_one({"user_id": id}, {"$set": {"counter": counter, "story": s}})
        return {"text": s+" [The scripted part of the story is done! Now, continue the story with the chatbot or send 'done' to stop the story.]"}
    db.storybuilder.update_one({"user_id": id}, {"$set": {"script":l, "counter": counter, "story": s}})
    if qr == []:
        return {"text": s}
    return {"text": s, "quick_replies": qr}

def determine_genre(id, col):
    # set state to genre
    update_state(col, id, "genre")
    genres = random.sample(list_genres,4)
    text = "What genre do you want? \n"
    quick_replies = []
    for i, genre in enumerate(genres):
        text += f"({i+1}) {genre} \n"
        quick_replies.append({"content_type": "text", "title": genre, "payload": genre})
    return {"text": text, "quick_replies": quick_replies}

def set_genre(message, id, col):
    if message not in list_genres:
        return determine_genre(id, col)
    # set genre in database 
    col.update_one({"user_id": id}, {"$set": {"genre": message}})
    # set state to turn
    update_state(col, id, "turn")
    return {"text": 'Type "done" if you want to stop playing. Do you want to start with writing a beginning of the story? \n\n[Answering no on this question can lead into the hidden feature if certain conditions are met.]', "quick_replies": quick_yes_no}

def turn(message, id, db):
    col = db.storybuilder
    if "yes" in message.lower():
        update_state(col, id, "user_prompt")
        return {"text": "Go ahead. Start with an event that happened in your life."}
    elif (db.questions.count_documents({"user_id": id}) != 0):
        update_state(col, id, "script")
        doc = None
        modules = random.sample(["activities", "smoking cues"], 2)
        for module in modules:
            doc = db.questions.find_one({"user_id": id, "module": module})
            if doc != None:
                db.storybuilder.update_one({"user_id":id}, {"$set": {"question_id": doc["_id"]}})
                return start_script(id, db, doc["module"], doc["data"])
    update_state(col, id, "game")
    return {"text": generate_prompt()}

def user_prompt(message, id, col, db):
    # insert data
    new_data = {'user_id': id, 'data': message, 'game': 'storybuilder', 'processed': False}
    db.data.insert_one(new_data)

    update_state(col, id, "game")
    return generate_story(message, id, db)

def generate_prompt():
    prompts = open(f'StoryBuilder/data/prompts.txt', mode='r', encoding="utf-8")
    return random.sample(prompts.read().splitlines(), 1)[0]

def stop_game(id, db):
    db.storybuilder.update_one({"user_id": id}, {"$set": {"story": "", 'dict': {}, "subject": "", "script": [], "options": [], "counter": 0}})
    update_state(db.storybuilder, id, "initiate")
    update_state(db.user, id, "choose_game")
    return {"text": "Stopped the game. Answer me if you want to play another game.\n\nSend \n'#': smoking registration \n'##': smoking registration (now) \n'ranking': leaderboard\n'help': more information"}

def award_points(id, db, points, em):
    col = db.storybuilder
    update_state(col, id, "again")
    doc = col.find_one({"user_id": id})
    total_points = doc["points"]+points
    nr_played = doc["played"] + 1
    col.update_one({"user_id": id}, {"$set": {"points": total_points, "played": nr_played}})
    msg = f"{em} You gain {points} points. You now have {total_points} points."
    msg += utils.check_streak(id, col, col.find_one({"user_id": id})["day"], total_points)   
    col.update_one({"user_id": id}, {"$set": {"story": "", 'dict': {}, "subject": "", "script": [], "options": []}})
    msg += ranking.get_ranking(id, db, "storybuilder")
    return {"text": f"{msg} Do you want to play again?", "quick_replies": quick_yes_no}

def again(message, id, col, db):
    if "yes" in message.lower():
        doc = db.storybuilder.find_one({"user_id": id})
        db.storybuilder.update_one({"user_id": id}, {"$set": {"state": "initiate", 'again': doc['again']+1}})
        return determine_genre(id, col)
    else:
        return stop_game(id, db)

def create_new_game(col, userid, state):
    new_user = {'user_id': userid, 'state': state, 'points': 0, 'counter': 0, 'day': date.today().strftime("%d-%m-%Y"), 'streak': 0, 'dict': {}, "story": "", "subject": "", "script": [], "options": [], "played": 0, "stopped": 0, "again": 0, 'all_streaks': []}
    col.insert_one(new_user)
    return utils.explanation('storybuilder')

def update_state(col, userid, state):
    query = {"user_id": userid}
    newvalue = {"$set": {"state": state}}
    col.update_one(query, newvalue)

def game(message, id, db):
    #get state
    state = ""
    game_col = db.storybuilder
    doc = game_col.find_one({"user_id": id})
    if doc == None:
        return create_new_game(game_col, id, "initiate")
    else:
        state = doc['state']

    # if message is stop, quit game
    if message.lower() == "stop":
        game_col.update_one({"user_id": id}, {"$set": {'stopped': doc['stopped']+1}})
        return stop_game(id, db)

    if state == 'initiate':
        return determine_genre(id, game_col)
    elif state == 'genre':
        return set_genre(message, id, game_col)
    elif state == "turn":
        return turn(message, id, db)
    elif state == "user_prompt":
        return user_prompt(message, id, game_col, db)
    elif state == 'game':
        return generate_story(message, id, db)
    elif state == 'script':
        return run_script(message, id, db)
    elif state == 'again':
        return again(message, id, game_col, db)

    update_state(game_col, id, "initiate")
    return {"text": "I did not understand you. Let's start again."}