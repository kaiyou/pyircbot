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

from twisted.words.protocols.irc import IRCClient
from twisted.internet.protocol import ClientFactory
from twisted.internet.defer import Deferred
from twisted.python import log

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
		return flow

	def _error (self, error, out, user, channel, command, args):
		'''
		Called when one step of the handling chain failed
		'''
		log.err (error)

	def _handle (self, user, channel, message, wrap = False):
		'''
		Handles a message sent directly to the robot
		'''
		commands = message.split('->') # separates the commands
		commands = [x.split(' ') for x in commands] # splitting
		commands = [(words[0], words[1:]) for words in commands]

		d = Deferred()
		if not all([self._check (user, channel, command, args) for command, args in commands]):
			return d
		if wrap:
			command, args = commands[0] # first command, setting up
			d.addCallback(self._setup, [], user, channel, command, args)
		for command, args in commands: # chaining every command
			out = []
			function = getattr (self, command)
			d.addCallback(function, out, user, channel, *args)
			d.addErrback(self._error, out, user, channel, command, args)
		if wrap:
			command, args = commands[-1] # tearing down
			d.addCallback(self._teardown, out, user, channel, command, args)
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
		self._handle (user, channel, message, True).callback (None)
			
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
