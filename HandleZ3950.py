# -*- coding: utf-8 -*-
import sys, json, os, datetime, time, copy, re, string, requests
from datetime import timedelta
from StringIO import StringIO
from PyZ3950 import zoom
from pymarc import Record, record_to_xml
from unicodedata import normalize
import xml.etree.ElementTree as ET
import codecs

#LC restricts number of accesses per minute to 10, so we need 6 seconds between calls to them to prevent being cut off for 24 hours
#	so this checks when we last called LC, and if it has been less than six seconds it waits for the current cycle of six seconds
#	to come to an end
def waitSixSeconds(lastCall):
	rightnow = datetime.datetime.now().time()
	time_remaining = 6 - ((rightnow.second - lastCall.second) + (rightnow.microsecond - lastCall.microsecond)/1E6)
	if time_remaining > 0:
		time.sleep(time_remaining)

#Wrapper for establishing a Z39.50 connection, meant to catch errors that may come instead of a response
def establishZ3950Connection(database_address,port,username,database_name):
	try:
		conn = zoom.Connection(database_address,port, user=username)
		conn.databaseName = database_name
		conn.preferredRecordSyntax = 'USMARC'
		return conn
	except zoom.ConnectionError:
		print "GRACEFUL CLOSE ERROR -- ESTABLISHING CONNECTION"
		waitSixSeconds(datetime.datetime.now().time())
		return establishZ3950Connection(database_address,port,username,database_name)

#Wrapper for sending a query throguh Z39.50 meant to catch errors that may come instead of a response
#	conn –	Connection built in establishZ3950Connection()
#	query –	Z39.50 query to be sent
def queryZ3950(database_address,username,database_name,query):
	try:
		conn = establishZ3950Connection(database_address,210,username,database_name)
		return conn.search(query)
	except zoom.ConnectionError:
		print "GRACEFUL CLOSE ERROR -- RUNNING QUERY"
		waitSixSeconds(datetime.datetime.now().time())
		return queryZ3950(database_address,username,database_name,query)

def reEncodeBrokenChars(content):
	print "FIXING BROKEN CHARACTERS:\n"
	print content
	guilty_index = content.find('&#x')
	while guilty_index != -1:
		semicolon_offset = content[guilty_index:].find(';')
		unicode_list = [content[:guilty_index], unichr(int(content[guilty_index+3:guilty_index+semicolon_offset], base=16)), content[guilty_index+semicolon_offset+1:]]
		content = u"".join(unicode_list)
		guilty_index = content.find('&#x')

	print content
	return content

#If a unicode character wasn't properly translated from MARC8
#Replace control characters in the leader
def fixNames(record):
	for field in record:
		for subfield in field:
			if subfield[1].find('&#x') != -1:
				#If the subfield is not unique we have no choice but to ignore it, because pymarc will crash if there's more than
				#one subfield per code
				if len(field.get_subfields(subfield[0])) == 1:
					new_content = reEncodeBrokenChars(subfield[1])
					field[subfield[0]] = new_content
				else:
					print record
#					sys.exit("FOUND PROBLEM")

	record.leader = record.leader.replace(unichr(2),'0')

def checkLeader(leader):
	try:
		leader.decode('utf-8')
		return True
	except UnicodeDecodeError:
		return False

def formatLCCN(lc_number):
	print "OLD LC NUMBER: ", lc_number
	position_one_is_a_number = re.match(r'[0-9]',lc_number[1])
	if position_one_is_a_number:
		lc_number = lc_number[0] + ' ' + lc_number[1:]
		print "NEW LC NUMBER: ", lc_number
	elif len(lc_number) < 12:
		lc_number = lc_number[:2] + ' ' + lc_number[2:]
		print "NEW LC NUMBER: ", lc_number

#	no_digits = filter(lambda x: x.isdigit(), lc_number)
	return '\"' + lc_number + '\"'

def callZ3950(search_id,target,depth=0):
	if target == 'UIU':
		print "UIUC NUMBER: ", search_id
		query = zoom.Query('PQF', '@attr 1=12 %s' % str(search_id))

		database_address = 'z3950.carli.illinois.edu'
		username = 'uiu'
		database_name = 'voyager'
	else:
		print "LC NUMBER: ", search_id
		query = zoom.Query('PQF', '@attr 1=9 %s' % str(formatLCCN(search_id)))

		database_address = 'lx2.loc.gov'
		username = ''
		if 'n' in search_id:
			database_name = 'NAF'
		else:
			database_name = 'SAF'

#	conn = establishZ3950Connection(database_address,210,username,database_name)
	res = queryZ3950(database_address,username,database_name,query)
	print len(res)
	print res

	if len(res) > 0:
		for r in res:
			valid_leader = checkLeader(r.data[:24])

			if valid_leader:
				if len(res) > 1:
					try:
						new_record = Record(data=r.data)
					except UnicodeDecodeError:
						return (False,'BROKEN CHARACTER IN RECORD')
					lccn = new_record.get_fields('001')[0].data.replace(" ", "")
					if lccn == search_id:
						marc_record = new_record
						fixNames(marc_record)
				else:
					try:
						marc_record = Record(data=r.data)
					except UnicodeDecodeError:
						return (False,'BROKEN CHARACTER IN RECORD')
					fixNames(marc_record)
			else:
				return (False, 'BROKEN LEADER')

		return (marc_record, None)
	elif depth < 20:
		waitSixSeconds(datetime.datetime.now().time())
		return callZ3950(search_id,target,depth=depth+1)
	else:
		return (None, 'RECORD NOT FOUND')