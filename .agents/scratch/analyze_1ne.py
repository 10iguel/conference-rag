from pathlib import Path
import re, math
from openai import OpenAI

STOP = set('''a about above after again against all am an and any are as at be because been before being below between both but by can could did do does doing down during each few for from further had has have having he her here hers herself him himself his how i if in into is it its itself just me more most my myself no nor not now of off on once only or other our ours ourselves out over own same she should so some such than that the their theirs them themselves then there these they this those through to too under until up very was we were what when where which while who whom why will with you your yours yourself yourselves yea ye'''.split())

def words(text):
    return [(m.group(), m.group().lower()) for m in re.finditer(r"[A-Za-z]+(?:'[A-Za-z]+)?", text)]

lines = (Path.home()/'projects/scriptures/book_of_mormon/1-ne/001.txt').read_text(encoding='utf-8').splitlines()
terms = []
for line in lines:
    seen = set()
    current = []
    for display, word in words(line):
        if word in STOP or len(word) < 2 or word in seen:
            continue
        seen.add(word)
        current.append((display, word))
        terms.append(word)
    terms = terms
all_terms = list(dict.fromkeys(terms))
client = OpenAI()
texts = lines + all_terms
response = client.embeddings.create(model='text-embedding-3-small', input=texts)
emb = {text: item.embedding for text, item in zip(texts, sorted(response.data, key=lambda x:x.index))}

def distance(a,b):
    dot=sum(x*y for x,y in zip(a,b)); na=math.sqrt(sum(x*x for x in a)); nb=math.sqrt(sum(y*y for y in b))
    return 1-dot/(na*nb)

out=['| Verse | Key words (cosine distance to verse) |','|---:|---|']
for n,line in enumerate(lines,1):
    seen=set(); vals=[]
    for display, word in words(line):
        if word in STOP or len(word)<2 or word in seen: continue
        seen.add(word); vals.append((distance(emb[line], emb[word]), display))
    vals.sort()
    cell=', '.join(f'`{word}` ({dist:.2f})' for dist,word in vals)
    out.append(f'| {n} | {cell} |')
Path('.agents/scratch/analysis_1ne.md').write_text('\n'.join(out)+'\n')
print(f'{len(lines)} verses, {len(all_terms)} unique content words')
