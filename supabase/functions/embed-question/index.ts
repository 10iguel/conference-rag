import { corsHeaders } from '../_shared/cors.ts'
import { verifyUser } from '../_shared/auth.ts'
import { getCachedEmbedding, normalizeQuestion, saveEmbedding } from '../_shared/embedding-cache.ts'

function embeddingResponse(embedding: number[], cached: boolean): Response {
  return new Response(
    JSON.stringify({ embedding, cached }),
    {
      status: 200,
      headers: { ...corsHeaders, 'Content-Type': 'application/json' }
    }
  )
}

Deno.serve(async (req: Request) => {
  if (req.method === 'OPTIONS') {
    return new Response('ok', { headers: corsHeaders })
  }

  try {
    await verifyUser(req)

    const body = await req.json()
    const question = body?.question

    if (!question || typeof question !== 'string' || question.trim() === '') {
      return new Response(
        JSON.stringify({ error: 'Question must be a non-empty string.' }),
        {
          status: 400,
          headers: { ...corsHeaders, 'Content-Type': 'application/json' }
        }
      )
    }

    const normalizedQuestion = normalizeQuestion(question)

    const cachedEmbedding = await getCachedEmbedding(normalizedQuestion)
    if (cachedEmbedding) {
      console.log('Embedding cache hit')
      return embeddingResponse(cachedEmbedding, true)
    }
    console.log('Embedding cache miss')

    const openAiKey = Deno.env.get('OPENAI_API_KEY')
    if (!openAiKey) {
      throw new Error('Server configuration error: Missing OpenAI API Key')
    }

    const openAiResponse = await fetch('https://api.openai.com/v1/embeddings', {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${openAiKey}`,
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        input: normalizedQuestion,
        model: 'text-embedding-3-small'
      })
    })

    if (!openAiResponse.ok) {
      const errData = await openAiResponse.json()
      throw new Error(`OpenAI error: ${errData.error?.message || 'Unknown error'}`)
    }

    const openAiData = await openAiResponse.json()
    const embedding = openAiData.data[0].embedding

    await saveEmbedding(normalizedQuestion, embedding)

    return embeddingResponse(embedding, false)

  } catch (error: any) {
    const isAuthError = error.message === 'Unauthorized' || error.message === 'Missing Authorization header'
    const status = isAuthError ? 401 : 500

    return new Response(
      JSON.stringify({ error: error.message }),
      {
        status,
        headers: { ...corsHeaders, 'Content-Type': 'application/json' }
      }
    )
  }
})