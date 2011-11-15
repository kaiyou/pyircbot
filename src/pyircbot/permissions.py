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

import re

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
