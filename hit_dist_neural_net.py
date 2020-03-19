import os
import sys
# stderr = sys.stderr
# sys.stderr = open(os.devnull, 'w')
from keras.models import Sequential
from keras.layers import Dense
# sys.stderr = stderr
import pandas as pd
import numpy as np
import ast

def init_model():
	model = Sequential()
	model.add(Dense(12, input_dim=2, activation='relu'))
	model.add(Dense(8, activation='relu'))
	model.add(Dense(5, activation='softmax'))
	model.compile(loss='categorical_crossentropy', optimizer='adam', metrics=['accuracy'])
	return model

def format_data(df):
	data = []
	for i in df.index:
		for c in df.columns:
			val = df[c][i]
			if not (type(val)==float and np.isnan(val)):
				tup = ast.literal_eval(val)
				singles = int(tup[1])
				doubles = int(tup[2])
				triples= int(tup[3])
				homeruns = int(tup[4])
				outs = int(tup[0]) - sum((singles, doubles, triples, homeruns))
				data.extend([[i,c,1,0,0,0,0]]*outs)
				data.extend([[i,c,0,1,0,0,0]]*singles)
				data.extend([[i,c,0,0,1,0,0]]*doubles)
				data.extend([[i,c,0,0,0,1,0]]*triples)
				data.extend([[i,c,0,0,0,0,1]]*homeruns)
	data = np.array(data)
	X = data[:,0:2]
	X = np.array([[int(x[0]), int(x[1])] for x in X])
	y = data[:,2:]
	return X, y

def train_model():
	# load the dataset
	df = pd.read_csv('hit_prob_matrix.csv', delimiter=',', index_col=0)
	#formatting
	X, y = format_data(df)
	model = init_model()
	# fit the keras model on the dataset
	model.fit(X, y, epochs=150, batch_size=10)
	return model

def save_model(model, filename='model.h5'):
	model.save_weights(filename)

def load_model(filename='model.h5'):
	model = init_model()
	model.load_weights(filename)
	return model

def user_input(model):
	res = input('Save this model (Overwrite last model)')
	if res == 'y':
		save_model(model)
	elif res == 'n':
		pass
	else:
		print('Input not understood.')
		user_input(model)

if __name__ == '__main__':
	model = train_model()
	user_input(model)