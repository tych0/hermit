import curses
import itertools

from collections import defaultdict

from textwrap import wrap
from curses.panel import new_panel, top_panel, update_panels

class Window(object):
  AUTO_SCROLL = 0
  def __init__(self, callback=None, win=None, parent=None, pos=AUTO_SCROLL):
    
    # If there is a parent, ask it for our window
    self.parent = parent
    if parent:
      self.win = parent._subwin()

    # just kidding, we might have also been given a window
    if win:
      self.win = win

    self.pos = pos
    if not callback:
      callback = lambda: []
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

    if self.parent:
      self.parent.update()

  def getmaxyx(self):
    return self.win.getmaxyx()

  def _subwin(self):
    """ Make a subwindow of this one that is the "size" it should be (i.e.
    self.getmaxyx()) """
    (y, x) = self.getmaxyx()
    return self.win.subwin(y, x)

class BorderWin(Window):
  # only support bottom and left borders for now
  BORDER_SPEC = {
    "left"   : { "ls" : 0,
                 "bl" : '*',
               },
    "bottom" : { "bs" : 0,
                 "bl" : '*',
                 "br" : '*',
               },
  }

  MOD_SPEC = {
    "left"   : lambda y, x: (y, x-1),
    "bottom" : lambda y, x: (y-1, x),
  }

  def __init__(self, borders=None, **kwarg):
    Window.__init__(self, **kwarg)
    d = defaultdict(lambda: ' ')
    self.xmod, self.ymod = 0, 0
    if borders:
      for border in borders:
        d.update(BorderWin.BORDER_SPEC[border])
        self.ymod, self.xmod = BorderWin.MOD_SPEC[border](self.ymod, self.xmod)
    self._b = d

  def getmaxyx(self):
    (y, x) = self.win.getmaxyx()
    # leave room for the status bar
    return (y + self.ymod, x + self.xmod)

  def update(self):
    self.win.border(self._b['ls'], self._b['rs'], self._b['ts'], self._b['bs'],
                    self._b['tl'], self._b['tr'], self._b['bl'], self._b['br'])
    Window.update(self)

class DividableWin(Window):
  def __init__(self, *args, **kwargs):
    Window.__init__(self, *args, **kwargs)
    self.children = []

  def update(self):
    for child in self.children:
      child.update()
    Window.update(self)

  def div(self, left_cell_width):
    (y, x) = self.getmaxyx()
    assert left_cell_width < x

    # make the curses windows
    l = self.win.subwin(y, left_cell_width, 0, 0)
    r = self.win.subwin(y, x - left_cell_width, 0, left_cell_width)

    # now set up the borders
    bl = BorderWin(win=l, parent=self)
    br = BorderWin(win=r, parent=self)

    # kill our callback since presumably the children will be painting

class StackWin(Window):
  def __init__(self, *arg, **kwarg):
    Window.__init__(self, *arg, **kwarg)
    self.panelstack = []

  def update(self):
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
      w = Window(callback=c, win=curses.newwin(30, 30, 0,0))
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
    c = lambda: ["you should see a border on the bottom and left"]
    w = BorderWin(callback=c, borders=["left", "bottom"], win=stdscr)
    w.update()
    stdscr.getch()

  curses.wrapper(f)
  curses.wrapper(g)
