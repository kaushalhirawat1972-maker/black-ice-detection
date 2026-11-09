'use client'

import { AnimatePresence, motion } from 'framer-motion'
import { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react'

export type ViewId = 'home' | 'workbench' | 'architecture' | 'diagnostics' | 'history'

const VIEW_IDS: ViewId[] = ['home', 'workbench', 'architecture', 'diagnostics', 'history']

interface ViewRouterValue {
  view: ViewId
  navigate: (view: ViewId) => void
}

const ViewRouterContext = createContext<ViewRouterValue | null>(null)

function viewFromHash(): ViewId {
  const hash = window.location.hash.slice(1)
  return (VIEW_IDS as string[]).includes(hash) ? (hash as ViewId) : 'home'
}

export function ViewRouterProvider({ children }: { children: React.ReactNode }) {
  const [view, setView] = useState<ViewId>('home')

  useEffect(() => {
    const sync = () => setView(viewFromHash())
    sync()
    window.addEventListener('popstate', sync)
    window.addEventListener('hashchange', sync)
    return () => {
      window.removeEventListener('popstate', sync)
      window.removeEventListener('hashchange', sync)
    }
  }, [])

  const navigate = useCallback((next: ViewId) => {
    const url = next === 'home' ? window.location.pathname : `#${next}`
    window.history.pushState(null, '', url)
    setView(next)
  }, [])

  const value = useMemo(() => ({ view, navigate }), [view, navigate])
  return <ViewRouterContext.Provider value={value}>{children}</ViewRouterContext.Provider>
}

export function useViewRouter() {
  const ctx = useContext(ViewRouterContext)
  if (!ctx) throw new Error('useViewRouter must be used within ViewRouterProvider')
  return ctx
}

export function ViewStage({ views }: { views: Record<ViewId, React.ReactNode> }) {
  const { view } = useViewRouter()
  return (
    <AnimatePresence mode="wait" onExitComplete={() => window.scrollTo({ top: 0, behavior: 'instant' })}>
      <motion.div
        key={view}
        initial={{ opacity: 0, y: 36, filter: 'blur(10px)' }}
        animate={{ opacity: 1, y: 0, filter: 'blur(0px)' }}
        exit={{ opacity: 0, y: -24, filter: 'blur(8px)' }}
        transition={{ duration: 0.6, ease: [0.16, 1, 0.3, 1] }}
      >
        {views[view]}
      </motion.div>
    </AnimatePresence>
  )
}
