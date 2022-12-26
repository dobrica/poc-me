import os
# suppress tensorflow info and warning messages
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '2'
import tensorflow_datasets as tfds
import tensorflow_text
import tensorflow as tf
from configparser import ConfigParser

config = ConfigParser()
config.read('config.ini')

MODEL_NAME = config["DEF"]["MODEL_NAME"]

print("Loading model...")
translation_model = tf.saved_model.load(MODEL_NAME)

corrections = { ": ' ": ": '", " ' } ": "'}", " _ ": "_", " - ": "-",
  " : ": ":", "( ": "(", " )": ")", "{ ": "{", " ]": "]"}

def get_formatted_query(question):
  # translate question to query
  query = translation_model(question).numpy().decode('utf-8')
  for key, value in corrections.items():
    # Replace key substrings, to remove space chars, 
    # but preserve space in artist name
    query = query.replace(key, value)
  return query