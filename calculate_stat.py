#expected change in run expectency
import ast
from hit_dist_neural_net import load_model
import numpy as np
import os
import pandas as pd
import progressbar
from pybaseball import playerid_lookup
from pybaseball import schedule_and_record
from pybaseball import statcast_pitcher
import re
import sys
import time


def get_pitcher_stats(player_id, year):
	""" returns a DataFrame containing data for all pitches that a pitcher threw in a year"""
	sys.stdout = open(os.devnull, "w") #prevent statcast_pitcher from printing to console
	stats = statcast_pitcher(str(year)+'-01-01', last_day(year), player_id) 
	sys.stdout = sys.__stdout__ #allow printing to console
	return stats

def last_day(year, team='NYY'):
	"""returns the last day of the regular season"""
	last_day_str=list(schedule_and_record(year, team)['Date'])[-1]
	last_day = time.strptime(last_day_str+', '+str(year), '%A, %b %d, %Y')
	last_day_str = time.strftime('%Y-%m-%d', last_day)
	return last_day_str

def get_id_table(): #player_ids from http://crunchtimebaseball.com/baseball_map.html
	table = pd.read_csv('player_ids.csv', encoding='latin-1')
	return table

def get_pitcher_list(): #player_list from https://www.baseball-reference.com/leagues/MLB/2019-standard-pitching.shtml
	table = pd.read_csv('player_list.csv', encoding='latin-1')
	table['Name'] = table['Name'].apply(format_player_name)
	return table

def format_player_name(string):
	"""get baseball-reference id from their name in pitcher list"""
	bref = re.split(r'\*?\\', string)[-1] #split at * or *\, select last str
	return bref

def get_player_table():
	"""merge id_table and pitcher_list"""
	#TODO output to csv
	ids = get_id_table()
	pitcher_list = get_pitcher_list()
	player_table = pd.merge(pitcher_list, ids, how='inner', left_on=['Name', 'Tm'], right_on=['bref_id', 'mlb_team'])
	player_table = player_table.loc[player_table['Name'] != 'LgAvg per 180 IP'] #remove extraneous row
	return player_table[['mlb_name','mlb_id']]

# def get_player_info(last_name, first_name):
# 	player_info = playerid_lookup(last_name, first_name)
# 	if len(player_info) > 1:
# 		s = 'Multiple Results Found. Please choose one:\n'
# 		i=0
# 		for index, player in player_info.iterrows():
# 			start = player['mlb_played_first']
# 			try:
# 				start = int(start)
# 			except:
# 				pass
# 			end = player['mlb_played_last']
# 			try:
# 				end = int(end)
# 			except:
# 				pass
# 			s += ('({}) '.format(i) + '{} {} played from {} to {}'.format(player['name_first'], player['name_last'], start, end))
# 			s += '\n'
# 			i+=1
# 		selection = input(s+'Choose (enter a number between 0 and {}): '.format(len(player_info)-1))
# 		return player_info.loc[int(selection)]
# 	else:
# 		print('Found player.')
# 		return player_info



def load_re_matrix():
	"""run expectation matrix"""
	return pd.read_csv('re_matrix.csv', delimiter='\t', index_col=0)

def load_hp_matrix():
	"""hit probability matrix"""
	df = pd.read_csv('hit_prob_matrix.csv', delimiter=',', index_col=0)
	df.columns = df.columns.astype(int)
	return df

def get_re_from_mat(matrix, outs, runner1, runner2, runner3):
	"""gets run expectation for a situation"""
	runners = runner1 + 2*runner2 + 4*runner3
	keys = ['0 Outs', '1 Out', '2 Outs']
	return matrix[keys[outs]][runners]

def runner_float2bool(runner):
	"""converts a runner value to a boolean (true if base is occupied)"""
	return not np.isnan(runner)

def get_velo_and_angle(pitch_data):
	velo = pitch_data['launch_speed']
	angle = pitch_data['launch_angle']
	return round(velo), round(angle)

def get_runners(pitch_data):
	runner1 = runner_float2bool(pitch_data['on_1b'])
	runner2 = runner_float2bool(pitch_data['on_2b'])
	runner3 = runner_float2bool(pitch_data['on_3b'])
	return (runner1, runner2, runner3)

def get_outs_and_runners(pitch_data):
	runner1, runner2, runner3 = get_runners(pitch_data)
	outs = pitch_data['outs_when_up']
	return (outs, runner1, runner2, runner3)

def get_start_re(pitch_data, re_matrix):
	"""calculates the run expectancy before the plate appearance"""
	outs, runner1, runner2, runner3 = get_outs_and_runners(pitch_data)
	return get_re_from_mat(re_matrix, outs, runner1, runner2, runner3)

def get_hp_data(hp_matrix, velo, angle):
	"""gets the hit distribution from angle & velo"""
	val = hp_matrix[velo][angle]
	tup = ast.literal_eval(val)
	return tuple(int(x) for x in tup)

def get_hp_data_from_nn(model, velo, angle):
	data = np.array([velo, angle]).reshape(1,-1)
	return model.predict(data)

def get_end_re(pitch_data, re_matrix, hp_matrix, model):
	"""gets run expectancy after a batted ball"""
	outs, runner1, runner2, runner3 = get_outs_and_runners(pitch_data)
	o, r1, r2, r3, runs = single(outs, runner1, runner2, runner3)
	single_re = get_re_from_mat(re_matrix, o, r1, r2, r3) + runs #run expectancy of a single
	o, r1, r2, r3, runs = double(outs, runner1, runner2, runner3)
	double_re = get_re_from_mat(re_matrix, o, r1, r2, r3) + runs #run expectancy of a double
	o, r1, r2, r3, runs = triple(outs, runner1, runner2, runner3)
	triple_re = get_re_from_mat(re_matrix, o, r1, r2, r3) + runs #run expectancy of a triple
	o, r1, r2, r3, runs = homerun(outs, runner1, runner2, runner3)
	homerun_re = get_re_from_mat(re_matrix, o, r1, r2, r3) + runs #run expectancy of a homerun
	o, r1, r2, r3, runs = out(outs, runner1, runner2, runner3)
	if o == 3:
		#if 3rd out of inning, run expectancy for that inning is 0
		out_re = 0 
	else:
		#otherwise get run expectancy from matrix
		out_re = get_re_from_mat(re_matrix, o, r1, r2, r3) + runs
	velo, angle = get_velo_and_angle(pitch_data)
	hp_data = get_hp_data_from_nn(model, velo, angle)
	#hp_data[i] => i=0: occurences | i=1: singles | i=2: doubles | i=3: triples | i=4: homeruns 
	# single_rate = hp_data[1] / hp_data[0]
	# double_rate = hp_data[2] / hp_data[0]
	# triple_rate = hp_data[3] / hp_data[0]
	# homerun_rate = hp_data[4] / hp_data[0]
	# out_rate = 1 - sum((single_rate, double_rate, triple_rate, homerun_rate))
	#TODO phase out hp_matrix
	out_rate, single_rate, double_rate, triple_rate, homerun_rate = hp_data
	#expected value: E(X) = ∑(X * P(X))
	exp_re = single_re*single_rate + double_re*double_rate + triple_re*triple_rate + homerun_re*homerun_rate + out_re*out_rate
	return exp_re

def change_in_re(pitch_data, re_matrix, hp_matrix, model):
	"""calculcate change in run expectancy from the beginning to the end of a plate appearance"""
	start = get_start_re(pitch_data, re_matrix)
	end = get_end_re(pitch_data, re_matrix, hp_matrix, model)
	delta = start - end #subtract this way so that higher number is better
	return delta

def single(outs, runner1, runner2, runner3):
	"""return the situation (outs & baserunners) that results from a single"""
	r1 = True
	r2 = runner1
	r3 = runner2
	runs = runner3
	return (outs, r1, r2, r3, runs)

def double(outs, runner1, runner2, runner3):
	"""return the situation (outs & baserunners) that results from a double"""
	r1 = False
	r2 = True
	r3 = runner1
	runs = (runner2+runner3)
	return (outs, r1, r2, r3, runs)

def triple(outs, runner1, runner2, runner3):
	"""return the situation (outs & baserunners) that results from a triple"""
	r1 = False
	r2 = False
	r3 = True
	runs = (runner1+runner2+runner3)
	return (outs, r1, r2, r3, runs)

def homerun(outs, runner1, runner2, runner3):
	"""return the situation (outs & baserunners) that results from a homerun"""
	r1 = False
	r2 = False
	r3 = False
	runs = (runner1+runner2+runner3+1)
	return (outs, r1, r2, r3, runs)

def out(outs, runner1, runner2, runner3):
	"""return the situation (outs & baserunners) that results from an out"""
	return (outs+1, runner1, runner2, runner3, 0)

def strikeout(re_matrix, pitch_data):
	"""returns the change in run expectancy follwing a strikeout"""
	outs, runner1, runner2, runner3 = get_outs_and_runners(pitch_data)
	if outs == 2:
		return get_re_from_mat(re_matrix, outs, runner1, runner2, runner3)
	else:
		return get_re_from_mat(re_matrix, outs, runner1, runner2, runner3)-get_re_from_mat(re_matrix, outs+1, runner1, runner2, runner3)

def walk(re_matrix, pitch_data):
	"""returns the change in run expectancy follwing a walk"""
	outs, runner1, runner2, runner3 = get_outs_and_runners(pitch_data)
	return get_re_from_mat(re_matrix, outs, runner1, runner2, runner3)-get_re_from_mat(re_matrix, outs, True, runner1, runner2)+runner3

def season_change_in_re(player_id, year, re_matrix, hp_matrix, model):
	"""calculates the expected change in run expectency for the entire season"""
	df = get_pitcher_stats(player_id, year)
	re = 0
	for index, row in df.iterrows():
		#if ball is put in play
		#TODO filter out before iteration
		if type(row['type']) == 'X':
			re += change_in_re(row, re_matrix, hp_matrix, model)
		#skip if event is a caught stealing
		#TODO filter out before iteration
		# elif row['events'] in ['caught_stealing_2b', 'caught_stealing_3b']:
		# 	continue
		#if strikeout, add strikeout change in run expectancy
		#TODO would this work? : elif 'strikeout' in row['events']
		elif row['events'] in ['strikeout', 'strikeout_double_play']:
			re += strikeout(re_matrix, row)
		#if bb or hbp, add walk change in run expectancy 
		elif row['events'] in ['walk', 'hit_by_pitch']:
			re += walk(re_matrix, row)
		#if pitch does not matter
		else:
			continue
	return re

def calculate(player_id, year, re_matrix, hp_matrix, model):
	"""calculate stat for one player"""
	
	return season_change_in_re(player_id, year, re_matrix, hp_matrix, model)

def calculate_all(year, player_table, progress=0):
	"""calculate stat for all players"""
	table = player_table.copy()
	row_count = len(table)
	re_matrix = load_re_matrix()
	hp_matrix = load_hp_matrix()
	model = load_model()
	bar = progressbar.ProgressBar(maxval=row_count, \
		widgets=[progressbar.Bar('=', '[', ']'), ' ', progressbar.Percentage(), ' | ', progressbar.ETA()])
	bar.start()
	stats = []
	for index, row in list(table.iterrows()):
		calc = calculate(row['mlb_id'], year, re_matrix, hp_matrix, model)
		stats.append(calc)
		bar.update(index+1)
	bar.update(row_count)
	table['Value'] = stats
	table.rename(columns={"mlb_name":"Name"}, inplace=True)
	table.sort_values(by="Value", inplace=True, ascending=False)
	table.index = np.arange(1,len(table)+1) #start index at 1 instead of 0
	return table

def export_values(calc_table, filename='values.csv'):
	"""export all players stats to a csv file"""
	try:
		with open(filename, 'w', newline='') as file:
			file.write(calc_table.to_csv())
	#if file is open, this error occurs. Try exporting again
	except (PermissionError):
		x = input('Error exported values. Enter a filename to export to or hit Enter to try the same filename again.')
		if not x:
			x = filename
		export_values(calc_table, x)
#TODO delete
# name = input('Enter pitcher name: ')
# year = input('Enter year: ')
# names = name.split(' ', 1) if ' ' in name else name
# re, error = calculate(names[1], names[0],year) if ' ' in name else calculate(names, None, year)
# print(name+"'s", str(year), "value is {:0.4f} (".format(re)+str(error), 'data points excluded)')

start = time.time()
print("Calculating all pitchers' values. This should take several minutes")
calc_table = calculate_all(2019, get_player_table())
export_values(calc_table)
print('\nDone in {} seconds'.format(int(np.ceil(time.time()-start))))
