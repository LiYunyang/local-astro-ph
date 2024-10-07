import os
import yaml
import requests
from bs4 import BeautifulSoup
import re
import unicodedata

def fetch_kicp():
    people = dict()
    for url in ['https://kavlicosmo.uchicago.edu/people/', 'https://astrophysics.uchicago.edu/people/']:
        response = requests.get(url)
        response.raise_for_status()  # Check for HTTP errors
        soup = BeautifulSoup(response.content, 'html.parser')    
        for li in soup.find_all('li', class_='mix'):
            if 'staff' not in li['class']:  
                name = li.find('span').get_text(strip=True) if li.find('span') else 'No name available.'
                role = li.find('b').get_text(strip=True) if li.find('b') else 'No role available.'
                role = role.split(',')[0]
                name = re.sub(r'\s*\(.*?\)\s*', ' ', name).strip()
                name = unicodedata.normalize('NFD', name)
                name = ''.join(c for c in name if unicodedata.category(c) != 'Mn')
                if name not in people:
                    people[name] = role
            else:
                pass
    return people

def get_local_authors(update=False):
    fname = 'kicp-members.yaml'
    if os.path.exists(fname) and not update:
        with open(fname, 'r') as f:
            authors = yaml.load(f, Loader=yaml.FullLoader)
            return authors
    else:
        authors = fetch_kicp()
        with open(fname, 'w') as f:
            yaml.dump(authors, f)
        return authors


def fetch_recent_astro_ph_papers():
    url = "https://arxiv.org/list/astro-ph/recent?skip=0&show=2000"

    response = requests.get(url)
    response.raise_for_status()  # Check for HTTP errors
    soup = BeautifulSoup(response.content, 'html.parser')
    articles = soup.find_all('div', class_='meta')
    records = []

    for article in articles:
        title_div = article.find('div', class_='list-title')
        title = title_div.get_text(strip=True).replace('Title:', '')
        
        authors_div = article.find('div', class_='list-authors')
        authors = ', '.join([a.get_text() for a in authors_div.find_all('a')])
        
        # Extract the corresponding link
        link_dt = article.find_previous('dt')
        link = "https://arxiv.org" + link_dt.find('a', title='Abstract')['href'] if link_dt and link_dt.find('a', title='Abstract') else 'No link available.'

        # Append extracted data to records
        records.append({
            'title': title,
            'authors': authors,
            'link': link
        })
    return records


def name_match(n1, n2):
    n1s = n1.split(' ')
    n2s = n2.split(' ')
    return n1s[0].lower()==n2s[0].lower() and n1s[-1].lower()==n2s[-1].lower()

def match_local_authors(records, authors):
    out = list()
    for p in records:
        _authors = p['authors'].split(', ')
        matched_authors = list()
        for idx, a1 in enumerate(_authors):
            for a2, role in authors.items():
                if name_match(a1, a2):
                    matched_authors.append((a2, idx+1, role))
                    continue
        if matched_authors:
            _ = p.copy()
            _.pop('authors')
            _['local_match'] = matched_authors
            out.append(_)
    return out

def format_output(matched_records):
    out_str = []
    
    for p in matched_records:
        out_str.append(f"- **{p['title']}**")
        out_str.append(f"[{p['link']}]")
        _ += '; '.join([f"  + {a} ({idx}th author, {role})" for (a, idx, role) in p['local_match']])
        _ += '\n'
        out_str.append(_)
    return '\n'.join(out_str)

if __name__ == '__main__':
    authors = get_local_authors()
    records = fetch_recent_astro_ph_papers()
    matched_records = match_local_authors(records, authors)
    out = format_output(matched_records)
    print(out)
    
    