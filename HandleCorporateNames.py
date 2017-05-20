# -*- coding: utf-8 -*-
import copy
from unicodedata import normalize
import GeneralUtilities, HandleZ3950, HeadingFunctions

def searchNameWithSubordinates(name):
	print "\nSEARCHING NAME WITH SUBORDINATES"
	if 'b' in name['subfields']:
		return_name = name['subfields']['a'].replace(';','').replace(' ','+').replace('"',"'").encode('utf-8')
		if type(name['subfields']['b']) is list:
			for instance in range(0,len(name['subfields']['b'])):
				return_name += '+' + name['subfields']['b'][instance].replace('.','').replace(',','').replace(' ','+').replace('"',"'").encode('utf-8')
		else:
			return_name += '+' + name['subfields']['b'].replace('.','').replace(',','').replace(' ','+').replace('"',"'").encode('utf-8')

		return return_name

	else:
		return False

def searchOnlyName(name):
	print "\nSEARCHING ONLY NAME"
	return name['subfields']['a'].replace(';','').replace(' ','+').replace('"',"'").encode('utf-8')

def queryVIAFSRUSearch(name):
	name['subfields']['a'] = HeadingFunctions.removeSpecificBrokenCharacters(name['subfields']['a'])

	suggestion = []
	search_methods = [ searchNameWithSubordinates, searchOnlyName ]
	url = 'http://www.viaf.org/viaf/search?query=local.corporateNames+all+"'
	index = 0

	while len(suggestion) == 0 and index < len(search_methods):
		print len(suggestion)
		suggestion = HeadingFunctions.SRUSearchQueryVariation(name,url,search_methods[index],True)
		index += 1

	print "LAST CALL: ", suggestion
	return suggestion

#Normalize names so that diacritics are all in the same form, then find how similar the two names are. If they're more
#	similar than the most similar names found so far, the new name is recorded as the best fit. Otherwise no change
def compareNames(problematic_name,candidate_name,best,best_score,lc_number,return_lc_number,field_110,return_value):
	if problematic_name != '':
		normalized_problematic_name = normalize('NFC',problematic_name)
	else:
		normalized_problematic_name = ''

	if candidate_name != '':
		normalized_candidate_name = normalize('NFC',candidate_name)
	else:
		normalized_candidate_name = ''
		
	lev_distance = GeneralUtilities.calculateLevenshteinDistance(normalized_problematic_name,normalized_candidate_name)
#	string_length_difference = abs(len(normalized_problematic_name)-len(normalized_candidate_name))
	print 'DIFFERENCE BETWEEN ' + normalized_problematic_name + ' AND ' + normalized_candidate_name + ' = ' + str(lev_distance)# - string_length_difference)
	if lev_distance < best_score:
		print 'OLD SCORE: ' + str(best_score) + ' NEW SCORE: ' + str(lev_distance)
		new_best = candidate_name
		new_best_score = lev_distance# - string_length_difference
		return (new_best,new_best_score,field_110,lc_number)
	else:
		return (best,best_score,return_value,return_lc_number)

def buildFullName(subfields,function):
	if function is None:
		full_name = subfields['a']
	else:
		full_name = function(subfields['a'])

	for subfield in subfields:
		if subfield != 'a' and subfield != 'w':
			if type(subfields[subfield]) is list:
				for instance in range(0,len(subfields[subfield])):
					full_name += ' ' + subfields[subfield][instance]
			else:
				full_name += ' ' + subfields[subfield]

	return full_name

#Look through the AutoSuggest results for an authority record that contains the name we're looking for or something close
#	This is where we code the judgement calls, and it should vary by heading type. For names we want this function to
#	take 670 fields into consideration. For Corporate names this is where the 510 field complications would be addressed.
def findBestSuggestedResult(name,lc_numbers,lastCall):
	best = None
	best_score = 1000000
	return_value = None
	return_lc_number = ''
	for lc_number in lc_numbers:
		print 'BEFORE: ', lastCall
		#Get the authorized name and the variations from the LC authority record
		lc_names, lastCall = HeadingFunctions.getLCAuthorityRecordContents(lc_number,lastCall,['110','410','510'])
		print 'AFTER: ', lastCall
		field_110 = None
		iterator = 0
		if lc_names:
			print lc_names
			for iterator in range(0,len(lc_names)):
#				print iterator
#				print lc_names
#				print lc_names[iterator]
#				print lc_names[iterator]['field']
				if lc_names[iterator]['field'] == '110':
					field_110 = lc_names[iterator]
				iterator += 1

			if field_110 is not None:
				#Compare each name from the authority record in 4 ways:	unchanged, without comma, only ASCII characters, only ASCII characters without comma
				for lc_name in lc_names:
					print 'COMPARING THE NAMES: ', name['subfields']['a'], ' AND ', lc_name['subfields']['a']

					print 'COMPARING STANDARD'
					best, best_score, return_value, return_lc_number = compareNames(buildFullName(name['subfields'],None),buildFullName(lc_name['subfields'],None),best,best_score,lc_number,return_lc_number,field_110,return_value)

					print 'COMPARING IN "FIRST LAST" FORMAT'
					best, best_score, return_value, return_lc_number = compareNames(buildFullName(name['subfields'],HeadingFunctions.removeComma),buildFullName(lc_name['subfields'],HeadingFunctions.removeComma),best,best_score,lc_number,return_lc_number,field_110,return_value)

					print 'COMPARING ONLY ASCII'
					best, best_score, return_value, return_lc_number = compareNames(buildFullName(name['subfields'],HeadingFunctions.removeNonASCIICharacters),buildFullName(lc_name['subfields'],HeadingFunctions.removeNonASCIICharacters),best,best_score,lc_number,return_lc_number,field_110,return_value)

					print 'COMPARING ONLY ASCII IN "FIRST LAST" FORMAT'
					best, best_score, return_value, return_lc_number = compareNames(buildFullName(name['subfields'],HeadingFunctions.removeCommaAndNonASCIICharacters),buildFullName(lc_name['subfields'],HeadingFunctions.removeCommaAndNonASCIICharacters),best,best_score,lc_number,return_lc_number,field_110,return_value)

	print 'BEST FIT: ', best, ' AT ', best_score
	print 'LC NAME: ', return_value
	if best_score > 2:
		return return_value, return_lc_number, False, lastCall
	else:
		return return_value, return_lc_number, True, lastCall

def getSuggestsedLCCNs(suggestion):
#	print "FIND BEST AUTOSUGGEST RESULT AMONG: ", suggestion
	lc_numbers = []

	#Place all the sugestions from AutoSuggest that list the LCCN into lc_numbers without repeating suggestions
	for i in range(0,len(suggestion)):
		if suggestion[i] not in lc_numbers:
			lc_numbers.append(suggestion[i])

	return lc_numbers

#Feed the given heading into the VIAF SRU Search API to generate suggestions for authorized headings. The suggestions
#	are then processed to find the best fit. If no fit is good enough, or if the API doesn't return any results, the
#	search is tried again with all periods removed from the search string. The results from the second search are then
#	judged the same as the first suggestions. If at the end of this process a best-fit has been found, we return that 
#	along with that fit's LCCN. Otherwise we return None in place of the heading and the LCCN.
def getBestSolution(name,lastCall):
	lc_name = None
	lc_number = None
	confident = False

	suggestions = queryVIAFSRUSearch(name)
	print 'GET SUGGESTIONS FOR: ', name
	print 'SUGGESTIONS: ', suggestions
	if len(suggestions) > 0:
		print "FIRST SRU QUERY WORKS"
		lc_numbers = suggestions
		lc_name, lc_number, confident, lastCall = findBestSuggestedResult(name,lc_numbers,lastCall)
		if not confident:
			new_name = copy.deepcopy(name)
			print new_name['subfields']['a'], name['subfields']['a']
			new_name['subfields']['a'] = new_name['subfields']['a'].replace('.','')
			print new_name['subfields']['a'], name['subfields']['a']
			if new_name['subfields']['a'] != name['subfields']['a']:
				print "\nSEARCH WITHOUT ANY PERIODS"
				new_suggestion = queryVIAFSRUSearch(new_name)
				print "NEW SUGGESTION: ", new_suggestion
				if len(new_suggestion) > 0:
					print "SECOND SRU QUERY WORKS"
					#Make sure we're not looking at LCCNs we've already checked
					new_suggested_lc_numbers = new_suggestion
					new_lc_numbers = []
					print new_suggested_lc_numbers
					for number in new_suggested_lc_numbers:
						if number not in lc_numbers:
							new_lc_numbers.append(number)
					print new_lc_numbers

					if len(new_lc_numbers) > 0:
						lc_name, lc_number, confident, lastCall = findBestSuggestedResult(new_name,new_lc_numbers,lastCall)
	else:
		print "FIRST SRU QUERY FAILS"
		new_name = copy.deepcopy(name)
		print new_name['subfields']['a'], name['subfields']['a']
		new_name['subfields']['a'] = new_name['subfields']['a'].replace('.','')
		print new_name['subfields']['a'], name['subfields']['a']
		if new_name['subfields']['a'] != name['subfields']['a']:
			print "\nSEARCH WITHOUT ANY PERIODS"
			new_suggestion = queryVIAFSRUSearch(new_name)
			print "NEW SUGGESTIONS: ", new_suggestion
			if len(new_suggestion) > 0:
				lc_numbers = getSuggestsedLCCNs(new_suggestion)
				lc_name, lc_number, confident, lastCall = findBestSuggestedResult(new_name,lc_numbers,lastCall)
				print lc_name
			else:
				lc_name = None
				lc_number = None
				confident = False
		else:
			lc_name = None
			lc_number = None
			confident = False
	return lc_name, lc_number, confident, lastCall