import re
import csv
from datetime import datetime
from collections import namedtuple

# Classes and Functions for reading and parsing invoices
InvRec = namedtuple('InvoiceRecord', ['NAMEDOSE', 'NAME', 'DOSE', 'COST', 'CATEGORY', 'ITEMNUM',\
        'REQDATE'])

def read_csv(filename):
    """Read and filter a csv to create a list of drug and price records.
    """
    # Open, read, and filter
    with open(filename, 'rU') as f:
        
        # Instantiate csv.reader
        readerobj = csv.reader(f)
        csvlines = [i for i in readerobj]

        # Filter for drug entries
        drugitemnumpatt = "\d{5}"
        itemnumcolumnindex = 2
        
        invoice = [i for i in csvlines if re.fullmatch(drugitemnumpatt,\
                i[itemnumcolumnindex])]
        
        return invoice

def store_pricetable(invoice):
    """Store only unique and most recent drug and price records.
 
    Parse drug and price records and load them as InvRec(Collections.namedtuple) instances.
    Store uniquely in a dictionary by using the ITEMNUM field as a key and the InvRec 
    instance as the value. If an entry with a more recent price is encountered, update the dictionary entry. 
    """

    # Iterate over and parse each drug and price record
    pricetable = {}
    for item in invoice:

        # Convert date string to datetime object
        dtformat = '%m/%d/%y %H:%M'
        datestr = item[12]
        converteddatetime = datetime.strptime(datestr, dtformat)


        # Instantiate namedtuple from using values returned by list indices
        entry = InvRec(NAMEDOSE = item[3], \
                NAME = "NaN", \
                DOSE = "NaN", \
                COST = item[15], \
                CATEGORY = item[8], \
                ITEMNUM = item[2], \
                REQDATE = converteddatetime)
        
        # Use NAMEDOSE field as the key 'k' for our dictionary of InvRec objects
        k = entry.NAMEDOSE

        # New keys will be stored immediately with their corresponding values.
        # Otherwise, check incoming entry's requisition date and only update the
        # dictionary value if it is more recent than the current one.
        if k not in pricetable:
            pricetable[k] = entry
        else:
            if entry.REQDATE > pricetable[k].REQDATE:
                pricetable[k] = entry
    
    return pricetable

def write_pricetable(pricetable):
    """ Write as pricetable based on Invoice Records in CSV format.
    """

    with open("pricetable.tsv", "w") as f:
        header_str = "\t".join(list(InvRec._fields))
        writeList = [header_str]

        for k, v in pricetable.items():
            row = "{}\t{}\t{}\t{}\t{}".format(v.ITEMNUM, v.CATEGORY, k, v.COST, v.REQDATE)
            writeList.append(row)

        writeString = "\n".join(writeList)
        
        # Write to file
        f.write(writeString)

# ---
# ---

# Classes and functions for reading and parsing the current EHHOP Formulary
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
    _NAMEGARBAGE_ = re.compile(r'(.+)(\s\(.+\).*)|(.+)(\s-.*)')
    _FEATURES_ = []

    def __init__(self, record):
        self.NAME = self._set_NAMEandBLACKLISTED(record)
        self.DOSECOST = self._get_DOSECOST(record)
        self.PRICETABLE = {}
        self.SUBCATEGORY = record[2]
        self.CATEGORY = record[3]
    
    def _set_NAMEandBLACKLISTED(self, record):
        """Sets the NAME and BLACKLISTED attribute.

        Uses regex pattern to find the name.
        Sniffs for the _BLACKLIST_ and strips it - 
        and sets the BLACKLISTED attribute to true.
        """

        namestring = record[0]
        m = self._NAMEGARBAGE_.match(namestring)
        
        if namestring[0] == self._BLACKLIST_:
            self.BLACKLISTED = True
            name = namestring.lstrip(self._BLACKLIST_)
        elif m:
            self.BLACKLISTED = False
            name = m.group(1)
            print('{} came from {}'.format(name, namestring))

            if bool(name) == False:
                name = m.group(3)
                print('What was once None is now {}'.format(name))

        else:
            self.BLACKLISTED = False
            name = namestring

        return name

    def _get_DOSECOST(self, record):
        """Sets the DOSECOST attribute.

        Uses regex pattern to find prices and associated doses.
        The method re.findall is called so that multiple dose/cost
        pairs for a given drug are returned in a list.
        If no dose/cost matches are found, an empty list is returned.
        """
        
        dosecoststring = record[1]
        match = self._DOSECOSTPATT_.findall(dosecoststring)

        return match

    def _get_SUBCATEGORY(self, record):
        """Sets the SUBCATEGORY attribute.
        """
        subcategory = ''

        return subcategory

    # Public Instance Methods

    def _set_PRICETABLE(self):
        """Produce a dictionary to assist price check.
        """

        for dosecost in self.DOSECOST:
            dose = dosecost[1]
            cost = dosecost[0]
            namedose = '{} {}'.format(self.NAME, dose)
            # self.PRICETABLE[namedose] = [cost, self.NAME, dose, str(self.BLACKLISTED), self.CATEGORY, self.SUBCATEGORY]
            self.PRICETABLE[namedose] = InvRec(NAMEDOSE = namedose,\
                    NAME = self.NAME,\
                    DOSE = dose,\
                    COST = cost,\
                    CATEGORY = self.CATEGORY,\
                    ITEMNUM = "NaN",\
                    REQDATE = "NaN")

    def _to_csv(self):
        """Generate CSV from PRICETABLE.
        """
        ndc_list = []

        for k, v in self.PRICETABLE.items():
            output_str = '{}\t{}\t{}\t{}\t{}'.format(k, v.COST, v.CATEGORY, v.ITEMNUM, v.REQDATE)
            ndc_list.append(output_str)

        write_str = '\n'.join(ndc_list)

        return write_str
        
    def _to_markdown(self):
        """ Generate output string.

        * CATEGORY
        > ~DRUG_NAME | COST_pD (DOSE) | SUBCATEGORY
        """

        if self.BLACKLISTED == True:
            prefix = '~'
        else:
            prefix = ''


        dosesandcosts_list = []
        
        for k, v in self.PRICETABLE.items():
            output_str = '{} ({})'.format(v.COST, v.DOSE)
            dosesandcosts_list.append(output_str)

        dosesandcosts_str = ', '.join(dosesandcosts_list)

        markdown = '> {}{} | {} | {}'.format(prefix, self.NAME, dosesandcosts_str, self.SUBCATEGORY)
 
        return markdown

def read_md(filename):
    '''Read Markdown Formulary and parse into a list containing strings for each drug.

    Each list item is a string in EHHapp Markdown format:

    A line that denotes the drug category of all drug lines following it looks like this:

        * CATEGORY

    A line that contains a drug, its prices, doses, subcategories, blacklisted status, and potentially other metadata looks like this.

        > ~DRUGNAME (brandname) - other metadata | COSTpD (DOSE) | SUBCATEGORY
    '''
    with open(filename, 'rU') as f:
        rxlines = f.readlines()
        
        rxfiltered = []

        # Provide a match string and variable to keep track of lines denoting drug classes
        CATEGORY_mdown = '*'
        category = None
        
        # Provide strings to match lines corresponding to drugs 
        DRUG_mdown = '>'
        beginningoflinestrindex = 0
        
        for l in rxlines:
            if l[beginningoflinestrindex] == CATEGORY_mdown:
                category = l.lstrip('\* ').rstrip()
                continue
            elif l[beginningoflinestrindex] == DRUG_mdown:
                rxfiltered.append(l + ' | ' + category)
            else:
                continue

        return rxfiltered

def parse_mddata(rxfiltered, delimiter="|"):
    """Parse a list of Markdown strings (lomd) to return list of lists (lol).
    """
    mdlol = [string.lstrip("> ").rstrip().split(delimiter) for string in rxfiltered]

    parsedformulary = []
    for item in mdlol:
        item = [s.strip() for s in item]
        parsedformulary.append(item)

    return parsedformulary

def store_formulary(parsedformulary):
    """Store a bunch of formulary record objects in a list.
    """

    formulary = []

    for record in parsedformulary:
        formulary.append(FormularyRecord(record))

    return formulary

"""
All of these functions should keep track of differences between new and old data
"""
def match_string(string, phrase):
    '''Determines if any of the full words in 'string' match any of the full words in the phrase
    Returns True or False
    '''
    string_split = string.split()
    phrase_split = phrase.split()
    is_match = set(string_split) < set(phrase_split)

    return is_match

def price_disc(dcost, invcost):
    if dcost != invcost:
        new_price = True
    else:
        new_price = False
    return new_price
        
def formulary_update(formulary, pricetable):
    """Update drugs in formulary with prices from invoice.
    """
    # Keeps track of soft matches
    smatchcount = 0

    # Keeps track of the number of matches
    mcount = 0

    # Keeps track of the number of price changes
    pricechanges = 0

    # Loop through each FormularyRecord
    for record in formulary:
        # Set the PRICETABLE attribute
        record._set_PRICETABLE()

        # Then loop through each dose/cost pair for the given record
        for k, v in record.PRICETABLE.items():
            dcost = v.COST.lower()
            dnamedose = k.lower()
            dname = v.NAME.lower()
            ddose = v.DOSE.lower()

            dosepatt = re.compile(r"\b{}".format(ddose))

            # Look up a matching record stored in the invoice-derived pricetable
            for nd, ir in pricetable.items():
                invnamedose = nd.lower()
                invcost = ir.COST.lower()
                itemnum = ir.ITEMNUM

                # check if formulary medication as any matches in pricetable
                has_match = False

                # If the name and dose are a subset of the pricetable key then we have a match
                if re.search(dname, invnamedose): # capture edge cases
                    if match_string(dname, invnamedose):
                        softmatch = True
                        smatchcount += 1
                        
                        if dosepatt.search(invnamedose):

                            mcount += 1
                            has_match = True

                            if price_disc(dcost, invcost):
                                pricechanges += 1
                                record.PRICETABLE[k] = v._replace(COST = invcost, ITEMNUM = itemnum)
                                print("New price found for {} a.k.a. {}\nFormulary price: {}\nInvoice price: {}".format(invnamedose, k, dcost, invcost))
                                print("Formulary updated so price is now {}".format(record.PRICETABLE[k].COST))
                                                            
                    else: # user input on edge cases
                        if dosepatt.search(invnamedose):
                            print('\nFound a poor match...')
                            print('Formulary name and dose is: '+str(dname)+' '+ str(ddose))
                            print('Invoice name and dose is: '+str(invnamedose))
                            
                            user_input = input('Are these the same medication?\nPlease type \'y\' or \'n\': ')

                            while not user_input == 'y' and not user_input == 'n':
                                user_input = input('Please try again. Are these the same medication?\nPlease type \'y\' or \'n\': ') # error check for user input

                            if user_input == 'y':
                                mcount += 1
                                record.PRICETABLE[k] = v._replace(COST = invcost, ITEMNUM = itemnum)
                            elif user_input == 'n':
                                print('This medication price will not be changed.')
                    
            if has_match == False:
                print(dname+' '+ddose+'has no matches')

    return mcount, pricechanges, formulary, smatchcount

"""
### WORK-IN-PROGRESS
These functions control output to Markdown
"""
def to_Markdown(formulary):
    '''Outputs updated Formulary database to Markdown.
    '''
    output = []
    
    category = formulary[0].CATEGORY
    output.append("* {}".format(category))
    
    for record in formulary:
        if record.CATEGORY != category:
            category = record.CATEGORY
            output.append("* {}".format(category))

        output.append(record._to_markdown())

    with open("Formulary_updated.markdown", "w") as f:
        f.write('\n'.join(output))

def to_TSV(formulary):
    '''Outputs updated Formulary database to CSV
    '''
    output = []

    for record in formulary:
        output.append(record._to_csv())

    with open("Formulary_updated.tsv", "w") as f:
        f.write('\n'.join(output))

"""
Janky ass debug functions
"""

if __name__ == "__main__":
    import sys
    
    # Processing Invoice
    print('Processing Invoice...\n')
    recordlist = read_csv(str(sys.argv[1]))
    print('Number of Invoice Entries: {}'.format(len(recordlist)))
    print(recordlist[0])
    
    pricetable = store_pricetable(recordlist)
    print('Number of Price Table Entries: {}\nEach Entry is a: {}'.format(len(pricetable), type(next(iter(pricetable.values())))))

    # Processing Formulary
    print('Processing Formulary...\n')
    formularylist = read_md(str(sys.argv[2]))
    formularyparsed = parse_mddata(formularylist)
    print('Number of Formulary Records: {}'.format(len(formularyparsed)))
    print(formularyparsed[0])
    for i in range(0,4):
        print('from Formulary: NAME:{} DOSECOST:{}'.format(FormularyRecord(formularyparsed[i]).NAME, FormularyRecord(formularyparsed[i]).DOSECOST))

    formulary = store_formulary(formularyparsed)
    
    # Updating Formulary Against Invoice
    mcount, pricechanges, updatedformulary, softmatch  = formulary_update(formulary, pricetable)
    print('Number of medication matches found: {}\nNumber of price changes found: {}\nNumber of soft matches made: {}'.format(mcount, pricechanges, softmatch))

    for i in range(0,4):
        print('updated Formulary markdown: {}'.format(updatedformulary[i]._to_markdown()))

    to_Markdown(updatedformulary)
    to_TSV(updatedformulary)
    write_pricetable(pricetable)

    # Test BLACKLISTED attribute

    blacklisted = [d for d in updatedformulary if d.BLACKLISTED]
    print('The number of drugs are blacklisted: {}'.format(len(blacklisted)))