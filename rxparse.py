"""
# How to Automatically Update the EHHOP Formulary

## Goal: Compare existing EHHapp Formulary data against new invoices and update prices/costs when necessary.

EHHapp Formulary Template: This is how we display information about drugs in the EHHapp.

* CATEGORY
> ~DRUG_NAME | COST_pD (DOSE) | SUBCATEGORY

Invoice Template: This is how information is recorded in monthly invoices.

[Insert Headers Here]

The relevant data fields in the EHHapp Formulary are:

* CATEGORY - e.g. ANALGESICS
* SUBCATEGORY - e.g. Topical, i.e. "Route of administration"
* DRUG_NAME
* APPROVED - if the drug is blacklisted
* DOSE - dose information, if any
* COST_pD - cost per dose

### N.B. Some drugs have multiple DOSE and corresponding COST_pD values
"""

import re
import csv
from datetime import datetime

def read_csv(filename):
    """Make csv files available as csv.reader objects.
    """

    with open(filename, 'rU') as f:
        iterablething = csv.reader(f)
        csvlines = []
        for item in iterablething:
            csvlines.append(item)
        return csvlines

def filter_loe(loe, value="\d{5}", index=2):
    """Filter list of enumerables (lol) by value and index.

    A list comprehension is used to check each list at
    position specified by index for a full match with
    the regular expression pattern specified by value
    argument.

    value = "\d{5}" by default.
    """

    filteredlist = [l for l in loe if re.fullmatch(value, l[index])]
    return filteredlist

"""
Create FormularyRecord objects from EHHapp Markdown so names of drugs and prices can be compared
"""
def read_md(filename):
    """Make md files available as a list of strings (yes these are enumerable).
    """
    with open(filename, 'rU') as f:
        mdlines = f.readlines()
        return mdlines

def parse_mddata(lomd, delimiter="|"):
    """Parse a list of Markdown strings (lomd) to return list of lists (lol).
    """
    mdlol = [string.lstrip("> ").rstrip().split(delimiter) for string in lomd]

    mdlolclean = []
    for item in mdlol:
        item = [s.strip() for s in item]
        mdlolclean.append(item)

    return mdlolclean

class FormularyRecord:
    """Define a class that corresponds to a formulary entry.

    Each formulary entry has the following instance attributes:
    
    * DRUG_NAME
    * DOSE, COST_pD - dosage size and price per dose
    * CATEGORY - e.g. ANALGESICS
    * BLACKLISTED - whether the drug is blacklisted or not
    * SUBCATEGORY - e.g. Topical, i.e. "Route of administration"
    """

    _BLACKLIST_ = '~'
    _DOSECOSTPATT_ = re.compile(r"""
    (\$\d+[.0-9]?\d*-\$\d+[.0-9]?\d*
                |\$\d+[.0-9]?\d*)
            (?:\s)
            (?:\()
            ([^\n]*?)
            (?:\))""", re.X)

    def __init__(self, record):
        self.NAME = self._get_NAME(record)
        self.DOSECOST = self._get_DOSECOST(record)
        self.CATEGORY = None
        self.SUBCATEGORY = None
        self.BLACKLISTED = False

    def _get_NAME(self, record):
        """Sets the name attribute.

        Uses regex pattern to find the name.
        Sniffs for the _BLACKLIST_ and strips it - 
        and sets the BLACKLISTED attribute to true.
        """

        namestring = record[0].lower()
        if namestring[0] == self._BLACKLIST_:
            self.BLACKLISTED = True
            name = namestring.lstrip(self._BLACKLIST_)
        else:
            name = namestring

        return name

    def _get_DOSECOST(self, record):
        """Sets the DOSECOST attribute.

        Uses regex pattern to find prices and associated doses.
        The method re.findall is called so that multiple dose/cost
        pairs for a given drug are returned in a list.
        If no dose/cost matches are found, an empty list is returned.
        """
        
        dosecoststring = record[1].lower()
        match = self._DOSECOSTPATT_.findall(dosecoststring)

        return match

"""
Some functions convert Tabular data to EHHapp Markdown 
"""

class InvoiceRecord:
    """A data structure in which to store relevant output attributes.
    """

    def __init__(self, record):
        self.NAMEDOSE = record[3].lower()
        self.COST = record[15].lower()
        self.CATEGORY = record[8]
        self.SUBCATEGORY = None
        self.ITEMNUM = record[2]
        self.RECDATE = self._get_RECDATE(record)

    def _get_RECDATE(self, record):
        dtformat = '%m/%d/%y %H:%M'
        
        recdate = datetime.strptime(record[12], dtformat)

        return recdate

def store_pricetable(recordlist):
    """For each drug record, generate an instance of drug with relevant parameters.
    
    Remove duplicates by generating a dictionary based on item number keys.
    """

    druglist = [InvoiceRecord(record) for record in recordlist]
    
    nodup_drugdict = {drug.itemnum: drug for drug in druglist}
    
    return nodup_drugdict

"""
All of these functions should keep track of differences between new and old data
"""
def formulary_update(formulary, invoice):
    """Update drugs in formulary with prices from invoice.
    
    Called when formulary and invoice are parsed lists of lists.
    """

    mcount = 0 # Keeps track of the number of matches

    for line in formulary:
        record = FormularyRecord(line)
        drugname = record.NAME
        dosecost = record.DOSECOST
        
        for entry in invoice:
            namedose = InvoiceRecord(entry).NAMEDOSE
            
            if drugname in namedose:
                match = True
                mcount += 1

    return mcount

"""
These functions control output to Markdown
"""
# Any dictionary with drug objects as values to Markdown
def to_Markdown(drugdict):
    output = []
    category = "Uncategorized"
    output.append("* {}".format(category))
    for itemnum, drug in drugdict.items():
        output.append("> {} | {} ({})| {}".format(drug.name, drug.cost, drug.dose, drug.subcategory))

    with open("invoice-extract.markdown", "w") as f:
        f.write('\n'.join(output))
"""
Janky debug functions
"""

def debug(datastructure):
    print(len(datastructure))

if __name__ == "__main__":
    import sys
    # Processing Invoice
    csvdata = read_csv(str(sys.argv[1]))
    print(len(csvdata))
    print(csvdata[0])
    recordlist = filter_loe(csvdata)
    print('Number of Invoice Entries: {}'.format(len(recordlist)))
    print(recordlist[0])
    for i in range(0,4):
        print('from Invoice: NAMEDOSE:{} COST:{} DATE:{}'.format(InvoiceRecord(recordlist[i]).NAMEDOSE, InvoiceRecord(recordlist[i]).COST, InvoiceRecord(recordlist[i]).RECDATE))

    # Processing Formulary
    mddata = read_md(str(sys.argv[2]))
    print(len(mddata))
    print(mddata[0])
    formularylist = filter_loe(mddata, value=">", index=0)
    print(len(formularylist))
    print(formularylist[0])
    formularyparsed = parse_mddata(formularylist)
    print('Number of Formulary Records: {}'.format(len(formularyparsed)))
    print(formularyparsed[0])
    for i in range(0,4):
        print('from Formulary: NAME:{} DOSECOST:{}'.format(FormularyRecord(formularyparsed[i]).NAME, FormularyRecord(formularyparsed[i]).DOSECOST))
    
    # Updating Formulary Against Invoice
    mcount = formulary_update(formularyparsed, recordlist)
    print('Number of matches found: {}'.format(mcount))

    """
    print(dataread[0])
    recordlist = read_parse(dataread)
    print(recordlist[0])
    druglist = parse_classify(recordlist)
    print(druglist[0].name)
    debug(druglist)
    nddd = classify_rmvdups(druglist)
    debug(nddd)
    to_Markdown(nddd)
    """
