# -*- coding: utf-8 -*-
import copy, re, string
from unicodedata import normalize
import GeneralUtilities, HandleZ3950, HeadingFunctions

def keepTitles(suggestion):
	new_results = []
	for element in suggestion['result']:
		print element
		if element['nametype'] == 'uniformtitlework' and 'lc' in element:
			new_results.append(element)
	if not new_results:
		return None
	else:
		return new_results

def searchNameWithSubordinates(name):
	print "\nSEARCHING NAME WITH SUBORDINATES"
	if 'b' in name['subfields']:
		return_name = name['subfields']['a'].replace(';','').rstrip().replace(' ','+').replace('"',"'").encode('utf-8')
		if type(name['subfields']['b']) is list:
			for instance in range(0,len(name['subfields']['b'])):
				return_name += '+' + name['subfields']['b'][instance].replace('.','').replace(',','').rstrip().replace(' ','+').replace('"',"'").encode('utf-8')
		else:
			return_name += '+' + name['subfields']['b'].replace('.','').replace(',','').rstrip().replace(' ','+').replace('"',"'").encode('utf-8')

		return return_name

	else:
		return False

def searchOnlyName(name):
	print "\nSEARCHING ONLY NAME"
	return name['subfields']['a'].replace(';','').rstrip().replace(' ','+').replace('"',"'").encode('utf-8')

#Feed a name from a Voyager record into VIAF's AutoSuggest API, and return the results
#	The search methods may be different for different heading types
def queryVIAFAutoSuggest(name):
	name['subfields']['a'] = HeadingFunctions.removeSpecificBrokenCharacters(name['subfields']['a'])

	suggestion = { 'result': None }
	search_methods = [ searchNameWithSubordinates, searchOnlyName ]
	url = 'http://www.viaf.org/viaf/AutoSuggest?query='
	index = 0

	while suggestion['result'] is None and index < len(search_methods):
		suggestion = HeadingFunctions.searchQueryVariation(name,url,search_methods[index],keepTitles,True)
		index += 1

	print "LAST CALL: ", suggestion
	return suggestion

#Normalize names so that diacritics are all in the same form, then find how similar the two names are. If they're more
#	similar than the most similar names found so far, the new name is recorded as the best fit. Otherwise no change
def compareNames(problematic_name,candidate_name,best,best_score,best_string_length_difference,lc_number,return_lc_number,field_130,return_value):
	if problematic_name != '':
		normalized_problematic_name = normalize('NFC',problematic_name)
	else:
		normalized_problematic_name = ''

	if candidate_name != '':
		normalized_candidate_name = normalize('NFC',candidate_name)
	else:
		normalized_candidate_name = ''
		
	character_range = re.compile(r'[^ -@\[-`{-~]+')
	if character_range.search(normalized_candidate_name) is not None:
		lev_distance = GeneralUtilities.calculateLevenshteinDistance(normalized_problematic_name,normalized_candidate_name)
		string_length_difference = abs(len(normalized_problematic_name)-len(normalized_candidate_name))
		print 'DIFFERENCE BETWEEN ' + normalized_problematic_name + ' AND ' + normalized_candidate_name + ' = ' + str(lev_distance)# - string_length_difference)
		if lev_distance < best_score:
			print 'OLD SCORE: ' + str(best_score) + ' NEW SCORE: ' + str(lev_distance)
			new_best = candidate_name
			new_best_score = lev_distance# - string_length_difference
			return (new_best,new_best_score, string_length_difference,field_130,lc_number)
		elif lev_distance - string_length_difference == best_score and string_length_difference < best_string_length_difference:
			print 'OLD SCORE: ' + str(best_score) + ' NEW SCORE: ' + str(lev_distance)
			print 'OLD STRING LENGTH DIFFERENCE: ' + str(best_string_length_difference) + ' NEW STRING LENGTH DIFFERENCE: ' + str(string_length_difference)
			new_best = candidate_name
			new_best_score = lev_distance
			return (new_best,new_best_score,string_length_difference,field_130,lc_number)
		else:
			return (best,best_score,best_string_length_difference,return_value,return_lc_number)
	else:
		print 'IGNORED ' + normalized_candidate_name
		return (best,best_score,best_string_length_difference,return_value,return_lc_number)

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
def findBestAutoSuggestResult(name,lc_numbers,lastCall):
	best = None
	best_score = 1000000
	best_string_length_difference = 1000000
	return_value = None
	return_lc_number = ''
	for lc_number in lc_numbers:
		print 'BEFORE: ', lastCall
		#Get the authorized name and the variations from the LC authority record
		lc_names, lastCall = HeadingFunctions.getLCAuthorityRecordContents(lc_number,lastCall,['130','430'])

		print 'AFTER: ', lastCall
		field_130 = None
		iterator = 0
		if lc_names:
			print lc_names
			try:
				while field_130 is None:
					if lc_names[iterator]['field'] == '130':
						field_130 = lc_names[iterator]
					iterator += 1

				#Compare each name from the authority record in 4 ways:	unchanged, without comma, only ASCII characters, only ASCII characters without comma
				for lc_name in lc_names:
					print 'COMPARING THE NAMES: ', name['subfields']['a'], ' AND ', lc_name['subfields']['a']

					print 'COMPARING STANDARD'
					best, best_score, best_string_length_difference, return_value, return_lc_number = compareNames(name['subfields']['a'],lc_name['subfields']['a'],best,best_score,best_string_length_difference,lc_number,return_lc_number,field_130,return_value)

					print 'COMPARING IN "FIRST LAST" FORMAT'
					revised_name = HeadingFunctions.removeComma(name['subfields']['a'])
					revised_lc_name = HeadingFunctions.removeComma(lc_name['subfields']['a'])
					best, best_score, best_string_length_difference, return_value, return_lc_number = compareNames(revised_name,revised_lc_name,best,best_score,best_string_length_difference,lc_number,return_lc_number,field_130,return_value)

					print 'COMPARING ONLY ASCII'
					name_with_replaced_characters = HeadingFunctions.removePuncuationAndNonASCIICharacters(name['subfields']['a'])
					lc_name_with_replaced_characters = HeadingFunctions.removePuncuationAndNonASCIICharacters(lc_name['subfields']['a'])
					best, best_score, best_string_length_difference, return_value, return_lc_number = compareNames(name_with_replaced_characters,lc_name_with_replaced_characters,best,best_score,best_string_length_difference,lc_number,return_lc_number,field_130,return_value)

					print 'COMPARING ONLY ASCII IN "FIRST LAST" FORMAT'
					revised_name_with_replaced_characters = HeadingFunctions.removeComma(name_with_replaced_characters)
					revised_lc_name_with_replaced_characters = HeadingFunctions.removeComma(lc_name_with_replaced_characters)
					best, best_score, best_string_length_difference, return_value, return_lc_number = compareNames(revised_name_with_replaced_characters,revised_lc_name_with_replaced_characters,best,best_score,best_string_length_difference,lc_number,return_lc_number,field_130,return_value)
			except IndexError:
				pass

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
	for i in range(0,len(suggestion['result'])):
		if 'lc' in suggestion['result'][i] and suggestion['result'][i]['lc'] not in lc_numbers:
			lc_numbers.append(suggestion['result'][i]['lc'])

	return lc_numbers


#Feed the given heading into the VIAF AutoSuggest API to generate suggestions for authorized headings. The suggestions
#	are then processed to find the best fit. If no fit is good enough, or if the API doesn't return any results, the
#	search is tried again with all periods removed from the search string. The results from the second search are then
#	judged the same as the first suggestions. If at the end of this process a best-fit has been found, we return that 
#	along with that fit's LCCN. Otherwise we return None in place of the heading and the LCCN.
def getBestSolution(name,lastCall):
	suggestions = queryVIAFAutoSuggest(name)
	print 'GET SUGGESTIONS FOR: ', name
	print 'SUGGESTIONS: ', suggestions
	if suggestions['result'] is not None:
		lc_numbers = getSuggestsedLCCNs(suggestions)
		lc_name, lc_number, confident, lastCall = findBestAutoSuggestResult(name,lc_numbers,lastCall)
		if not confident:
			new_name = copy.deepcopy(name)
			print new_name['subfields']['a'], name['subfields']['a']
			new_name['subfields']['a'] = ''.join([ch for ch in new_name['subfields']['a'] if ch not in string.punctuation])
			print new_name['subfields']['a'], name['subfields']['a']
			if new_name['subfields']['a'] != name['subfields']['a']:
				print "\nSEARCH WITHOUT ANY PERIODS"
				new_suggestion = queryVIAFAutoSuggest(new_name)
				print "NEW SUGGESTION: ", new_suggestion
				if new_suggestion['result'] is not None:
					#Make sure we're not looking at LCCNs we've already checked
					new_suggested_lc_numbers = getSuggestsedLCCNs(new_suggestion)
					new_lc_numbers = []
					print new_suggested_lc_numbers
					for number in new_suggested_lc_numbers:
						if number not in lc_numbers:
							new_lc_numbers.append(number)
					print new_lc_numbers

					if len(new_lc_numbers) > 0:
						lc_name, lc_number, confident, lastCall = findBestAutoSuggestResult(new_name,new_lc_numbers,lastCall)
	else:
		new_name = copy.deepcopy(name)
		print new_name['subfields']['a'], name['subfields']['a']
		new_name['subfields']['a'] = ''.join([ch for ch in new_name['subfields']['a'] if ch not in string.punctuation])
		print new_name['subfields']['a'], name['subfields']['a']
		if new_name['subfields']['a'] != name['subfields']['a']:
			print "\nSEARCH WITHOUT ANY PERIODS"
			new_suggestion = queryVIAFAutoSuggest(new_name)
			print "NEW SUGGESTIONS: ", new_suggestion
			if new_suggestion['result'] is not None:
				lc_numbers = getSuggestsedLCCNs(new_suggestion)
				lc_name, lc_number, confident, lastCall = findBestAutoSuggestResult(new_name,lc_numbers,lastCall)
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