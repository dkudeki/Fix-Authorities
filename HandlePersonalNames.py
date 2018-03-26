# -*- coding: utf-8 -*-
import copy, string, json
from unicodedata import normalize
import GeneralUtilities, HeadingFunctions

def keepPersonalLCNames(suggestion,nametype):
	new_results = []
	for element in suggestion['result']:
		print element
		if element['nametype'] == nametype:
			new_results.append(element)
	if not new_results:
		return None
	else:
		return new_results

def searchOnlyName(heading):
	print "\nSEARCHING ONLY NAME"
	print heading
	return heading['name'].replace(';','').replace(' ','+').replace('"',"'").encode('utf-8')

def searchNameWithoutTrailingComma(heading):
	print "\nSEARCHING NAME WITHOUT TRAILING COMMAS"
	if heading['name'][-1:] == ',':
		return heading['name'][:-1].replace(';','').replace(' ','+').replace('"',"'").encode('utf-8')
	else:
		return False

def searchNameWithoutTrailingPeriod(heading):
	print "\nSEARCHING NAME WITHOUT TRAILING PERIODS"
	if heading['name'][-1:] == '.':
		return heading['name'][:-1].replace(';','').replace(' ','+').replace('"',"'").encode('utf-8')
	else:
		return False

def searchNameWithDate(heading):
	print "\nSEARCHING NAME WITH DATE"
	if 'years' in heading:
		return_name = heading['name'].replace(';','').replace(' ','+').replace('"',"'").encode('utf-8')
		return_name += '+' + heading['years'].rstrip().replace('.','').replace(',','').replace(' ','+').replace('"',"'").encode('utf-8')

		if return_name[len(return_name)-1] == '-':
			return_name = return_name[:-1]

		return return_name
	else:
		return False

#Feed a name from a Voyager record into VIAF's AutoSuggest API, and return the results
#	The search methods may be different for different heading types
def queryVIAFAutoSuggest(heading,nametype):
	heading['name'] = HeadingFunctions.removeSpecificBrokenCharacters(heading['name'])

	suggestion = { 'result': None }
#	search_methods = [ searchNameWithDate, searchNameWithoutTrailingComma, searchOnlyName ]
	search_methods = [ searchNameWithDate, searchNameWithoutTrailingPeriod, searchOnlyName ]
#	url = 'http://www.viaf.org/viaf/search?query=local.corporateNames+all+'
	url = 'http://www.viaf.org/viaf/AutoSuggest?query='
	index = 0

	while suggestion['result'] is None and index < len(search_methods):
		suggestion = HeadingFunctions.searchQueryVariation(heading,url,search_methods[index],keepPersonalLCNames,nametype,True)
		index += 1

	print "LAST CALL: ", suggestion
	return suggestion

#def queryVIAFSRUSearch(name):
#	name['subfields']['a'] = HeadingFunctions.removeSpecificBrokenCharacters(name['subfields']['a'])
#
#	suggestion = []
#	search_methods = [ searchNameWithSubordinates, searchNameWithoutTrailingComma, searchOnlyName ]
#	search_methods = [ searchNameWithSubordinates, searchOnlyName ]
#	url = 'http://www.viaf.org/viaf/search?query=local.corporateNames+all+"'
#	index = 0
#
#	while len(suggestion) == 0 and index < len(search_methods):
#		print len(suggestion)
#		suggestion = HeadingFunctions.SRUSearchQueryVariation(name,url,search_methods[index],True)
#		index += 1
#
#	print "LAST CALL: ", suggestion
#	return suggestion

#Normalize names so that diacritics are all in the same form, then find how similar the two names are. If they're more
#	similar than the most similar names found so far, the new name is recorded as the best fit. Otherwise no change
def compareNames(problematic_name,candidate_name,best,best_score,best_variants,best_links,candidate_variants,candidate_links,viaf_main_heading,return_value,viaf_number,return_number):
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
	print 'DIFFERENCE BETWEEN ' + normalized_problematic_name + ' AND ' + normalized_candidate_name + ' = ' + str(lev_distance)
	if lev_distance < best_score:
		new_best = candidate_name
		new_best_score = lev_distance
		return (new_best,new_best_score,candidate_variants,candidate_links,viaf_main_heading,viaf_number)
	else:
		return (best,best_score,best_variants,best_links,return_value,return_number)

def getVIAFRecord(viaf_number):
	viaf_url = 'https://viaf.org/viaf/' + viaf_number + '/viaf.json'
	print viaf_url
	viaf_record = GeneralUtilities.getRequest(viaf_url,True)
	print "VIAF RECORD: "
	print viaf_record
	return viaf_record


#Look through the AutoSuggest results for an authority record that contains the name we're looking for or something close
#	This is where we code the judgement calls, and it should vary by heading type. For names we want this function to
#	take 670 fields into consideration. For Corporate names this is where the 510 field complications would be addressed.
def findBestAutoSuggestReult(heading,suggestion,outputtype):
#	print "FIND BEST AUTOSUGGEST RESULT AMONG: ", suggestion
	viaf_numbers = []
	print "~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~"
	print suggestion

	#Place all the sugestions from AutoSuggest that list the LCCN into lc_numbers without repeating suggestions
	for i in range(0,len(suggestion['result'])):
		print "RESULTS: ", suggestion['result'][i]['viafid']
		if 'viafid' in suggestion['result'][i] and suggestion['result'][i]['viafid'] not in viaf_numbers:
			viaf_numbers.append(suggestion['result'][i]['viafid'])
	best = None
	best_score = 1000000
	best_variants = False
	best_links = False
	return_value = None
	return_number = None
	print "VIAF NUMBERS: ", viaf_numbers
	for viaf_number in viaf_numbers:
		viaf_record = json.JSONDecoder().decode(getVIAFRecord(viaf_number))
		print "VIAF RECORD: "
		print viaf_record

		try:
			if type(viaf_record['ns1:mainHeadings']['ns1:data']) is dict:
				viaf_main_heading = viaf_record['ns1:mainHeadings']['ns1:data']['ns1:text']
			else:
				viaf_main_heading = viaf_record['ns1:mainHeadings']['ns1:data'][0]['ns1:text']
			print viaf_main_heading
			if 'ns1:x400s' in viaf_record:
				viaf_variants = True
			else:
				viaf_variants = False

			viaf_links = False
			if 'ns1:xLinks' in viaf_record:
				print "LINKS: ", viaf_record['ns1:xLinks']
				if type(viaf_record['ns1:xLinks']['ns1:xLink']) is dict:
					if 'en.wikipedia' in viaf_record['ns1:xLinks']['ns1:xLink']['#text'] or 'fr.wikipedia' in viaf_record['ns1:xLinks']['ns1:xLink']['#text']:
						if viaf_links == False:
							viaf_links = [viaf_record['ns1:xLinks']['ns1:xLink']['#text']]
						else:
							viaf_links.append(viaf_record['ns1:xLinks']['ns1:xLink']['#text'])
				else:
					for instance in viaf_record['ns1:xLinks']['ns1:xLink']:
						print instance
						if 'en.wikipedia' in instance['#text'] or 'fr.wikipedia' in instance['#text']:
							if viaf_links == False:
								viaf_links = [instance['#text']]
							else:
								viaf_links.append(instance['#text'])

			print viaf_links

			names_to_check = [viaf_main_heading]
			if 'ns1:x400s' in viaf_record:
				if type(viaf_record['ns1:x400s']['ns1:x400']) is dict:
					subfield = viaf_record['ns1:x400s']['ns1:x400']['ns1:datafield']['ns1:subfield']
					if type(subfield) is dict:
						if subfield['@code'] == 'a' and subfield['#text'] not in names_to_check:
							names_to_check.append(subfield['#text'])
					else:
						for code in subfield:
							print code
							if code['@code'] == 'a' and code['#text'] not in names_to_check:
								names_to_check.append(code['#text'])
				else:
					for instance in viaf_record['ns1:x400s']['ns1:x400']:
						subfield = instance['ns1:datafield']['ns1:subfield']
						if type(subfield) is dict:
							if subfield['@code'] == 'a' and subfield['#text'] not in names_to_check:
								names_to_check.append(subfield['#text'])
						else:
							for code in subfield:
								if code['@code'] == 'a' and code['#text'] not in names_to_check:
									names_to_check.append(code['#text'])

			print "NAMES TO CHECK: ", names_to_check
			if len(names_to_check) > 1:
				viaf_variants = '\n'.join(names_to_check[1:])

			for viaf_name in names_to_check:
				print 'COMPARING THE NAMES: ', heading['name']+heading['years'], ' AND ', viaf_name
				best, best_score, best_variants, best_links, return_value, return_number = compareNames(heading['name']+heading['years'],viaf_name,best,best_score,best_variants,best_links,viaf_variants,viaf_links,viaf_main_heading,return_value,viaf_number,return_number)

				revised_name = HeadingFunctions.removeComma(heading['name']+heading['years'])
				revised_viaf_name = HeadingFunctions.removeComma(viaf_name)
				best, best_score, best_variants, best_links, return_value, return_number = compareNames(revised_name,revised_viaf_name,best,best_score,best_variants,best_links,viaf_variants,viaf_links,viaf_main_heading,return_value,viaf_number,return_number)

				name_with_replaced_characters = HeadingFunctions.removeNonASCIICharacters(heading['name']+heading['years'])
				viaf_name_with_replaced_characters = HeadingFunctions.removeNonASCIICharacters(viaf_name)
				best, best_score, best_variants, best_links, return_value, return_number = compareNames(name_with_replaced_characters,viaf_name_with_replaced_characters,best,best_score,best_variants,best_links,viaf_variants,viaf_links,viaf_main_heading,return_value,viaf_number,return_number)

				revised_name_with_replaced_characters = HeadingFunctions.removeComma(name_with_replaced_characters)
				revised_viaf_name_with_replaced_characters = HeadingFunctions.removeComma(viaf_name_with_replaced_characters)
				best, best_score, best_variants, best_links, return_value, return_number = compareNames(revised_name_with_replaced_characters,revised_viaf_name_with_replaced_characters,best,best_score,best_variants,best_links,viaf_variants,viaf_links,viaf_main_heading,return_value,viaf_number,return_number)

			print "BEST SCORE: ", best_score
		except KeyError:
			pass

	if best_score <= 2:
		if outputtype == 'extended':
			return return_value, return_number, best_variants, best_links, True
		else:
			return None, return_number, None, None, True
	else:
		return None, None, None, None, False

#Search through the suggestions for valid LC form of name. If nothing turns up run an altered query on AutoSuggest.
#	If still nothing, simply return None
#	Should be static across all heading types, but queryVIAFAutoSuggest and findBestAutoSuggestResult may vary
def getVIAFSuggestion(heading,nametype,outputtype):
	suggestions = queryVIAFAutoSuggest(heading,nametype)
	print 'GET SUGGESTIONS FOR: ', heading['name']
	print 'SUGGESTIONS: ', suggestions
	if suggestions['result'] is not None:
		viaf_name, viaf_number, variants, wikipedia, confident = findBestAutoSuggestReult(heading,suggestions,outputtype)
		if not confident:
			new_heading = copy.deepcopy(heading)
			print new_heading['name'], heading['name']
			new_heading['name'] = new_heading['name'].replace('.','')
			print new_heading['name'], heading['name']
			if new_heading != heading:
				print "\nSEARCH WITHOUT ANY PERIODS"
				new_suggestion = queryVIAFAutoSuggest(new_heading,nametype)
				if new_suggestion['result'] is not None:
					viaf_name, viaf_number, variants, wikipedia, confident = findBestAutoSuggestReult(new_heading,new_suggestion,outputtype)
	else:
		new_heading = copy.deepcopy(heading)
		print new_heading['name'], heading['name']
		new_heading['name'] = new_heading['name'].replace('.','')
		print new_heading['name'], heading['name']
		if new_heading != heading:
			print "\nSEARCH WITHOUT ANY PERIODS"
			new_suggestion = queryVIAFAutoSuggest(new_heading,nametype)
			print "NEW SUGGESTIONS: ", new_suggestion
			if new_suggestion['result'] is not None:
				viaf_name, viaf_number, variants, wikipedia, confident = findBestAutoSuggestReult(new_heading,new_suggestion,outputtype)
			else:
				viaf_name = None
				viaf_number = None
				variants = None
				wikipedia = None
				confident = False
		else:
			viaf_name = None
			viaf_number = None
			variants = None
			wikipedia = None
			confident = False
	return viaf_name, viaf_number, variants, wikipedia
#	return viaf_number

#Search for the name in VIAF, and use the results to determie if the name is correct, incorect but changable, or totally incorrect
#	The tags passed to doubleCheckHeading should vary by heading type
def findName(row,nametype,outputtype):
	heading = {}
	heading['name'] = row['SearchName'].decode('utf-8')
	heading['years'] = ''
	if 'StartDate' in row or 'EndDate' in row:
		if row['StartDate'] != '':
			heading['years'] = row['StartDate']

		if row['EndDate'] != '':
			heading['years'] +=  '-' + row['EndDate']

		if heading['years'] != '':
			heading['years'] = ', ' + heading['years']

	print 'CSV NAME: ', heading['name']
	viaf_name, viaf_number, variants, wikipedia = getVIAFSuggestion(heading,nametype,outputtype)

	row['VIAF LINK'] = 'http://viaf.org/viaf/' + viaf_number if viaf_number else viaf_number

	if outputtype == 'extended':
		en_wiki = None
		fr_wiki = None
		if wikipedia:
			for entry in wikipedia:
				if 'en.wikipedia' in entry:
					en_wiki = entry
				elif 'fr.wikipedia' in entry:
					fr_wiki = entry

		row['VIAF NAME'] = viaf_name if viaf_name else ''
		row['VARIANTS'] = variants if variants else ''
		row['EN_WIKIPEDIA'] = en_wiki if en_wiki else ''
		row['FR_WIKIPEDIA'] = fr_wiki if fr_wiki else ''