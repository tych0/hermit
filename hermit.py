import curses

from window import DividableWin
from containers import TextContainer
from vimbox import VimBox

def mk_command_handler(win):
  static_cmds = {
    ':sp' : win.sp,
    ':vsp' : win.vsp,
  }
  def handler(s):
    static_cmds[s]()
  return handler

def main(stdscr):
  (y, x) = stdscr.getmaxyx()

  out = DividableWin(win=stdscr.derwin(y-5, x, 0, 0))
  out.callback = TextContainer()

  def userinput(s):
    out.getactive().callback.userinput(s)

  inp = VimBox(stdscr.derwin(5, x, y-5, 0), out.update, userinput, out)
  inp()

if __name__ == "__main__":
  curses.wrapper(main)
