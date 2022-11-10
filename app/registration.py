from datetime import datetime, date, timedelta, time
import chatbot

quick_yes_no = [{"content_type":"text", "title": "Yes", "payload": "yes"}, {"content_type":"text", "title": "No", "payload": "no"}]

def update_state(col, userid, state, el):
    query = {"user_id": userid}
    newvalue = {"$set": {el: state}}
    col.update_one(query, newvalue)

def create_new_temp(col, userid, state):
    now = datetime.now()
    new_temp = {'user_id': userid, 'state': state, 'timestamp': now, 'date': now.strftime("%d-%m-%Y"), 'time': now.strftime("%H:%M:%S"), 'counter': 2}
    col.insert_one(new_temp)

def create_smoking_event(db, userid, timestamp, date, time):
    new_smoking_event = {'user_id': userid, 'timestamp': timestamp, 'date': date, 'time': time}
    db.smoking_events.insert_one(new_smoking_event)

def determine_day(message, id, db):
    state = ""
    doc = db.temp.find_one({"user_id": id})
    if doc == None:
        create_new_temp(db.temp, id, "today")
        state = "today"
    else: 
        state = doc['state']
    
    if state == "today":
        update_state(db.temp, id, "yesterday", "state")
        return {"text": "Did the smoking event happen today?", "quick_replies": quick_yes_no}
    elif state == "yesterday":
        if message.lower() == "yes":
            db.temp.update_one({"user_id": id}, {"$set": {"date": date.today().strftime("%d-%m-%Y")}})
            update_state(db.temp, id, "now", "state")
            return determine_time(message, id, db)
        update_state(db.temp, id, "earlier", "state")
        return {"text": "Did the smoking event happen yesterday?", "quick_replies": quick_yes_no}
    elif state == "earlier":
        counter = doc['counter']
        if message.lower() == "yes":
            day = date.today() - timedelta(days=counter-1)
            db.temp.update_one({"user_id": id}, {"$set": {"date": day.strftime("%d-%m-%Y")}})
            update_state(db.temp, id, "now", "state")
            return determine_time(message, id, db)
        else:
            day = date.today() - timedelta(days=counter)
            db.temp.update_one({"user_id": id}, {"$set": {"counter": counter+1}})
            return {"text": f"Did the smoking event happen on {day.strftime('%d-%m-%Y')}?", "quick_replies": quick_yes_no}
    else:
        return determine_time(message, id, db)

def determine_time(message, id, db):
    doc = db.temp.find_one({"user_id": id})
    state = doc['state']

    if state == "now":
        update_state(db.temp, id, "hour", "state")
        return {"text": "Did the smoking event happen at this time of the day?", "quick_replies": quick_yes_no}
    elif state == "hour":
        if message.lower() == "yes":
            now = datetime.now() + timedelta(hours=2)
            t = now.time()
            day = datetime.strptime(doc["date"], "%d-%m-%Y")
            event = t.strftime("%H:%M")+" "+day.strftime("%d-%m-%Y")
            db.temp.update_one({"user_id": id}, {"$set": {"time": t.strftime("%H:%M:%S")}})
            db.temp.update_one({"user_id": id}, {"$set": {"timestamp": day + timedelta(hours=t.hour, minutes=t.minute, seconds=t.second)}})
            update_state(db.temp, id, "verify", "state")
            return {"text": f"Did the smoking event happen on {event}?", "quick_replies": quick_yes_no}
        else:
            update_state(db.temp, id, "minutes", "state")
            return {"text": "At which hour did you smoke? Give a number from 0 to 23."}
    elif state == "minutes":
        try:
            number = int(message.strip())
            if number >= 0 and number < 24:
                update_state(db.temp, id, "confirm", "state")
                hour = time(hour=number)
                db.temp.update_one({"user_id": id}, {"$set": {"time": hour.strftime("%H:%M:%S")}})
                return {"text": "What were the minutes when you smoked? Give a number from 0 to 59."}
            else:
                return {"text": f"'{message}' is not a number from 0 to 23. Give a number from 0 to 23."}
        except ValueError:
            return {"text": f"'{message}' is not a number. Give a number from 0 to 23."}
    elif state == "confirm":
        try:
            number = int(message.strip())
            if number >= 0 and number < 60:
                update_state(db.temp, id, "verify", "state")
                hour = datetime.strptime(doc["time"], "%H:%M:%S")
                t = hour + timedelta(minutes=number)
                db.temp.update_one({"user_id": id}, {"$set": {"time": t.strftime("%H:%M:%S")}})
                day = doc["date"]
                event = t.strftime("%H:%M") + " " + day
                db.temp.update_one({"user_id": id}, {"$set": {"timestamp": datetime.strptime(doc["date"], "%d-%m-%Y") + timedelta(hours=t.hour, minutes=t.minute, seconds=t.second)}})
                return {"text": f"Did the smoking event happen on {event}?", "quick_replies": quick_yes_no}
            else:
                return {"text": f"'{message}' is not a number from 0 to 59. Give a number from 0 to 59."}
        except ValueError:
            return {"text": f"'{message}' is not a number. Give a number from 0 to 59."}
    elif state == "verify":
        update_state(db.temp, id, "today", "state")
        if message.lower() == "yes":
            save(id, db)
            return done(message, id, db)
        else:
            update_state(db.user, id, "start", "registration")
            return register(message, id, db)
    return {"text": "Something went wrong with the registration of the smoking event with determining the date."}

def done(message, id, db):
    doc = db.user.find_one({"user_id": id})
    update_state(db.temp, id, "today", "state")
    if doc["last_state"] == "games":
        update_state(db.user, id, "done", "registration")
        update_state(db.user, id, "registration", "state")
        return {"text": "Do you want to go back to your game?", 
        "quick_replies": quick_yes_no}
    else:
        update_state(db.user, id, "start", "registration")
        return chatbot.choose_game(db, id)

def save(id, db):
    doc = db.temp.find_one({"user_id": id})
    now = datetime.now()
    create_smoking_event(db, id, doc["timestamp"], doc["date"], doc["time"])
    db.temp.update_one({"user_id": id}, {"$set": {'state': "today", 'timestamp': now, 'date': now.strftime("%d-%m-%Y"), 'time': now.strftime("%H:%M:%S"), 'counter': 2}})


def register(message, id, db):
    doc = db.user.find_one({"user_id": id})
    state = doc['registration']

    if message.lower().strip() == "stop":
        return done(message, id, db)

    if state == "start":
        update_state(db.user, id, "valid", "registration")
        return {"text": "Do you want to register a smoking event?",
        "quick_replies": quick_yes_no}
    if state == "valid":
        if message.lower() == "yes":
            update_state(db.user, id, "determine day", "registration")
            return determine_day(message, id, db)
        else:
            return done(message, id, db)   
    if state == "done":
        last_state = doc["last_state"]
        update_state(db.user, id, last_state, "state")
        if message.lower() == "yes":
            r = f'The last message in the game was: "{doc["last_message"]["text"]}"'
            if "quick_replies" in doc["last_message"]:
                return {"text": r, "quick_replies": doc["last_message"]["quick_replies"]}
            return {"text": r}
        else:
            update_state(db.user, id, "start", "registration")
            chatbot.respond("stop", id, None)
            return chatbot.choose_game(db, id)
    if state == "determine day":
        return determine_day(message, id, db)
    return {"text": "Something went wrong with the registration of the smoking event."}

def register_now(message, id, db):
    doc = db.user.find_one({"user_id": id})
    state = doc['registration']

    if message.lower().strip() == "stop":
        done(message, id, db)

    if state == "start":
        doc_temp = db.temp.find_one({"user_id": id})
        if doc_temp == None:
            create_new_temp(db.temp, id, "today")
        update_state(db.user, id, "verify", "registration")
        now = datetime.now() + timedelta(hours=2)
        t = now.strftime("%H:%M:%S")
        day = now.strftime("%d-%m-%Y")
        event = t[:-3]+" "+day
        db.temp.update_one({"user_id": id}, {"$set": {"time": t, "date": day, "timestamp": now}})
        return {"text": f"Did the smoking event happen on {event}?", "quick_replies": quick_yes_no}
    if state == "verify":
        update_state(db.temp, id, "today", "state")
        if message.lower() == "yes":
            save(id, db)
            return done(message, id, db)
        else:
            update_state(db.user, id, "start", "registration")
            update_state(db.user, id, "registration", "state")
            return register(message, id, db)
    return {"text": "Something went wrong with the registration of the smoking event."}