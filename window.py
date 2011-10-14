import curses
import itertools
from textwrap import wrap
from curses.panel import new_panel, top_panel, update_panels

class Window(object):
  AUTO_SCROLL = -1
  def __init__(self, win, histlen=1000, nlpadding="   ", pos=AUTO_SCROLL):
    self.win = win
    self.histlen = histlen
    self.nlpadding = nlpadding
    self.history = []
    self.pos = pos

  def add(self, s):
    self.history.append(s)
    self.history = self.history[-self.histlen:]

  def scroll_up(self):
    if self.pos == AUTO_SCROLL:
      self.pos = len(self.history) - 1
    if self.pos != 1:
      self.pos -= 1

  def scroll_down(self):
    if self.pos != AUTO_SCROLL:
      self.pos += 1
    if self.pos == len(self.history):
      self.pos = AUTO_SCROLL

  def scroll_lock(self):
    self.pos = AUTO_SCROLL

  def update(self):
    (rows, cols) = self.getmaxyx()

    hist = self.history
    if self.pos != AUTO_SCROLL:
      hist = self.history[:pos]

    # Wrap each message correctly
    lines = list(itertools.chain(*map(lambda s: "\n   ".join(wrap(s, rows)), hist)))
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
      w.add(str(i))
      w.add('the quick brown fox jumped over the lazy dog')
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
