import random

qr_options = [{"content_type":"text", "title": "Always", "payload": 1}, {"content_type":"text", "title": "Usually", "payload": 0.8}, 
        {"content_type":"text", "title": "Often", "payload": 0.6}, {"content_type":"text", "title": "Sometimes", "payload": 0.4},
        {"content_type":"text", "title": "Rarely", "payload": 0.2}, {"content_type":"text", "title": "Never", "payload": 0}]

types = ["negative emotions", "stress", "general", "activities", "smoking cues", "substance abuse", "location", "moment of day/week"]

def next_line(id, db, l, s):
    sen = l[0].replace('$','"')
    s += sen.replace('#', '\n')
    subs = l[1]
    subject = l[2]
    op = l[3]
    doc = db.storybuilder.find_one({"user_id": id})
    dic = doc["dict"]
    
    subj = subject
    if subs != "-":
        fill = []
        for sub in subs.split(","):
            if (sub in types) and (subject == "options"):
                subj = sub
            f = ""
            if sub in dic:
                f = dic[sub]
            else:
                profile = db.profile.find_one({"user_id": id})
                f = profile[sub]
            fill.append(f)
        s = s % tuple(fill)
    
    if subject == "-":
        return (s, [], None)
    
    db.storybuilder.update_one({"user_id": id}, {"$set": {"subject": subj, "options": []}})
    
    profile = db.profile.find_one({"user_id": id})
    if subject in profile:
        s = s.split("[")[0]
        if profile[subject] in ["True", "False"]:
            s += " not" if profile[subject] else ""
        else:
            s += str(profile[subject])
        dic[subject] = profile[subject]
        db.storybuilder.update_one({"user_id": id}, {"$set": {"dict": dic}})
        return next_line(id, db, l[4:], s)
    if subject != "-":
        if op != "-" or subject == "options":
            qr = qr_options
            options = [0,0.2,0.4,0.6,0.8,1]
            if subject != "options":
                options = op.split("/")
                qr = []
                for option in options:
                    qr.append({"content_type": "text", "title": option, "payload": option})
            db.storybuilder.update_one({"user_id": id}, {"$set": {"options": options, "qr": qr}})
            return (s, qr, l[4:])
    return (s, [], l[4:])

def script_story(message, id, db, l):
    doc = db.storybuilder.find_one({"user_id": id})
    dic = doc["dict"]
    options = doc["options"]
    if doc["subject"] in types:
        ans = message
        try:
            ans = float(message)
        except:
            return ("Choose one of the options.", doc["qr"], l)
        if ans not in options:
            return ("Choose one of the options.", doc["qr"], l)
        duo = db.triggers.find_one({"user_id": id})[doc["subject"]]
        tr = duo["triggers"]
        level = duo["confidence_levels"]
        tr.append(dic[doc["subject"]])
        level.append(ans)
        db.triggers.update_one({"user_id": id}, {"$set": {doc["subject"]: {"triggers": tr, "confidence_levels": level}}})
        db.questions.delete_one({"_id":doc["question_id"]})
    elif doc["subject"] != "":
        ans = message
        if options != []:
            if message not in options:
                return ("Choose one of the options.", doc["qr"], l)
            elif message in ["True", "False"]:
                if message == "True":
                    ans = True
                else:
                    ans = False
        else:
            try:
                ans = int(message)
            except:
                return ("Enter a number, and only a number.", [], l)
        dic["subject"] = ans
        db.storybuilder.update_one({"user_id": id}, {"$set": {"dict": dic}})
        db.profile.update_one({"user_id": id}, {"$set": {doc["subject"]: ans}})
    if l == []:
        return ("", [], None)
    return next_line(id, db, l, "")

def begin_script(db, id, genre, subject, data):
    sentences = open(f'StoryBuilder/data/{subject}.txt', mode='r', encoding="utf-8")
    l = sentences.read().splitlines()
    scr = [el.split("\t") for el in l]
    choices = []
    for sc in scr:
        if sc[0] == genre:
            choices.append(sc)
    option = [x for x in random.sample(choices, 1)[0] if x]
    dic = {}
    dic[subject] = data
    db.storybuilder.update_one({"user_id": id}, {"$set": {"dict": dic}})
    return option[1:]