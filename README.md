# Simple Name Reconciliation Tool
## Requirements
Python 2.7: https://www.python.org/download/releases/2.7/

### Required Libraries
requests: https://pypi.python.org/pypi/requests/

## Running the code
The simple name reconciliation tool uses the [VIAF Auto Suggest API](https://platform.worldcat.org/api-explorer/apis/VIAF/AuthorityCluster/AutoSuggest) to find VIAF links for personal and corporate names. The script reads in a csv with personal or corporate names, and outputs a copy of the CSV that has additional columns with the results. The results can be improved with the inclusion of columns for birth date and death date. By default this tool just outputs the VIAF link for the name, but the tool can be told to output additional data like authorized name, name varaiants and Wikipedia links.

### CSV Formatting
The input CSV must have field names in the top row, which follow the following rules to allow for proper input and output.
#### Required Column
**SearchName** - This is the full name of the person or corporate entity that is being searched for
#### Optional Columns
**StartDate** - If the name is accompanied by a date range, the start of that range should go here. If there is only a single associated date, it should also go here.

**EndDate** - If the name is accompanied by a date range, the end of that range should go here, even if the range has no start.
#### Disallowed Columns
The following columns will be used to write results. If columns with these names exist in the input CSV, they will be overwritten in the output.

**VIAF LINK**, **VIAF NAME**, **VARIANTS**, **EN_WIKIPEDIA**, **FR_WIKIPEDIA**

### Running the Script
The script reads in the given CSV, and outputs the resulting CSV in the same folder as the input. The default execution of the script expects personal names and outputs just the VIAF link. Running the default script in the command prompt will look like this:
```
python fixAuthorities.py input.csv
```
To run the script on corportate names, include the **-c** option, like this:
```
python fixAuthorities.py -c input.csv
```
To get extended results like wikipedia links and variant names, use the **-e** option, like this:
```
python fixAuthorities.py -e input.csv
```
