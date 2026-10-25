import { createClient } from 'npm:@supabase/supabase-js@2'

export async function verifyUser(req: Request) {
  const authHeader = req.headers.get('Authorization')
  if (!authHeader) {
    throw new Error('Missing Authorization header')
  }

  const token = authHeader.replace('Bearer ', '')

  const supabase = createClient(
    Deno.env.get('SUPABASE_URL') ?? '',
    Deno.env.get('SUPABASE_ANON_KEY') ?? ''
  )

  const { data: { user }, error } = await supabase.auth.getUser(token)

  if (error || !user) {
    throw new Error('Unauthorized')
  }

  return user
}