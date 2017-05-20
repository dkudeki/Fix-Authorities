# -*- coding: utf-8 -*-
import csv, sys, json, os, datetime, time, copy, re, string, requests
from datetime import timedelta
from StringIO import StringIO
from pymarc import Record, record_to_xml
from unicodedata import normalize
import xml.etree.ElementTree as ET
import codecs
import GeneralUtilities

#Overwrite all subfields in suggestion, remove all other subfields. Except the '6' subfield, which should never be touched
#	so that we can maintain the link to the 880 field
def buildSubfieldTagLists(lc_name):
	master_subfield_list = ['a','b','c','d','e','f','g','h','j','k','l','m','n','o','p','q','r','s','t','u','v','w','x','y','z','0','2','3','4','5','7','8']
	overwritelist = []
	removelist = []
	for tag in master_subfield_list:
		if tag in lc_name['subfields']:
			overwritelist.append(tag)
		else:
			removelist.append(tag)

	print lc_name
	print overwritelist
	print removelist

	return overwritelist, removelist

#Every subfield in name should be added, but we don't want to overwrite any extra subfields the record may have,
#	so we are overwriting only the subfields the authorized name has. This makes a checklist to see what subfields
#	were present in the old record and were overwritten, and what subfields need a new subfield written
def writeHeadingsToRecord(record,headings,heading_type,bib_fields):
	print record
	record_headings = record.get_fields(*bib_fields)

	for rh in record_headings:
		print rh.tag, rh.subfields

	for heading in headings:
		overwrite_subfields, remove_subfields = buildSubfieldTagLists(heading['lc'][heading_type])
		not_found = True
		record_heading_index = 0
		while not_found and record_heading_index < len(record_headings):
			if record_headings[record_heading_index].tag == heading['voyager'][heading_type]['field'] and 'a' in record_headings[record_heading_index] and 'a' in heading['voyager'][heading_type]['subfields'] and record_headings[record_heading_index]['a'].replace('.','') == heading['voyager'][heading_type]['subfields']['a'].replace('.',''):
				for tag in overwrite_subfields:
					if tag in record_headings[record_heading_index]:
						if type(heading['lc'][heading_type]['subfields'][tag]) is list:
							record_headings[record_heading_index].delete_subfield(tag)
							for instance in range(0,len(heading['lc'][heading_type]['subfields'][tag])):
								record_headings[record_heading_index].add_subfield(tag,heading['lc'][heading_type]['subfields'][tag][instance])
						else:
							record_headings[record_heading_index].delete_subfield(tag)
							record_headings[record_heading_index].add_subfield(tag,heading['lc'][heading_type]['subfields'][tag])
#						except KeyError:
#							record_headings[record_heading_index].delete_subfield(tag)
#							record_headings[record_heading_index].add_subfield(tag,heading['lc'][heading_type]['subfields'][tag])
					else:
						if type(heading['lc'][heading_type]['subfields'][tag]) is list:
							for instance in range(0,len(heading['lc'][heading_type]['subfields'][tag])):
								record_headings[record_heading_index].add_subfield(tag,heading['lc'][heading_type]['subfields'][tag][instance])
						else:
							record_headings[record_heading_index].add_subfield(tag,heading['lc'][heading_type]['subfields'][tag])

				for tag in remove_subfields:
					if tag in record_headings[record_heading_index]:
						record_headings[record_heading_index].delete_subfield(tag)

			record_heading_index += 1
		print heading

	print record
	return record
#	return record_to_xml(record)

def createWriteRow(id_number,name,lc_name,lc_number,error_reason):
	sequence = ['b','c','d','e','f','g','h','j','k','l','m','n','o','p','q','r','s','t','v','x','y','z','0','2','3','4','5','7','8']
	output = [id_number,name['field'],''.join(name['query version']).encode('utf-8')]
	output.append(GeneralUtilities.buildHeadingAsString(name,sequence))

	if lc_name is not None:
		output.append(GeneralUtilities.buildHeadingAsString(lc_name,sequence))
		output.append(lc_number)
	else:
		output.append('None')
		output.append('None')

	if error_reason is not None:
		output.append(error_reason)

	print "WRITE ROW: ", output
	return output

#Record our results onto spreadsheets that make each processed heading easily readable and sortable. Correct lists the headings that
#	were already authorized. Incorrect lists the headings that were not authorized, but we couldn't find a good solution to. If a
#	bad solution is found it is listed as a jumping off point for a human looking for the soluiton. Changed lists the headings that
#	we were able to find a good solution for, and it lists the original unauthorized name as well as our solution.
def writeRecordResultsToSpreadsheet(record,correct_headings,changed_headings,incorrect_headings,heading_type,counts,writers):
	#Correct and changed values to be written to record and the appropriate spreadsheet, incorrect or missing values written to spreadsheet
	counts['correct_count'] += len(correct_headings)
	counts['changed_count'] += len(changed_headings)
	counts['incorrect_count'] += len(incorrect_headings)

	for heading in correct_headings:
		writers['correct_writer'].writerow(createWriteRow(heading['voyager']['id_number'],heading['voyager'][heading_type],heading['lc'][heading_type],heading['lc']['lc_number'],None)) 
	for heading in changed_headings:
		writers['changed_writer'].writerow(createWriteRow(heading['voyager']['id_number'],heading['voyager'][heading_type],heading['lc'][heading_type],heading['lc']['lc_number'],None))
	for heading in incorrect_headings:
		writers['incorrect_writer'].writerow(createWriteRow(heading['voyager']['id_number'],heading['voyager'][heading_type],heading['lc'][heading_type],heading['lc']['lc_number'],heading['error']))

	print incorrect_headings
	print len(incorrect_headings)

	return counts

def writeChangesToRecord(record,correct_headings,changed_headings,heading_type_settings):
	for heading_type in changed_headings:
		if len(correct_headings[heading_type]) > 0 or len(changed_headings[heading_type]) > 0:
			print heading_type
			print correct_headings[heading_type]
			print changed_headings[heading_type]
			print heading_type_settings
			print heading_type_settings
			record = writeHeadingsToRecord(record,correct_headings[heading_type] + changed_headings[heading_type],heading_type_settings[heading_type]['heading_type'],heading_type_settings[heading_type]['bib_fields'])

	if record is not None:
		return record_to_xml(record)


#Statistical output
def printResults(counts,start):
	print(' FINAL RESULTS '.center(80,'*'))
	print "Start time: " + str(start)
	end_time = datetime.datetime.now().time()
	print "End time: " + str(end_time)
	print "Run duration: " + str(datetime.datetime.combine(datetime.date.min,end_time)-datetime.datetime.combine(datetime.date.min,start))
	print "Number of Records: " + str(counts['record_count'])
	print "Total Number of Names: " + str(counts['personal_names_count'] + counts['corporate_names_count'])
	print "Total Number of Titles: " + str(counts['titles_count'])
	print "Total Number of Name-titles: " + str(counts['name_titles_count'])
	print "Total Number of Subjects: " + str(counts['subjects_count'])
	print "Number of Names Ignored (Names from the 8XX field): " + str(counts['ignored_count'])
	print "Number of Names Processed: (Names from 100, 110, 700 or 710 fields): " + str(counts['processed_personal_names_count'] + counts['processed_corporate_names_count'])
	print "Number of Processed Headings Fixed: " + str(counts['changed_count'] + counts['correct_count'])
	print "Number of Processed Headings Not Fixed: " + str(counts['incorrect_count'])
	processed_headings_count = counts['processed_personal_names_count'] + counts['processed_corporate_names_count'] + counts['processed_titles_count'] + counts['processed_name_titles_count'] + counts['processed_subjects_count']
	if processed_headings_count > 0:
		print "Percent of headings that were already authorized: " + str(100.00 * counts['correct_count']/processed_headings_count)
		print "Percent of headings different than the LC name: " + str(100.00 * counts['changed_count']/processed_headings_count)
		print "Percent of headings that cannot be found in VIAF: " + str(100.00 * counts['incorrect_count']/processed_headings_count)

#When a record has been processed, print out the status of how many of each kind of record has been processed,
#	with counts from the most recent record added
def outputIncrementalStatusUpdate(counts):
	template = "{0:7}   {1:12}   {2:8}   {3:8}   {4:10}   {5:10}   {6:11}"
	print template.format('#RECORD', '#TOTAL_HEADINGS', '#CORRECT', '#CHANGED', '#INCORRECT', '#PROCESSED', '#8XXIGNORED')
	print template.format(counts['record_count'], counts['personal_names_count'] + counts['corporate_names_count'] + counts['titles_count'] + counts['name_titles_count'] + counts['subjects_count'], counts['correct_count'], counts['changed_count'], counts['incorrect_count'], counts['processed_personal_names_count'] + counts['processed_corporate_names_count'] + counts['processed_titles_count'] + counts['processed_name_titles_count'] + counts['processed_subjects_count'], counts['ignored_count'])