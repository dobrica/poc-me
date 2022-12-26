import speech_recognition as sr
import subprocess
from configparser import ConfigParser
import dbUtil
import modelUtil

config = ConfigParser()
config.read('config.ini')

mic = sr.Microphone()

TEMPLATE_QUESTIONS = config["DEF"]["Q_FILE"]
HELP = config["DEF"]["H_FILE"]

def print_template_questions():
  with open(TEMPLATE_QUESTIONS, 'r') as f:	
    lines = f.read().split('\t')
    print('\nTemplate questions: ')
    for i, line in enumerate(lines):
      if line != '':
        line = line.split("ENGLISH")[1]
        line = line.replace("END", "")
        print('%s. %s' %(i+1, line.strip()))

def voice_search():
  try:
    r = sr.Recognizer()
    with mic as source:
      print('\nAsk a question: ')
      audio = r.record(source, duration=5)
      line =  r.recognize_google(audio)
      return line[0].upper() + line[1:] + "?"
  except sr.UnknownValueError:
    print("Voice not recognized")
    return ""

def print_help():
  print('')
  with open(HELP, 'r') as file:
    lines = file.readlines()
    for line in lines:
      print(line.strip())

print_help()
while True:
  
  line = input("\n> ")        
  
  if line.lower() == "clear" or line.lower() == "-c":
    subprocess.run(["clear"])
    line = ''
  if line.lower() == "questions" or line.lower() == "-q":
    print_template_questions()
    line = ''
  if line.lower() == "help" or line.lower() == "-h":
    print_help()
    line = ''
  if line.lower() == "exit" or line.lower() == "-e":
    exit()
  if line.lower() == "musicbrainz" or line.lower() == "-m":
    line = voice_search()

  if line.lower() != "":
    print("\nEnglish question: " + line)
    query = modelUtil.get_formatted_query(line)
    print("Translated query: " + query)
    if (query != ""):
      print("\nAnswer: " + dbUtil.get_answer(query))
    else:
      print("Not a valid query!")
