import curses
import itertools
from textwrap import wrap
from curses.panel import new_panel, top_panel, update_panels

class Window(object):
  def __init__(self, win, histlen=1000, nlpadding="   "):
    self.win = win
    self.histlen = histlen
    self.nlpadding = nlpadding
    self.history = []

  def add(self, s):
    self.history.append(s)
    self.history = self.history[-self.histlen:]

  def update(self):
    (rows, cols) = self.getmaxyx()

    # Wrap each message correctly
    lines = list(itertools.chain(*map(lambda s: "\n   ".join(wrap(s, rows)), self.history)))
    # we can only print up to rows number of lines
    lines = lines[-rows:]

    for (row, line) in enumerate(lines):
      self.win.addstr(row, 0, line) 
      self.win.clrtoeol()

  def getmaxyx(self):
    return self.win.getmaxyx()

if __name__ == '__main__':
  def f(stdscr):
    panels = []
    windows = []
    for i in xrange(10):
      w = Window(curses.newwin(30, 30, 0,0))
      w.history.append(str(i))
      w.history.append('the quick brown fox jumped over the lazy dog')
      w.update()
      p = new_panel(w.win)
      p.set_userptr(w)
      panels.append(p)

    for i in xrange(15):
      p = top_panel()
      p.show()
      update_panels()
      curses.doupdate()

      stdscr.getch()
      p.bottom()
      p.userptr().win.resize(10,10)
      p.userptr().update()

  curses.wrapper(f)
