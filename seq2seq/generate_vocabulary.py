import os
# suppress tensorflow info and warning messages
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '2'
import pathlib
import re
from tensorflow._api.v2 import data
import tensorflow_datasets as tfds
import tensorflow_text as text
import tensorflow as tf
from tensorflow_text.tools.wordpiece_vocab import bert_vocab_from_dataset as bert_vocab
from pathlib import Path

path_to_file = Path('max_eng2cypher.txt')

def load_data(path):
  text = path.read_text(encoding='utf-8')

  lines = text.splitlines()
  pairs = [line.split('\t') for line in lines]

  inp = [inp for targ, inp in pairs]
  targ = [targ for targ, inp in pairs]

  return targ, inp

targ, inp = load_data(path_to_file)
print(inp[-1])
print(targ[-1])

dataset = tf.data.Dataset.from_tensor_slices((inp, targ))

train_en = dataset.map(lambda english, cypher: english)
train_cy = dataset.map(lambda english, cypher: cypher)

bert_tokenizer_params=dict(lower_case=False)
reserved_tokens=["[PAD]", "[UNK]", "[START]", "[END]"]

bert_vocab_args = dict(
    # The target vocabulary size
    vocab_size = 8000,
    # Reserved tokens that must be included in the vocabulary
    reserved_tokens=reserved_tokens,
    # Arguments for `text.BertTokenizer`
    bert_tokenizer_params=bert_tokenizer_params,
    # Arguments for `wordpiece_vocab.wordpiece_tokenizer_learner_lib.learn`
    learn_params={},
)

def write_vocab_file(filepath, vocab):
  with open(filepath, 'w') as f:
    for token in vocab:
      print(token, file=f)

cy_vocab = bert_vocab.bert_vocab_from_dataset(
    train_cy.batch(1000).prefetch(2),
    **bert_vocab_args
)
print(cy_vocab[:10])
print(cy_vocab[100:110])
print(cy_vocab[1000:1010])
print(cy_vocab[-10:])

write_vocab_file('cy_vocab.txt', cy_vocab)

en_vocab = bert_vocab.bert_vocab_from_dataset(
    train_en.batch(1000).prefetch(2),
    **bert_vocab_args
)
print(en_vocab[:10])
print(en_vocab[100:110])
print(en_vocab[1000:1010])
print(en_vocab[-10:])

write_vocab_file('en_vocab.txt', en_vocab)


cy_tokenizer = text.BertTokenizer('cy_vocab.txt', **bert_tokenizer_params)
en_tokenizer = text.BertTokenizer('en_vocab.txt', **bert_tokenizer_params)

for cy_examples, en_examples in dataset.batch(3).take(1):
  for ex in en_examples:
    print(ex.numpy())

# Tokenize the examples -> (batch, word, word-piece)
token_batch = en_tokenizer.tokenize(en_examples)
# Merge the word and word-piece axes -> (batch, tokens)
token_batch = token_batch.merge_dims(-2,-1)

for ex in token_batch.to_list():
  print(ex)

# Lookup each token id in the vocabulary.
txt_tokens = tf.gather(en_vocab, token_batch)
# Join with spaces.
tf.strings.reduce_join(txt_tokens, separator=' ', axis=-1)

words = en_tokenizer.detokenize(token_batch)
tf.strings.reduce_join(words, separator=' ', axis=-1)

START = tf.argmax(tf.constant(reserved_tokens) == "[START]")
END = tf.argmax(tf.constant(reserved_tokens) == "[END]")

def add_start_end(ragged):
  count = ragged.bounding_shape()[0]
  starts = tf.fill([count,1], START)
  ends = tf.fill([count,1], END)
  return tf.concat([starts, ragged, ends], axis=1)

words = en_tokenizer.detokenize(add_start_end(token_batch))
tf.strings.reduce_join(words, separator=' ', axis=-1)

def cleanup_text(reserved_tokens, token_txt):
  # Drop the reserved tokens, except for "[UNK]".
  bad_tokens = [re.escape(tok) for tok in reserved_tokens if tok != "[UNK]"]
  bad_token_re = "|".join(bad_tokens)

  bad_cells = tf.strings.regex_full_match(token_txt, bad_token_re)
  result = tf.ragged.boolean_mask(token_txt, ~bad_cells)

  # Join them into strings.
  result = tf.strings.reduce_join(result, separator=' ', axis=-1)

  return result

en_examples.numpy()

token_batch = en_tokenizer.tokenize(en_examples).merge_dims(-2,-1)
words = en_tokenizer.detokenize(token_batch)
words

cleanup_text(reserved_tokens, words).numpy()

class CustomTokenizer(tf.Module):
  def __init__(self, reserved_tokens, vocab_path):
    self.tokenizer = text.BertTokenizer(vocab_path, lower_case=False)
    self._reserved_tokens = reserved_tokens
    self._vocab_path = tf.saved_model.Asset(vocab_path)

    vocab = pathlib.Path(vocab_path).read_text().splitlines()
    self.vocab = tf.Variable(vocab)

    ## Create the signatures for export:   

    # Include a tokenize signature for a batch of strings. 
    self.tokenize.get_concrete_function(
        tf.TensorSpec(shape=[None], dtype=tf.string))

    # Include `detokenize` and `lookup` signatures for:
    #   * `Tensors` with shapes [tokens] and [batch, tokens]
    #   * `RaggedTensors` with shape [batch, tokens]
    self.detokenize.get_concrete_function(
        tf.TensorSpec(shape=[None, None], dtype=tf.int64))
    self.detokenize.get_concrete_function(
          tf.RaggedTensorSpec(shape=[None, None], dtype=tf.int64))

    self.lookup.get_concrete_function(
        tf.TensorSpec(shape=[None, None], dtype=tf.int64))
    self.lookup.get_concrete_function(
          tf.RaggedTensorSpec(shape=[None, None], dtype=tf.int64))

    # These `get_*` methods take no arguments
    self.get_vocab_size.get_concrete_function()
    self.get_vocab_path.get_concrete_function()
    self.get_reserved_tokens.get_concrete_function()

  @tf.function
  def tokenize(self, strings):
    enc = self.tokenizer.tokenize(strings)
    # Merge the `word` and `word-piece` axes.
    enc = enc.merge_dims(-2,-1)
    enc = add_start_end(enc)
    return enc

  @tf.function
  def detokenize(self, tokenized):
    words = self.tokenizer.detokenize(tokenized)
    return cleanup_text(self._reserved_tokens, words)

  @tf.function
  def lookup(self, token_ids):
    return tf.gather(self.vocab, token_ids)

  @tf.function
  def get_vocab_size(self):
    return tf.shape(self.vocab)[0]

  @tf.function
  def get_vocab_path(self):
    return self._vocab_path

  @tf.function
  def get_reserved_tokens(self):
    return tf.constant(self._reserved_tokens)

tokenizers = tf.Module()
tokenizers.cy = CustomTokenizer(reserved_tokens, 'cy_vocab.txt')
tokenizers.en = CustomTokenizer(reserved_tokens, 'en_vocab.txt')

model_name = 'english_to_cypher'
tf.saved_model.save(tokenizers, model_name)

reloaded_tokenizers = tf.saved_model.load(model_name)
reloaded_tokenizers.en.get_vocab_size().numpy()
reloaded_tokenizers.cy.get_vocab_size().numpy()

def detokenize_and_print_en(tokens):
  tokens.numpy()
  text_tokens = reloaded_tokenizers.en.lookup(tokens)
  text_tokens
  round_trip = reloaded_tokenizers.en.detokenize(tokens)
  print(round_trip.numpy()[0].decode('utf-8'))

tokens = reloaded_tokenizers.en.tokenize(['Where is Led Zeppelin from?'])
detokenize_and_print_en(tokens)
tokens = reloaded_tokenizers.en.tokenize(['Which instruments Jimmy Page plays?'])
detokenize_and_print_en(tokens)
tokens = reloaded_tokenizers.en.tokenize(['Show me all events that Led Zeppelin held?'])
detokenize_and_print_en(tokens)
tokens = reloaded_tokenizers.en.tokenize(['Which genre Led Zeppelin belongs to?'])
detokenize_and_print_en(tokens)

def detokenize_and_print_cy(tokens):
  tokens.numpy()
  text_tokens = reloaded_tokenizers.cy.lookup(tokens)
  text_tokens
  round_trip = reloaded_tokenizers.cy.detokenize(tokens)
  print(round_trip.numpy()[0].decode('utf-8'))

tokens = reloaded_tokenizers.cy.tokenize(["MATCH (var1: Artist{name: 'Shawn Drover'})-[:HELD]-(var2: Event) RETURN var2"])
detokenize_and_print_cy(tokens)
tokens = reloaded_tokenizers.cy.tokenize(["MATCH (var1: Artist{name: 'Toto'})-[:IS_FROM]-(var2: Area) RETURN var2"])
detokenize_and_print_cy(tokens)
tokens = reloaded_tokenizers.cy.tokenize(["MATCH (var1: Artist{name: 'DJ Smoke'})-[:PLAYS]-(var2: Instrument) RETURN var2"])
detokenize_and_print_cy(tokens)
tokens = reloaded_tokenizers.cy.tokenize(["MATCH (var1: Artist{name: 'Norman Harris'})-[:BELONGS_TO]-(var2: Genre) RETURN var2"])
detokenize_and_print_cy(tokens)