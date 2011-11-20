#!/usr/bin/python
#
# PyIRCBot
# Copyright (C) Pierre Jaury 2011 <pierre@jaury.eu>
# 
# PyIRCBot is free software: you can redistribute it and/or modify it
# under the terms of the GNU General Public License as published by the
# Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
# 
# ognbot is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.
# See the GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License along
# with this program.  If not, see <http://www.gnu.org/licenses/>.

from core import BotProtocol, botcommand
from twisted.internet.defer import Deferred
from twisted.internet.task import LoopingCall
from twisted.python import log
import shelve
import new

class LoggingBotProtocol(BotProtocol):
	'''
	I am a bot protocol which is able to log commands and messages to
	a file-like object.
	'''
	def privmsg (self, user, channel, message):
		log.msg ('incoming %s %s %s' % (user, channel, message))
		super (LoggingBotProtocol, self).privmsg (user, channel, message)

	def msg (self, channel, message):
		log.msg ('outgoing %s %s' % (channel, message))
		super (LoggingBotProtocol, self).msg (channel, message)

	def command (self, out, command, *args):
		log.msg ('command %s %s' % (command, ' '.join (args)))
		super (LoggingBotProtocol, self).command (out, command, *args)

class AsynchronousCallBotProtocol(BotProtocol):
	'''
	I am a bot protocol which implements asynchronous queries to other bots
	or services (even users if really needed for a check or anything)
	For every actor i can interact with, you have to provide me with a
	reference handshake, so that I know when they are finished talking
	
	For instance, if one service called DummyServ replies 'Pong!' to the
	message 'ping', just add {'DummyServ': ('ping', 'Pong!')} to your factory
	and I will be able to interact with it (him).
	
	I maintain a pool of pending requests for every actor. When an actor is
	finished talking, I simply fires your callback and execute the next
	pending request.
	'''
	def _sync (self, user, channel, message):
		'''
		This is called when a message is recieve from one of the actors
		I am connected to
		'''
		if self._job[channel]:
			query, stop = self.factory.sync[channel]
			if not message == stop:
				self._buffer[channel].append (message)
			else:
				self._job[channel].callback (self._buffer[channel])
				self._buffer[channel] = []
				self._nextjob (channel)				
			
	def _nextjob (self, channel):
		'''
		This is called to trigger the next job in the pool if available
		'''
		if len(self._pool[channel]) > 0:
			query, stop = self.factory.sync[channel]
			d, message = self._pool[channel].pop (0)
			self.msg (channel, message)
			for line in query:
				self.msg (channel, line)
			self._buffer[channel] = []
			self._job[channel] = d
		else:
			self._job[channel] = None

	def _addjob (self, channel, message):
		'''
		You might use this method to add a new request message for the
		actor channel, just rely on the returned deferred
		'''
		d = Deferred ()
		self._pool[channel].append ((d, message))
		if not self._job[channel]:
			self._nextjob (channel)
		return d
		
	def connectionMade (self):
		'''
		Initialization of specific attributes
		'''
		self._pool = {key: [] for key in self.factory.sync}
		self._job = {key: None for key in self.factory.sync}
		self._buffer = {key: [] for key in self.factory.sync}
		super(AsynchronousCallBotProtocol, self).connectionMade ()

	def _handle (self, user, channel, message, wrap):
		'''
		Triggers the _sync method if necessary
		'''
		if channel in self.factory.sync:
			self._sync (user, channel, message)
		return super(AsynchronousCallBotProtocol, self)._handle (user, channel, message, wrap)

class AliasBotProtocol (BotProtocol):
	'''
	I am a bot protocol which implement command aliases
	'''
	def connectionMade (self):
		'''
		Initialization of specific attributes
		'''
		self._aliases = {}
		self._aliases = shelve.open('aliases.db', flag='c', protocol=None, 
					    writeback=True)
		loop = LoopingCall (self._aliases.sync)
		loop.start (10)
		super(AliasBotProtocol, self).connectionMade ()

	@botcommand
	def setAlias (self, flow, out, user, channel, name, *command):
		'''
		\x02setAlias\x02 <name> <command line>
		Saves the given command line as responding to the specified name
		Every '=>' in the command line will be replaced by the piping pattern
		Arguments to the alias can be retrived using %(0)s, %(1)s, etc.
		\x02Aliases shall not be piped to other commands for now.\x02
		'''
		if name in dir (self) or name.startswith ('_'):
			out.append ('\x02Error\x02: illegal alias name')
		else:
			command = ' '.join (command).replace ('=>', '->')
			self._aliases[name] = command
			out.append ('\x02Saved %s as\x02: %s' % (name, command))

	@botcommand
	def listAliases (self, flow, out, user, channel):
		'''
		\x02listAliases\x02
		Lists currently defined aliases
		'''
		if len (self._aliases.keys ()) == 0:
			out.append ('\x02Notice\x02 No alias is currently defined')
		for name, command in self._aliases.items ():
			out.append ('\x02%s:\x02 %s' % (name, command))

	@botcommand
	def delAlias (self, flow, out, user, channel, name):
		'''
		\x02delAlias\x02 <name>
		Deletes the specified alias
		'''
		if name not in self._aliases:
			out.append ('\x02Warning\x02 Unkown alias %s' % name)
		out.append ('Deleted alias \x02%s\x02' % name)
		del self._aliases[name]

	def _check (self, user, channel, command, args):
		return (super(AliasBotProtocol, self)._check (user, channel, command, args)
			or command in self._aliases)
	
	def __getattr__ (self, name):
		if name in self._aliases:
			def f (self, flow, out, user, channel, *args):
				args = dict (zip (map (str, range (len (args))), args))
				return  self._handle (user, channel, self._aliases[name] % args)
			return new.instancemethod (f, self, self.__class__)
