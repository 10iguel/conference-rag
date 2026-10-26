from pathlib import Path
import re, math
from openai import OpenAI

STOP = set('''a about above after again against all am an and are as at be because been before being below between both but by can could did do does doing down during each few for from further had has have having he her here hers herself him himself his how i if in into is it its itself just me more most my myself no nor not now of off on once only or other our ours ourselves out over own same she should so some such than that the their theirs them themselves then there these they this those through to too under until up very was we were what when where which while who whom why will with you your yours yourself yourselves yea ye'''.split())

def words(text):
    return [(m.group(), m.group().lower()) for m in re.finditer(r"[A-Za-z]+(?:'[A-Za-z]+)?", text)]

def unit(vector):
    norm = math.sqrt(sum(x*x for x in vector))
    return [x/norm for x in vector]

lines = (Path.home()/'projects/scriptures/book_of_mormon/1-ne/001.txt').read_text(encoding='utf-8').splitlines()
terms = []
for line in lines:
    seen = set()
    for display, word in words(line):
        if word not in STOP and len(word) >= 2 and word not in seen:
            seen.add(word); terms.append(word)
all_terms = list(dict.fromkeys(terms))
client = OpenAI()
texts = lines + all_terms
response = client.embeddings.create(model='text-embedding-3-small', input=texts)
data = sorted(response.data, key=lambda x:x.index)
raw = [item.embedding for item in data]
verse_raw = raw[:len(lines)]
word_raw = raw[len(lines):]
dim = len(verse_raw[0])
mean = [sum(v[d] for v in verse_raw)/len(verse_raw) for d in range(dim)]
verse = [unit([x-m for x,m in zip(v,mean)]) for v in verse_raw]
word = {term: unit([x-m for x,m in zip(v,mean)]) for term,v in zip(all_terms,word_raw)}

def distance(a,b):
    return 1-sum(x*y for x,y in zip(a,b))

out=['| Verse | Key words (normalized cosine distance to verse) |','|---:|---|']
for n,line in enumerate(lines,1):
    seen=set(); vals=[]
    for display, term in words(line):
        if term in STOP or len(term)<2 or term in seen: continue
        seen.add(term); vals.append((distance(verse[n-1], word[term]), display))
    vals.sort()
    cell=', '.join(f'`{word_text}` ({dist:.2f})' for dist,word_text in vals)
    out.append(f'| {n} | {cell} |')
Path('.agents/scratch/analysis_1ne_normalized.md').write_text('\n'.join(out)+'\n')
print(f'{len(lines)} verses, {len(all_terms)} unique content words')
