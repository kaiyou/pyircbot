#!/usr/bin/python
#
# main.py
# Copyright (C) Pierre Jaury 2011 <pierre@jaury.eu>
# 
# ognbot is free software: you can redistribute it and/or modify it
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

from twisted.words.protocols.irc import IRCClient
from twisted.internet.protocol import ClientFactory
from twisted.internet.defer import Deferred
from twisted.internet.task import LoopingCall
import shelve
import re
import new

class BotRegister(object):
	'''
	I am the command register
	'''
	commands = {}

def botcommand (function):
	'''
	I'm a Python decorator updating the commands register
	'''
	BotRegister.commands[function.__name__] = function
	return function

class BotProtocol (IRCClient, object):
	'''
	I'm a generic and dynamic irc bot protocol
	Feel free to extend my behavior by subclassing using new-style dynamic
	Python classes
	
	To add a command to the protocol, simply add a method with the folloing
	signature:
	
		@botcommand
		def commandName (self, message, user, channel, *args):
		
	*args will receive the remaining arguments from the call line on IRC
	If the command fails or raises an exception, nothing will happen
	'''
	
	# Here are simply a couple of properties
	@property
	def nickname (self):
		return self.factory.nickname
	@nickname.setter
	def nickname (self, new):
		self.factory.nickname = new
	@property
	def password (self):
		return self.factory.password

	def _check (self, user, channel, command, args):
		'''
		Checks that a command exists and is ok to run
		Default behavior only queries the register for the given command
		'''
		return command in BotRegister.commands

	def _setup (self, flow, out, user, channel, command, args):
		'''
		Prepares the handling chain of the command
		'''
		return flow

	def _teardown (self, flow, out, user, channel, command, args):
		'''
		Called when the handling chain ends, usually to display the
		message
		'''
		for line in out:
			self.msg (channel, line)

	def _error (self, error, out, user, channel, command, args):
		'''
		Called when one step of the handling chain failed
		'''
		print error

	def _handle (self, user, channel, message):
		'''
		Handles a message sent directly to the robot
		'''
		commands = message.split('->') # separates the commands
		commands = [x.split(' ') for x in commands] # splitting
		commands = [(words[0], words[1:]) for words in commands] # (command, arguments)
		self._launch (user, channel, commands)
		
	def _launch (self, user, channel, commands):
		'''
		Launches a list of commands
		The list has to look like:
			
			[(command, args), (command, args), ...]
		'''
		if not all([self._check (user, channel, command, args) 
			    for command, args in commands]):
			return None
		d = Deferred() # asynchronous deferred
		command, args = commands[0] # first command, setting up
		out = [] # output list
		d.addCallback(self._setup, out, user, channel, command, args)
		for command, args in commands: # chaining every command
			out = [] # output list
			function = getattr (self, command)
			d.addCallback(function, out, user, channel, *args)
			d.addErrback(self._error, out, user, channel, command, args)
		command, args = commands[-1] # last command, tearing down
		d.addCallback(self._teardown, out, user, channel, command, args)
		d.callback(None) # fires everything
		return d

	def signedOn (self):
		'''
		Simply joins every channel when the robot is connected
		'''
		for channel in self.factory.channels:
			self.join (channel)

	def noticed (self, user, channel, message):
		'''
		A notice message is handles exactly like a private message
		'''
		self.privmsg (user, channel, message)		

	def privmsg (self, user, channel, message):
		'''
		A private message can either actually be private or be a channel
		message
		'''
		if channel[0] == '#': # for channel messages
			if not message.startswith (self.factory.bang):
				return # we only handle relevant messages
			message = message[len (self.factory.bang):]
		else:
			channel = user.split ('!')[0] # trick to reply directly
		self._handle (user, channel, message)
			
	def sendmsg (self, out, channel, message):
		'''
		Sends a message to a specific channel
		'''
		self.msg (channel, message)

	def msg (self, channel, message):
		'''
		Simply adds a space in front of the message to avoir recursive
		calls
		'''
		IRCClient.msg (self, channel, ' ' + message)

	def command (self, out, command, *args):
		'''
		Launches a specific command
		'''
		self.sendLine ('%s %s' % (command, ' '.join (args)))

class DebugBotProtocol(BotProtocol):
	'''
	I am a bot protocol which implements a debugging behavior. When debugging
	is enabled, no command nor message is sent to anyone, but everything is
	simply printed over the output channel
	'''
	def sendmsg (self, out, channel, message):
		if self.factory.debug:
			out.append ('%s \x02<-\x02 %s' % (channel, message))
		else:
			super(DebugBotProtocol, self).sendmsg (out, channel, message)
		
	def command (self, out, command, *args):
		if self.factory.debug:
			out.append ('\x02%s\x02 %s' % (command, ' '.join (args)))
		else:
			super(DebugBotProtocol, self).command (out, command, *args)
			
	@botcommand
	def debug (self, flow, out, user, channel, value = None):
		'''
		\x02debug\x02 [<value>]
		Displays the current debug flag status.
		If a value is specified, also set the flag status.
		'''
		if not value is None:
			self.factory.debug = not value == '0'
		out.append ('Debug is ' + ('enabled' if self.factory.debug else 'disabled'))
	
class HelpBotProtocol(BotProtocol):
	'''
	I am a bot protocol which implements a help command
	When an error occures, the help function is called as well
	'''
	def _error (self, error, out, user, channel, command, args):
		self.help (None, out, user, channel, command)
		super(HelpBotProtocol, self)._error (error, out, user, channel, command, args)
		
	@botcommand
	def help (self, flow, out, user, channel, command = None, *args):
		if command and self._check (user, channel, command, args):
			doc = getattr (self, command).__doc__
			out += ([line.strip () for line in doc.split ('\n') if not line.strip () == '']
			        if doc else ['No documentation available for %s' % (command,)])
		else:
			out.append ('\x02Available commands:\x02 ' + ', '.join (
				[x for x in BotRegister.commands.keys () if self._check (user, channel, x, [])]
			))
			
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

	def _handle (self, user, channel, message):
		'''
		Triggers the _sync method if necessary
		'''
		if channel in self.factory.sync:
			self._sync (user, channel, message)
		super(AsynchronousCallBotProtocol, self)._handle (user, channel, message)

		
class PermissionBotProtocol (BotProtocol):
	'''
	I am a bot protocol which implements a permission behavior to access
	the available commands, please overrides the _permit function to fit
	in your permission model
	'''
	def _check (self, user, channel, command, args):
		return (super(PermissionBotProtocol, self)._check (user, channel, command, args)
			and
			self._permit (user, channel, command, args)
		)
			   
	def _permit (self, user, channel, command, args):
		return False

class HostPermissionBotProtocol (PermissionBotProtocol):
	'''
	I am a bot protocol which implements a permission behavior relying on
	the host of the user who emits the command, you just have to provide
	me with granted hosts for every command
	'''
	def _permit (self, user, channel, command, args):	
		if command not in self.factory.permissions:
			return False
		for host in self.factory.permissions[command]:
			if re.match (host, user):
				return True
		return False
		
class WhoBotProtocol (BotProtocol):
	'''
	I am a bot protocol which implements the /who command to list users
	from a specific channel
	'''
	def _who (self, channel):
		if channel in self._whoqueries:
			return self._whoqueries[channel]
		else:
			self._whoqueries[channel] = Deferred ()
			self._whobuffers[channel] = []
			self.sendLine ('WHO %s' % channel)
			return self._whoqueries[channel]

	def irc_RPL_WHOREPLY (self, *nargs):
		server, args = nargs
		if args[1] in self._whoqueries:
			self._whobuffers[args[1]].append ((args[5], args[3], args[6]))
			
	def irc_RPL_ENDOFWHO (self, *nargs):
		server, args = nargs
		if args[1] in self._whoqueries:
			self._whoqueries[args[1]].callback (self._whobuffers[args[1]])
			del self._whoqueries[args[1]]
			del self._whobuffers[args[1]]
		
	@botcommand
	def who (self, flow, out, user, channel, what):
		return self._who (what)
		
	def connectionMade (self):
		'''
		Initialization of specific attributes
		'''
		self._whoqueries = {}
		self._whobuffers = {}
		super(WhoBotProtocol, self).connectionMade ()

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
		command = ' '.join (command).replace ('=>', '->')
		self._aliases[name] = command
		out.append ('\x02Saved %s as\x02: %s' % (name, command))

	@botcommand
	def listAliases (self, flow, out, user, channel):
		for name, command in self._aliases.items ():
			out.append ('\x02%s:\x02 %s' % (name, command))

	@botcommand
	def delAlias (self, flow, out, user, channel, name):
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
				self._handle (user, channel, self._aliases[name] % args)
			return new.instancemethod (f, self, self.__class__)
		else:
			raise AttributeError
	
				
class BotFactory (ClientFactory, object):
	'''
	I'm a generic irc bot factory
	'''
	def __init__ (self, nickname, password, channels, bang, pipe):
		self.nickname = nickname
		self.password = password
		self.channels = channels
		self.bang = bang
		self.pipe = pipe

	def clientConnectionLost (self, connector, reason):
		connector.connect ()
