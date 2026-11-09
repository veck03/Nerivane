import { useState } from 'react'
import { useAuth } from '../auth/useAuth.js'
import './auth-screen.css'

export default function AuthScreen({ onCancel, onAuthenticated }) {
  const { signIn, signUp, signInWithGoogle, supabaseConfigured, authError } = useAuth()
  const [mode, setMode] = useState('signin')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const [notice, setNotice] = useState('')

  async function handleSubmit(event) {
    event.preventDefault()
    setError('')
    setNotice('')
    if (!supabaseConfigured) {
      setError('Add VITE_SUPABASE_URL and VITE_SUPABASE_PUBLISHABLE_KEY to frontend/react_app/.env, then restart Vite.')
      return
    }

    setBusy(true)
    try {
      const result = mode === 'signin'
        ? await signIn(email.trim(), password)
        : await signUp(email.trim(), password)
      if (result.error) throw result.error
      if (mode === 'signup' && !result.data.session) {
        setNotice('Check your email to confirm your account, then sign in.')
      } else if (mode === 'signup') {
        setNotice('Your account is ready.')
        onAuthenticated?.()
      } else {
        onAuthenticated?.()
      }
    } catch (requestError) {
      setError(requestError.message || 'Authentication failed. Please try again.')
    } finally {
      setBusy(false)
    }
  }

  async function handleGoogleSignIn() {
    setError('')
    setNotice('')
    setBusy(true)
    try {
      const { error: oauthError } = await signInWithGoogle()
      if (oauthError) throw oauthError
    } catch (requestError) {
      setError(requestError.message || 'Google sign-in could not be started.')
      setBusy(false)
    }
  }

  function changeMode(nextMode) {
    setMode(nextMode)
    setError('')
    setNotice('')
  }

  return <main className="auth-page" onClick={(event) => { if (event.target === event.currentTarget) onCancel?.() }}>
    <section className="auth-card" role="dialog" aria-modal="true" aria-labelledby="auth-title">
      <div className="auth-brand">
        <span className="nerivane-mark" aria-hidden="true"><span /></span>
        <span>Nerivane</span>
      </div>
      <p className="auth-eyebrow">Scientific research workspace</p>
      <h1 id="auth-title">{mode === 'signin' ? 'Welcome back' : 'Create your account'}</h1>
      <p className="auth-description">{mode === 'signin' ? 'Sign in to use the research chat.' : 'Create an account to use the research chat.'}</p>

      <button className="google-signin-button" type="button" onClick={handleGoogleSignIn} disabled={busy || !supabaseConfigured}>
        <svg viewBox="0 0 48 48" aria-hidden="true"><path fill="#4285F4" d="M43.6 24.5c0-1.4-.1-2.8-.4-4.1H24v7.8h11a9.4 9.4 0 0 1-4.1 6.2v5.1h6.6c3.9-3.6 6.1-8.8 6.1-15Z"/><path fill="#34A853" d="M24 44c5.5 0 10.1-1.8 13.5-4.8l-6.6-5.1c-1.8 1.2-4.1 2-6.9 2-5.3 0-9.8-3.6-11.4-8.4H5.8v5.3A20 20 0 0 0 24 44Z"/><path fill="#FBBC05" d="M12.6 27.7a12 12 0 0 1 0-7.4V15H5.8a20 20 0 0 0 0 18l6.8-5.3Z"/><path fill="#EA4335" d="M24 11.9c3 0 5.7 1 7.8 3.1l5.8-5.8A19.4 19.4 0 0 0 24 4 20 20 0 0 0 5.8 15l6.8 5.3c1.6-4.8 6.1-8.4 11.4-8.4Z"/></svg>
        Continue with Google
      </button>
      <div className="auth-divider"><span>or continue with email</span></div>

      <form className="auth-form" onSubmit={handleSubmit}>
        <label htmlFor="auth-email">Email</label>
        <input id="auth-email" type="email" autoComplete="email" value={email} onChange={(event) => setEmail(event.target.value)} required disabled={busy} />
        <label htmlFor="auth-password">Password</label>
        <input id="auth-password" type="password" autoComplete={mode === 'signin' ? 'current-password' : 'new-password'} minLength={6} value={password} onChange={(event) => setPassword(event.target.value)} required disabled={busy} />
        {authError && <p className="auth-error" role="alert">{authError}</p>}
        {error && <p className="auth-error" role="alert">{error}</p>}
        {notice && <p className="auth-notice" role="status">{notice}</p>}
        {!supabaseConfigured && <p className="auth-config-note">Supabase settings are needed before you can sign in.</p>}
        <button className="auth-submit" type="submit" disabled={busy || !supabaseConfigured}>
          {busy ? 'Please wait…' : mode === 'signin' ? 'Sign in' : 'Create account'}
        </button>
      </form>

      <p className="auth-mode-switch">
        {mode === 'signin' ? 'New to Nerivane?' : 'Already have an account?'}
        <button type="button" onClick={() => changeMode(mode === 'signin' ? 'signup' : 'signin')} disabled={busy}>
          {mode === 'signin' ? 'Create an account' : 'Sign in'}
        </button>
      </p>
      {onCancel && <button className="auth-cancel" type="button" onClick={onCancel}>Continue as guest</button>}
    </section>
  </main>
}
