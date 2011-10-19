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
    (y, x) = self.win.getmaxyx()
    self.textwin = self.win.derwin(y-1, x, 0, 0)
    self.textwin.timeout(blocktime)
    self.cmdwin = self.win.derwin(1, x, y-1, 0)

    self.textbox = _Textbox(self.textwin, insert_mode=True)
    self.textbox.stripspaces = True

    self.updater = updater
    self.inputer = inputer
    self.insertmode = True

    self.update()

  def update(self, updater=False):
    (cursory, cursorx) = self.textwin.getyx()

    if updater:
      self.updater()

    if self.insertmode:
      self.cmdwin.clear()
      self.cmdwin.addstr(0, 0, "-- INSERT --")
    self.textwin.move(cursory, cursorx)
    self.textwin.cursyncup()

    self.win.refresh()

  def __call__(self):
    def callback(ch):
      self.update()
      if ch == curses.ascii.ESC:
        self.escmode()
        return None
      if ch < 0:
        self.update(updater=True)
        return None
      return ch

    while True:
      inp = self.textbox.edit(callback)
      self.textwin.clear()
      inp = string.replace(inp, '\n', '')
      if inp.strip() == '/quit':
        return
      self.inputer(inp)

  def escmode(self):
    (cursory, cursorx) = self.win.getyx()

    self.insertmode = False
    self.cmdwin.clear()
    self.update()

    while True:
      ch = self.cmdwin.getch()
      if ch > 0:
        self.inputer('got: ' + chr(ch))

      (y, x) = self.cmdwin.getyx()

      # are we typing?
      if ch < 0:
        pass
      elif curses.ascii.isprint(ch) and x > 0:
        self.cmdwin.addch(ch)
      elif ch == ord(':') and x == 0:
        self.cmdwin.addch(ch)

      # silent commands
      elif ch == ord('i'):
        break
      elif ch == ord('h'):
        self.win.move(cursory, cursorx-1)

      # special keys
      elif ch in (curses.ascii.BS, curses.KEY_BACKSPACE, 0x7f):
        if x > 0:
          self.cmdwin.move(y, x-1)
          self.cmdwin.delch()
        else:
          self.cmdwin.move(0,0)
      elif ch == curses.ascii.NL:
        cs = [chr(curses.ascii.ascii(self.cmdwin.inch(y, i))) for i in range(x)]
        self.cmdwin.clear()

        self.inputer('command: ' + ''.join(cs))
      self.update(True)
    
    self.insertmode = True
    self.update()

    self.win.move(cursory, cursorx)
    self.win.cursyncup()
    self.win.refresh()

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

