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

from twisted.internet.defer import Deferred
from core import BotProtocol, botcommand
from ast import literal_eval

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

	@botcommand
	def echo (self, flow, out, user, channel, *args):
		'''
		\x02echo\x02 <item> [<item> [...]]
		Simply outputs a list of items
		'''
		result = (flow if type(flow) is list else []) + list(args)
		result = [str(x) for x in result]
		out.append ('\x02Output:\x02 %s' % ', '.join (result))
		return result

	@botcommand
	def mass (self, flow, out, user, channel, *args):
		'''
		\x02mass\x02 <command> [<arguments>]
		Execute the command with the specified arguments mapped on every piped list item
		The arguments string must contain '%s' exactly once, which will hold the iterated items
		'''
		d = Deferred ()
		command = ' '.join (args).replace ('=>', '->')
		for item in flow:
			d.chainDeferred (self._handle (user, channel, command.replace ('?', item), True))
		d.callback (None)
		return d

class PyBotProtocol (BotProtocol):
	'''
	I am a bot protocol that allow the user to evaluate Python statements
	'''
	@botcommand
	def py (self, flow, out, user, channel, *args):
		'''
		\x02py\x02 <python statement>
		Executes the specified python statement. The incoming piped message is stored in 'x'
		Examples : 'py 1', 'py 1+1', 'py [1,2,3]'
		'''
		result = eval (' '.join (args),{'__builtins__':None},{'x': flow})
		if type (result) is list:
			result = [str (x) for x in result]
		else:
			result = [str (result)]
		out.append ('\x02Python:\x02 %s' % ', '.join (result))
		return result
