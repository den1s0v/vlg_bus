# scrapper_main.py


from time import sleep
import os
from importlib import reload

import bus_scrapper as bus

# os.path.getmtime(path)

# print((bus_scrapper.__file__))

# bus_scrapper, reloaded = bus_scrapper.ifreload(bus_scrapper)

__mod_times = {}

def ifreload(module) -> ("module", "True if reloaded"):
	"""reload if the module has been changed"""
	global __mod_times
	reloaded = False
	t = os.path.getmtime(module.__file__)
	if module.__file__ in __mod_times:
		if t > __mod_times.get(module.__file__, 0):
			module = reload(module)
			reloaded = True
			__mod_times[module.__file__] = t
	else:
		__mod_times[module.__file__] = t
	return module, reloaded


if __name__ == '__main__':

	# prepare_dir(SAVED_DIR)
	# prepare_dir(HTML_DUMP_DIR)

	print('Starting...', flush=True)

	# read config
	workers = []
	with open("routes_in.txt") as f:
		lines = f.readlines()
		
	for line in lines:
		if not line:
			continue
		title, url = [s.strip() for s in line.split("::")]
		worker = bus.BusScraper(title, url)
		workers.append(worker)
		

	while True:
		try:
			bus, reloaded = ifreload(bus)
			if reloaded:
				# пересоздать все объекты с новым определением класса
				workers = [bus.BusScraper(w) for w in workers]

			for worker in workers:
				worker.run()
			
			sleep(bus.REQUEST_INTERVAL)

		except KeyboardInterrupt:
			if bus.really_exit_by_Ctrl_C():
				break

	print('\nFinished!')

