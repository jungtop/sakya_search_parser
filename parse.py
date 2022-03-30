from curses.textpad import Textbox
from urllib.parse import ParseResultBytes
from bs4 import BeautifulSoup
from openpecha.core.pecha import OpenPechaFS
from openpecha.core.layer import InitialCreationEnum, Layer, LayerEnum, PechaMetaData
from openpecha.core.annotation import Page, Span
from pathlib import Path
import requests
from uuid import uuid4
from datetime import datetime
import re

sample_url = "https://sakyaresearch.org/etexts/1183"
main_url = "https://sakyaresearch.org"
e_text_url = "https://sakyaresearch.org/etexts?filter%5Blanguage_id%5D=2"


def get_page(url):
    res = requests.get(url)
    soup = BeautifulSoup(res.content,"html.parser")
    return soup


def get_languages_url(page):
    langs = page.select("div.btn-group.btn-group-justified.etext-language-switch a")
    return langs


def get_text(url):
    page = get_page(url)
    text_meta = page.select_one("div.etext-page-border-center.etext-titlepage").text
    next_page = page.select_one("div.etext-page-border-right.with-page-link a")['href']
    base_text = extract_base_text(main_url+next_page)
    return base_text


def extract_base_text(url):
    page = get_page(url)
    base_text={}
    text = re.sub("\[\D:\d+\D?\]","",page.select_one("div.etext-body").text)
    pagination = convert_pagination(page.select_one("div.col-sm-8 div.row div:nth-child(2)").text.strip().replace("\n",""))
    base_text.update({pagination:change_text_format(text)})
    next_page = page.select_one("div.etext-page-border-right.with-page-link a")
    if next_page != None:
        base_text.update(extract_base_text(main_url+next_page['href']))
    return base_text

def convert_pagination(pagination):
    new_pagination =""
    m = re.match(".*:(\d+)(\D+)",pagination)
    if m.group(2) == "a":
        new_pagination = int(m.group(1))*2 -1
    else:
        new_pagination = int(m.group(1))*2

    return new_pagination



def get_pecha_links(url):
    page = get_page(url)
    e_texts = []
    links = [i.attrs.get('href') for i in page.select("div.listing a")]
    e_texts.extend(links)
    next_page = page.select_one("ul.pagination li.next a")
    if next_page != None:
        e_texts.extend(get_pecha_links(main_url+next_page['href']))
    return e_texts    

def get_metadata():
    pass

def get_base_layer(text_with_pagination):
    bases = {}
    text_clean = ""
    for pagintation in text_with_pagination:
        text_clean +=text_with_pagination[pagintation]+"\n\n"
    #base_text,_ = seperate_text_from_pagination(text_with_pagination)
    bases.update({"sample_title":text_clean})
    return bases


def get_layers(text_with_pagination):
    layers = {}
    layers["sample_title"] = {
        LayerEnum.pagination : get_pagination_layers(text_with_pagination)
    }
    return layers

def get_pagination_layers(text_with_pagination):
    page_annotations = {}
    char_walker = 0
    for pagination in text_with_pagination:
        text = text_with_pagination[pagination]
        page_annotation,char_walker = get_page_annotation(text,char_walker,pagination)
        page_annotations.update(page_annotation)

    pagination_layer = Layer(
        annotation_type=LayerEnum.pagination,annotations=page_annotations
    ) 

    return pagination_layer

def get_page_annotation(text,char_walker,pagination):
    page_start = char_walker
    page_end = char_walker + len(text)
    page_annotation = {
        uuid4().hex:Page(span=Span(start = page_start,end =page_end),imgnum=pagination)
    }    

    return page_annotation,page_end+2

def get_metadata():
    instance_meta = PechaMetaData(
        initial_creation_type=InitialCreationEnum.input,
        created_at=datetime.now(),
        last_modified_at=datetime.now(),
        source_metadata= {})
    return instance_meta

def create_opf(opf_path,text_with_pagination):
    opf = OpenPechaFS(
        meta= get_metadata(),
        base=get_base_layer(text_with_pagination),
        layers= get_layers(text_with_pagination)
        )

    opf.save(output_path=opf_path)


def remove_double_linebreak(text):
    prev = ""
    new_text = ""

    for i in range(len(text)):
        if text[i] == "\n" and prev == "\n":
            continue
        new_text += text[i]
        prev = text[i]

    return new_text.strip("\n").strip()


def change_text_format(text):
    text = remove_double_linebreak(text)
    base_text=""
    prev= ""
    text = text.replace("\n","") 
    ranges = iter(range(len(text)))
    for i in ranges:
        if i<len(text)-1:
            if i%220 == 0 and i != 0 and re.search("\s",text[i+1]):
                base_text+=text[i]+"\n"
            elif i%220 == 0 and i != 0 and re.search("\S",text[i+1]):
                while i < len(text)-1 and re.search("\S",text[i+1]):
                    base_text+=text[i]
                    i = next(ranges) 
                base_text+=text[i]+"\n" 
            elif prev == "\n" and re.search("\s",text[i]):
                continue
            else:
                base_text+=text[i]
        else:
            base_text+=text[i]
        prev = base_text[-1]    
    return base_text[:-1] if base_text[-1] == "\n" else base_text
    
def main():
    opf_path = Path('./opfs')
    e_text_links = get_pecha_links(e_text_url)
    for e_text_link in e_text_links:
        page = get_page(main_url+e_text_link)
        lang_urls = get_languages_url(page)
        for lang_url in lang_urls:
            texts = get_text(main_url+lang_url['href'])
            create_opf(opf_path,texts)
            break
        break

if __name__ == "__main__":
    main()