from pybaseball import statcast
import pandas
end_days = {3:31, 4:30, 5:31, 6:30, 7:31, 8:31, 9:30}
for month in range(3,10):
	a = statcast('2019-0{}-01'.format(month), '2019-0{}'.format(month) + '-%02d'%end_days[month])#[['des', 'events', 'pitcher', 'on_1b', 'on_2b', 'on_3b', 'launch_speed', 'launch_angle', 'outs_when_up']]
	a.to_csv('data/statcast_data{}.csv'.format(month),  chunksize=1000)