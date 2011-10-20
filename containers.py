class TextContainer(object):
  def __init__(self, histlen=1000, nlpadding="   "):
    self.histlen = histlen
    self.nlpadding = nlpadding
    self.history = []
    self.dirtybit = False

  def _add(self, s):
    self.history.append(s)
    self.history = self.history[-self.histlen:]
    self.dirtybit = True

  def userinput(self, s):
    self._add(s)

  def modified(self):
    """ Return if this conversation has been modified since the last call to
    modified. """
    dirtybit = self.dirtybit
    self.dirtybit = False
    return dirtybit

  def __call__(self):
    return self.history[:]

  def roster(self):
    return None

if __name__ == "__main__":
  c = TextContainer(histlen=3)
  for i in range(5):
    c.userinput(i)
  assert c.modified()
  assert not c.modified()
  assert c() == [2,3,4]
