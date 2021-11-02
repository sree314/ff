#!/usr/bin/env python3
#
# ff.py
# Simple form filler for Google Forms
#
# Placed in the Public Domain by Sreepathi Pai

import selenium.webdriver as webdriver
from selenium.webdriver.firefox.options import Options
import argparse
import tempfile
import os
import math
import functools
import configparser
import sys
import itertools
import csv

def get_form_titles(d):
    x = d.find_elements_by_xpath('//*[@role="heading"]')
    out = []
    for xx in x:
        cls = set(xx.get_attribute('class').split(' '))

        if 'freebirdFormviewerComponentsQuestionBaseTitle' in cls:
            out.append((xx, xx.text))

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
    def find(form, fld_ids):
        out = []
        for ti in itertools.chain(form.find_elements_by_xpath('//input[@type="text"]'),
                                  form.find_elements_by_xpath('//textarea')):
            tid = ti.get_attribute('aria-labelledby')
            if tid in fld_ids:
                out.append(TextField(fld_ids[tid], ti))

        return out

class RadioButtonFields(FormField):
    @staticmethod
    def find(form, fld_ids):
        out = []
        for rb in form.find_elements_by_xpath('//div[contains(concat(" ",normalize-space(@class)," ")," freebirdFormviewerViewItemsRadiogroupRadioGroup ")]'):
            rbid = rb.get_attribute('aria-labelledby')
            if rbid in fld_ids:
                ti = rb.find_element_by_xpath('.//input[@type="text"]')
                if ti is not None:
                    # doesn't work for some reason
                    al = ti.get_attribute('aria-label')
                    if al == 'Other response':
                        out.append(TextField(fld_ids[rbid], ti)) # Note: TextField!
                else:
                    pass

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

if __name__ == "__main__":
    p = argparse.ArgumentParser(description="Fill a Google Form")
    p.add_argument("formspec", help="Form configuration")
    p.add_argument("formdata", help="Form data as CSV")

    args = p.parse_args()
    cfg = read_formspec(args.formspec)
    formdata = read_formdata(args.formdata)

    url = cfg.get('form', 'url')

    o = Options()
    d = webdriver.Firefox(options=o)
    d.get(url)

    for r in formdata:
        fields = get_form_fields(cfg, d)
        set_form_data(fields, r)

        x = input()
        if x == 'q': break

    #b = d.find_element_by_xpath("//aside[@id='sidebar-second']")

    d.quit()
