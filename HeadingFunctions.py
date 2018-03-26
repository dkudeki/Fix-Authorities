# -*- coding: utf-8 -*-
import sys, json, os, datetime, time, copy, re, string, requests, urllib
from datetime import timedelta
from StringIO import StringIO
from unicodedata import normalize
import xml.etree.ElementTree as ET
import codecs
import GeneralUtilities

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
	check_name = name
	print "BEFORE CHANGE:\n\t", name, '\n\t', name_copy
	check_name = normalize('NFD', check_name)
	check_name = ''.join([i if ord(i) < 128 else '' for i in check_name])
	name_copy = check_name
	print "AFTER CHANGE:\n\t", name, '\n\t', name_copy
	return name_copy

def isASCII(string):
	try:
		results = string.decode('ascii')
		return True
	except UnicodeDecodeError:
		return False

def removeComma(name):
	first_comma_index = name.find(',')
	if first_comma_index == -1:
		return name
	else:
		part_two = name[:first_comma_index]
		part_one = name[first_comma_index+2:]
		return_string = part_one + ' ' + part_two
		return return_string.lstrip()

#Try to set up string to add to the URL to call the AutoSuggest API with. If results are returned, weed out irrelevent ones
#	filter_function should vary by heading type to select only suggestions of that specific heading type
def searchQueryVariation(heading,url,search_method,filter_function,nametype,first_try):
	search_heading = search_method(heading)
	#Certain methods require a specific subfield to exist, if it does not the heading comes back as False and this method can
	#	return no meaningful results
	if not search_heading:
		return { 'result': None }

	full_url = url + search_heading

	print "SEARCH QUERY: ", search_heading
	print full_url

#	suggestion_string = callAPI(full_url)
#	suggestion_string = requests.get(full_url).content
	suggestion_string = GeneralUtilities.getRequest(full_url,False)

	print "GOT DATA"
#	suggestion_string = getRequest(full_url)

	suggestion = { 'result': None}
	try:
		suggestion = json.JSONDecoder().decode(suggestion_string)
	except:
		pass
	print "TRANSLATED DATA"

	if suggestion['result'] is not None:
		suggestion['result'] = filter_function(suggestion,nametype)

	if suggestion['result'] is None and first_try and not isASCII(heading['name']):
		#Second pass of each method removes characters that may have been wrongly encoded
		print "REPEATING SEARCH WITHOUT NON-ASCII CHARACTERS"
		heading_copy = copy.deepcopy(heading)
		heading_copy['name'] = removeNonASCIICharacters(heading_copy['name'])
		return searchQueryVariation(heading_copy,url,search_method,filter_function,nametype,False)
	else:
		return suggestion