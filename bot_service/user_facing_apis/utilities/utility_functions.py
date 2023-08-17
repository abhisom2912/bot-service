import json
import smtplib
from email.message import EmailMessage
import nltk
from datetime import datetime, timedelta

nltk.download('nps_chat')
posts = nltk.corpus.nps_chat.xml_posts()[:10000]
start_time = datetime(2020, 5, 17)
classifier = ''

# sending a mail whenever a user's data is uploaded succesfully
def send_mail(receiver_mail):
    # creates SMTP server
    server = smtplib.SMTP('smtp.gmail.com', 587)

    # start TLS for security
    server.starttls()

    # Authentication
    server.login("scarlettai.official@gmail.com", "KEY_GOES_HERE") # replace the email address with your email address

    # Composing the mail
    msg = EmailMessage()
    msg.set_content('Your data has been uploaded successfully on our server. You can now start asking your questions.')

    msg['Subject'] = 'Scarlett'
    msg['From'] = "scarlettai.official@gmail.com"
    msg['To'] = receiver_mail

    # Send mail
    server.send_message(msg)

    # terminating the session
    server.quit()


def untuplify_dict_keys(mapping):
    string_keys = {json.dumps(k): v for k, v in mapping.items()}
    return string_keys

def tuplify_dict_keys(string):
    mapping = string
    return {tuple(json.loads(k)): v for k, v in mapping.items()}

def dialogue_act_features(post):
    features = {}
    for word in nltk.word_tokenize(post):
        features['contains({})'.format(word.lower())] = True
    return features

def generate_binary_feature(label):
    if label in ['whQuestion', 'yAnswer', 'ynQuestion']:
        return True
    else:
        return False

def check_if_question(text):
    global start_time, classifier
    if datetime.now() - start_time > timedelta(seconds=15 * 24 * 60 * 60):
        featuresets = [(dialogue_act_features(post.text), generate_binary_feature(post.get('class'))) for post in posts]
        # 10% of the total data
        size = int(len(featuresets) * 0.1)
        # first 10% for test_set to check the accuracy, and rest 90% after the first 10% for training
        train_set, test_set = featuresets[size:], featuresets[:size]
        # get the classifer from the training set
        classifier = nltk.NaiveBayesClassifier.train(train_set)
        start_time = datetime.now()
    if classifier != '':
        return classifier.classify(dialogue_act_features(text))
    else:
        return False
