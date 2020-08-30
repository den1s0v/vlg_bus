""" Bus time saver
Date:       17.08.2020 - 30.08.2020


Usage examples:
===============


Requirements:
=============
- Python 3
- requests          (pip install requests)
- beautifulsoup4    (pip install beautifulsoup4)


"""

import requests, pickle, re, datetime, os
from bs4 import BeautifulSoup
# import csv
from time import sleep


print(__name__, "module loaded.")

REQUEST_INTERVAL = 2 * 60  # seconds
# REQUEST_INTERVAL = 10  # seconds   -- DEBUG

# DOMEN = 'http://transport.volganet.ru'

CTRL_C_TIMEOUT = 3 # seconds to think after you hit Ctrl+C before execution continues
MAX_FILENAME_LENGTH = 60

CLIENT_TZ = datetime.timedelta(hours=4)  # Volgograd timezone (UTC+4)


SAVED_DIR = 'saved/'
HTML_DUMP_DIR = 'html_dump/'

# Опции для http-запросов:      (полезно про то, как писать веб-парсеры: https://python-scripts.com/requests-rules)
# HEADERS = { 'User-Agent': 'Mozilla/5.0 (Windows NT 5.1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/57.0.2987.137 YaBrowser/17.4.1.919 Yowser/2.5 Safari/537.36' }
# HTTP_TIMEOUT = 15 # seconds

WEEKDAYS = list("ПН ВТ СР ЧТ ПТ СБ ВС".split())

def fit_filename(path, rename=False):
	"""Makes path valid: removes unsuported chars and renames if such file exists. """
	dir, filename = os.path.split(path)
	name, ext = os.path.splitext(filename)

	# remove extra chars
	name = re.sub(r'(?:%\d+)|[^а-яёa-z\s\d.,!@#$%\(\)=+_-]+', r'', name, flags=re.IGNORECASE).strip()
	name = re.sub(r'\s+',r'_', name)
	filename = name + ext

	# shrink filename if too long
	if(len(filename) > MAX_FILENAME_LENGTH):
		name = name[0:MAX_FILENAME_LENGTH-len(ext)]

	path = os.path.join(dir, name + ext)

	if not os.path.exists(path):
		return path

	# rename if exists  чтобы не затирать файл с таким же именем
	if rename:
		root, ext = os.path.splitext(path)
		count = 1
		while True:  # `do..while` emulation
			path = root + ' ('+str(count)+')' + ext
			if not os.path.exists(path):
				break
			count += 1

	return path


def really_exit_by_Ctrl_C():
	"Console helper. Returns True if user pressed Ctrl+C again wihin the interval of `CTRL_C_TIMEOUT` seconds."
	print("\n^C")
	print("To break the process, Press Ctrl+C once again.")
	print("Waiting for",CTRL_C_TIMEOUT,"seconds...", end='\t', flush=True)
	try:
		sleep(CTRL_C_TIMEOUT)
	except KeyboardInterrupt:
		print("\n^C")
		print("Stopping...", end='\n'*2, flush=True)
		return True # exit, stop working
	print("continue...")
	print() # add newline
	return False # no exit, continue working


def prepare_dir(dir):
	"""Checks the path and creates a directory if nesessary.
	If path does exist and is not a directory,
	or specified location is not writable, an exception is trown.

	"""
	if not os.path.exists(dir):
		# create a directory tree
		try:
			os.makedirs(dir, exist_ok=True)
		except Exception as e:
			terminate_with_error(str(e) + '\n\tOccured while preparing dir:',dir)
		print('Dir created.')
	else:
		# check write permission
		if not os.access(dir, os.F_OK | os.W_OK):
			terminate_with_error("directory is not accessible or writable: "+dir)


class BusScraper:
	def __init__(self, title, url=None):
		if not url:
			other = title  # copy state from other object
			assert other.__class__.__name__ == "BusScraper"
			self.title, self.url = other.title, other.url
			self.filepath = other.filepath
			self.header = other.header
			self.prev_result_str = other.prev_result_str
			self.collapse_row_written = other.collapse_row_written
		else:
			self.title = title
			self.url = url
			
			self.filepath = SAVED_DIR + title + ".tsv"
			self.header = None
			self.prev_result_str = ""
			self.collapse_row_written = False

	def run(self):
		self.scrap_bus_time_now()
		
	def get_page(self, url):
		for i in range(3):  # make 3 attempts
			try:
				# print("Requesting page: %s ..." % url)
				return requests.get(url).text
			except Exception as e:
				print("Requesting page time %d failed" % (i+1))
				error = e
		# raise error
		print("ERROR Requesting a page!")
		print("page URL: %s" % url)
		print(error)
		exit()

	def extract_time(self, html):
		result = {}
		print("Parsing page ... ", end="")
		soup = BeautifulSoup(html, "html.parser")
		
		update_time = soup.find("b").text
		
		result["Обновл."] = update_time
		
		print(update_time)
		
		table = soup.find("table")
		bus_here = False
		bus_distance = 0
		for tr in table.findAll("tr"):
			time_td, _, stop_td = list(tr.findAll("td"))
			time, stop = time_td.text, stop_td.text
			if "до ост.)" in stop:
				# обозначение автобуса
				bus_here = True
				bus_distance = re.search(r"\((.+) до ост.\)", stop).group(1)
				continue
			
			if bus_here:
				time = f"* {time} (-{bus_distance})"  # пометка: автобус подъезжает к этой остановке
				bus_here = False
			
			result[stop] = time
		return result

	def scrap_bus_time_now(self):
		data = {}
		now = datetime.datetime.utcnow() + CLIENT_TZ
		data["Дата"] = now.strftime("%Y.%m.%d")
		data["День"] = WEEKDAYS[now.weekday()]
		data["Время"]= now.strftime("%H:%M")
		dump_time    = now.strftime("%H:%M:%S")


		html = self.get_page(self.url)
		self.dump_html(data["Дата"] + "_" + dump_time, html)
		result = self.extract_time(html)
		# update_time = result["Обновл."]
		
		result_str = str(list(result.values())[1:])
		if result_str != self.prev_result_str:
			self.prev_result_str = result_str
			self.collapse_row_written = False
		elif not self.collapse_row_written:
			result = {k: "==/==" for k in result}
			self.collapse_row_written = True
		else:
			return
		
		data.update(result)
		
		if not self.header:
			self.header = list(data.keys())
			self.dump_list(self.header)
			
		row = [data[k] for k in self.header]
		self.dump_list(row)
		# return data

	def dump_list(self, csv_row):
		try:
			with open(self.filepath, "a", encoding="1251") as f:
				text = "\t".join(csv_row)  # CSV delimeter
				f.write(text)
				f.write("\n")
				
			csv_to_html_table(self.filepath, "\t", encoding_in="1251", max_rows=100)
			return True
		except OSError as e:
			print(f"Error writing file `{self.filepath}` :\n" + str(e))
			return None

	def dump_html(self, name_key, text):
		filepath = fit_filename(HTML_DUMP_DIR + f"{self.title}_{name_key}.htm", rename=True)
		try:
			with open(filepath, "w", encoding="utf-8") as f:
				f.write(text)
			return True
		except OSError as e:
			print(f"Error writing file `{filepath}` :\n" + str(e))
			return None


def csv_to_html_table(filepath, csv_sep=",", use_cols=None, encoding_in="utf8", encoding_out="utf8", max_rows=None):
	with open(filepath, "r", encoding=encoding_in) as f:
		lines = [r for r in f.readlines() if r]
	
	if not lines:
		return  # del the file..?
		
	rows = [r.split(csv_sep) for r in lines if r]
	header = rows[0]
	
	if use_cols:
		header_new = [v for v in header if v in use_cols]
		rows = [ 
			[row[header.index(h)] for h in header_new]
			for row in rows
		]
	header = rows[0]
	
	if not header:
		return  # del the file..?
		
	tr = """<tr>%s</tr>"""
	th = """<th>%s</th>"""
	td = """<td>%s</td>"""
	
	column_name2color = {
		"Дом детского": "#ffe789",
		"Казачий театр": "#9efebd",
	}
	column_index2color = {}
	for i,v in enumerate(header):
		for n in column_name2color:
			if n in v:
				column_index2color[i] = column_name2color[n]
				
		
	def render_td(v, i=None):
		td = """<td>%s</td>"""
		if i in column_index2color:
			td = f"""<td style="background-color:{column_index2color[i]}">%s</td>"""
		if v.startswith("*"):
			v = v[1:].strip()
			td = """<td style="background-color:#8cd7ff">%s</td>"""
		return td % v
		
	table_data = list(reversed(rows[1:]))[:max_rows]
		
	table_header = tr % "\n".join(th % v for v in rows[0])
	table_empty = tr % "\n".join(td % " " for v in rows[0])
	table_body = "\n".join(
			(tr % "\n".join(render_td(v, i) for i,v in enumerate(row))) 
			for row in table_data
	)
	
	
	html = f"""
	<head><meta charset="utf-8"></head>
	<h2>{filepath[(filepath.rfind("/")+1):(filepath.rfind("."))]}</h2>
	(последние данные - вверху)
	<table cellspacing="2" border="1" cellpadding="5" width="600">
		{table_header}
		{table_empty}
		{table_body}
		{table_empty}
		{table_header}
	</table>
	"""
	
	filepath_out = filepath[:(filepath.rfind("."))] + ".html"
	
	with open(filepath_out, "w", encoding=encoding_out) as f:
		f.write(html)
	

if __name__ == '__main__':
	print("run scrapper_main.py instead")

prepare_dir(SAVED_DIR)
prepare_dir(HTML_DUMP_DIR)

