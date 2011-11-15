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

# This is a Cow example
# Just say mooooooo on a random chan, it will reply in cow language
# Do not insult the Cow or you will get some really angry moooooooes

# Please note this implentation is perfectly wrong, just to illustrate
# how you can hack into PyIRCBot design to drive it with runtime built
# functions and whatsoever

from ..core import *
from random import choice

class CowBotProtocol (BotProtocol):
	moes = ['o'*i for i in range(30)]

	def _check (self, user, channel, command, args):
		return command in CowBotProtocol.moes and args == []

	def __getattr__ (self, name):
		if name in CowBotProtocol.moes:
			return self.mooo
			
	def mooo (self, flow, out, user, channel):
		mo = 'm' + ''.join ([choice(['o','0']) 
				     for i in range(choice(range(5,30)))])
		self.command ('

class CowBotFactory (BotFactory):
	protocol = CowBotProtocol
	bang = 'moooo'

