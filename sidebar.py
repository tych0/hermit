import curses

class Sidebar(object):
  def __init__(self, win):
    self.win = win
    self.win.border(' ', 0, ' ', ' ', ' ', curses.ACS_VLINE, ' ', curses.ACS_VLINE)

  def update(self):
    s = '1' * (self.win.getmaxyx()[1] - 1)
    self.win.addstr(3, 0, s)
    self.win.cursyncup()
    curses.doupdate()
  
  def getmaxyx(self):
    return self.win.getmaxyx()

if __name__ == '__main__':
  def f(stdscr):
    s = Sidebar(stdscr)
    s.update()
    stdscr.getch()
  curses.wrapper(f)
