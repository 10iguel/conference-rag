import { createClient } from 'npm:@supabase/supabase-js@2'

const CACHE_TABLE = 'question_embeddings'

// Service role key: server-side only. RLS blocks the browser from this table.
const supabase = createClient(
  Deno.env.get('SUPABASE_URL') ?? '',
  Deno.env.get('SUPABASE_SERVICE_ROLE_KEY') ?? ''
)

// "  Faith?  " and "faith?" should share one cache entry.
export function normalizeQuestion(question: string): string {
  return question.trim().toLowerCase().replace(/\s+/g, ' ')
}

// Returns null on a miss or a cache failure, so the caller falls back to OpenAI.
export async function getCachedEmbedding(question: string): Promise<number[] | null> {
  const { data, error } = await supabase
    .from(CACHE_TABLE)
    .select('embedding')
    .eq('question', question)
    .maybeSingle()

  if (error) {
    console.error('Cache read failed:', error.message)
    return null
  }
  if (!data) return null

  // PostgREST returns a vector column as text like "[0.01,-0.03,...]"
  return typeof data.embedding === 'string' ? JSON.parse(data.embedding) : data.embedding
}

// A failed write only costs a future cache miss, so log it and move on.
export async function saveEmbedding(question: string, embedding: number[]): Promise<void> {
  const { error } = await supabase
    .from(CACHE_TABLE)
    .upsert({ question, embedding })

  if (error) {
    console.error('Cache write failed:', error.message)
  }
}
