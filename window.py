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

class DividableWin(Window):
  VERTICAL = "v"
  HORIZONTAL = "h"
  def __init__(self, *args, **kwargs):
    self.children = []
    self.splitdir = None
    self.active = None
    self.static_size = False
    if "static_size" in kwargs:
      self.static_size = kwargs["static_size"]
      del kwargs["static_size"]
    Window.__init__(self, *args, **kwargs)

  def update(self):
    for child in self.children:
      child.update()
    Window.update(self)

  def wup(self):
    if self.splitdir == HORIZONTAL:
      self.active = (self.active - 1) % len(children)
    else:
      self.children[active].wup()

  def wdn(self):
    if self.splitdir == HORIZONTAL:
      self.active = (self.active + 1) % len(children)
    else:
      self.children[active].wdn()

  def wlf(self):
    if self.splitdir == VERTICAL:
      self.active = (self.active - 1) % len(children)
    else:
      self.children[active].wlf()

  def wrt(self):
    if self.splitdir == VERTICAL:
      self.active = (self.active + 1) % len(children)
    else:
      self.children[active].wrt()

  def _resize(self):
    pass

  def _addwin(self, win):
    # if we're "splitting", we need to make two windows initially, since we're
    # acting as the first child right now
    if len(children) == 0:
      w = DividableWin(parent=self)

      # pass on our duties
      w.callback = self.callback
      self.callback = None
      self.children.append(w)

    # add the new window 
    self.children.append(win)
    self._resize()

  def div(self, left_cell_width):
    """ Divide an empty dividable to have a cell of static size and another
    window. Right now you can only do this on an undivided window. """
    (y, x) = self.getmaxyx()
    assert left_cell_width < x

    # XXX: Refactor so this isn't required.
    assert len(self.children) == 0

    # make the curses windows
    l = self.win.subwin(y, left_cell_width, 0, 0)
    r = self.win.subwin(y, x - left_cell_width, 0, left_cell_width)

    # now set up the borders
    bl = DividableWin(win=l, parent=self, static_size=True)
    br = BorderWin(win=r, parent=self, border=["left"])

    # kill our callback since presumably the children will be painting
    self.callback = None

    # we have children
    self.children = self.children + [bl,br]

    return (bl, br)

  def sp(self):
    """ Split the current window. """
    if self.splitdir and self.splitdir != HORIZONTAL:
      return self.active.sp()
    self.splitdir = HORIZONTAL

    # make the new window 
    w = BorderWin(parent=self, borders=["left"])
    self._addwin(w)
    return w

  def vdiv(self, top_cell_length):
    (y, x) = self.getmaxyx()
    assert top_cell_length < y
    # XXX: Refactor so this isn't required.
    assert len(self.children) == 0

    # make the curses windows
    t = self.win.subwin(top_cell_length, x, 0, 0)
    b = self.win.subwin(y - top_cell_length, x, top_cell_length, 0)
    
    # now set up the borders
    bt = BorderWin(win=t, parent=self, border=["bottom"], static_size=True)
    bb = DividableWin(win=b, parent=self)

    # kill our callback since presumably the children will be painting
    self.callback = None

    # we have children
    self.children = self.children + [bt,bb]

    return (bt, bb)

  def vsp(self):
    """ Split the current window vertically. """
    if self.splitdir and self.splitdir != VERTICAL:
      return self.active.sp()
    self.splitdir = VERTICAL

    w = BorderWin(parent=self, borders=["top"])
    self._addwin(w)
    return w

class BorderWin(DividableWin):
  # only support bottom and left borders for now
  BORDER_SPEC = {
    "left"   : { "ls" : 0,
                 "bl" : '*',
               },
    "bottom" : { "bs" : 0,
                 "bl" : '*',
                 "br" : '*',
               },
    "top"    : { "ts" : 0,
                 "tl" : '*',
                 "tr" : '*',
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
    DividableWin.update(self)

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
