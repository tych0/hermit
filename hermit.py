""" The hermit entry point. It initializes curses and xmpp, spawns threads for
their event loops, and then joins both threads. """

from window import DividableWin
from conversation import Conversation
from vimbox import VimBox

def main(stdscr):
  (y, x) = stdscr.getmaxyx()

  out = DividableWin(win=stdscr.derwin(y-5, x, 0, 0))

  def userinput(s):
    out.getactive().callback.userinput(s)

  inp = VimBox(stdscr.derwin(5, x, y-5, 0), out.update, userinput)
  
  inp()
