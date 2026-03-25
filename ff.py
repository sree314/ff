#!/usr/bin/env python3
#
# ff.py
# Simple form filler for Google Forms
#
# Placed in the Public Domain by Sreepathi Pai

import selenium.webdriver as webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.firefox.options import Options
import selenium.common.exceptions
import argparse
import tempfile
import os
import math
import functools
import configparser
import sys
import itertools
import csv
import time

def get_form_titles_old(d):
    x = d.find_elements("xpath", '//*[@role="heading"]')
    out = []
    for xx in x:
        cls = set(xx.get_attribute('class').split(' '))

        if 'freebirdFormviewerComponentsQuestionBaseTitle' in cls:
            out.append((xx, xx.text))

    return out

class MSForm:
    def get_form_titles(self, d):
        x = d.find_elements("xpath", '//div[@class="-a-142"]')

        out = []
        for div_with_id in x:
            # will look at id attr of div_with_id to match with input field
            y = div_with_id.find_element(By.CSS_SELECTOR, 'span.text-format-content')
            
            if y:
                txt = y.text.replace('\n', ' ')
                if txt.strip() == '':
                    print("WARNING: missing title, ignoring form field")
                    continue

                out.append((div_with_id, txt))

        return out

    def get_form_fields(self, cfg, form):
        fields = cfg['fields'].keys()

        f2t = {}
        t2f = {}
        for k in fields:
            assert k not in f2t, f"Duplicate field {k}"
            f2t[k] = cfg.get('fields', k)

            assert f2t[k] not in t2f, f"Duplicate title {f2t[k]}"
            t2f[f2t[k]] = k

        ff = self.get_form_titles(form)
        assert len(ff), f"Form has no titles"

        flds = {}
        for fld in ff:
            if fld[1] in t2f:
                id_ = fld[0].get_attribute("id")
                print(fld[1], "found", fld, id_)
                flds[id_] = fld
            else:
                print(fld[1], "not found!")

        ti = RadioButtonFields.find(form, flds) + TextField.find(form, flds)
        for tii in ti:
             tii.csvfield = t2f[tii.name]

        return ti

    def set_form_data(self, fields, formdata):
        for f in fields:
            print("Setting ", f.csvfield)
            if isinstance(f, TextField):
                f.element.send_keys(formdata[f.csvfield])
            elif isinstance(f, RadioButtonFields):
                data = str(formdata[f.csvfield])
                for rb in f.element:
                    if data in rb[0]:
                        rb[1].click()
                        break
            else:
                raise NotImplementedError(f)


def get_form_titles(d):
    x = d.find_elements("xpath", '//*[@role="heading"]')

    out = []
    for xx in x:
        if xx.get_attribute('aria-level') == '3':
            # for some strange reason, .text now contains \n between
            # field title and *

            txt = xx.text.replace('\n', ' ')
            out.append((xx, txt))

    return out

def read_formspec(formspec_file):
    cfg = configparser.ConfigParser()
    cfg.read(formspec_file)
    #with open(formspec_file, "r") as f:
        #cfg = cfg.read(f)

    return cfg

class FormField(object):
    name = None
    title = None
    element = None

    def __init__(self, title, element):
        self.title = title[0]
        self.name = title[1]
        self.element = element

    def __str__(self):
        return f"{self.name} {self.title} {self.element}"

    __repr__ = __str__

class TextField(FormField):
    @staticmethod
    def find(form, fld_ids): # works for MS forms as well
        out = []
        for ti in itertools.chain(form.find_elements("xpath", '//input[@type="text"]'),
                                  form.find_elements("xpath", '//input[@data-automation-id="textInput"]'), form.find_elements("xpath", '//textarea')):
            tid = ti.get_attribute('aria-labelledby')
            tid = set(tid.split())
            if len(tid) == 1:
                tid = tid.pop()
            else:
                if len(tid) == 2:
                    tid = [x for x in tid if x.startswith('QuestionId')]
                    assert len(tid) == 1
                    tid = tid[0]
                else:
                    print('ERROR: Multiple text IDs', rbid)
                    continue

            if tid in fld_ids:
                out.append(TextField(fld_ids[tid], ti))
            else:
                print("Don't know what to do with", tid)

        return out

class RadioButtonFields(FormField):
    @staticmethod
    def find(form, fld_ids):
        out = []
        for rb in form.find_elements("xpath", '//div[@role="radiogroup"]'):
            rbid = rb.get_attribute('aria-labelledby')

            # ms form stuff
            rbid = set(rbid.split())
            if len(rbid) == 1:
                rbid = rbid.pop()
            else:
                if len(rbid) == 2:
                    rbid = [x for x in rbid if x.startswith('QuestionId')]
                    assert len(rbid) == 1
                    rbid = rbid[0]
                else:
                    print('ERROR: Multiple radio button IDs', rbid)
                    continue

            if rbid in fld_ids:
                try:
                    ti = rb.find_element("xpath", './/input[@type="text"]')
                except selenium.common.exceptions.NoSuchElementException:
                    ti = None

                if ti is not None:
                    # doesn't work for some reason
                    al = ti.get_attribute('aria-label')
                    if al == 'Other response':
                        out.append(TextField(fld_ids[rbid], ti)) # Note: TextField!
                else:
                    ti = rb.find_elements("xpath", './/input[@type="radio"]')
                    rbuttons = []
                    for tii in ti:
                        val = tii.get_attribute('value')
                        rbuttons.append((val, tii))

                    if len(rbuttons):
                        out.append(RadioButtonFields(fld_ids[rbid], rbuttons))
                    else:
                        print(f"WARNING: Radiobutton field {rbid} does not have a text field and I could not find radio buttons")

        return out

def get_form_fields(cfg, form):
    fields = cfg['fields'].keys()

    f2t = {}
    t2f = {}
    for k in fields:
        assert k not in f2t, f"Duplicate field {k}"
        f2t[k] = cfg.get('fields', k)

        assert f2t[k] not in t2f, f"Duplicate title {f2t[k]}"
        t2f[f2t[k]] = k

    ff = get_form_titles(form)
    assert len(ff), f"Form has no titles"

    flds = {}
    for fld in ff:
        if fld[1] in t2f:
            id_ = fld[0].get_attribute("id")
            print(fld[1], "found", fld, id_)
            flds[id_] = fld
        else:
            print(fld[1], "not found!")

    ti = RadioButtonFields.find(form, flds) + TextField.find(form, flds)
    for tii in ti:
        tii.csvfield = t2f[tii.name]

    return ti

def set_form_data(fields, formdata):
    for f in fields:
        if isinstance(f, TextField):
            f.element.send_keys(formdata[f.csvfield])


def read_formdata(formdata):
    with open(formdata, 'r') as f:
        rdr = csv.DictReader(f)
        out = [r for r in rdr]

    print(out)
    return out

def read_formdata_ods(formdata, sheetname):
    from pandas_ods_reader import read_ods
    df = read_ods(formdata, sheetname)
    d = df.to_dict('records')

    out = []
    for r in d:
        out.append(dict([(k, str(v) if not isinstance(v, float) else str(int(v))) for k, v in r.items()]))

    print(out)
    return out

if __name__ == "__main__":
    p = argparse.ArgumentParser(description="Fill a Google Form")
    p.add_argument("formspec", help="Form configuration")
    p.add_argument("formdata", help="Form data as CSV")
    p.add_argument("-s", dest="sheetname", help="Sheet to use")

    args = p.parse_args()
    cfg = read_formspec(args.formspec)
    if args.formdata.endswith('.ods'):
        if args.sheetname is None:
            print("ERROR: Need -s when formdata is an ODS")
            p.print_help()
            sys.exit(1)

        formdata = read_formdata_ods(args.formdata, args.sheetname)
    else:
        formdata = read_formdata(args.formdata)

    url = cfg.get('form', 'url')

    o = Options()
    d = webdriver.Firefox(options=o)
    d.get(url)
    time.sleep(3)

    form = MSForm()

    for r in formdata:
        fields = form.get_form_fields(cfg, d)
        form.set_form_data(fields, r)

        x = input()
        if x == 'q': break

    #b = d.find_element("xpath", "//aside[@id='sidebar-second']")

    d.quit()
