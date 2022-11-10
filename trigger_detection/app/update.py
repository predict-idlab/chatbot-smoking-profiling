import threading
import mongoconnection
from determine_trigger.determine_trigger import determine_trigger

db = mongoconnection.get_db()

justonelie = {'What does your family look like?': 'family',
'What do you do in your free time?': 'activities',
'What are your hobbies?': 'activities',
'What makes you stressed?': 'stress',
'What makes you angry?': 'anger',
'What makes you sad?': 'sad',
'What are daily things you do at home?': 'activities',
'What are your priorities in life?': 'priorities',
'What are your smoking triggers?': 'triggers',
'Why did you start smoking?': 'smoking',
'What do you do when you visit a bar?': 'activities',
'Why do you want to stop smoking?': 'smoking',
'What type of beverages do you like to drink?': 'substance abuse',
'Who among your friends do you like to meet up with the most?': 'friends',
'What do you like to do with your friends?': 'activities',
'If the world were coming to an end, what would you like to do one more time?': 'activities',
'Who had the most impact in your life?': 'friends'
}

listbuilder = {'hobbies': 'activities',
'stress factors': 'stress',
'smoking triggers': 'triggers',
'family': 'family'
}

def update_triggers():
    threading.Timer(900, update_triggers).start()
    col = db.data
    if col.count_documents({'processed': False}) != 0:
        cursor = col.find({'processed': False})
        for doc in cursor:
            id = doc["user_id"]
            data = doc["data"]
            if doc["game"] == "justonelie":
                for option in data["user_options"]:
                    if option != data["user_lie"]:
                        subject = justonelie[data["user_question"]]
                        determine_trigger(id, db, option, subject)
            elif doc["game"] == "listbuilder":
                for answer in data["user_answers"]:
                    subject = listbuilder[data["subject"]]
                    determine_trigger(id, db, answer, subject)
            elif doc["game"] == "storybuilder":
                determine_trigger(id, db, doc["data"], "")
            elif doc["game"] == "whereami":
                determine_trigger(id, db, doc["data"], "location")
            else:
                determine_trigger(id, db, data, "")
            col.update_one({"_id": doc["_id"]}, {"$set": {"processed": True}})


update_triggers()