import curses
import itertools

from collections import defaultdict

from textwrap import wrap
from curses.panel import new_panel, top_panel, update_panels

from sys import stderr
from conversation import Conversation

class Window(object):
  AUTO_SCROLL = 0
  def __init__(self, callback=None, win=None, parent=None, pos=AUTO_SCROLL):
    
    # If there is a parent, ask it for our window
    self.parent = parent
    if parent:
      self.win = parent._derwin()

    # just kidding, we might have also been given a window
    if win:
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

    assert ((len(self.children) == 0 and self.callback) or
            (len(self.children) != 0 and not self.callback))

    if self.callback:
      hist = self.callback()
      self.win.clear()
    else:
      hist = []

    if self.pos != Window.AUTO_SCROLL:
      hist = self.history[:pos]

    # Wrap each message correctly
    lines = list(itertools.chain(*map(lambda s: wrap(s, rows), hist)))
    # we can only print up to rows number of lines
    lines = lines[-rows:]

    for (row, line) in enumerate(lines):
      self.win.addstr(row, 0, line) 
      self.win.clrtoeol()

    # swap the virtual buffers for the next call to doupdate() (but don't
    # actually redraw the physical screen, hopefully saving some flicker)
    self.win.noutrefresh()

    # if we are the root window, do the update
    if not self.parent:
      curses.doupdate()

  def getmaxyx(self):
    return self.win.getmaxyx()

  def _derwin(self):
    """ Make a derwindow of this one that is the "size" it should be (i.e.
    self.getmaxyx()) """
    (y, x) = self.getmaxyx()
    return self.win.derwin(y, x, 0, 0)

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
    if self.splitdir == DividableWin.HORIZONTAL:
      self.active = (self.active - 1) % len(self.children)
    else:
      self.children[active].wup()

  def wdn(self):
    if self.splitdir == DividableWin.HORIZONTAL:
      self.active = (self.active + 1) % len(self.children)
    else:
      self.children[active].wdn()

  def wlf(self):
    if self.splitdir == DividableWin.VERTICAL:
      self.active = (self.active - 1) % len(self.children)
    else:
      self.children[active].wlf()

  def wrt(self):
    if self.splitdir == DividableWin.VERTICAL:
      self.active = (self.active + 1) % len(self.children)
    else:
      self.children[active].wrt()

  def _resize(self):
    """ Resize all the windows (and their children) appropriately. This
    includes respecting things that are statically sized. """

    if len(self.children) == 0:
      return

    (y, x) = self.getmaxyx()
    
    def partition(f, it):
      result = {}
      for i in it:
        result.setdefault(f(i), []).append(i) 
      return result

    p = partition(lambda w: w.static_size, self.children)
    ssize_wins, dsize_wins = [], []
    try:
      ssize_wins = p[True]
    except KeyError:
      pass
    try:
      dsize_wins = p[False]
    except KeyError:
      pass

    def size_getter(w):
      (wy, wx) = w.getmaxyx()
      if self.splitdir == DividableWin.VERTICAL:
        return wx
      else:
        return wy
    diff = sum(map(size_getter, ssize_wins))

    if self.splitdir == DividableWin.VERTICAL:
      pixels_left = x - diff
      cur_y, cur_x = 0, diff
    else:
      pixels_left = y - diff
      cur_y, cur_x = diff, 0

    inc = pixels_left / len(dsize_wins)

    # for the intermediate windows, make their sizes as calculated
    for w in dsize_wins[:-1]:
      if self.splitdir == DividableWin.VERTICAL:
        w.win.resize(y, inc)
        cur_x += inc
      else:
        w.win.resize(inc, x)
        cur_y += inc
      w.win.mvwin(cur_y, cur_x)

    # for the last window, make it fell the rest of the canvas
    w = dsize_wins[-1]
    if self.splitdir == DividableWin.VERTICAL:
      w.win.resize(y, pixels_left - cur_x)
    else:
      w.win.resize(pixels_left - cur_y, x)
    w.win.mvwin(cur_y, cur_x)

    # now resize our children, in case they have changed size
    for c in self.children:
      c._resize()

  def _addwin(self, win):
    # if we're "splitting", we need to make two windows initially, since we're
    # acting as the first child right now
    if len(self.children) == 0:
      w = DividableWin(parent=self)

      # pass on our duties
      w.callback = self.callback
      self.callback = None
      self.children.append(w)
      self.active = 0

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
    l = self.win.derwin(y, left_cell_width, 0, 0)
    r = self.win.derwin(y, x - left_cell_width, 0, left_cell_width)

    # now set up the borders
    bl = DividableWin(win=l, parent=self, static_size=True)
    br = DividableWin(win=r, parent=self)

    # kill our callback since presumably the children will be painting
    self.callback = None

    # we have children
    self.children = self.children + [bl,br]

    return (bl, br)

  def sp(self):
    """ Split the current window. """
    if self.splitdir and self.splitdir != DividableWin.HORIZONTAL:
      w = self.children[active].sp()
      return w
    self.splitdir = DividableWin.HORIZONTAL

    # make the new window 
    w = DividableWin(parent=self) 
    self._addwin(w)
    return w

  def vdiv(self, top_cell_length):
    (y, x) = self.getmaxyx()
    assert top_cell_length < y
    # XXX: Refactor so this isn't required.
    assert len(self.children) == 0

    # make the curses windows
    t = self.win.derwin(top_cell_length, x, 0, 0)
    b = self.win.derwin(y - top_cell_length, x, top_cell_length, 0)
    
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
    if self.splitdir and self.splitdir != DividableWin.VERTICAL:
      active = self.children[self.active]
      w = active.vsp()
      return w
    self.splitdir = DividableWin.VERTICAL

    w = DividableWin(parent=self)
    self._addwin(w)
    return w

class BorderWin(DividableWin):
  # These are what the arguments to border() should be to draw a particular
  # border.
  BORDER_SPEC = {
    "left"   : { "ls" : 0,
                 "bl" : '*',
                 "tl" : '*',
               },
    "bottom" : { "bs" : 0,
                 "bl" : '*',
                 "br" : '*',
               },
    "top"    : { "ts" : 0,
                 "tl" : '*',
                 "tr" : '*',
               },
    "right"  : { "rs" : 0,
                 "tr" : '*',
                 "br" : '*',
               },
  }

  # How does drawing a particular border affect the window size? In order of:
  #  (min_y, min_x, max_y, max_x)
  MOD_SPEC = {
    "left"   : lambda min_y, min_x, max_y, max_x: (min_y, min_x+1, max_y, max_x),
    "right"  : lambda min_y, min_x, max_y, max_x: (min_y, min_x, max_y, max_x-1),
    "bottom" : lambda min_y, min_x, max_y, max_x: (min_y, min_x, max_y-1, max_x),
    "top"    : lambda min_y, min_x, max_y, max_x: (min_y+1, min_x, max_y, max_x),
  }

  def __init__(self, borders=None, **kwarg):
    DividableWin.__init__(self, **kwarg)
    d = defaultdict(lambda: ' ')
    min_y, min_x = 0, 0
    max_y, max_x = self.win.getmaxyx()
    if borders:
      for border in borders:
        d.update(BorderWin.BORDER_SPEC[border])
        min_y, min_x, max_y, max_x = \
          BorderWin.MOD_SPEC[border](min_y, min_x, max_y, max_x)
    self._b = d

    # A little window hackery. We really want self.win to be the window that we
    # draw text on, and we want users to not have to worry about the border, so
    # we fake that self.win is the window we were given by making the window we
    # were given self.root and reallocating self.win.
    self.root = self.win
    self.win = self.root.derwin(max_y-1, max_x-1, min_y, min_x)

  def update(self):
    self.root.border(self._b['ls'], self._b['rs'], self._b['ts'], self._b['bs'],
                     self._b['tl'], self._b['tr'], self._b['bl'], self._b['br'])
    self.root.noutrefresh()
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

      stdscr.getch()
      p.bottom()
      p.userptr().win.resize(10,10)
      p.userptr().update()

  def g(stdscr):
    c = lambda: ["you should see a border on the bottom and left"]
    w = BorderWin(callback=c, borders=["left", "bottom"], win=stdscr)
    w.update()
    stdscr.getch()

  def h(stdscr):
    c = Conversation()
    c.add("divide four ways")

    w = DividableWin(callback=c, win=stdscr.derwin(0,0))
    w.update()
    stdscr.getch()
    new_w = w.sp()
    new_w.callback = Conversation()
    new_w.callback.add("new_w")
    w.children[0].callback.add("hi to upper left from new_w")

    ul = w.children[0]

    assert ul.callback
    assert w.children[0].callback is c
    assert len(c()) == 2

    w.update()
    stdscr.getch()
    new_w2 = w.vsp()
    new_w2.callback = Conversation()
    new_w.callback.add("hi from new_w2")
    new_w2.callback.add("new_w2")

    assert w.children[0].children[1].callback is new_w2.callback

    w.update()
    stdscr.getch()

    w.children[0].children[0].callback.add("hello upper left")
    w.children[1].callback.add("hello bottom")
    w.children[0].children[1].callback.add("hello upper right")

    w.update()
    stdscr.getch()

  tests = [h] # g
  for test in tests:
    def clear(stdscr):
      test(stdscr)
      stdscr.clear()
    curses.wrapper(clear)
