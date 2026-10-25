import { corsHeaders } from '../_shared/cors.ts'
import { verifyUser } from '../_shared/auth.ts'

Deno.serve(async (req: Request) => {
  if (req.method === 'OPTIONS') {
    return new Response('ok', { headers: corsHeaders })
  }

  try {
    await verifyUser(req)

    const body = await req.json()
    const { question, context_talks } = body

    if (!question || typeof question !== 'string' || question.trim() === '') {
      return new Response(
        JSON.stringify({ error: 'Question must be a non-empty string.' }),
        { status: 400, headers: { ...corsHeaders, 'Content-Type': 'application/json' } }
      )
    }

    if (!Array.isArray(context_talks)) {
      return new Response(
        JSON.stringify({ error: 'context_talks must be an array.' }),
        { status: 400, headers: { ...corsHeaders, 'Content-Type': 'application/json' } }
      )
    }

    const systemMessage = {
      role: 'system',
      content: 'You are a helpful assistant. Answer the user\'s question using ONLY the provided talks. Cite the title and speaker in your answer when you reference their information.'
    }

    const talksText = context_talks.map(talk =>
      `Title: ${talk.title}\nSpeaker: ${talk.speaker}\nContent: ${talk.text}`
    ).join('\n\n---\n\n')

    const userMessage = {
      role: 'user',
      content: `Here are the reference talks:\n\n${talksText}\n\nQuestion: ${question}`
    }

    const openAiKey = Deno.env.get('OPENAI_API_KEY')
    if (!openAiKey) {
      throw new Error('Server configuration error: Missing OpenAI API Key')
    }

    const openAiResponse = await fetch('https://api.openai.com/v1/chat/completions', {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${openAiKey}`,
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        model: 'gpt-4o',
        messages: [systemMessage, userMessage],
        temperature: 0.3
      })
    })

    if (!openAiResponse.ok) {
      const errData = await openAiResponse.json()
      throw new Error(`OpenAI error: ${errData.error?.message || 'Unknown error'}`)
    }

    const data = await openAiResponse.json()

    const answer = data.choices[0].message.content

    return new Response(
      JSON.stringify({ answer }),
      { status: 200, headers: { ...corsHeaders, 'Content-Type': 'application/json' } }
    )

  } catch (error: any) {
    const isAuthError = error.message === 'Unauthorized' || error.message === 'Missing Authorization header'
    const status = isAuthError ? 401 : 500

    return new Response(
      JSON.stringify({ error: error.message }),
      { status, headers: { ...corsHeaders, 'Content-Type': 'application/json' } }
    )
  }
})