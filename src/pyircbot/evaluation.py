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

class ListBulkingBotProtocol (BotProtocol):
	'''
	I am a bot protocol that allow users to manipulate lists without having to
	evaluate list comprehensions
	'''
	@botcommand
	def filter (self, flow, out, user, channel, *expr):
		'''
		\x02filter\x02 <expression>
		I filter the input list using the given Python expression, input list
		items are bound to 'x', the expression should evaluate to True or False
		'''
		expr = ' '.join (expr)
		return filter (lambda x: eval (expr,{'__builtins__':None},{'x': x}), flow)

	@botcommand
	def map (self, flow, out, user, channel, *expr):
		'''
		\x02map\x02 <expression>
		I map the given expression to the input list, the item being bount to the
		variable 'x'.
		'''
		expr = ' '.join (expr)
		return map (lambda x: eval (expr,{'__builtins__':None},{'x': x}), flow)
