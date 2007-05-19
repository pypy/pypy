
class W_Root(object):

	def is_pair(self):
		return False

	def to_string(self):
		return ''

	def to_boolean(self):
		return False

	def __str__(self):
		return self.to_string()

class W_Boolean(W_Root):
	pass

class W_False(W_Boolean):

	def to_string(self):
		return "#f"

class W_True(W_Boolean):

	def to_boolean(self):
		return True
		
	def to_string(self):
		return "#t"
