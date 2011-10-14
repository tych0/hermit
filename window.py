import curses
import itertools
from textwrap import wrap
from curses.panel import new_panel, top_panel, update_panels

class Window(object):
  AUTO_SCROLL = 0
  def __init__(self, win, callback, pos=AUTO_SCROLL):
    self.win = win
    self.pos = pos
    self.callback = callback

  def scroll_up(self):
    self.pos -= 1

  def scroll_down(self):
    if self.pos != Window.AUTO_SCROLL:
      self.pos += 1

  def scroll_lock(self):
    self.pos = Window.AUTO_SCROLL

  def update(self):
    (rows, cols) = self.getmaxyx()

    hist = self.callback()
    if self.pos != Window.AUTO_SCROLL:
      hist = self.history[:pos]

    # Wrap each message correctly
    lines = list(itertools.chain(*map(lambda s: wrap(s, rows), hist)))
    # we can only print up to rows number of lines
    lines = lines[-rows:]

    for (row, line) in enumerate(lines):
      self.win.addstr(row, 0, line) 
      self.win.clrtoeol()

  def getmaxyx(self):
    return self.win.getmaxyx()

  def subwin(self):
    """ Make a subwindow of this one that is the "size" it should be (i.e.
    self.getmaxyx()) """
    (y, x) = self.getmaxyx()
    return self.win.subwin(y, y)

class MainWin(Window):
  def __init__(self, *arg, **kwarg):
    Window.__init__(self, *arg, **kwarg)
    self.panelstack = []

  def getmaxyx(self):
    (y, x) = self.win.getmaxyx()
    # leave room for the status bar
    return (y-1, x)
  
  def update(self):
    # here, we want to know the actual window size, not the fake window size,
    # since we're drawing the status bar.
    (y, x) = self.win.getmaxyx()
    form = '{:-^'+str(x-1)+'}'
    self.win.addstr(y-1, 0, form.format(''))

    # Perhaps the panels changed, we should reflect that.
    update_panels()

    # Now put the actual text in.
    Window.update(self)

  def addwin(self, win):
    p = new_panel(win)
    self.panelstack = [p] + self.panelstack

  def removewin(self):
    """ Remove the currently selected window."""
    if len(self.panelstack) > 0:
      self.panelstack[0].bottom()

      # XXX: Apparently there is no way to explicitly delete these things, so we
      # just delete our reference to it and pray that the gc does its job.
      self.panelstack = self.panelstack[1:]

      self.update()

  def up(self):
    """ Go up in the window stack. """
    if len(self.panelstack) > 1:
      self.panelstack[0].bottom()
      self.panelstack = self.panelstack[1:].append(self.panelstack[0])
      update_panels()

  def down(self):
    """ Go down in the window stack. """
    if len(self.panelstack) > 1:
      self.panelstack[-1].top()
      self.panelstack = self.panelstack[-1] + self.panelstack[:-1]

if __name__ == '__main__':
  def f(stdscr):
    panels = []
    windows = []
    for i in xrange(10):
      c = lambda: ['the quick brown fox jumped over the lazy dog', str(i)]
      w = Window(curses.newwin(30, 30, 0,0), c)
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

  def g(stdscr):
    c = lambda: ["you should see a status bar at the bottom"]
    w = MainWin(stdscr, c)
    w.update()
    stdscr.getch()

  curses.wrapper(f)
  curses.wrapper(g)
