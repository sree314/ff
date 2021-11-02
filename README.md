# FormFiller

Simple, Selenium-based script to upload a CSV to a Google Form.

## Installation

Make sure Selenium and Firefox are installed. Then, on Ubuntu:

```
apt install python3-selenium
```

Should install Python bindings for Selenium.

## Usage

You need to create a configuration file that describes the form, its
structure as well as the structure of the CSV file:

```
[form]
url=set-form-url here

[fields]
csvheader1=Form Field Title
csvheader2=Required Form Field Title *

```

The CSV will be assumed to contain a header whose fields are
`csvheader1` and `csvheader2`. The contents of these field will be
stored in the form fields `Form Field Title` and `Required Form Field
Title *`. For example:

```
csvheader1,csvheader2
data1,data2
data3,data4
```

Then, to upload data to the form, use:

```
ff.py formspec.cfg formdata.csv
```

A new Firefox window will be opened and all data in the CSV will be
uploaded to the form, row-by-row. This script will NOT submit the
form. You need to click the Submit button to actually submit the form.

Once you've submitted the form and you're looking at a new, empty
form, press Enter in the console running `ff.py` to advance to the
next record in the CSV file. Press `q` to exit.

## Known Bugs

Google Form does not use standard radio buttons. So you will need to
click a required radio button to set a value. Sometimes, even with a
text field for a Radio button (e.g. "Other"), a radio button will need
to be clicked.
