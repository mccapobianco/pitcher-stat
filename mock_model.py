#mock model used for testing the calculation

class mock_model:
	def __init__(self, outcomes=[1,1,1,1,1]):
		if len(outcomes) != 5:
			raise ValueError('Incorrect number of outcomes')
		total = sum(outcomes)
		outcomes = [i/total for i in outcomes]
		self.outcomes = outcomes

	def predict(self, data):
		return self.outcomes