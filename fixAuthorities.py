# -*- coding: utf-8 -*-
import csv, sys, json, os, datetime, time, copy, re, string, requests
from datetime import timedelta
from StringIO import StringIO
from unicodedata import normalize
import xml.etree.ElementTree as ET
import codecs
import GeneralUtilities, HandlePersonalNames

reload(sys)  
sys.setdefaultencoding('utf8')

#Process all the problematic headings of a single type in a single record and return the updated record if everything is good
def processHeadings(headings,nametype,outputtype,output_writer,find_function):
	for row in headings:
		print row
		find_function(row,nametype,outputtype)
		print "RESULTSRESULTSRESULTSRESULTSRESULTSRESULTSRESULTSRESULTSRESULTSRESULTSRESULTSRESULTSRESULTSRESULTSRESULTSRESULTSRESULTSRESULTSRESULTSRESULTSRESULTSRESULTS"
		print row
		output_writer.writerow(row)

	return headings

#Wrapper for processHeadings that passes specific info for personal names
def processNames(names,nametype,outputtype,output_writer):
	return processHeadings(names,nametype,outputtype,output_writer,HandlePersonalNames.findName)

#Wrapper for processHeadings that passes specific info for corporate names
def processCorporateNames(names,nametype,outputtype,output_writer):
	return processHeadings(names,nametype,outputtype,output_writer,HandleCorporateNames.findCorporateName)

#On Windows, the Command Prompt doesn't know how to display unicode characters, causing it to halt when it encounters non-ASCII characters
def setupByOS():
	if os.name == 'nt':
		if sys.stdout.encoding != 'cp850':
			sys.stdout = codecs.getwriter('cp850')(sys.stdout, 'replace')
		if sys.stderr.encoding != 'cp850':
			sys.stderr = codecs.getwriter('cp850')(sys.stderr, 'replace')

		return '\\'
	else:
		return '/'

#Read the results of a SQL query searching for problematic records
def startup():
	SLASH = setupByOS()
	read_file = sys.argv[len(sys.argv)-1]
	nametype = 'personal'
	if '-c' in sys.argv:
		nametype = 'corporate'

	outputtype = 'simple'
	if '-e' in sys.argv:
		outputtype = 'extended'

	with codecs.open(read_file, 'rU', 'utf-8') as readfile:
		reader = csv.DictReader(readfile,delimiter=',')

		rows = []
		label_row = []

		if outputtype == 'simple':
			label_row = ['VIAF LINK']
		else:
			label_row = ['VIAF NAME','VIAF LINK','VARIANTS','EN_WIKIPEDIA', 'FR_WIKIPEDIA']

		label_row = reader.fieldnames + label_row
		for row in reader:
			print row
			rows.append(row)

		print rows[0]
		print label_row

		slash_index = read_file.rfind(SLASH)
		if slash_index > -1:
			output_csvfile = open(read_file[:slash_index+1] + 'output_' + read_file[slash_index+1:],'w')
		else:
			output_csvfile = open('output_' + read_file,'w')

		output_writer = csv.DictWriter(output_csvfile,fieldnames=label_row)
		output_writer.writeheader()

		results = processNames(rows,nametype,outputtype,output_writer)

	output_csvfile.close()

startup()