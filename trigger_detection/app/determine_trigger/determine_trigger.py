import spacy
import string
from datetime import datetime, date, timedelta, time
from transformers import AutoTokenizer, AutoModelForSequenceClassification
from transformers import pipeline

tokenizer = AutoTokenizer.from_pretrained("bhadresh-savani/distilbert-base-uncased-emotion")
model = AutoModelForSequenceClassification.from_pretrained("bhadresh-savani/distilbert-base-uncased-emotion")

qr = [{"content_type":"text", "title": "Always", "payload": 1}, {"content_type":"text", "title": "Usually", "payload": 0.8}, 
        {"content_type":"text", "title": "Often", "payload": 0.6}, {"content_type":"text", "title": "Sometimes", "payload": 0.4},
        {"content_type":"text", "title": "Rarely", "payload": 0.2}, {"content_type":"text", "title": "Never", "payload": 0}]

types = ["negative emotions", "stress", "general", "activities", "smoking cues", "substance abuse", "location", "moment of day/week"]

def create_new_user(col, userid):
    # create user
    new_user = {'user_id': userid}
    for type in types:
        new_user[type] = {"triggers": [], "confidence_levels": []}
    col.insert_one(new_user)

def flatten(t):
    return [item for sublist in t for item in sublist]

def get_data(subject):
    file = f'determine_trigger/data/{subject}.txt'
    return list(filter(None, map(lambda s: s.strip(), flatten([x.split('\t') for x in open(file).readlines()]))))

def get_similarities(message, subject):
    nlp = spacy.load("en_core_web_lg")
    doc_before = nlp(message)
    doc1 = nlp((' '.join([str(t) for t in doc_before if not t.is_stop])).translate(str.maketrans('','',string.punctuation)))
    l = get_data(subject)
    labels = {}
    for item in l:
        item_uncleaned = nlp(item)
        doc2 = nlp(' '.join([str(t) for t in item_uncleaned if not t.is_stop]))
        #print(doc1, "<->", doc2, doc1.similarity(doc2))
        if doc1.similarity(doc2) > 0.70:
            labels[item] = doc1.similarity(doc2)
    if labels != {}:
        m = max(labels)
        return (m, labels[m])
    else:
        return ('', 0)

def get_similarities_word_per_word(message, subject):
    nlp = spacy.load("en_core_web_lg")
    doc_before = nlp(message)
    doc1 = nlp((' '.join([str(t) for t in doc_before if not t.is_stop])).translate(str.maketrans('','',string.punctuation)))
    l = get_data(subject)
    labels = {}
    for token in doc1:
        for item in l:
            item_uncleaned = nlp(item)
            doc2 = nlp(' '.join([str(t) for t in item_uncleaned if not t.is_stop]))
            #print(doc1, "<->", doc2, doc1.similarity(doc2))
            if token.similarity(doc2) > 0.75:
                labels[item] = token.similarity(doc2)

    return labels

def emotion_detection(message):
    classifier = pipeline("text-classification",model='bhadresh-savani/distilbert-base-uncased-emotion', return_all_scores=True)
    prediction = classifier(message, )
    return prediction

def smoking_cues_detection(message):
    return False

def substance_abuse_detection(message):
    if any(word in message.lower() for word in ['alcohol', 'drugs', 'beer', 'beers', 'cocktail', 'cocktails', 'wine', 'cider', 'gin', 'brandy', 'whiskey', 
                                                'vodka', 'tequila', 'liqueurs', 'rum', 'soju', 'absinthe', 'bourbon', 'vermouth', 'cognac', 'mead', 'saké', 
                                                'everclear', 'cannabis', 'opiods', 'medication', 'heroin', 'LSD', 'depressants', 'hallucinogens', 'dissociatives', 
                                                'stimulants', 'coffee']):
        return True
    return False

def check_trigger_not_already_added(id, db, doc, trigger):
    for t in types:
        triggers = doc[t]["triggers"]
        if trigger in triggers:
            return False
    
    cursor = db.questions.find({"user_id": id})
    for c in cursor:
        if c["data"] == trigger:
            return False
    return True

def determine_trigger(id, db, message, subject):
    confidence_level = 1
    col = db.triggers
    doc = col.find_one({"user_id": id})
    if doc == None:
        create_new_user(col, id)
        doc = col.find_one({"user_id": id})

    if check_trigger_not_already_added(id, db, doc, message):
        if subject == 'triggers':
            tr = doc["general"]["triggers"]
            level = doc["general"]["confidence_levels"]
            tr.append(message)
            level.append(confidence_level)
            col.update_one({"user_id": id}, {"$set": {"general": {"triggers": tr, "confidence_levels": level}}})
        
        elif subject == 'activities':
            activity = message
            question = {'text': f'If you are doing the following activity: "{activity}", do you smoke at the same time? Or do you smoke as a break in the activity?',
            "quick_replies": qr}
            db.questions.insert_one({"user_id": id, "question": question, "subject": subject, "module": "activities", "data": activity, "status": False})
        
        elif subject in ['family', 'friends']:
            question = {'text': f'If you are with the person mentioned here "{message}", do you smoke in the presence of this person?', "quick_replies": qr}
            db.questions.insert_one({"user_id": id, "question": question, "subject": subject, "module": "smoking cues", "data": message, "status": False})
        
        elif subject == 'location':
            loc = message["user_location"]
            timestamp = message["time"]
            d = db.locations.find_one({"location": loc, "user_id": id})
            stamps = [timestamp]
            added = False
            if d == None:
                db.locations.insert_one({"location": loc, "timestamps": stamps, "added": False, "user_id": id})
            else:
                stamps = d["timestamps"] + [timestamp]
                added = d["added"]
                db.locations.update_one({"location": loc}, {"$set": {"timestamps": stamps}})
            
            counter = 0
            total = 0
            if added is False and len(stamps) > 2:
                for t in stamps:
                    day = t.strftime("%d-%m-%Y")
                    cursor = db.smoking_events.find({"date": day, "user_id": id})
                    for event in cursor:
                        total += 1
                        difference = event["timestamp"] - t
                        if timedelta(minutes=-10) < difference < timedelta(minutes=10):
                            counter += 1
                ratio = 0
                if total != 0:
                    ratio = counter/total
                
                if ratio > 0.1:
                    duo = doc['location']
                    tr = duo["triggers"] + [loc]
                    level = duo["confidence_levels"] + [ratio]
                    col.update_one({"user_id": id}, {"$set": {"location": {"triggers": tr, "confidence_levels": level}}})
                    db.locations.update_one({"location": loc}, {"$set": {"added": True}})

        elif subject in ['anger', 'sad']:
            question = {'text': f'If your emotions get too much and the following happens: "{message}", does the urge to smoke get worse?', "quick_replies": qr}
            db.questions.insert_one({"user_id": id, "question": question, "subject": subject, "module": "negative emotions", "data": message, "status": False})
        
        elif subject == 'stress':
            question = {'text': f'If your emotions get too much and the following happens: "{message}", does the urge to smoke get worse?', "quick_replies": qr}
            db.questions.insert_one({"user_id": id, "question": question, "subject": subject, "module": subject, "data": message, "status": False})
        
        else:
            if smoking_cues_detection(message):
                question = {'text': f'If you encounter the smoking cue mentioned here "{message}", do you smoke after seeing this smoking cue?', "quick_replies": qr}
                db.questions.insert_one({"user_id": id, "question": question, "subject": subject, "module": "smoking cues", "data": message, "status": False})

            if substance_abuse_detection(message) or subject=='substance abuse':
                question = {'text': f'If you use the following substance mentioned here "{message}", does the urge to smoke get worse?', "quick_replies": qr}
                db.questions.insert_one({"user_id": id, "question": question, "subject": subject, "module": "substance abuse", "data": message, "status": False})

            emotions = emotion_detection(message)[0]

            emo = False
            score = 0
            for emotion in emotions:
                if emotion['label'] in ['anger', 'sadness', 'fear']:
                    if (emotion['score'] > 0.9) and (emotion['score'] > score):
                        emo = True
                        score = emotion['score']
            
            if emo:
                question = {'text': f'If your emotions get too much and the following happens: "{message}", does the urge to smoke get worse?', "quick_replies": qr}
                db.questions.insert_one({"user_id": id, "question": question, "subject": subject, "module": "negative emotions", "data": message, "score": score, "status": False})

            for trigger in ['stress', 'anger']:
                sim = get_similarities(message, trigger)
                module = trigger
                if trigger != 'stress':
                    module = "negative emotions"
                if sim[0] != '':
                    question = {'text': f'If your emotions get too much and the following happens: "{sim[0]}", does the urge to smoke get worse?', "quick_replies": qr}
                    db.questions.insert_one({"user_id": id, "question": question, "subject": subject, "module": module, "data": sim[0], "score": sim[1],"status": False})