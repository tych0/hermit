class VimBox(object):
  def __init__(self, win, updater, blocktime=500):
    self.win = win
    self.win.timeout(self.blocktime)
    self.updater = updater

  def __call__(self):
    def callback(ch):
      self.updater()
      if ch < 0:
        return None
      return ch
