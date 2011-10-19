import curses
from curses.textpad import Textbox

import string

class _Textbox(Textbox):
  """ curses.textpad.Textbox requires users to ^g on completion, which is sort
  of annoying for an interactive chat client such as this, which typically only
  reuquires an enter. This subclass fixes this problem by signalling completion
  on Enter as well as ^g. """
  def __init__(*args, **kwargs):
    Textbox.__init__(*args, **kwargs)

  def do_command(self, ch):
    if ch == 10: # Enter
      return 0
    return Textbox.do_command(self, ch)

class VimBox(object):
  def __init__(self, win, updater, inputer, blocktime=500):
    self.win = win
    self.win.timeout(blocktime)
    self.textbox = _Textbox(self.win, insert_mode=True)
    self.textbox.stripspaces = True

    self.updater = updater
    self.inputer = inputer

  def __call__(self):
    def callback(ch):
      (cursory, cursorx) = self.win.getyx()
      self.updater()
      self.win.move(cursory, cursorx)
      self.win.cursyncup()
      self.win.refresh()

      if ch < 0:
        return None
      return ch

    while True:
      inp = self.textbox.edit(callback)
      inp = string.replace(inp, '\n', '')
      if inp.strip() == '/quit':
        return
      self.win.clear()
      self.inputer(inp)

if __name__ == '__main__':
  from conversation import Conversation
  from window import DividableWin

  def f(stdscr):
    (y, x) = stdscr.getmaxyx()
    outp = stdscr.derwin(y - 5, x, 0, 0)
    wout = DividableWin(win=outp)
    wout.callback = Conversation()

    inp = stdscr.derwin(5, x, y - 5, 0)
    vb = VimBox(inp, wout.update, wout.callback.add)

    vb()
  
  curses.wrapper(f)

