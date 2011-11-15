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

from core import BotProtocol
from datetime import datetime

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

class VersionBotProtocol (BotProtocol):
	'''
	I am a bot protocol aware of its imlementation version
	'''
	@botcommand
	def version (self, flow, out, user, channel):
		out.append ('Bot version: %s, running since %s' % (self.__version__, str (self._startTime)))
		out.append ('PyIRCBot version: %s, visit %s' % (pyircbot.__version__, pyircbot.website))
		out.append ('This is free software, feel free to use, modify, extend and contribute')

	def connectionMade (self):
		self._startTime = datetime.now ()
		super (VersionBotProtocol, self).connectionMade ()
