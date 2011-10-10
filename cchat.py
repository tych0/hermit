#!/usr/bin/env python

"""
 ----------------------------------------------------------------------------
 "THE BEER-WARE LICENSE" (Revision 42):
 <tycho@tycho.ws> wrote this file. As long as you retain this notice you
 can do whatever you want with this stuff. If we meet some day, and you think
 this stuff is worth it, you can buy me a beer in return. Tycho Andersen
 (Shamelessly stolen from: http://people.freebsd.org/~phk/)
 ----------------------------------------------------------------------------
"""

import threading
import curses
import string
import itertools
import signal

from curses.textpad import Textbox
from Queue import Queue, Empty

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

# Since curses is not thread safe and we do curses operations from multiple
# threads, we need to synchronize. This decorator does that.
def synchronized(lock_name):
  """ Synchronization decorator. """

  def wrap(f):
    def new_function(*args, **kw):
      self = args[0]
      lock = getattr(self, lock_name)
      lock.acquire()
      try:
        return f(*args, **kw)
      finally:
        lock.release()
    return new_function
  return wrap

class CommandError(Exception):
  pass

class Chat(object):
  """ Implements an ncurses chat client. It has two windows on the
  virtual screen: one for displaying chat history and one for
  entering text. As this interface matures, I may split it out and
  make an XMPP backend for it as well, since mcabber doesn't support
  MUC. """

  CHATBOX_SIZE = 3

  def __init__(self, blocktime=500):
    self.blocktime = blocktime
    
    self.curses_lock = threading.RLock()
    self.events_lock = threading.RLock()

    self.global_screen = curses.initscr()
    (globaly, globalx) = self.global_screen.getmaxyx()
    curses.noecho()
    # one row for status bar, and CHATBOX_SIZE rows for the chatbox
    self.chatscreen = curses.newwin(globaly-Chat.CHATBOX_SIZE, globalx, 0, 0)
    self.entryscreen = curses.newwin(Chat.CHATBOX_SIZE, globalx, globaly-Chat.CHATBOX_SIZE, 0)

    # only block for blocktime ms when waiting for a character
    self.entryscreen.timeout(self.blocktime)

    # Set up the text entry.
    self.textpad = _Textbox(self.entryscreen, insert_mode=True)
    self.textpad.stripspaces = True
    self.history = []

    # Curses things to make the cursor behave correctly.
    self.global_screen.leaveok(True)
    self.chatscreen.leaveok(True)
    self.entryscreen.leaveok(False)

    # initially, we have no commands or events
    self.commands = {}
    self.events = []

    # set up the queue thread
    self.q = Queue()
    self.running = True
    self.busy = False
    self.qt = threading.Thread(target=self._queue_thread)
    self.qt.start()

    # Now, draw the initial screen/status bar
    self.update()

  def __enter__(self):
    # Just shutdown nicely when the user wants to.
    def int_handler(signo, frame):
      self.running = False
    signal.signal(signal.SIGINT, int_handler)

    return self

  def __exit__(self, type, value, traceback):
    # stop the other threads
    self.running = False

    # cancel any pending events
    self.events_lock.acquire()
    map(lambda t: t.cancel(), self.events)
    self.events_lock.release()

    # wait for everything to stop before unitializing curses
    map(lambda t: t.join(), self.events)
    self.qt.join()

    # reset the screen
    curses.nocbreak()
    curses.echo()
    curses.endwin()

  def _queue_thread(self):
    """ Thread for managing the queue. Started automatically once by the
    constructor of Chat, runs until self.running is set to False. We also
    hijack this thread to prune the dead events from the events list. """
    while self.running:
      try:
        msg = self.q.get(True, max(self.blocktime / 1000, 1))
        self.busy = True
        self.send(msg)
        self.update()
      except Empty:
        self.busy = False
        pass

      # Prune the events list of dead events
      self.events_lock.acquire()
      self.events = filter(lambda t: t.is_alive(), self.events)
      self.events_lock.release()

  @synchronized("curses_lock")
  def _drawstatus(self):
    """ Draw a generic status bar of "*"s or "-"s depending on whether or not
    there are messages in the queue. """
    (y, x) = self.chatscreen.getmaxyx()

    fillchar = '*' if self.busy > 0 else '-'
    form = '{:'+ fillchar +'^' + str(x - 1) + '}'

    self.chatscreen.addstr(y-1, 0, form.format('%s' % self.status()))

  def status(self):
    """ By default, just indicate whether there are pending things in the
    queue. Users should override this method if they would like to provide a
    richer status bar. """
    return ''

  @synchronized("curses_lock")
  def update(self):
    """ Redraw the window with the current history. """
    (cursory, cursorx) = self.entryscreen.getyx()
    (rows, cols) = self.chatscreen.getmaxyx()

    def message_lines(message):
      words = message.split()
      accum = words[0]
      words = words[1:]
      while len(words) > 0:
        while True: 
          accum += " "
          if len(words[0]) >= cols - 3:
            # if the word is too huge to fit on the screen (note that
            # there's 3 spaces for padding), split it into parts
            first_part = words[0][:cols - len(accum)]
            words[0] = words[0][len(first_part):]
            accum += first_part
          elif len(accum) + len(words[0]) < cols:
            # otherwise, just grab this word off the front
            accum += words[0]
            words = words[1:]
          else:
            # the word is not too big to fit on the screen, but it
            # is too big for this line
            break
          # have we filled up accum? are we out of stuff to print?
          if len(accum) >= cols or len(words) == 0:
            break
        yield accum
        accum = "  "
    lines = list(itertools.chain(*[message_lines(msg) for msg in self.history]))

    # we can only print up to rows number of lines, and we save the last row
    # for the status bar
    lines = lines[-(rows-1):]

    for (row, line) in zip(range(len(lines)), lines):
      self.chatscreen.addstr(row, 0, line) 
      self.chatscreen.clrtoeol()

    self._drawstatus()

    self.entryscreen.move(cursory, cursorx)
    self.entryscreen.cursyncup()
    self.chatscreen.noutrefresh()
    self.entryscreen.noutrefresh()
    curses.doupdate()

  def user_input(self):
    """ Get some user input and return it. """

    # Above, we set the timeout of getch() on entryscreen to 500ms. That means
    # that the invalid character (-1) is returned every 500 ms if the user
    # enters nothing, and our validator is called. We take this opportunity to
    # relese the curses lock so any other threads (e.g. the message handling
    # thread) have a chance to update the screen. Additionally, we call
    # update() so that any other changes are picked up. We raise _StoppedError
    # to get out of the surrounding loop in edit() so that we can exit this
    # function cleanly and without hijacking any other exceptions (such as
    # KeyboardInterrupt).

    class _StoppedError(Exception):
      pass

    def validator(ch):
      if ch == curses.KEY_RESIZE:
        self.chatscreen.clear()
        (y, x) = self.global_screen.getmaxyx()
        curses.resizeterm(y, x)
        self.chatscreen.resize(y-Chat.CHATBOX_SIZE, x)
        self.entryscreen.mvwin(y-Chat.CHATBOX_SIZE, 0)
        self.update()
        return None
      try:
        self.curses_lock.release()
        if not self.running:
          raise _StoppedError
        self.update() # has anything changed?
        if ch < 0:
          return None
        return ch
      finally:
        self.curses_lock.acquire()

    try:
      self.curses_lock.acquire()
      cmd = self.textpad.edit(validator)
      self.entryscreen.clear()
    except _StoppedError:
      return ''
    finally:
      self.curses_lock.release()

    # strip the newlines out of the middle of the words
    cmd = string.replace(cmd, '\n', '')

    # remove unprintable characters
    cmd = (''.join(c if c in string.printable else '' for c in cmd)).strip()

    # process commands if necessary
    if cmd.startswith('/'):
      words = cmd.split()
      cmdname = words[0][1:]
      args = words[1:]

      if cmdname in self.commands:
        try:
          self.commands[cmdname](*args)
        except CommandError as e:
          self.message('System:', 'Problem executing command: ' + str(e))
        except TypeError as e:
          self.message('System:', str(e))
      else:
        self.message('System:', 'Unknown command: '+cmdname)
    else:
      # it's not a cmd so it must be a message to send
      self.q.put(cmd)
    self.update()

  def register_command(self, func):
    """ A command is something the user can enter, such as /nick to change
    their nickname or /refresh to refresh something. Chat automatically handles
    commands: the name of the function should be the name of the command (e.g.
    `nick' or `refresh' above) and func should be a function which processes
    the command.
    
    func will recieve the user's arguments to the command as individual
    arguments to the function (i.e. `/refresh one two three' will call 
      func('one', 'two', 'three')
    If the number of arguments the user provided does not match the number func
    expects, an error message will be given to the user. 

    If func encouters an error and wishes to notify the user, it should raise a
    LoginError. func's return value is ignored.

    func will be called in the main GUI thread, but without the curses lock.
    """
    self.commands[func.__name__] = func

  def remove_command(self, func):
    """ Remove a command which has been registered. """
    del self.commands[func.__name__]

  def register_event(self, freq, func):
    """ Register an event. An event is something that happens every so often.
    Chat provides a way to manage these events automatically: by registering
    them here. Chat will continue to call `func' with frequency `freq' until
    the client exits (cleanup happens automatically). If `func' returns something
    which evaluates to false, the event sequence is terminated. `func' is
    called once initially."""
    def wrapper():
      if self.running:
        if func():
          t = threading.Timer(freq, wrapper)

          self.events_lock.acquire()
          self.events.append(t)
          t.start()
          self.events_lock.release()

    wrapper()

  def message(self, who, what):
    """ Add a message to the history. NOTE: This method does not acquire
    curses_lock. This is perhaps safe (nobody else in Chat edits history, so
    they will only read outdated state), however it is undesirable. It is
    recommended to acquire curses_lock before calling this method. This also
    enables applications to indicate to users interesting messages via
    curses.beep() safely, since they have the curses_lock at this point. """
    (rows, cols) = self.chatscreen.getmaxyx()
    self.history.append(who+': '+what)

    # We can only display at most rows number of messages, since we display one
    # message on each line. (Note that we may display fewer messages than are
    # in self.history, since messages might be longer than one line and wrap.)
    if len(self.history) > rows:
      self.history = self.history[-rows:]
  
  def send(self, msg):
    """ This method is called when the user generates a message to send. It
    should be overridden by base classes to be have appropriately. """
    self.message('Me', msg)

def main():

  with Chat() as chat:

    # set up handlers
    def quit():
      chat.running = False
    chat.register_command(quit)

    def refresh():
      chat.getsms()
    chat.register_command(refresh)

    while chat.running:
      chat.user_input()

if __name__ == '__main__':
  main()
