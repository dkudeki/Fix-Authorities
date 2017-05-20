# Authority-Maintenance
##Requirements
Python 2.7: https://www.python.org/download/releases/2.7/

SQL Developer: http://www.oracle.com/technetwork/developer-tools/sql-developer/overview/index-097090.html
###Required Libraries
requests: https://pypi.python.org/pypi/requests/

PyZ3950: https://github.com/Brown-University-Library/PyZ3950

pymarc: https://github.com/edsu/pymarc

ply (Windows only): https://pypi.python.org/pypi/ply/

##Running the code
Once the requirements have been installed, generate a spreadsheet of problematic headings by running the sql query, and save the output as a csv. Then in the command prompt enter: 
```
python fixAuthorities.py query_results.csv
```

When the code is done running it will output a MARCXML collection of records that have been updated with fixed headings, as well as several spreadsheets that document which headings have been changed and which were not.
