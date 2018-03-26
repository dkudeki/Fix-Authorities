# -*- coding: utf-8 -*-
import sys, json, os, datetime, time, copy, re, string, requests
from datetime import timedelta
from StringIO import StringIO
from unicodedata import normalize
import xml.etree.ElementTree as ET
import codecs

#Continue requesting url if connection is dropped.
def getRequest(url,include_timeout):
	try:
		if include_timeout:
			results = requests.get(url, timeout=10).content
		else:
			results = requests.get(url).content
		return results
	except (requests.exceptions.ConnectionError, requests.exceptions.ReadTimeout):
		print "Connection Error on " + url
		print "Trying again."
		return getRequest(url,include_timeout)

#Determine how similar two names are. For avoiding The Stravinsky Error.
# The Stravinsky Error is named after the example where AutoSuggest is given the name Robert Craft, and the first suggestion
# actually points to VIAF's record for Igor Stravinsky. Stravinsky was an associate of Craft, and more famous, so he is
# legitimately turning up as the first result, and he has a LC name associated. It is impossible for the script to understand
# this is not a valid result without determining that the names are very dissimilar.
def calculateLevenshteinDistance(string1,string2):
	matrix = []
	for counter1 in range(0,len(string1)+1):
		empty_row = []
		for counter2 in range(0,len(string2)+1):
			empty_row.append(0)
		matrix.append(empty_row)
	
	for i in range(1,len(string1)+1):
		matrix[i][0] = i

	for j in range(1,len(string2)+1):
		matrix[0][j] = j

	for j in range(1,len(string2)+1):
		for i in range(1,len(string1)+1):
			if string1[i-1] == string2[j-1]:
				matrix[i][j] = matrix[i-1][j-1]
			else:
				matrix[i][j] = min(matrix[i-1][j]+1, matrix[i][j-1]+1,matrix[i-1][j-1]+1)

	#for i in range(1,len(string1)+1):
	#	print matrix[i]

	return matrix[len(string1)][len(string2)]

#Returns a score based on the lev distance between the two names, and maybe the longest common string
def getSimilarityScore(problem,solution):
	built_string = solution['subfields']['a']
	if 'b' in solution['subfields']:
		built_string += ' ' + solution['subfields']['b']
	if 'c' in solution['subfields']:
		built_string += ' ' + solution['subfields']['c']
	if 'd' in solution['subfields']:
		built_string += ' ' + solution['subfields']['d']
	return calculateLevenshteinDistance(problem,built_string)