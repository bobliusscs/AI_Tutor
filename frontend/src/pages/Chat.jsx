import React, { useState, useRef, useEffect, useCallback, useMemo } from 'react'
import { useSearchParams, useLocation, useNavigate } from 'react-router-dom'
import { message, Tooltip } from 'antd'
import {
  CopyOutlined, CheckOutlined,
  RobotOutlined, ExpandOutlined, LoadingOutlined
} from '@ant-design/icons'
import { motion, AnimatePresence } from 'framer-motion'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter'
import { oneDark } from 'react-syntax-highlighter/dist/esm/styles/prism'
import dayjs from 'dayjs'
import ChatInputBar from '../components/ChatInputBar'
import CanvasPanel from '../components/CanvasPanel'
import MermaidRenderer from '../components/MermaidRenderer'
import ChatPPTVisualizer, { InlineMiniCard } from '../components/ChatPPTVisualizer'
import { InlineExerciseCard } from '../components/ExercisePractice'
import { studyGoalAPI } from '../utils/api'

// ── 工具调用卡片组件 ──────────────────────────────────────────────────────────
function ToolCallCard({ toolCall }) {
  const [expanded, setExpanded] = useState(false)
  const isDone = toolCall.status === 'done'

  return (
    <div style={{
      background: 'rgba(99,102,241,0.04)',
      border: '1px solid rgba(99,102,241,0.15)',
      borderRadius: 10,
      padding: '8px 12px',
      marginBottom: 6,
      fontSize: 13,
    }}>
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          gap: 8,
          cursor: isDone ? 'pointer' : 'default',
          userSelect: 'none',
        }}
        onClick={() => isDone && setExpanded(v => !v)}
      >
        {isDone ? (
          <span style={{ fontSize: 14 }}>✅</span>
        ) : (
          <span className="tool-call-spinner" style={{
            display: 'inline-block',
            width: 14,
            height: 14,
            border: '2px solid rgba(99,102,241,0.2)',
            borderTopColor: '#6366f1',
            borderRadius: '50%',
            flexShrink: 0,
          }} />
        )}
        <span style={{ fontWeight: 600, color: '#4f46e5' }}>
          {toolCall.toolName}
        </span>
        <span style={{ color: '#94a3b8', marginLeft: 2 }}>
          {isDone ? '调用完成' : '调用中...'}
        </span>
        {isDone && (
          <span style={{ marginLeft: 'auto', color: '#94a3b8', fontSize: 12 }}>
            {expanded ? '▲ 收起' : '▼ 展开结果'}
          </span>
        )}
      </div>
      {isDone && expanded && toolCall.toolResult && (
        <div style={{
          marginTop: 8,
          padding: '8px 10px',
          background: 'rgba(15,23,42,0.04)',
          borderRadius: 6,
          fontFamily: "'JetBrains Mono', 'Courier New', monospace",
          fontSize: 12,
          color: '#475569',
          lineHeight: 1.6,
          whiteSpace: 'pre-wrap',
          wordBreak: 'break-word',
          borderLeft: '3px solid rgba(99,102,241,0.3)',
        }}>
          {toolCall.toolResult}
        </div>
      )}
    </div>
  )
}

// ── 工具调用状态指示器 ────────────────────────────────────────────────────────
function ToolStatusIndicator({ statusMessage }) {
  return (
    <div style={{
      display: 'flex',
      alignItems: 'center',
      gap: 8,
      padding: '6px 12px',
      background: 'rgba(99,102,241,0.06)',
      border: '1px solid rgba(99,102,241,0.12)',
      borderRadius: 8,
      marginBottom: 8,
      fontSize: 13,
      color: '#6366f1',
    }}>
      <span className="tool-call-spinner" style={{
        display: 'inline-block',
        width: 13,
        height: 13,
        border: '2px solid rgba(99,102,241,0.2)',
        borderTopColor: '#6366f1',
        borderRadius: '50%',
        flexShrink: 0,
      }} />
      <span>{statusMessage || '🔧 调用工具中...'}</span>
    </div>
  )
}


// ── AI 头像 ───────────────────────────────────────────────────────────────────
function AIAvatar({ size = 28 }) {
  return (
    <div style={{
      width: size,
      height: size,
      borderRadius: 8,
      background: 'linear-gradient(145deg, #0ea5e9, #6366f1, #8b5cf6)',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      flexShrink: 0,
      boxShadow: '0 4px 12px rgba(99,102,241,0.4), inset 0 1px 0 rgba(255,255,255,0.2)',
      border: '1px solid rgba(255,255,255,0.15)',
    }}>
      <RobotOutlined style={{ color: '#fff', fontSize: size * 0.55, filter: 'drop-shadow(0 1px 2px rgba(0,0,0,0.2))' }} />
    </div>
  )
}

// ── 快捷操作按钮组件 ──────────────────────────────────────────────────────────
function QuickActionButtons({ onAction, loading }) {
  const actions = [
    { key: 'practice', label: '练习巩固', icon: '✍️' }
  ]

  return (
    <div style={{
      display: 'flex',
      gap: 10,
      marginTop: 12,
      padding: '12px 0',
      borderTop: '1px solid #f1f5f9',
    }}>
      {actions.map(action => (
        <motion.button
          key={action.key}
          whileHover={{ scale: 1.02, y: -1 }}
          whileTap={{ scale: 0.98 }}
          onClick={() => !loading && onAction(action.key, action)}
          disabled={loading}
          style={{
            padding: '8px 14px',
            borderRadius: 8,
            border: '1px solid #e5e7eb',
            background: '#ffffff',
            color: '#374151',
            fontSize: 13,
            fontWeight: 500,
            cursor: loading ? 'not-allowed' : 'pointer',
            display: 'flex',
            alignItems: 'center',
            gap: 6,
            opacity: loading ? 0.6 : 1,
            transition: 'all 0.15s ease',
          }}
          onMouseEnter={(e) => {
            if (!loading) {
              e.currentTarget.style.borderColor = '#f97316'
              e.currentTarget.style.background = '#fff7ed'
              e.currentTarget.style.color = '#ea580c'
            }
          }}
          onMouseLeave={(e) => {
            e.currentTarget.style.borderColor = '#e5e7eb'
            e.currentTarget.style.background = '#ffffff'
            e.currentTarget.style.color = '#374151'
          }}
        >
          <span style={{ fontSize: 14 }}>{action.icon}</span>
          <span>{action.label}</span>
        </motion.button>
      ))}
    </div>
  )
}

// ── 附件渲染 ──────────────────────────────────────────────────────────────────
function AttachmentDisplay({ attachments }) {
  if (!attachments || attachments.length === 0) return null
  return (
    <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8, marginBottom: 8 }}>
      {attachments.map(att => {
        if (att.type === 'image' && att.preview) {
          return (
            <img
              key={att.id}
              src={att.preview}
              alt={att.name}
              style={{ maxWidth: 200, borderRadius: 8, display: 'block' }}
            />
          )
        }
        if (att.type === 'video') {
          return (
            <video
              key={att.id}
              src={att.preview || URL.createObjectURL(att.file)}
              controls
              style={{ maxWidth: 240, borderRadius: 8 }}
            />
          )
        }
        return (
          <div key={att.id} style={{
            display: 'flex',
            alignItems: 'center',
            gap: 6,
            padding: '6px 10px',
            background: 'rgba(255,255,255,0.5)',
            borderRadius: 8,
            border: '1px solid rgba(226,232,240,0.7)',
          }}>
            <span style={{ fontSize: 16 }}>📄</span>
            <div>
              <div style={{ fontSize: 12, fontWeight: 600, color: '#1e293b' }}>{att.name}</div>
              <div style={{ fontSize: 11, color: '#94a3b8' }}>
                {att.size < 1024 * 1024
                  ? (att.size / 1024).toFixed(1) + ' KB'
                  : (att.size / (1024 * 1024)).toFixed(1) + ' MB'}
              </div>
            </div>
          </div>
        )
      })}
    </div>
  )
}

// ── 安全的 JSON 解析 ──────────────────────────────────────────────────────────
function safeJsonParse(str) {
  try {
    return { success: true, data: JSON.parse(str) }
  } catch (e) {
    // 尝试修复被截断的 JSON（通常出现在大型内容传输中）
    // 检查是否是 SSE 格式的 data: 前缀被截断混入内容的情况
    if (str.includes('data:') || str.includes('data: ')) {
      // 尝试找到完整的 JSON 部分
      const jsonMatch = str.match(/data:\s*(\{[\s\S]*\})/)
      if (jsonMatch) {
        try {
          return { success: true, data: JSON.parse(jsonMatch[1]) }
        } catch {
          // 继续尝试其他修复
        }
      }
    }
    return { success: false, error: e }
  }
}

// ── 消息内容渲染（AI 消息） ────────────────────────────────────────────────────
function AIMessageContent({ content, openInCanvas }) {
  const markdownComponents = useMemo(() => ({
    code({ node, inline, className, children, ...props }) {
      const lang = /language-(\w+)/.exec(className || '')
      const codeStr = String(children).replace(/\n$/, '')

      if (!inline && lang && lang[1].toLowerCase() === 'mermaid') {
        return (
          <div style={{ margin: '16px 0', maxWidth: '720px', width: '100%' }}>
            <MermaidRenderer
              code={codeStr}
              compact={true}
              onExpand={() => openInCanvas(codeStr, 'mermaid')}
            />
          </div>
        )
      }

      if (!inline && lang) {
        const language = lang[1]
        return (
          <div style={{ position: 'relative', marginBottom: 8 }}>
            <div style={{
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              background: '#1a1a2e',
              borderRadius: '8px 8px 0 0',
              padding: '5px 12px',
            }}>
              <span style={{ fontSize: 11, color: '#94a3b8', fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.05em' }}>
                {language}
              </span>
              <Tooltip title="在画布中打开">
                <button
                  onClick={() => openInCanvas(codeStr, 'code', language)}
                  style={{
                    background: 'rgba(255,255,255,0.1)',
                    border: '1px solid rgba(255,255,255,0.15)',
                    borderRadius: 5,
                    padding: '2px 6px',
                    cursor: 'pointer',
                    color: '#94a3b8',
                    fontSize: 12,
                    display: 'flex',
                    alignItems: 'center',
                    gap: 4,
                  }}
                >
                  <ExpandOutlined style={{ fontSize: 11 }} />
                  展开
                </button>
              </Tooltip>
            </div>
            <SyntaxHighlighter
              style={oneDark}
              language={language}
              PreTag="div"
              customStyle={{ margin: 0, borderRadius: '0 0 8px 8px', fontSize: 13 }}
              {...props}
            >
              {codeStr}
            </SyntaxHighlighter>
          </div>
        )
      }

      return (
        <code style={{
          background: 'rgba(99,102,241,0.08)',
          padding: '2px 6px',
          borderRadius: 4,
          fontSize: '0.9em',
          color: '#6366f1',
        }} {...props}>
          {children}
        </code>
      )
    },
    p({ children }) {
      return <p style={{ margin: '0.5em 0' }}>{children}</p>
    }
  }), [openInCanvas])

  return (
    <div className="chat-markdown-content" style={{ overflowX: 'auto' }}>
      <ReactMarkdown remarkPlugins={[remarkGfm]} components={markdownComponents}>
        {content}
      </ReactMarkdown>
    </div>
  )
}

// ── 主组件 ────────────────────────────────────────────────────────────────────
const SESSION_STORAGE_KEY = 'ai_tutor_chat_messages'

function Chat() {
  // 获取 URL 参数和导航状态
  const [searchParams, setSearchParams] = useSearchParams()
  const location = useLocation()
  const navigate = useNavigate()
  const urlGoalId = searchParams.get('goalId')
  const autoLesson = searchParams.get('autoLesson')
  const goalTitle = location.state?.goalTitle || searchParams.get('goalTitle') || ''
  
  // 初始化时从 sessionStorage 恢复聊天记录和PPT数据
  const [messages, setMessages] = useState(() => {
    try {
      const saved = sessionStorage.getItem(SESSION_STORAGE_KEY)
      if (saved) {
        const msgs = JSON.parse(saved)
        // 为有PPT数据的消息设置默认的 pptViewMode 为 'inline'
        return msgs.map(msg => {
          if (msg.toolCalls) {
            for (const tc of msg.toolCalls) {
              if ((tc.toolName === 'get_current_lesson_ppt' || tc.toolName === 'get_section_ppt_content' || tc.toolName === 'get_lesson_ppt_content' || tc.toolName === 'get_current_ppt') && tc.toolResult) {
                try {
                  const result = typeof tc.toolResult === 'string' ? JSON.parse(tc.toolResult) : tc.toolResult
                  if (result.success) {
                    return { 
                      ...msg, 
                      pptData: result,
                      pptViewMode: msg.pptViewMode || (result.slides && result.slides.length > 0 ? 'inline' : 'inline'),
                      pptCurrentPage: msg.pptCurrentPage || 0
                    }
                  }
                } catch (e) {
                  console.warn('[Chat] 恢复PPT数据解析失败:', e)
                }
              }
            }
          }
          return msg
        })
      }
      return []
    } catch {
      return []
    }
  })
  const [pptData, setPptData] = useState(() => {
    // 从恢复的消息中查找PPT数据
    try {
      const saved = sessionStorage.getItem(SESSION_STORAGE_KEY)
      if (saved) {
        const msgs = JSON.parse(saved)
        for (let i = msgs.length - 1; i >= 0; i--) {
          const msg = msgs[i]
          if (msg.toolCalls) {
            for (const tc of msg.toolCalls) {
              if ((tc.toolName === 'get_current_lesson_ppt' || tc.toolName === 'get_section_ppt_content' || tc.toolName === 'get_lesson_ppt_content' || tc.toolName === 'get_current_ppt') && tc.toolResult) {
                const result = typeof tc.toolResult === 'string' ? JSON.parse(tc.toolResult) : tc.toolResult
                if (result.success) {
                  return result
                }
              }
            }
          }
        }
      }
    } catch (e) {
      console.warn('[Chat] 恢复pptData失败:', e)
    }
    return null
  })
  
  // 初始化 PPT 视图模式 - 如果有恢复的 pptData，则显示内联卡片
  const [pptViewMode, setPptViewMode] = useState(() => {
    try {
      const saved = sessionStorage.getItem(SESSION_STORAGE_KEY)
      if (saved) {
        const msgs = JSON.parse(saved)
        for (let i = msgs.length - 1; i >= 0; i--) {
          const msg = msgs[i]
          if (msg.toolCalls) {
            for (const tc of msg.toolCalls) {
              const _isPptTool = tc.toolName === 'get_current_lesson_ppt' || tc.toolName === 'get_section_ppt_content' || tc.toolName === 'get_lesson_ppt_content' || tc.toolName === 'get_current_ppt'
              if (_isPptTool && tc.toolResult) {
                const result = typeof tc.toolResult === 'string' ? JSON.parse(tc.toolResult) : tc.toolResult
                if (result.success) {
                  // 如果已有pptViewMode设置，保持原值；否则默认inline
                  if (msg.pptViewMode) return msg.pptViewMode
                  return 'inline'  // 恢复后显示内联卡片
                }
              }
            }
          }
        }
      }
    } catch (e) {
      console.warn('[Chat] 恢复pptViewMode失败:', e)
    }
    return 'hidden'
  })
  const [pptCurrentPage, setPptCurrentPage] = useState(0)
  const [inputValue, setInputValue] = useState('')
  const [loading, setLoading] = useState(false)
  const [stopping, setStopping] = useState(false)
  const [copiedId, setCopiedId] = useState(null)

  // Canvas 状态
  const [canvasItems, setCanvasItems] = useState([])
  const [canvasPanelVisible, setCanvasPanelVisible] = useState(false)
  const [activeCanvasIndex, setActiveCanvasIndex] = useState(0)
  const [viewportWidth, setViewportWidth] = useState(typeof window !== 'undefined' ? window.innerWidth : 1280)
  const [sidebarCollapsed, setSidebarCollapsed] = useState(() => localStorage.getItem('sidebar_collapsed') === 'true')

  // PPT 可视化状态（pptData 存在时 ChatPPTVisualizer 自动显示全屏）
  // 不再需要额外的 mode 状态，组件内部自己管理显示状态

  // 追踪当前全屏查看的PPT属于哪条消息
  const [activePptMessageId, setActivePptMessageId] = useState(null)

  // 学习目标快捷入口状态
  const [quickGoals, setQuickGoals] = useState([])
  const [loadingGoals, setLoadingGoals] = useState(false)

  // 快捷操作按钮状态（当AI回复完成后显示，刷新后恢复）
  const [showQuickActions, setShowQuickActions] = useState(() => {
    try {
      const saved = sessionStorage.getItem(SESSION_STORAGE_KEY)
      if (saved) {
        const msgs = JSON.parse(saved)
        // 查找最后一条有内容且完整的AI消息
        const lastAIMsg = [...msgs].reverse().find(m => m.role === 'assistant' && m.content)
        // 如果有AI消息内容，说明回复已完成
        if (lastAIMsg) return true
      }
    } catch {}
    return false
  })

  // 从 API 获取的目标标题（兜底方案）
  const [fetchedGoalTitle, setFetchedGoalTitle] = useState('')

  // 当前活跃学习目标ID（用于追踪用户正在学习的目标）
  // 优先使用 URL 参数中的 goalId，其次使用状态中的值
  const [activeStudyGoalId, setActiveStudyGoalId] = useState(() => {
    if (urlGoalId) {
      return parseInt(urlGoalId, 10) || null
    }
    return null
  })
  
  // 使用 ref 存储 activeStudyGoalId，确保在异步请求中能获取最新值
  const activeStudyGoalIdRef = useRef(activeStudyGoalId)
  useEffect(() => {
    activeStudyGoalIdRef.current = activeStudyGoalId
  }, [activeStudyGoalId])

  // ── 获取目标标题（兜底方案）───────────────────────────────────────────────
  useEffect(() => {
    // 如果已经有目标标题，无需获取
    if (goalTitle) {
      return
    }
    // 如果没有 goalId，无需获取
    if (!urlGoalId) {
      return
    }

    const fetchGoalTitle = async () => {
      try {
        const res = await studyGoalAPI.get(urlGoalId)
        
        if (res.data?.success && res.data?.data?.title) {
          setFetchedGoalTitle(res.data.data.title)
        }
      } catch (err) {
        console.error('[Chat] 获取目标标题失败:', err)
      }
    }
    fetchGoalTitle()
  }, [urlGoalId, goalTitle])

  // 计算最终使用的目标标题（优先级：location.state > API获取 > 空）
  const finalGoalTitle = goalTitle || fetchedGoalTitle

  const abortControllerRef = useRef(null)
  const isSendingRef = useRef(false)
  const isStoppedRef = useRef(false)
  const messagesEndRef = useRef(null)
  // 用于在 useCallback([], []) 中读取最新 messages，避免在 setMessages 回调内发请求（防 StrictMode 双调）
  const messagesRef = useRef([])
  messagesRef.current = messages
  // 用于标记自动发送是否已执行，避免重复触发
  const autoLessonExecutedRef = useRef(false)

  // ── 认证头 ──────────────────────────────────────────────────────────────────
  const getAuthHeaders = () => {
    const headers = { 'Content-Type': 'application/json' }
    const token = localStorage.getItem('token')
    if (token) headers['Authorization'] = `Bearer ${token}`
    return headers
  }

  // ── 获取学习目标快捷入口列表 ────────────────────────────────────────────────
  const fetchQuickGoals = useCallback(async () => {
    setLoadingGoals(true)
    try {
      const result = await studyGoalAPI.list()
      if (result.data?.success && result.data.data) {
        // 【关键修复】优先将有进度的学习目标排在前面
        const goalsWithProgress = []
        const goalsWithoutProgress = []
        
        for (const goal of (result.data.data || [])) {
          const progress = goal.progress || {}
          const masteredPoints = progress.mastered_points || 0
          const completedLessons = progress.completed_lessons || 0
          const hasProgress = masteredPoints > 0 || completedLessons > 0
          
          const goalData = {
            id: goal.id,
            title: goal.title,
            hasProgress,
          }
          
          if (hasProgress) {
            goalsWithProgress.push(goalData)
          } else {
            goalsWithoutProgress.push(goalData)
          }
        }
        
        // 有进度的排前面，没进度的排后面
        const sortedGoals = [...goalsWithProgress, ...goalsWithoutProgress]
        const top3Goals = sortedGoals.slice(0, 3)
        setQuickGoals(top3Goals)
      }
    } catch (error) {
      console.error('获取学习目标失败:', error)
      setQuickGoals([])
    } finally {
      setLoadingGoals(false)
    }
  }, [])

  // ── 格式化时间 ──────────────────────────────────────────────────────────────
  const formatTime = (ts) => {
    if (!ts) return ''
    return dayjs(ts).format('HH:mm')
  }

  // ── 监听清空聊天事件（来自侧边栏右键菜单） ────────────────────────────────────
  useEffect(() => {
    const handleClearChat = () => {
      setMessages([])
      setCanvasItems([])
      setCanvasPanelVisible(false)
      sessionStorage.removeItem(SESSION_STORAGE_KEY)
    }
    window.addEventListener('clear-chat', handleClearChat)
    return () => window.removeEventListener('clear-chat', handleClearChat)
  }, [])

  // ── 监听学情分析刷新事件（来自 ExercisePractice 答题提交后） ──────────────────────
  useEffect(() => {
    const handleRefreshAnalysis = (e) => {
      // 刷新学习目标快捷入口数据（包含进度信息）
      fetchQuickGoals()
    }
    window.addEventListener('refresh-analysis', handleRefreshAnalysis)
    return () => window.removeEventListener('refresh-analysis', handleRefreshAnalysis)
  }, [fetchQuickGoals])

  // ── 加载学习目标快捷入口 ────────────────────────────────────────────────────
  useEffect(() => {
    fetchQuickGoals()
  }, [fetchQuickGoals])

  // ── 监听视口宽度和侧边栏状态变化 ──────────────────────────────────────────────
  useEffect(() => {
    const handleResize = () => setViewportWidth(window.innerWidth)
    const handleStorageChange = () => {
      setSidebarCollapsed(localStorage.getItem('sidebar_collapsed') === 'true')
    }
    window.addEventListener('resize', handleResize)
    window.addEventListener('storage', handleStorageChange)
    // 也监听自定义事件（同一标签页内）
    window.addEventListener('sidebar-toggle', handleStorageChange)
    return () => {
      window.removeEventListener('resize', handleResize)
      window.removeEventListener('storage', handleStorageChange)
      window.removeEventListener('sidebar-toggle', handleStorageChange)
    }
  }, [])

  // ── 自动滚动 ────────────────────────────────────────────────────────────────
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  // ── 保存聊天记录到 sessionStorage ───────────────────────────────────────────
  useEffect(() => {
    try {
      sessionStorage.setItem(SESSION_STORAGE_KEY, JSON.stringify(messages))
    } catch (e) {
      console.warn('[Chat] 保存聊天记录失败:', e)
    }
  }, [messages])

  // ── 复制消息 ────────────────────────────────────────────────────────────────
  const copyMessage = async (content, id) => {
    try {
      await navigator.clipboard.writeText(content)
      setCopiedId(id)
      setTimeout(() => setCopiedId(null), 2000)
    } catch {
      message.error('复制失败')
    }
  }

  // ── Canvas 操作 ─────────────────────────────────────────────────────────────
  const openInCanvas = useCallback((content, type, language) => {
    const titleMap = { mermaid: 'Mermaid 图表', code: `${language || ''} 代码`, html: 'HTML 预览' }
    const newItem = {
      id: `canvas-${Date.now()}`,
      type,
      content,
      language: language || '',
      title: titleMap[type] || '画布内容',
    }
    setCanvasItems(prev => {
      const next = [...prev, newItem]
      setActiveCanvasIndex(next.length - 1)
      return next
    })
    setCanvasPanelVisible(true)
  }, [])

  // ── 停止生成 ────────────────────────────────────────────────────────────────
  const stopGeneration = useCallback(() => {
    if (abortControllerRef.current) {
      isStoppedRef.current = true
      setStopping(true)
      abortControllerRef.current.abort()
      message.info('已停止生成')
    }
  }, [])

  // ── 新对话 ──────────────────────────────────────────────────────────────────
  const startNewChat = useCallback(() => {
    setMessages([])
    setCanvasItems([])
    setCanvasPanelVisible(false)
  }, [])
  
  // ── 发送消息 ────────────────────────────────────────────────────────────────
  // 将附件中的图片转换为 base64 字符串列表（与后端 List[str] 格式一致）
  const convertAttachmentsToImages = (attachments) => {
    return attachments
      .filter(att => att.type === 'image' && att.file)
      .map(att => {
        return new Promise((resolve, reject) => {
          const reader = new FileReader()
          reader.onload = () => {
            // 提取纯 base64 数据（去掉 data:image/...;base64, 前缀）
            const base64 = reader.result.split(',')[1]
            resolve(base64)
          }
          reader.onerror = reject
          reader.readAsDataURL(att.file)
        })
      })
  }
  
  // 将附件中的文档（PDF/Word/TXT）转换为对象列表
  const convertAttachmentsToDocuments = (attachments) => {
    return attachments
      .filter(att => att.type !== 'image' && att.file)
      .map(att => {
        return new Promise((resolve, reject) => {
          const reader = new FileReader()
          reader.onload = () => {
            // 提取纯 base64 数据
            const base64 = reader.result.split(',')[1]
            // 根据文件类型确定文档类型
            let docType = 'txt'
            if (att.name) {
              const ext = att.name.split('.').pop()?.toLowerCase()
              if (ext === 'pdf') docType = 'pdf'
              else if (ext === 'doc' || ext === 'docx') docType = 'docx'
              else if (ext === 'txt') docType = 'txt'
            }
            resolve({
              name: att.name || '未命名文档',
              type: docType,
              data: base64,
            })
          }
          reader.onerror = reject
          reader.readAsDataURL(att.file)
        })
      })
  }

  const sendMessageDirect = useCallback(async (messageContent, attachments = []) => {
    if (isSendingRef.current) return
    isSendingRef.current = true
    isStoppedRef.current = false

    const userMessage = {
      id: Date.now(),
      role: 'user',
      content: messageContent,
      attachments,
      timestamp: new Date(),
    }

    const aiMessageId = Date.now() + 1

    // 在 setMessages 外计算历史，避免在更新函数内发起请求（React StrictMode 会调两次更新函数）
    // 构建历史消息：携带工具调用信息，后端据此重建OpenAI标准的tool_calls+tool消息序列
    // 重要：当消息有 toolCalls 时，content 应为空，避免模型误以为需要输出类似的引导语
    const historyForRequest = messagesRef.current.map(m => {
      const entry = { role: m.role }
      if (m.role === 'assistant' && m.toolCalls?.length > 0) {
        // 有工具调用时，content 为空，只保留 toolCalls
        // 回复内容应该只来自工具调用后的最终输出
        entry.content = ''
        entry.toolCalls = m.toolCalls
      } else {
        entry.content = m.content || ''
      }
      return entry
    })

    setLoading(true)
    setStopping(false)
    setShowQuickActions(false) // 隐藏快捷操作按钮
    abortControllerRef.current = new AbortController()

    // 将附件中的图片和文档分别转换
    let images = []
    let documents = []
    if (attachments && attachments.length > 0) {
      try {
        const imagePromises = convertAttachmentsToImages(attachments)
        images = await Promise.all(imagePromises)
      } catch (err) {
        console.error('[Chat] 转换图片失败:', err)
      }
      try {
        const docPromises = convertAttachmentsToDocuments(attachments)
        documents = await Promise.all(docPromises)
      } catch (err) {
        console.error('[Chat] 转换文档失败:', err)
      }
    }

    // 仅用于更新消息列表状态，不含副作用
    setMessages(prev => [...prev, userMessage, { id: aiMessageId, role: 'assistant', content: '', toolCalls: [], statusMessage: '', timestamp: new Date() }])

    // fetch 在 setMessages 外部调用，确保只执行一次
    fetch('/api/chat/message/stream', {
      method: 'POST',
      headers: getAuthHeaders(),
      body: JSON.stringify({
        message: messageContent,
        history: historyForRequest,
        images: images.length > 0 ? images : null,
        documents: documents.length > 0 ? documents : null,
        goal_id: activeStudyGoalIdRef.current,  // 使用 ref 确保获取最新值
      }),
      signal: abortControllerRef.current.signal,
    })
    .then(response => {
      if (!response.ok) throw new Error('Network response was not ok')
      const reader = response.body.getReader()
      const decoder = new TextDecoder()

      const readStream = async () => {
        while (true) {
          if (isStoppedRef.current) break
          const { done, value } = await reader.read()
          if (isStoppedRef.current) break
          if (done) break

          const chunk = decoder.decode(value, { stream: true })
          for (const line of chunk.split('\n')) {
            if (line.startsWith('data: ')) {
              const jsonStr = line.slice(6)
              const parseResult = safeJsonParse(jsonStr)
              if (!parseResult.success) {
                // 如果解析失败但包含 SSE 数据，可能是流被截断，继续等待下一块数据
                console.warn('[Chat] JSON 解析失败，可能因流式传输被截断:', parseResult.error?.message)
                continue
              }
              const data = parseResult.data

              // 处理特殊 Action 事件（如 session_ended）
              if (data.action === 'session_ended' && data.data) {
                // 显示学习记录保存成功的提示
                if (data.data.message) {
                  message.success(data.data.message)
                }
                // 隐藏快捷操作按钮（结束学习后不再需要）
                setShowQuickActions(false)
              }

              // 工具调用状态
              if (data.status === 'thinking' && data.status_message) {
                setMessages(msgPrev => {
                  const idx = msgPrev.findIndex(msg => msg.id === aiMessageId)
                  if (idx === -1) return msgPrev
                  const next = [...msgPrev]
                  next[idx] = { ...next[idx], statusMessage: data.status_message }
                  return next
                })
              }

              // 工具调用结果
              if (data.tool_call) {
                setMessages(msgPrev => {
                  const idx = msgPrev.findIndex(msg => msg.id === aiMessageId)
                  if (idx === -1) return msgPrev
                  const next = [...msgPrev]
                  const existingToolCalls = next[idx].toolCalls || []
                  // 查找是否已有同名调用中状态，有则更新为完成，否则新增
                  const callIdx = existingToolCalls.findIndex(
                    tc => tc.toolName === data.tool_call && tc.status === 'calling'
                  )
                  let newToolCalls
                  if (callIdx !== -1) {
                    newToolCalls = existingToolCalls.map((tc, i) =>
                      i === callIdx ? { ...tc, toolResult: data.tool_result, status: 'done' } : tc
                    )
                  } else {
                    newToolCalls = [
                      ...existingToolCalls,
                      { toolName: data.tool_call, toolResult: data.tool_result, status: 'done' },
                    ]
                  }
                  
                  // 检测是否为PPT数据并存储到消息中
                  let pptDataUpdate = {}
                  const _isPptToolCall = data.tool_call === 'get_current_lesson_ppt' || data.tool_call === 'get_section_ppt_content' || data.tool_call === 'get_lesson_ppt_content' || data.tool_call === 'get_current_ppt'
                  if (_isPptToolCall && data.tool_result) {
                    try {
                      const result = typeof data.tool_result === 'string'
                        ? JSON.parse(data.tool_result)
                        : data.tool_result
                      if (result && result.success && result.slides && result.slides.length > 0) {
                        pptDataUpdate = { 
                          pptData: result,
                          pptViewMode: 'inline',
                          pptCurrentPage: 0
                        }
                        // 默认显示inline迷你卡片，用户点击后可切换到fullscreen
                        setPptData(result)
                        setPptViewMode('inline')
                        setPptCurrentPage(0)
                        setActivePptMessageId(aiMessageId)
                        // 从PPT工具返回结果中提取goal_id并更新activeStudyGoalId
                        if (result.goal_id) {
                          setActiveStudyGoalId(result.goal_id)
                        }
                      }
                    } catch (e) {
                      console.warn('[Chat] 解析PPT数据失败:', e, 'raw:', data.tool_result?.substring?.(0, 200))
                    }
                  }
                  
                  // 检测是否为习题数据并存储到消息中
                  let exerciseDataUpdate = {}
                  const _isExerciseToolCall = data.tool_call === 'get_section_exercises'
                  if (_isExerciseToolCall && data.tool_result) {
                    try {
                      const result = typeof data.tool_result === 'string'
                        ? JSON.parse(data.tool_result)
                        : data.tool_result
                      if (result && result.success && result.exercises && result.exercises.length > 0) {
                        exerciseDataUpdate = {
                          exerciseData: result
                        }
                      }
                    } catch (e) {
                      console.warn('[Chat] 解析习题数据失败:', e, 'raw:', data.tool_result?.substring?.(0, 200))
                    }
                  }
                  
                  next[idx] = { ...next[idx], toolCalls: newToolCalls, statusMessage: '', ...pptDataUpdate, ...exerciseDataUpdate }
                  
                  return next
                })
              }

              // 流式内容块
              if (data.type === 'chunk' && data.content && typeof data.content === 'string') {
                setMessages(msgPrev => {
                  const idx = msgPrev.findIndex(msg => msg.id === aiMessageId)
                  if (idx === -1) return msgPrev
                  const next = [...msgPrev]
                  const prevMsg = next[idx]
                  next[idx] = { 
                    ...next[idx], 
                    content: (prevMsg.content || '') + data.content, 
                    statusMessage: '',
                    pptData: prevMsg.pptData || next[idx].pptData,
                    pptViewMode: prevMsg.pptViewMode || next[idx].pptViewMode,
                    pptCurrentPage: prevMsg.pptCurrentPage ?? next[idx].pptCurrentPage ?? 0,
                    exerciseData: prevMsg.exerciseData || next[idx].exerciseData
                  }
                  return next
                })
              }

              if (data.done) {
                setLoading(false)
                setShowQuickActions(true) // 显示快捷操作按钮
                // 确保 PPT 全局状态与消息中的 pptData 一致
                setMessages(msgPrev => {
                  const idx = msgPrev.findIndex(msg => msg.id === aiMessageId)
                  if (idx !== -1 && msgPrev[idx].pptData) {
                    const msg = msgPrev[idx]
                    // 更新全局 PPT 状态
                    setPptData(msg.pptData)
                    setPptViewMode(msg.pptViewMode || 'fullscreen')
                    setPptCurrentPage(msg.pptCurrentPage ?? 0)
                    setActivePptMessageId(aiMessageId)
                  }
                  return msgPrev
                })
                return
              }
              if (data.error) throw new Error(data.error)
            }
          }
        }
      }
      readStream()
    })
    .catch(error => {
      console.error('[Chat] 请求失败:', error)
      if (error.name !== 'AbortError') {
        message.error('发送消息失败: ' + error.message)
        setMessages(msgPrev => msgPrev.filter(m => m.id !== aiMessageId))
      }
    })
    .finally(() => {
      isSendingRef.current = false
      setLoading(false)
      setStopping(false)
      abortControllerRef.current = null
    })
  }, [])

  const handleSend = useCallback((text, attachments) => {
    if (!text && (!attachments || attachments.length === 0)) return
    if (isSendingRef.current || loading) return
    sendMessageDirect(text, attachments)
  }, [loading, sendMessageDirect])

  // ── 自动加载课件（从学习计划页面跳转时触发）──────────────────────────────────
  useEffect(() => {
    // 确保只执行一次，且满足条件
    if (autoLessonExecutedRef.current) {
      return
    }
    if (autoLesson !== 'true') {
      return
    }
    if (!urlGoalId) {
      return
    }
    // 需要有目标名称才能发送消息（优先使用 finalGoalTitle）
    const title = goalTitle || fetchedGoalTitle
    if (!title) {
      return
    }
    
    // 标记为已执行
    autoLessonExecutedRef.current = true

    // 设置当前活跃的学习目标ID
    const goalIdInt = parseInt(urlGoalId, 10)
    if (!isNaN(goalIdInt)) {
      setActiveStudyGoalId(goalIdInt)
    }

    // 构造消息并发送（格式：继续学习下一节「目标名称」）
    // 必须包含"下一节"关键词，后端意图检测才能识别
    const messageContent = `继续学习下一节「${title}」`
    
    // 直接调用 sendMessageDirect，避免 handleSend 的 loading 检查可能阻止发送
    // 使用 setTimeout 确保状态更新完成
    setTimeout(() => {
      if (!isSendingRef.current) {
        sendMessageDirect(messageContent)
      } else {
        setTimeout(() => sendMessageDirect(messageContent), 500)
      }
    }, 100)  // 增加延迟确保状态更新完成

    // 清除 URL 中的 autoLesson 参数，避免刷新页面重复触发
    setSearchParams(prev => {
      prev.delete('autoLesson')
      return prev
    }, { replace: true })
  }, [autoLesson, urlGoalId, goalTitle, fetchedGoalTitle, sendMessageDirect, setSearchParams])

  // ── 学习计划页面"继续学习"按钮处理 ─────────────────────────────────────────
  const autoContinue = location.state?.autoContinue === true
  
  useEffect(() => {
    if (!autoContinue) return
    if (!urlGoalId) return
    
    const title = goalTitle || fetchedGoalTitle
    if (!title) return

    // 设置当前活跃的学习目标ID
    const goalIdInt = parseInt(urlGoalId, 10)
    if (!isNaN(goalIdInt)) {
      setActiveStudyGoalId(goalIdInt)
    }

    // 构造消息（格式：继续学习「目标名称」），与首页完全一致
    const messageContent = `继续学习「${title}」`
    
    // 发送消息
    setTimeout(() => {
      if (!isSendingRef.current) {
        sendMessageDirect(messageContent)
      }
    }, 100)

    // 清除 state，避免刷新页面重复触发
    navigate(location.pathname + location.search, { replace: true, state: {} })
  }, [autoContinue, urlGoalId, goalTitle, fetchedGoalTitle, sendMessageDirect, navigate, location])

  // ── 学习目标快捷入口点击处理 ────────────────────────────────────────────────
  const handleQuickGoalClick = useCallback((goal) => {
    // 记录当前正在学习的目标ID
    setActiveStudyGoalId(goal.id)
    const actionText = goal.hasProgress ? '继续学习' : '开始学习'
    const messageContent = `${actionText}「${goal.title}」`
    // 发送消息并开始学习
    handleSend(messageContent)
  }, [handleSend])

  // ── 快捷操作按钮点击处理 ──────────────────────────────────────────────────
  const handleQuickAction = useCallback(async (actionKey, actionData = {}) => {
    setShowQuickActions(false) // 隐藏按钮

    switch (actionKey) {
      case 'practice':
        // 向Agent发送请求习题的消息，由Agent调用get_section_exercises工具获取习题
        handleSend('为这一小节推荐习题')
        break
      default:
        break
    }
  }, [quickGoals, activeStudyGoalId, handleSend])

  // 练习巩固完成后的后续操作处理（习题已内联到消息中）
  const handlePracticeComplete = useCallback((action) => {
    switch (action) {
      case 'next':
        handleSend('继续学习下一节内容')
        break
      case 'retry':
        // 重新请求习题
        handleSend('为这一小节推荐习题')
        break
      case 'finish':
        handleSend('今天的学习到此结束，感谢陪伴！')
        break
    }
  }, [handleSend])


  const hasMessages = messages.length > 0

  return (
    <div style={{
      height: '100vh',
      display: 'flex',
      flexDirection: 'column',
      background: '#ffffff',
      overflow: 'hidden',
    }}>
      {/* ── 主体区域 ── */}
      <div style={{ flex: 1, display: 'flex', overflow: 'hidden' }}>

        {/* ── 左侧聊天区域 ── */}
        <div style={{
          flex: 1,
          display: 'flex',
          flexDirection: 'column',
          overflow: 'hidden',
          transition: 'all 0.3s',
        }}>
          {/* 消息列表 */}
          <div style={{ flex: 1, overflowY: 'auto', padding: '32px 20px 100px' }}>
            <div style={{ maxWidth: 768, margin: '0 auto' }}>

              {/* 无消息时：欢迎区域 */}
              <AnimatePresence>
                {!hasMessages && (
                  <motion.div
                    key="welcome"
                    initial={{ opacity: 0, scale: 0.95 }}
                    animate={{ opacity: 1, scale: 1 }}
                    exit={{ opacity: 0, scale: 0.95 }}
                    transition={{ duration: 0.3 }}
                    style={{
                      display: 'flex',
                      flexDirection: 'column',
                      alignItems: 'center',
                      justifyContent: 'center',
                      minHeight: 'calc(100vh - 200px)',
                      textAlign: 'center',
                      padding: '40px 20px',
                    }}
                  >
                    <div style={{
                      width: 56,
                      height: 56,
                      borderRadius: 16,
                      background: 'linear-gradient(145deg, #0ea5e9, #6366f1, #8b5cf6)',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      marginBottom: 20,
                      boxShadow: '0 12px 32px rgba(99,102,241,0.35), inset 0 1px 0 rgba(255,255,255,0.25)',
                      border: '1px solid rgba(255,255,255,0.2)',
                    }}>
                      <span style={{ color: '#fff', fontSize: 28, fontWeight: 800, textShadow: '0 2px 4px rgba(0,0,0,0.15)' }}>T</span>
                    </div>
                    <div style={{ fontSize: 20, fontWeight: 600, color: '#1e293b', marginBottom: 8 }}>
                      你好，我是 AI Tutor
                    </div>
                    <div style={{ fontSize: 14, color: '#64748b', marginBottom: 24 }}>
                      你的智能学习助手，有什么我可以帮你的吗？
                    </div>

                    {/* 学习目标快捷入口 - 横向卡片式排列 */}
                    {!loadingGoals && quickGoals.length > 0 && (
                      <div style={{
                        display: 'flex',
                        gap: 16,
                        justifyContent: 'center',
                        marginTop: 24,
                        width: '100%',
                        maxWidth: 720,
                      }}>
                        {quickGoals.map((goal) => (
                          <motion.button
                            key={goal.id}
                            whileHover={{ scale: 1.02, y: -2 }}
                            whileTap={{ scale: 0.98 }}
                            onClick={() => handleQuickGoalClick(goal)}
                            style={{
                              flex: 1,
                              maxWidth: 220,
                              minWidth: 160,
                              padding: '18px 16px',
                              borderRadius: 12,
                              border: '1px solid #e5e7eb',
                              background: '#ffffff',
                              color: '#1f2937',
                              fontSize: 14,
                              fontWeight: 500,
                              cursor: 'pointer',
                              display: 'flex',
                              flexDirection: 'column',
                              alignItems: 'center',
                              gap: 6,
                              boxShadow: '0 1px 3px rgba(0,0,0,0.08)',
                              transition: 'all 0.2s ease',
                              textAlign: 'center',
                            }}
                            onMouseEnter={(e) => {
                              e.currentTarget.style.borderColor = '#f97316'
                              e.currentTarget.style.boxShadow = '0 4px 12px rgba(249, 115, 22, 0.15)'
                            }}
                            onMouseLeave={(e) => {
                              e.currentTarget.style.borderColor = '#e5e7eb'
                              e.currentTarget.style.boxShadow = '0 1px 3px rgba(0,0,0,0.08)'
                            }}
                          >
                            <span style={{ fontSize: 28, marginBottom: 4 }}>
                              {goal.hasProgress ? '📚' : '🎯'}
                            </span>
                            <span style={{
                              fontSize: 12,
                              color: '#6b7280',
                              fontWeight: 500,
                            }}>
                              {goal.hasProgress ? '继续学习' : '开始学习'}
                            </span>
                            <span style={{
                              fontSize: 13,
                              fontWeight: 600,
                              lineHeight: 1.4,
                              maxWidth: '100%',
                              overflow: 'hidden',
                              textOverflow: 'ellipsis',
                              whiteSpace: 'nowrap',
                              color: '#111827',
                            }}>
                              {goal.title}
                            </span>
                          </motion.button>
                        ))}
                      </div>
                    )}

                    {/* 没有学习目标时的提示 */}
                    {!loadingGoals && quickGoals.length === 0 && (
                      <motion.button
                        whileHover={{ scale: 1.02, y: -1 }}
                        whileTap={{ scale: 0.98 }}
                        onClick={() => {
                          // 触发创建学习目标弹窗
                          window.dispatchEvent(new CustomEvent('open-goal-form'))
                        }}
                        style={{
                          marginTop: 24,
                          padding: '12px 24px',
                          borderRadius: 8,
                          border: '1px solid #e5e7eb',
                          background: '#ffffff',
                          color: '#374151',
                          fontSize: 14,
                          fontWeight: 500,
                          cursor: 'pointer',
                          display: 'flex',
                          alignItems: 'center',
                          gap: 8,
                          boxShadow: '0 1px 3px rgba(0,0,0,0.06)',
                          transition: 'all 0.2s ease',
                        }}
                        onMouseEnter={(e) => {
                          e.currentTarget.style.borderColor = '#f97316'
                          e.currentTarget.style.background = '#fff7ed'
                          e.currentTarget.style.color = '#ea580c'
                        }}
                        onMouseLeave={(e) => {
                          e.currentTarget.style.borderColor = '#e5e7eb'
                          e.currentTarget.style.background = '#ffffff'
                          e.currentTarget.style.color = '#374151'
                        }}
                      >
                        <span style={{ fontSize: 16 }}>✨</span>
                        <span>创建一个学习目标吧</span>
                      </motion.button>
                    )}
                  </motion.div>
                )}
              </AnimatePresence>

              {/* 消息列表 */}
              <AnimatePresence>
                {messages.map((msg) => (
                  <motion.div
                    key={msg.id}
                    initial={{ opacity: 0, y: 16 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ duration: 0.22, ease: 'easeOut' }}
                    style={{ marginBottom: 24 }}
                  >
                    {msg.role === 'assistant' ? (
                      /* ── AI 消息 ── */
                      <div style={{ display: 'flex', gap: 12, alignItems: 'flex-start' }}>
                        <AIAvatar size={28} />
                        <div style={{ flex: 1, minWidth: 0 }}>
                          {/* ── 工具调用卡片（如有）显示在消息上方 ── */}
                          {msg.toolCalls && msg.toolCalls.length > 0 && (
                            <div style={{ marginBottom: 12 }}>
                              {msg.toolCalls.map((tc, i) => (
                                <ToolCallCard key={i} toolCall={tc} />
                              ))}
                            </div>
                          )}
                          {/* ── 消息内容 ── */}
                          <div style={{
                            color: '#1e293b',
                            fontSize: 14,
                            lineHeight: 1.7,
                            wordBreak: 'break-word',
                          }}>
                            {/* 工具调用状态指示器 */}
                            {msg.statusMessage && !msg.content && (
                              <ToolStatusIndicator statusMessage={msg.statusMessage} />
                            )}
                            {msg.content
                              ? <AIMessageContent content={msg.content} openInCanvas={openInCanvas} />
                              : !msg.statusMessage && (!msg.toolCalls || msg.toolCalls.length === 0) && (
                                <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                                  {stopping ? (
                                    <>
                                      <LoadingOutlined style={{ color: '#6366f1', fontSize: 14 }} />
                                      <span style={{ color: '#94a3b8', fontSize: 13 }}>正在停止...</span>
                                    </>
                                  ) : (
                                    <div className="thinking-dots">
                                      <span className="thinking-dot" />
                                      <span className="thinking-dot" />
                                      <span className="thinking-dot" />
                                    </div>
                                  )}
                                </div>
                              )
                            }
                            {/* PPT 内联迷你卡片 */}
                            {msg.pptData && msg.pptViewMode === 'inline' && (
                              <InlineMiniCard 
                                pptData={msg.pptData} 
                                currentPage={msg.pptCurrentPage || 0} 
                                onExpand={() => {
                                  setPptData(msg.pptData)
                                  setPptCurrentPage(msg.pptCurrentPage || 0)
                                  setPptViewMode('fullscreen')
                                  setActivePptMessageId(msg.id)
                                }}
                              />
                            )}
                            {/* 内联习题卡片 */}
                            {msg.exerciseData && (
                              <InlineExerciseCard
                                exerciseData={msg.exerciseData}
                                onComplete={() => {
                                  setMessages(msgPrev => msgPrev.map(m =>
                                    m.id === msg.id ? { ...m, exerciseData: null } : m
                                  ))
                                }}
                                onNextSection={() => handlePracticeComplete('next')}
                                onFinish={() => handlePracticeComplete('finish')}
                              />
                            )}
                            {/* 快捷操作按钮 */}
                            {msg.pptData && showQuickActions && msg === messages.filter(m => m.role === 'assistant' && m.content).slice(-1)[0] && msg.content && (
                              <QuickActionButtons 
                                onAction={handleQuickAction} 
                                loading={loading}
                              />
                            )}
                          </div>
                          <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginTop: 6 }}>
                            <span style={{ fontSize: 11, color: '#94a3b8' }}>{formatTime(msg.timestamp)}</span>
                            {msg.content && (
                              <Tooltip title={copiedId === msg.id ? '已复制' : '复制'}>
                                <motion.button
                                  whileHover={{ scale: 1.1 }}
                                  whileTap={{ scale: 0.9 }}
                                  onClick={() => copyMessage(msg.content, msg.id)}
                                  style={{
                                    width: 24, height: 24, borderRadius: 6,
                                    border: 'none', background: 'transparent', cursor: 'pointer',
                                    display: 'flex', alignItems: 'center', justifyContent: 'center',
                                    color: copiedId === msg.id ? '#10b981' : '#94a3b8',
                                    transition: 'all 0.15s',
                                  }}
                                >
                                  {copiedId === msg.id
                                    ? <CheckOutlined style={{ fontSize: 12 }} />
                                    : <CopyOutlined style={{ fontSize: 12 }} />}
                                </motion.button>
                              </Tooltip>
                            )}
                          </div>
                        </div>
                      </div>
                    ) : (
                      /* ── 用户消息 ── */
                      <div style={{ display: 'flex', justifyContent: 'flex-end' }}>
                        <div style={{ maxWidth: '70%' }}>
                          {msg.attachments && msg.attachments.length > 0 && (
                            <div style={{ marginBottom: 8 }}>
                              <AttachmentDisplay attachments={msg.attachments} />
                            </div>
                          )}
                          <div style={{
                            background: '#f1f5f9',
                            borderRadius: 18,
                            padding: '10px 16px',
                            color: '#1e293b',
                            fontSize: 14,
                            lineHeight: 1.65,
                            wordBreak: 'break-word',
                            whiteSpace: 'pre-wrap',
                          }}>
                            {msg.content}
                          </div>
                          <div style={{ display: 'flex', justifyContent: 'flex-end', marginTop: 4 }}>
                            <span style={{ fontSize: 11, color: '#94a3b8' }}>{formatTime(msg.timestamp)}</span>
                          </div>
                        </div>
                      </div>
                    )}
                  </motion.div>
                ))}
              </AnimatePresence>

              {/* 加载状态：在消息列表的 AI 消息中已包含，这里不再单独渲染 */}

              <div ref={messagesEndRef} style={{ height: 8 }} />
            </div>
          </div>

          {/* ── 输入区域（固定定位悬浮，相对于聊天区域居中） */}
          {(
          <div style={{
            position: 'fixed',
            bottom: 19,
            width: 768,
            left: canvasPanelVisible
              ? (sidebarCollapsed ? 64 : 288) + (viewportWidth - (sidebarCollapsed ? 64 : 288) - 481 - 768) / 2  // 侧边栏 + CanvasPanel481px
              : (sidebarCollapsed ? 64 : 288) + (viewportWidth - (sidebarCollapsed ? 64 : 288) - 768) / 2,       // 侧边栏
            zIndex: 50,
            transition: 'left 0.2s cubic-bezier(0.25, 0.46, 0.45, 0.94)',
          }}>
            <div style={{ padding: '0 20px 0' }}>
              <ChatInputBar
                value={inputValue}
                onChange={setInputValue}
                onSend={handleSend}
                loading={loading}
                stopping={stopping}
                onStop={stopGeneration}
              />
            </div>
          </div>
          )}
        </div>

        {/* ── 右侧 Canvas Panel ── */}
        <CanvasPanel
          visible={canvasPanelVisible}
          onClose={() => setCanvasPanelVisible(false)}
          items={canvasItems}
          activeIndex={activeCanvasIndex}
          onTabChange={setActiveCanvasIndex}
        />
      </div>

      {/* ── PPT 全屏查看器 ── */}
      <ChatPPTVisualizer
        pptData={pptData}
        viewMode={pptViewMode === 'fullscreen' ? 'fullscreen' : 'hidden'}
        currentPage={pptCurrentPage}
        onPageChange={(page) => {
          setPptCurrentPage(page)
          // 同时更新对应消息的 pptCurrentPage
          if (activePptMessageId) {
            setMessages(msgPrev => msgPrev.map(msg => 
              msg.id === activePptMessageId 
                ? { ...msg, pptCurrentPage: page }
                : msg
            ))
          }
        }}
        onCollapse={() => {
          // 将对应消息的 pptViewMode 设置为 inline
          if (activePptMessageId) {
            setMessages(msgPrev => msgPrev.map(msg => 
              msg.id === activePptMessageId 
                ? { ...msg, pptViewMode: 'inline' }
                : msg
            ))
          }
          setPptViewMode('hidden')
          setActivePptMessageId(null)
        }}
        onExpand={() => setPptViewMode('fullscreen')}
      />

      {/* ── CSS ── */}
      <style>{`
        .thinking-dots {
          display: flex;
          align-items: center;
          gap: 4px;
        }
        .thinking-dot {
          display: inline-block;
          width: 7px;
          height: 7px;
          background: #94a3b8;
          border-radius: 50%;
          animation: thinking-bounce 1.4s infinite ease-in-out both;
        }
        .thinking-dot:nth-child(1) { animation-delay: -0.32s; }
        .thinking-dot:nth-child(2) { animation-delay: -0.16s; }
        .thinking-dot:nth-child(3) { animation-delay: 0s; }
        @keyframes thinking-bounce {
          0%, 80%, 100% { transform: scale(0.6); opacity: 0.4; }
          40% { transform: scale(1); opacity: 1; }
        }
        .tool-call-spinner {
          animation: tool-spin 0.8s linear infinite;
        }
        @keyframes tool-spin {
          from { transform: rotate(0deg); }
          to   { transform: rotate(360deg); }
        }
      `}</style>
    </div>
  )
}

export default Chat
