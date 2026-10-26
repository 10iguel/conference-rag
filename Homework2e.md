# Homework 2e

## How you completed the required tasks

- I used Supabase for my vector DB, scraped five years of General Conference talks with a script called 02_scrape_data, split them into
sentences, embedded them with OpenAI `text-embedding-3-small`, and built a chatbot website that embeds
the question, retrieves the closest sentences with my match_sentences function, fetches the full text of the
top 3 talks, and has GPT-4o as my model to answer with citations through a `generate-answer` Edge Function whose 
system prompt tells it to use only the provided talks.

## What additional exploration you did

- I added an embedding cache to the `embed-question` Edge Function by adding a `question_embeddings` table with normalized questions, protected by RLS
and used only through the service key, so repeated questions will skip OpenAI calls and wil not spend more tokens.

## What obstacles you encountered

- I hit a permission denied error because the tables had RLS but no `GRANT` for `service_role`, Edge Function deploys failed 
until I fixed some imports and the function folder name, and vector search
timed out because the table had no vector index, so every search compared the question against all my 26,256 sentence embeddings, 
until I raised the database statement timeout.

## What you learned

- I learned that RAG works in three steps (retrieve the closest text, 
add it to the prompt, then generate an answer), and that embeddings let the search
match meaning instead of exact words. I also learned that splitting talks into 
sentences gives more precise results, that RLS and table grants are two separate layers
of access control, that an Edge Function keeps the OpenAI key off the 
browser, and that a vector search needs an index and caching once the data gets big.

## Why this matters in the context of agent engineering

- An agent is only as reliable as the context it retrieves and the system prompt that
grounds it, and keeping keys server-side with least-privilege access, plus caching 
and indexing for cost and speed, are what make agent tools safe and scalable.

## How many hours you spent on the homework

- 4.5 hours
