# -*- coding: utf-8 -*-
import sys, json, os, datetime, time, copy, re, string, requests
from datetime import timedelta
from StringIO import StringIO
from pymarc import Record, record_to_xml
from unicodedata import normalize
from lxml import html
import codecs
import HTMLParser
import CheckSelection, GeneralUtilities, HandleZ3950

def removeSpecificBrokenCharacters(name):
	to_convert_index = name.find('&#x')
	while (to_convert_index != -1):
		to_convert = name[to_convert_index:to_convert_index+8]
		converted = unichr(int(to_convert[3:-1],16))
		name = name.replace(to_convert,converted)
		to_convert_index = name.find('&#x')

	return name

def removeNonASCIICharacters(name):
	name_copy = copy.deepcopy(name)
	print "BEFORE CHANGE:\n\t", name, '\n\t', name_copy
	print name_copy
	name_copy = normalize('NFD', name_copy)
	name_copy = ''.join([i if ord(i) < 128 else '' for i in name_copy])
	print "AFTER CHANGE:\n\t", name, '\n\t', name_copy
	return name_copy

def removePuncuationAndNonASCIICharacters(name):
	return removeNonASCIICharacters(''.join([ch for ch in name if ch not in string.punctuation]))

def isASCII(string):
	try:
		results = string['subfields']['a'].decode('ascii')
		return True
	except UnicodeDecodeError:
		return False

def removeComma(name):
	print name
	first_comma_index = name.find(',')
	if first_comma_index == -1:
		return name
	else:
		part_two = name[:first_comma_index]
		part_one = name[first_comma_index+2:]
		return_string = part_one + ' ' + part_two
		return return_string.lstrip()

def removeCommaAndNonASCIICharacters(name):
	return removeNonASCIICharacters(removeComma(name))

#Try to set up string to add to the URL to call the AutoSuggest API with. If results are returned, weed out irrelevent ones
#	filter_function should vary by heading type to select only suggestions of that specific heading type
def searchQueryVariation(heading,url,search_method,filter_function,first_try):
	search_heading = search_method(heading)

	try:
		h = HTMLParser.HTMLParser()
		search_heading = h.unescape(search_heading)
	except:
		pass

	#Certain methods require a specific subfield to exist, if it does not the heading comes back as False and this method can
	#	return no meaningful results
	if not search_heading:
		return { 'result': None }

	full_url = url + search_heading

	if 'id.worldcat.org' in url:
		full_url += '&maximumRecords=10&sortKeys=usage'

	print "SEARCH QUERY: ", search_heading
	print full_url

	suggestion = None
	while suggestion is None:
		try:
			suggestion_string = GeneralUtilities.getRequest(full_url,False)

			print "GOT DATA"
			print suggestion_string

			if 'id.worldcat.org' in url:
				tree = html.fromstring(suggestion_string)
				suggestion = { 'result': tree }
			else:
				suggestion = json.JSONDecoder().decode(suggestion_string)
		except:
			pass
	print "TRANSLATED DATA"

	if suggestion['result'] is not None:
		suggestion['result'] = filter_function(suggestion)

	if suggestion['result'] is None and first_try and not isASCII(heading):
		#Second pass of each method removes characters that may have been wrongly encoded
		print "REPEATING SEARCH WITHOUT NON-ASCII CHARACTERS"
		heading_copy = copy.deepcopy(heading)
		heading_copy['subfields']['a'] = removeNonASCIICharacters(heading['subfields']['a'])
		return searchQueryVariation(heading_copy,url,search_method,filter_function,False)
	else:
		return suggestion

def SRUSearchQueryVariation(heading,url,search_method,first_try):
	search_heading = search_method(heading)

	try:
		h = HTMLParser.HTMLParser()
		search_heading = h.unescape(search_heading)
	except:
		pass

	if not search_heading:
		return []

	full_url = url + search_heading + '"+and+local.sources+any+"lc"&sortKeys=holdingscount&httpAccept=application/json'

	print "SEARCH QUERY: ", search_heading
	print full_url

	suggestion = None
	while suggestion is None:
		try:
			suggestion_string = GeneralUtilities.getRequest(full_url,False)

			print "GOT DATA"
			print suggestion_string

			suggestion = json.JSONDecoder().decode(suggestion_string)
		except:
			pass
	print "TRANSLATED DATA"

	if suggestion['searchRetrieveResponse'] is not None:
		#In the future we may want to make lccns a dict with the variation results, which are written in here, but for now we're just getting the LCCNs
		lccns = []
		number_of_records = int(suggestion['searchRetrieveResponse']['numberOfRecords'])
		print str(number_of_records) + ' RECORDS SUGGESTED BY SRU'
		if number_of_records > 0:
			for index in range(0,len(suggestion['searchRetrieveResponse']['records'])):
				if type(suggestion['searchRetrieveResponse']['records'][index]['record']['recordData']['sources']['source']) is list:
					for instance in range(0,len(suggestion['searchRetrieveResponse']['records'][index]['record']['recordData']['sources']['source'])):
						if suggestion['searchRetrieveResponse']['records'][index]['record']['recordData']['sources']['source'][instance]['#text'][:2] == 'LC' and suggestion['searchRetrieveResponse']['records'][index]['record']['recordData']['sources']['source'][instance]['@nsid'] not in lccns:
							lccns.append(suggestion['searchRetrieveResponse']['records'][index]['record']['recordData']['sources']['source'][instance]['@nsid'])
				else:
					if suggestion['searchRetrieveResponse']['records'][index]['record']['recordData']['sources']['source']['#text'][:2] == 'LC' and suggestion['searchRetrieveResponse']['records'][index]['record']['recordData']['sources']['source']['@nsid'] not in lccns:
						lccns.append(suggestion['searchRetrieveResponse']['records'][index]['record']['recordData']['sources']['source']['@nsid'])
	#			print suggestion['searchRetrieveResponse']['records'][index]['record']['recordData']['sources']['source']
	#			print suggestion['searchRetrieveResponse']['records'][index]['record']['recordData']
		
		return lccns
	elif suggestion['searchRetrieveResponse'] is None and first_try and not isASCII(heading):
		print "REPEATING SEARCH WITHOUT NON-ASCII CHARACTERS"
		heading_copy = copy.deepcopy(heading)
		heading_copy['subfields']['a'] = removeNonASCIICharacters(heading['subfields']['a'])
		return SRUSearchQueryVariation(heading_copy,url,search_method,False)
	else:
		return []


#Call LC with Z39.50 to retrieve the full authority record. If the record can be retrieved, extract the relevant fields
#	In the future implement a search and return of other tags that can retrive fields like 670 if relevant
def getLCAuthorityRecordContents(lc_number,lastCall,heading_tags,non_heading_tags=None):
	return_headings = []
	lastCall = datetime.datetime.now().time()

#	conn = HandleZ3950.establishZ3950Connection('lx2.loc.gov',210,'','NAF')
	record, error_type = HandleZ3950.callZ3950(lc_number,'LC')
	if record:
		print "LC RECORD:"
		print record

		headings = record.get_fields(*heading_tags)
		for heading in headings:
			new_heading = {}
			new_heading['subfields'] = {}
			for subfield_index in range(0,len(heading.subfields),2):
				if heading.subfields[subfield_index] in new_heading['subfields']:
					if type(new_heading['subfields'][heading.subfields[subfield_index]]) is list:
						new_heading['subfields'][heading.subfields[subfield_index]].append(heading.subfields[subfield_index+1])
					else:
						new_heading['subfields'][heading.subfields[subfield_index]] = [new_heading['subfields'][heading.subfields[subfield_index]], heading.subfields[subfield_index+1]]
				else:
					new_heading['subfields'][heading.subfields[subfield_index]] = heading.subfields[subfield_index+1]
			new_heading['field'] = heading.tag

			return_headings.append(new_heading)

		if non_heading_tags is not None:
			return_non_headings = []

			non_headings = record.get_fields(*non_heading_tags)
			for non_heading in non_headings:
				new_non_heading = {}
				new_non_heading['subfields'] = {}
				for subfield_index in range(0,len(non_heading.subfields),2):
					new_non_heading['subfields'][non_heading.subfields[subfield_index]] = non_heading.subfields[subfield_index+1]
				new_non_heading['field'] = non_heading.tag

				return_non_headings.append(new_non_heading)

			return (return_headings,lastCall, return_non_headings)
		else:
			return (return_headings,lastCall)
	else:
		return (None,lastCall)