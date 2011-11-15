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

class RawBotProtocol (BotProtocol):
	'''
	I am a bot protocol that alows the user to send raw information to the server
	'''			
	@botcommand
	def do (self, flow, out, user, channel, *args):
		'''
		\x02do\x02 <something>
		Sends something raw to the IRC server, this must be explicitelly
		allowed by the regexp mechanism
		'''
		command = args[0]
		args = ' '.join (args[1:])
		allowed = False
		if command in self.factory.do:
			for regexp in self.factory.do[command][0]:
				if re.search (regexp, args):
					allowed = True
			for regexp in self.factory.do[command][1]:
				if re.search (regexp, args):
					allowed = False
		if not allowed:
			out.append ('\x02Error\x02 Command not allowed')
		else:
			out .append ('\x02Do:\x02 [%s] %s' % (command, args))
			self.command (out, command, args)

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
	
	@inlineCallbacks	
	@botcommand
	def who (self, flow, out, user, channel, what):
		'''
		\x02who\x02 <channel>
		Lists the users from the given channel, output flow is a list like
		following:
			
			[(<nickname>, <host>, <mode>,), ...]
		'''
		result = yield self._who (what)
		print result
		out.append ('\x02Channels %s:\x02 %s' % (what, ', '.join ([x[0] for x in result])))
		returnValue (result)
		
	def connectionMade (self):
		'''
		Initialization of specific attributes
		'''
		self._whoqueries = {}
		self._whobuffers = {}
		super(WhoBotProtocol, self).connectionMade ()


