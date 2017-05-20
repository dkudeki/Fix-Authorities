# -*- coding: utf-8 -*-
import csv, sys, json, os, datetime, time, copy, re, string, requests, logging
from datetime import timedelta
from StringIO import StringIO
from pymarc import Record, record_to_xml
from unicodedata import normalize
import xml.etree.ElementTree as ET
import codecs
from Tkinter import *
import OutputResults, HandleZ3950, GeneralUtilities, CheckSelection, HandlePersonalNames, HandleCorporateNames, HandleNameTitles, HandleTitles, HandleSubjects, gui

reload(sys)  
sys.setdefaultencoding('utf8')

#Read in the 245 field
def getWorkTitle(record):
	titles = record.get_fields('245')
	for title in titles:
		print "WORK TITLE: ", title
		work_title = {}
		work_title['subfields'] = {}
		for subfield_index in range(0,len(title.subfields),2):
			work_title['subfields'][title.subfields[subfield_index]] = title.subfields[subfield_index+1]

		print work_title['subfields']

	return work_title

#Search a Voyager record for all headings. Looks in the appropriate fields for the headings that are being fixed.
#	record - A Record object
#	Outputs a list of headings. Each heading in the list is a dictionary. Each dictionary has a field for each of the
#		subfields present in that heading
def linkProblematicHeadingsToVoyagerData(record,counts,problemed_headings,bib_fields):
	print "LINK PROBLEMATIC HEADINGS"
	print type(record)
	headings = []
	heading_scores = []

	for index in range(0,len(problemed_headings)):
		headings.append('')
		heading_scores.append(1000000000)

	print type(record)
	record_headings = record.get_fields(*bib_fields)
	for record_heading in record_headings:
		new_heading = {}
		new_heading['subfields'] = {}
		#The list of subfields is a list that is formatted as ['subfield tag', 'contents'], so info always comes in pairs
		print "Heading from Voyager: ", record_heading.subfields
		for subfield_index in range(0,len(record_heading.subfields),2):
			if record_heading.subfields[subfield_index] in new_heading['subfields']:
				if type(new_heading['subfields'][record_heading.subfields[subfield_index]]) is list:
					new_heading['subfields'][record_heading.subfields[subfield_index]].append(record_heading.subfields[subfield_index+1])
				else:
					new_heading['subfields'][record_heading.subfields[subfield_index]] = [new_heading['subfields'][record_heading.subfields[subfield_index]], record_heading.subfields[subfield_index+1]]
			else:
				new_heading['subfields'][record_heading.subfields[subfield_index]] = record_heading.subfields[subfield_index+1]
		new_heading['field'] = record_heading.tag

		for index in range(0,len(problemed_headings)):
			if 'a' in new_heading['subfields']:
				if '650' in bib_fields:
					potential_subfields = ['b','c','d','e','f','g','h','j','k','l','m','n','o','p','q','r','s','t','v','x','y','z','0','2','3','4','5','7','8']
				else:
					potential_subfields = ['b','c','d']
				similarity_score = GeneralUtilities.getSimilarityScore(problemed_headings[index],new_heading,potential_subfields)
				if similarity_score < heading_scores[index]:
					heading_scores[index] = similarity_score
					headings[index] = new_heading
					print similarity_score, problemed_headings[index], new_heading
#		print "HEADINGS SCORES: ", heading_scores
#		print "HEADINGS: ", headings
#		print new_heading

	index = 0
	print problemed_headings
	print headings
	while index < len(problemed_headings) and index < len(headings):
#		print headings[index]
#		print problemed_headings[index]
		if headings[index] != '':
			headings[index]['query version'] = problemed_headings[index]
		index += 1
	headings = [x for x in headings if x != '']
	print "FINAL HEADINGS LIST: ", headings
	counts['ignored_count'] += len(problemed_headings) - len(headings)
	return headings, counts

#Search for the heading with the appropriate web API, and use the results to determine if the heading is correct, incorect 
#	but changable, or totally incorrect. If the heading looks correct or if an authorized version is found, that result is
#	checked against OCLC's version of the bib record containing the error. If our solution is in the OCLC record, we take
#	that as independent confirmation of our results and output the results noting if the solution is a change or the same
#	as the input. If the heading isn't in the OCLC record, we still output the solution we selected, but note that the 
#	solution should be considered incorrect, and should not be written to the record.
def findHeading(name,oclc_number,lastCall,selected_results,results_type,bib_fields,version,options=[]):
	print 'VOYAGER NAME: ', name
	voyager_name_as_string = GeneralUtilities.buildHeadingAsString(name,['b','c','d','e','f','g','h','j','k','l','m','n','o','p','q','r','s','t','v','x','y','z','0','2','3','4','5','7','8'])

	if voyager_name_as_string in selected_results:
		lc_name = selected_results[voyager_name_as_string]['lc'][results_type]
		lc_number = selected_results[voyager_name_as_string]['lc']['lc_number']
		confident = True
	else:
		lc_name, lc_number, confident, lastCall = version.getBestSolution(name,lastCall,*options)

	if lc_name is None or not confident:
		return lc_name, lc_number, 'INCORRECT_CONFIDENCE', lastCall, voyager_name_as_string

	if CheckSelection.doubleCheckHeading(oclc_number,lc_name,bib_fields):
		#overwrite name in record

		if CheckSelection.checkHeadingEquality(name,lc_name,False):
			name_group = "CORRECT"
		else:
			name_group = "CHANGED"

		return lc_name, lc_number, name_group, lastCall, voyager_name_as_string
	else:
		return lc_name, lc_number, 'INCORRECT_CHECK', lastCall, voyager_name_as_string

#Process all the problematic headings of a single type in a single record and wirte the results to the appropraite
#	spreadsheets. Output updated counts and lists that contain the changes and the already correct headings.
def processHeadings(record,bib_ids,id_number,counts,writers,lastCall,heading_type,bib_fields,results_type,selected_results,counter_name,version,options=[]):
	headings, counts = linkProblematicHeadingsToVoyagerData(record,counts,bib_ids[id_number][heading_type],bib_fields)
	print bib_ids[id_number]

	correct_headings = []
	changed_headings = []
	incorrect_headings = []

	for heading in headings:
		print '~~~~~~~~~~~~~~~~~New ' + heading_type + '~~~~~~~~~~~~~~~~~'
		print 'RECORD ID NUMBER: ', id_number
		print 'RECORD DATA: ', bib_ids[id_number]
		counts[counter_name] += 1
		lc_heading, lc_number, heading_group, lastCall, voyager_name_as_string = findHeading(heading,bib_ids[id_number]['OCLC Number'],lastCall,selected_results,results_type,bib_fields,version,options)
		heading_results = { 
			'voyager': { 
				results_type: heading,
				'id_number': id_number
			},
			'lc': { 
				results_type: lc_heading,
				'lc_number': lc_number
			}
		}

		if 'INCORRECT' in heading_group:
			if 'CHECK' in heading_group:
				print "SHOULD HAVE CHECK: ", heading_group
				heading_results['error'] = "FAILED DOUBLE CHECK"
			else:
				print "SHOULD HAVE CONFIDENCE: ", heading_group
				heading_results['error'] = "LOW CONFIDENCE"

			incorrect_headings.append(heading_results)
		elif heading_group == 'CHANGED':
			changed_headings.append(heading_results)

			if voyager_name_as_string not in selected_results:
				selected_results[voyager_name_as_string] = heading_results
		else:
			correct_headings.append(heading_results)

			if voyager_name_as_string not in selected_results:
				selected_results[voyager_name_as_string] = heading_results

	counts = OutputResults.writeRecordResultsToSpreadsheet(record,correct_headings,changed_headings,incorrect_headings,results_type,counts,writers)

	return counts, lastCall, correct_headings, changed_headings

#Wrapper for processHeadings that passes specific info for personal names
def processNames(record,bib_ids,id_number,counts,writers,lastCall,heading_type,bib_fields,results_type,selected_results):
	bib_ids[id_number]['Work Title'] = getWorkTitle(record)
	return processHeadings(record,bib_ids,id_number,counts,writers,lastCall,heading_type,bib_fields,results_type,selected_results,'processed_personal_names_count',HandlePersonalNames,options=[bib_ids[id_number]['Work Title']])

#Wrapper for processHeadings that passes specific info for corporate names
def processCorporateNames(record,bib_ids,id_number,counts,writers,lastCall,heading_type,bib_fields,results_type,selected_results):
	return processHeadings(record,bib_ids,id_number,counts,writers,lastCall,heading_type,bib_fields,results_type,selected_results,'processed_corporate_names_count',HandleCorporateNames)

#Wrapper for processHeadings that passes specific info for name-titles
def processNameTitles(record,bib_ids,id_number,counts,writers,lastCall,heading_type,bib_fields,results_type,selected_results):
	return processHeadings(record,bib_ids,id_number,counts,writers,lastCall,heading_type,bib_fields,results_type,selected_results,'processed_name_titles_count',HandleNameTitles)

#Wrapper for processHeadings that passes specific info for titles
def processTitles(record,bib_ids,id_number,counts,writers,lastCall,heading_type,bib_fields,results_type,selected_results):
	return processHeadings(record,bib_ids,id_number,counts,writers,lastCall,heading_type,bib_fields,results_type,selected_results,'processed_titles_count',HandleTitles)

#Wrapper for processHeadings that passes specific info for subjects
def processSubjects(record,bib_ids,id_number,counts,writers,lastCall,heading_type,bib_fields,results_type,selected_results):
	return processHeadings(record,bib_ids,id_number,counts,writers,lastCall,heading_type,bib_fields,results_type,selected_results,'processed_subjects_count',HandleSubjects)

def makeOutputFolder(folder_name,counter):
	try:
		if counter is not None:
			write_folder_name = folder_name + ' (' + str(counter) + ')'
		else:
			write_folder_name = folder_name

		write_folder = os.mkdir(write_folder_name)
		return write_folder, write_folder_name
	except OSError:
		if counter is not None:
			return makeOutputFolder(folder_name,counter+1)
		else:
			return makeOutputFolder(folder_name,0)


#Open all the files for running output and build writers for them
def buildWriters(read_file,output_folder=None):
	if output_folder is not None:
		write_folder_name = output_folder +  '/fixed_' + read_file[read_file.rfind('/')+1:-4]
	else:
		write_folder_name = 'fixed_' + read_file[:-4]

	write_folder, write_folder_name = makeOutputFolder(write_folder_name,None)

	correct_csvfile = open(write_folder_name + '/correct.csv','w')
	correct_writer = csv.writer(correct_csvfile)

	changed_csvfile = open(write_folder_name + '/changed.csv','w')
	changed_writer = csv.writer(changed_csvfile)

	incorrect_csvfile = open(write_folder_name + '/incorrect.csv','w')
	incorrect_writer = csv.writer(incorrect_csvfile)

	writers = {
		'correct_writer': correct_writer,
		'changed_writer': changed_writer,
		'incorrect_writer': incorrect_writer,
	}

	csvfiles = {
		'correct_csvfile': correct_csvfile,
		'changed_csvfile': changed_csvfile,
		'incorrect_csvfile': incorrect_csvfile,
	}

	writers['incorrect_writer'].writerow(['BIBID','DATAFIELD','NAME FROM DATABASE','NAME FROM RECORD','BEST GUESS','LC NUMBER','REASON'])
	writers['changed_writer'].writerow(['BIBID','DATAFIELD','NAME FROM DATABASE','NAME FROM RECORD','LC NAME','LC NUMBER'])
	writers['correct_writer'].writerow(['BIBID','DATAFIELD','NAME FROM DATABASE','NAME FROM RECORD','LC NAME','LC NUMBER'])

	return writers, csvfiles, write_folder_name

def closeCsvfiles(csvfiles):
	for csvfile in csvfiles:
		csvfiles[csvfile].close()

#If the name is in an alphabet besides the Roman alphabet, then it is in the 880 field, which we aren't concerned with,
#	so we ignore it altogether
def removeNamesInNonRomanAlphabets(names_list,counts):
	romanized_names = []
	for name in names_list:
		uses_roman_characters = re.match(r'[^[0-9 -().,?]]*',name)

		if uses_roman_characters:
			print "NAME USES ROMAN CHARACTERS: ", name
			romanized_names.append(name)
		else:
			counts['ignored_count'] += 1

	return romanized_names, counts

#Record-level processing. Initialize counters, writers, memory and heading types. Write to error log, and write collections
#	when enough records have been corrected. Cycle through list of bib_id's and use the GetMARC tool to retrieve that record 
#	from Voyager. If the record exists, the processHeading functions are called and the results are written to the collections
#	and correct or changed spreadsheets. If the record doesn't exist, the relevant data is written to the incorrect spreadsheet. 
#	This is where we update the progress bar, after each record that has been iterated through.
def processBIBIDs(bib_ids,start,fix_records,progress_bar_object,read_file,output_folder=None,):
	counts = {
		'record_count': 0,
		'correct_count': 0,
		'changed_count': 0,
		'incorrect_count': 0,
		'ignored_count': 0,
		'personal_names_count': 0,
		'corporate_names_count': 0,
		'titles_count': 0,
		'name_titles_count': 0,
		'subjects_count': 0,
		'processed_personal_names_count': 0,
		'processed_corporate_names_count': 0,
		'processed_titles_count': 0,
		'processed_name_titles_count': 0,
		'processed_subjects_count': 0
	}

	writers, csvfiles, write_folder = buildWriters(read_file,output_folder)

	selected_results = {
		'Personal Name': {},
		'Corporate Name': {},
		'Subject': {},
		'Name-title': {},
		'Title': {}
	}

#	Basic info about each kind of heading. Commenting out an entry here stops that kind of heading from being processed. This is
#		where the different branches of the program begin branching.
	heading_type_settings = {
		'Personal Name': { 
			'heading_type': 'name',
			'bib_fields': ['100','700'],
			'count': 'personal_names_count',
			'function': processNames
		},
		'Corporate Name': {
			'heading_type': 'name',
			'bib_fields': ['110','710'],
			'count': 'corporate_names_count',
			'function': processCorporateNames
#		},
#		'Subject': {
#			'heading_type': 'subject',
#			'bib_fields': ['600','610','650'],
#			'count': 'subjects_count',
#			'function': processSubjects
#		},
#		'Name-title': {
#			'heading_type': 'name-title',
#			'bib_fields': ['600','700'],
#			'count': 'name_titles_count',
#			'function': processNameTitles
#		},
#		'Title': {
#			'heading_type': 'title',
#			'bib_fields': ['440','490','830'],
#			'count': 'titles_count',
#			'function': processTitles
		}
	}

	progress_bar_object.update_idletasks()
	progress_bar_object.update()

	log_filename = 'error_log.out'
	logging.basicConfig(filename=write_folder + '/' + log_filename, level=logging.DEBUG)
	
#	Try loop exists so crahses will be properly written to the logger before the whole thing breaks down
	try:
		with open(write_folder + '/' + log_filename,'w') as log_file:
			sys.stdout = GeneralUtilities.Logger(sys.stdout,log_file)
			collection_counter = 0
			record_counter = 0
			collection = '<?xml version="1.0" encoding="UTF-8"?>\n<collection xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:schemaLocation="http://www.loc.gov/MARC21/slim http://www.loc.gov/standards/marcxml/schema/MARC21slim.xsd" xmlns="http://www.loc.gov/MARC21/slim">\n'

			lastCall = ''
			for id_number in bib_ids:
				print '================NEW RECORD================'
				print 'RECORD ID#: ', id_number

				correct_headings = {
					'Personal Name': [],
					'Corporate Name': [],
					'Subject': [],
					'Name-title': [],
					'Title': []
				}
				changed_headings = {
					'Personal Name': [],
					'Corporate Name': [],
					'Subject': [],
					'Name-title': [],
					'Title': []
				}

				counts['personal_names_count'] += len(bib_ids[id_number]['Personal Name'])
				problemed_names, counts = removeNamesInNonRomanAlphabets(bib_ids[id_number]['Personal Name'],counts)
				bib_ids[id_number]['Personal Name'] = problemed_names

				counts['corporate_names_count'] += len(bib_ids[id_number]['Corporate Name'])

				counts['subjects_count'] += len(bib_ids[id_number]['Subject'])
				counts['name_titles_count'] += len(bib_ids[id_number]['Name-title'])
				counts['titles_count'] += len(bib_ids[id_number]['Title'])

				record = None
				if len(bib_ids[id_number]['Personal Name']) or len(bib_ids[id_number]['Corporate Name']) or len(bib_ids[id_number]['Title']) or len(bib_ids[id_number]['Name-title']) or len(bib_ids[id_number]['Subject']):
					record, error_type = HandleZ3950.callZ3950(id_number,'UIU')

				counts['record_count'] += 1

				print record
				if record:
					print record
					if fix_records:
						for version in heading_type_settings:
							print version
							if len(bib_ids[id_number][version]) > 0:
#								This is where we call the processHeading function for the specific heading type and feed it the appropriate
#									problematic headings. This calls the core functionality of the program.
								counts, lastCall, correct_headings[version], changed_headings[version] = heading_type_settings[version]['function'](record,bib_ids,id_number,counts,writers,lastCall,version,heading_type_settings[version]['bib_fields'],heading_type_settings[version]['heading_type'],selected_results[version])

					number_of_changes = 0
					for version in heading_type_settings:
						number_of_changes += len(changed_headings[version])

					if (number_of_changes > 0) or not fix_records:
						updated_record = OutputResults.writeChangesToRecord(record,correct_headings,changed_headings,heading_type_settings)
						collection += updated_record + '\n'
						record_counter += 1

						if record_counter % 120 == 0:
							collection += '</collection>'
							collection_output = open(write_folder + '/' + read_file[read_file.rfind('/')+1:-4] + '_for_upload' + str(collection_counter) + '.xml','w')
							collection_output.write(collection)
							collection_output.close()

							collection_counter += 1
							collection = '<?xml version="1.0" encoding="UTF-8"?>\n<collection xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:schemaLocation="http://www.loc.gov/MARC21/slim http://www.loc.gov/standards/marcxml/schema/MARC21slim.xsd" xmlns="http://www.loc.gov/MARC21/slim">\n'
				elif fix_records:
					#Add record to incorrect
					for version in heading_type_settings:
						unloaded_information = []

						problematic_headings = bib_ids[id_number][version]

						if len(problematic_headings) > 0:
							counts['processed_' + heading_type_settings[version]['count']] += len(problematic_headings)
							for index in range(0,len(problematic_headings)):
								unloaded_information.append({
									'voyager': {
										'id_number': id_number,
										heading_type_settings[version]['heading_type']: {
											'field': 'NA',
											'subfields': { 'a': 'NA' },
											'query version': problematic_headings[index] 
										}
									},
									'lc': {
										'lc_number': 'NA',
										heading_type_settings[version]['heading_type']: {
											'field': 'NA',
											'subfields': { 'a': 'NA' }
										}
									},
									'error': error_type
								})
							counts = OutputResults.writeRecordResultsToSpreadsheet(None,[],[],unloaded_information,heading_type_settings[version]['heading_type'],counts,writers)
						else:
							print "No Problematic " + version + 's'

					print "BROKEN LEADER"

				OutputResults.outputIncrementalStatusUpdate(counts)

				progress_bar_object.updateProgress()

				print 'NUMBER OF RECORDS PROCESSED: ', counts['record_count']	

			collection += '</collection>'
			collection_output = open(write_folder + '/' + read_file[read_file.rfind('/')+1:-4] + '_for_upload' + str(collection_counter) + '.xml','w')
			collection_output.write(collection)
			collection_output.close()

			closeCsvfiles(csvfiles)
			OutputResults.printResults(counts,start)

		logging.shutdown()
		os.remove(write_folder + '/' + log_filename)
	except:
		logging.exception('Crash report:')
		raise

#On Windows, the Command Prompt doesn't know how to display unicode characters, causing it to halt when it encounters non-ASCII characters
def setupByOS():
	if os.name == 'nt':
		if sys.stdout.encoding != 'cp850':
		  sys.stdout = codecs.getwriter('cp850')(sys.stdout, 'replace')
		if sys.stderr.encoding != 'cp850':
		  sys.stderr = codecs.getwriter('cp850')(sys.stderr, 'replace')

#Read the results of a SQL query into a list of dicts, each of which represents a unique record in the spreadsheet. Each
#	problematic heading in a record is sorted by heading type. Once everything has been read in, we have enough information
#	to build the progress bar.
def startup(input_file=None,output_folder=None,fix_records=True):
	#Make any adjustments based on what system is running the code
	setupByOS()
	start_time = datetime.datetime.now().time()

	if input_file is not None:
		read_file = input_file
	else:
		read_file = sys.argv[1]

	with open (read_file, 'rb') as readfile:
		reader = csv.reader(readfile)

		bibids = {}
		for row in reader:
			if row[7] != 'BIB_ID':
				if row[7] not in bibids:
					bibids[row[7]] = {
						'Personal Name': [],
						'Corporate Name': [],
						'Subject': [],
						'Name-title': [],
						'Title': [],
						'OCLC Number': row[8]
					}

				if row[0] == 'Name':
					if row[12] == 'personal name':
						bibids[row[7]]['Personal Name'].append(row[3])
					else:
						bibids[row[7]]['Corporate Name'].append(row[3])
				elif row[0] != '':
					bibids[row[7]][row[0]].append(row[3])

		for bibid in bibids:
			print bibids[bibid]

		progress_bar_object, root = gui.showProgress(len(bibids))
		processBIBIDs(bibids,start_time,fix_records,progress_bar_object,read_file,output_folder)

#From the command line you can either run the GUI or skip that and run the whole thing from the command line. The GUI is just
#	used for selecting the inputs. Either way we end up feeding 3 pieces of information to launch the program:
#		-The input file, a csv that comes from running one of the queries
#		-The output folder, where we want the results to be written to
#		-fix_records, if this value is true the full process is run and the records are fixed, if it's false the voyager records
#			are retrieved without being fixed. Default as true
if len(sys.argv) >= 2 and '.csv' in sys.argv[1]:
	if len(sys.argv) == 3:
		startup(input_file=sys.argv[1],output_folder=sys.argv[2])
	elif len(sys.argv) == 4:
		if sys.argv[3] == '-nofix':
			startup(input_file=sys.argv[1],output_folder=sys.argv[2],fix_records=False)
		else:
			startup(input_file=sys.argv[1],output_folder=sys.argv[2])
	else:
		startup()
else:
	file, folder, fix_records_boolean, root = gui.startGUI()
	root.destroy()
	startup(input_file=file,output_folder=folder,fix_records=fix_records_boolean)