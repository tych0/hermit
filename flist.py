from keyring import get_password

from xmpp import Client, Presence
from xmpp.protocol import Message

from xmpp.roster import Roster

cl = Client('wisc.edu')
cl.connect()
cl.auth('tjandersen', get_password("xmpp", "tjandersen"), "bot")

roster = Roster()
roster.PlugIn(cl)

roster.getRoster()

print roster.getRawRoster()
cl.disconnect()
