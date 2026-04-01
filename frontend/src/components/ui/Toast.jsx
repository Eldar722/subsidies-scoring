import { createContext, useContext, useReducer, useCallback } from 'react'
import { createPortal } from 'react-dom'
import { motion, AnimatePresence } from 'framer-motion' // eslint-disable-line no-unused-vars
import { CheckCircle, XCircle, Info, X } from '@phosphor-icons/react'

const ToastContext = createContext(null)

function reducer(state, action) {
  switch (action.type) {
    case 'ADD':    return [...state, action.toast]
    case 'REMOVE': return state.filter(t => t.id !== action.id)
    default:       return state
  }
}

const icons = { success: CheckCircle, error: XCircle, info: Info }
const colors = { success: 'bg-green-600', error: 'bg-red-600', info: 'bg-blue-600' }

export function ToastProvider({ children }) {
  const [toasts, dispatch] = useReducer(reducer, [])

  const showToast = useCallback(({ message, type = 'success' }) => {
    const id = Date.now() + Math.random()
    dispatch({ type: 'ADD', toast: { id, message, type } })
    setTimeout(() => dispatch({ type: 'REMOVE', id }), 3000)
  }, [])

  return (
    <ToastContext.Provider value={{ showToast }}>
      {children}
      {createPortal(
        <div className="fixed bottom-4 right-4 z-50 flex flex-col gap-2">
          <AnimatePresence>
            {toasts.map(toast => {
              const Icon = icons[toast.type] || CheckCircle
              return (
                <motion.div
                  key={toast.id}
                  initial={{ opacity: 0, y: 20, scale: 0.95 }}
                  animate={{ opacity: 1, y: 0, scale: 1 }}
                  exit={{ opacity: 0, y: 10, scale: 0.95 }}
                  transition={{ duration: 0.2 }}
                  className={`flex items-center gap-3 px-4 py-3 rounded-lg text-white text-sm font-medium shadow-lg min-w-64 ${colors[toast.type] || colors.success}`}
                >
                  <Icon size={18} weight="fill" className="flex-shrink-0" />
                  <span className="flex-1">{toast.message}</span>
                  <button onClick={() => dispatch({ type: 'REMOVE', id: toast.id })} className="opacity-70 hover:opacity-100 ml-1">
                    <X size={14} />
                  </button>
                </motion.div>
              )
            })}
          </AnimatePresence>
        </div>,
        document.body
      )}
    </ToastContext.Provider>
  )
}

// eslint-disable-next-line react-refresh/only-export-components
export function useToast() {
  const ctx = useContext(ToastContext)
  if (!ctx) throw new Error('useToast must be used within ToastProvider')
  return ctx
}
