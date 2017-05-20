# -*- coding: utf-8 -*-
import sys, json, os, datetime, time, copy, re, string, requests
from datetime import timedelta
from StringIO import StringIO
from pymarc import Record, record_to_xml
from unicodedata import normalize
import xml.etree.ElementTree as ET
import codecs
import GeneralUtilities

def removeOCLCHeader(oclc_number):
	cutoff = oclc_number.find('m')
	if cutoff == -1:
		cutoff = oclc_number.find('n')
	return oclc_number[cutoff+1:].rstrip()

def buildChecklist(lc_name):
	checklist = {}
	for tag in lc_name['subfields']:
		if type(lc_name['subfields'][tag]) is list:
			checklist[tag] = []
			for instance in range(0,len(lc_name['subfields'][tag])):
				checklist[tag].append(False)
		else:
			checklist[tag] = False
	return checklist

#Check that two headings and all their subfields are exactly the same
#	Returns True when headings are identical, and False when they are not
#	ignore_punctuation is a boolean that removes periods and commas from both headings before we check them
def checkHeadingEquality(heading1,heading2,ignore_punctuation):
	if len(heading1['subfields']) != len(heading2['subfields']):
		print heading1['subfields']
		print len(heading1['subfields'])
		print heading2['subfields']
		print len(heading2['subfields'])
		print "NAMES ARE DIFFERENT"
		return False
	else:
		print "NAME 1: ", heading1, heading1['subfields'].keys()
		print "NAME 2: ", heading2, heading2['subfields'].keys()
		if heading1['subfields'].keys() == heading2['subfields'].keys():
			print "SAME SUBFIELDS"
			for key in heading1['subfields'].keys():
				if type(heading1['subfields'][key]) is list:
					if type(heading2['subfields'][key]) is not list:
						return False

					for instance in range(0,len(heading1['subfields'][key])):
						if ignore_punctuation:
							print heading1['subfields'][key][instance].replace('.','').replace(',','') + ' vs ' + heading2['subfields'][key][instance].replace('.','').replace(',','')
							if heading1['subfields'][key][instance].replace('.','').replace(',','') != heading2['subfields'][key][instance].replace('.','').replace(',',''):
								return False
						else:
							print heading1['subfields'][key][instance] + ' vs ' + heading2['subfields'][key][instance]
							if heading1['subfields'][key][instance] != heading2['subfields'][key][instance]:
								return False
				else:
					if type(heading2['subfields'][key]) is list:
						return False
					else:
						if ignore_punctuation:
							print heading1['subfields'][key].replace('.','').replace(',','') + ' vs ' + heading2['subfields'][key].replace('.','').replace(',','')
							if heading1['subfields'][key].replace('.','').replace(',','') != heading2['subfields'][key].replace('.','').replace(',',''):
								return False
						else:
							print heading1['subfields'][key] + ' vs ' + heading2['subfields'][key]
							if heading1['subfields'][key] != heading2['subfields'][key]:
								return False

			#All Subfields are the same
			return True
		else:
			return False

def getKey():
	try:
		with open('WorldCatKey.txt','r') as keyfile:
			key = keyfile.read()

		return key
	except:
		print "No WorldCat key detected. A key to access the WorldCat API should be written to 'WorldCatKey.txt' and placed in the same folder as 'fixAuthorities.py'"

#Call WorldCat API to get OCLC record, then check all the names to see if any of them match the lc_heading
def doubleCheckHeading(oclc_number,lc_heading,heading_tags):
	oclc_number = removeOCLCHeader(oclc_number)
	key = getKey()
	print 'DOUBLE CHECK: ', lc_heading
	oclc_record = GeneralUtilities.getRequest('http://www.worldcat.org/webservices/catalog/content/' + oclc_number + '?wskey=' + key,True)
	if '<title> - Error report</title>' in oclc_record:
		return False
	checklist = buildChecklist(lc_heading)
	oclc_headings = []
	print oclc_record
	tree = ET.fromstring(oclc_record)
	for datafield in tree:
		if 'datafield' in datafield.tag and datafield.attrib['tag'] in heading_tags:
			new_oclc_heading = {}
			new_oclc_heading['subfields'] = {}
			for subfield in datafield:
				if subfield.attrib['code'] in new_oclc_heading['subfields']:
					if type(new_oclc_heading['subfields'][subfield.attrib['code']]) is list:
						new_oclc_heading['subfields'][subfield.attrib['code']].append(subfield.text)
					else:
						new_oclc_heading['subfields'][subfield.attrib['code']] = [new_oclc_heading['subfields'][subfield.attrib['code']], subfield.text]
				else:
					new_oclc_heading['subfields'][subfield.attrib['code']] = subfield.text
#	The following code checks that the subfields in the selected LC name are in OCLC and are the same, but it does not exclude
#		OCLC records with additional subfields.

				if subfield.attrib['code'] in lc_heading['subfields']:
					if type(lc_heading['subfields'][subfield.attrib['code']]) is list:
						if len(lc_heading['subfields'][subfield.attrib['code']]) <= len(new_oclc_heading['subfields'][subfield.attrib['code']]):
							for instance in range(0,len(lc_heading['subfields'][subfield.attrib['code']])):
								print lc_heading['subfields'][subfield.attrib['code']][instance].replace('.','').replace(',','') + ' vs ' + subfield.text.replace('.','').replace(',','')
								if lc_heading['subfields'][subfield.attrib['code']][instance].replace('.','').replace(',','') == subfield.text.replace('.','').replace(',',''):
									checklist[subfield.attrib['code']][instance] = True
					else:
						print lc_heading['subfields'][subfield.attrib['code']].replace('.','').replace(',','') + ' vs ' + subfield.text.replace('.','').replace(',','')
						if lc_heading['subfields'][subfield.attrib['code']].replace('.','').replace(',','') == subfield.text.replace('.','').replace(',',''):
							checklist[subfield.attrib['code']] = True

	if checklist['a'] == True:
		print checklist
		if False in checklist.values():
			return False
		else:
			return True
	else:
		return False

#	The following code looks for an exact match between the selected LC name, and the equivalent name in OCLC. It turns out this gives
#		us worse results that aren't really more accurate
#
#			oclc_headings.append(new_oclc_heading)
#
#	print "OCLC NAMES: ", oclc_headings
#
#	for oclc_heading in oclc_headings:
#		if checHeadingEquality(lc_heading,oclc_heading,True):
#			return True
#
#	return False