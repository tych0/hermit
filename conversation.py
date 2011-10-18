class Conversation(object):
  def __init__(self, histlen=1000, nlpadding="   "):
    self.histlen = histlen
    self.nlpadding = nlpadding
    self.history = []

  def add(self, s):
    self.history.append(s)
    self.history = self.history[-self.histlen:]

  def __call__(self):
    return self.history[:]

if __name__ == "__main__":
  c = Conversation(histlen=3)
  for i in range(5):
    c.add(i)
  assert c() == [2,3,4]
