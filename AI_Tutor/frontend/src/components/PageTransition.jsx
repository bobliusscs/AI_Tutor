import { motion, AnimatePresence } from 'framer-motion'
import { useLocation } from 'react-router-dom'

// 页面过渡动画组件
export function PageTransition({ children }) {
  const location = useLocation()
  
  return (
    <AnimatePresence mode="sync">
      <motion.div
        key={location.pathname}
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ duration: 0.2, ease: 'easeOut' }}
        style={{ minHeight: '100vh' }}
      >
        {children}
      </motion.div>
    </AnimatePresence>
  )
}
