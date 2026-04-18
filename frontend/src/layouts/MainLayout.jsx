import { useState, useEffect, useCallback, useRef } from 'react'
import { Spin, message, Modal, DatePicker, Form, InputNumber, Radio, Slider, Input, Select, Button, App } from 'antd'
import { Drawer } from 'antd'
import dayjs from 'dayjs'
import {
  RobotOutlined,
  BookOutlined,
  PlusOutlined,
  ApartmentOutlined,
  CalendarOutlined,
  BarChartOutlined,
  FileTextOutlined,
  QuestionCircleOutlined,
  MessageOutlined,
  RightOutlined,
  DownOutlined,
  MenuFoldOutlined,
  MenuUnfoldOutlined,
  UserOutlined,
  LogoutOutlined,
  SettingOutlined,
  DeleteOutlined,
  HeartOutlined,
  AimOutlined,
  EditOutlined,
  AppstoreOutlined,
} from '@ant-design/icons'
import { Outlet, useParams, useNavigate, useLocation } from 'react-router-dom'
import { motion, AnimatePresence } from 'framer-motion'
import { studyGoalAPI } from '../utils/api'
import LearningStyle from '../components/LearningStyle'
import apiClient from '../utils/api'

const { Option } = Select

const MODULES = [
  { key: 'knowledge-graph', icon: <ApartmentOutlined />, label: '知识图谱', color: '#6366f1' },
  { key: 'learning-plan',   icon: <CalendarOutlined />,  label: '学习计划', color: '#06b6d4' },
  { key: 'analysis',        icon: <BarChartOutlined />,  label: '学情分析', color: '#10b981' },
  { key: 'materials',       icon: <FileTextOutlined />,  label: '学习资料', color: '#f59e0b' },
  { key: 'questions',       icon: <QuestionCircleOutlined />, label: '习题库', color: '#ec4899' },
  { key: 'chat',            icon: <MessageOutlined />,   label: '学习记录', color: '#8b5cf6' },
]

// Gradient colors for goals
const GOAL_GRADIENTS = [
  'linear-gradient(135deg,#6366f1,#8b5cf6)',
  'linear-gradient(135deg,#06b6d4,#10b981)',
  'linear-gradient(135deg,#f59e0b,#ec4899)',
  'linear-gradient(135deg,#ec4899,#6366f1)',
  'linear-gradient(135deg,#10b981,#06b6d4)',
]

function MainLayout() {
  const { goalId } = useParams()
  const navigate = useNavigate()
  const location = useLocation()
  const [goals, setGoals] = useState([])
  const [loading, setLoading] = useState(true)
  const [collapsed, setCollapsed] = useState(() => localStorage.getItem('sidebar_collapsed') === 'true')
  const [expandedGoals, setExpandedGoals] = useState([])
  const [profileMenuVisible, setProfileMenuVisible] = useState(false)
  const [contextMenu, setContextMenu] = useState({ visible: false, x: 0, y: 0, goalId: null, goalTitle: '', type: 'goal' })
  const [learningStyleVisible, setLearningStyleVisible] = useState(false)

  // AI Tutor 快捷方式重命名状态
  const [aiTutorRenameVisible, setAiTutorRenameVisible] = useState(false)
  const [aiTutorName, setAiTutorName] = useState(() => localStorage.getItem('ai_tutor_name') || 'AI Tutor')
  const [renameInput, setRenameInput] = useState('')

  // 侧边栏收起/展开时保存状态
  const handleToggleCollapsed = () => {
    const newCollapsed = !collapsed
    setCollapsed(newCollapsed)
    localStorage.setItem('sidebar_collapsed', String(newCollapsed))
    // 触发自定义事件让 Chat 页面及时响应
    window.dispatchEvent(new CustomEvent('sidebar-toggle'))
  }

  // 保存 AI Tutor 名称
  const handleSaveAiTutorName = () => {
    const name = renameInput.trim() || 'AI Tutor'
    setAiTutorName(name)
    localStorage.setItem('ai_tutor_name', name)
    setAiTutorRenameVisible(false)
    setRenameInput('')
  }

  // 学习目标表单相关状态
  const [showGoalForm, setShowGoalForm] = useState(false)  // 显示目标表单弹窗
  const [goalFormLoading, setGoalFormLoading] = useState(false)  // 表单提交loading
  const [form] = Form.useForm()  // 表单实例
  
  const getUserInfo = () => {
    const username = localStorage.getItem('username') || '用户'
    const email = localStorage.getItem('email') || ''
    return { username, email }
  }
  
  // 学习目标表单提交处理
  const handleGoalFormSubmit = async (values) => {
    setGoalFormLoading(true)
    try {
      const studentId = localStorage.getItem('student_id')
      if (!studentId) {
        showError('未登录或会话已过期，请重新登录')
        setGoalFormLoading(false)
        return
      }
      
      const requestData = {
        student_id: parseInt(studentId),
        title: values.title,
        description: values.description || '',
        subject: values.subject || null,
        target_hours_per_week: values.targetHoursPerWeek || 5.0,
        target_completion_date: values.targetCompletionDate ? dayjs(values.targetCompletionDate).format('YYYY-MM-DD') : null,
        study_depth: values.studyDepth || 'intermediate',
        has_reference_book: false,
        reference_book: null,
        reference_book_files: [],
        has_exercise_bank: false,
        exercise_bank_files: [],
        model: null,
      }
      
      const response = await apiClient.post('/chat/create-goal-from-chat', requestData)
      
      if (response.data.success && response.data.data) {
        const goalData = response.data.data
        
        // 重置表单
        form.resetFields()
        
        // 关闭弹窗
        setShowGoalForm(false)
        
        // 显示成功消息
        showSuccess({ content: `学习目标「${goalData.title}」创建成功！`, duration: 3 })
        
        // 刷新目标列表
        fetchGoals()
        
        // 自动展开新创建的目标
        if (goalData.goal_id && !expandedGoals.includes(String(goalData.goal_id))) {
          setExpandedGoals(prev => [...prev, String(goalData.goal_id)])
        }
        
        // 导航到新创建的目标
        navigate(`/goals/${goalData.goal_id}/knowledge-graph`)
        
        // 触发事件
        window.dispatchEvent(new CustomEvent('goal-created', { 
          detail: { 
            goalId: goalData.goal_id, 
            title: goalData.title,
            totalNodes: goalData.total_nodes,
            estimatedHours: goalData.estimated_hours
          }
        }))
      } else {
        showError(response.data.message || '创建学习目标失败')
      }
    } catch (error) {
      console.error('创建学习目标失败:', error)
      showError('创建学习目标失败，请重试')
    } finally {
      setGoalFormLoading(false)
    }
  }
  
  // 关闭表单时重置表单
  const handleGoalFormClose = () => {
    setShowGoalForm(false)
    form.resetFields()
  }
  
  const handleLogout = () => {
    localStorage.removeItem('token')
    localStorage.removeItem('username')
    localStorage.removeItem('email')
    showSuccess('已退出登录')
    navigate('/login')
  }

  // 获取目标列表
  const fetchGoals = useCallback(async () => {
    setLoading(true)
    try {
      const studentId = localStorage.getItem('student_id') || '1'
      const result = await studyGoalAPI.list(parseInt(studentId))
      if (result.data?.success) setGoals(result.data?.data || [])
    } catch {
      showError('获取学习目标失败')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => { fetchGoals() }, [fetchGoals])

  // 监听学习目标创建事件
  useEffect(() => {
    const handleGoalCreated = (e) => {
      const { goalId } = e.detail
      // 刷新目标列表
      fetchGoals()
      // 自动展开新创建的目标
      if (goalId && !expandedGoals.includes(String(goalId))) {
        setExpandedGoals(prev => [...prev, String(goalId)])
      }
    }
    
    // 监听打开创建学习目标弹窗事件
    const handleOpenGoalForm = () => {
      setShowGoalForm(true)
    }
    
    window.addEventListener('goal-created', handleGoalCreated)
    window.addEventListener('open-goal-form', handleOpenGoalForm)
    return () => {
      window.removeEventListener('goal-created', handleGoalCreated)
      window.removeEventListener('open-goal-form', handleOpenGoalForm)
    }
  }, [fetchGoals, expandedGoals])

  useEffect(() => {
    if (goalId && !expandedGoals.includes(goalId)) {
      setExpandedGoals(prev => [...prev, goalId])
    }
  }, [goalId, expandedGoals])

  const toggleExpand = (id, e) => {
    e.stopPropagation()
    setExpandedGoals(prev =>
      prev.includes(id) ? prev.filter(g => g !== id) : [...prev, id]
    )
  }

  // 右键菜单处理 - 学习目标
  const handleGoalContextMenu = (e, goal) => {
    e.preventDefault()
    e.stopPropagation()
    setContextMenu({
      visible: true,
      x: e.clientX,
      y: e.clientY,
      goalId: goal.id,
      goalTitle: goal.title,
      type: 'goal'
    })
  }

  // 右键菜单处理 - AI Tutor
  const handleAiTutorContextMenu = (e) => {
    e.preventDefault()
    e.stopPropagation()
    setContextMenu({
      visible: true,
      x: e.clientX,
      y: e.clientY,
      goalId: null,
      goalTitle: '',
      type: 'aiTutor'
    })
  }

  // 清空聊天
  const handleClearChat = () => {
    window.dispatchEvent(new CustomEvent('clear-chat'))
    closeContextMenu()
    showSuccess('已清空聊天记录')
  }

  // 使用 App context 获取 message（如果可用）
  const { message: appMessage } = App.useApp()

  // 使用 appMessage（支持动态主题）
  const showSuccess = (content) => {
    appMessage.success(content)
  }
  const showError = (content) => {
    appMessage.error(content)
  }
  const showInfo = (content) => {
    appMessage.info(content)
  }

  // 关闭右键菜单
  const closeContextMenu = () => {
    setContextMenu({ visible: false, x: 0, y: 0, goalId: null, goalTitle: '', type: 'goal' })
  }

  // 重命名 AI Tutor
  const handleRenameAiTutor = () => {
    setRenameInput(aiTutorName)
    setAiTutorRenameVisible(true)
    closeContextMenu()
  }

  // 删除学习目标
  const handleDeleteGoal = async () => {
    if (!contextMenu.goalId) return
    
    Modal.confirm({
      title: '确认删除',
      content: `确定要删除学习目标「${contextMenu.goalTitle}」吗？此操作不可恢复。`,
      okText: '删除',
      okType: 'danger',
      cancelText: '取消',
      onOk: async () => {
        try {
          const currentStudentId = localStorage.getItem('student_id') || '1'
          await studyGoalAPI.delete(contextMenu.goalId, parseInt(currentStudentId))
          showSuccess('学习目标已删除')
          // 刷新列表
          fetchGoals()
          // 如果当前查看的是被删除的目标，跳转到 AI Tutor 页面
          if (goalId === String(contextMenu.goalId)) {
            navigate('/ai-tutor')
          }
        } catch (error) {
          console.error('删除失败:', error)
          showError('删除失败')
        }
        closeContextMenu()
      }
    })
  }

  // 点击其他地方关闭右键菜单
  useEffect(() => {
    const handleClick = () => closeContextMenu()
    document.addEventListener('click', handleClick)
    return () => document.removeEventListener('click', handleClick)
  }, [])

  const getActiveModule = () => {
    const p = location.pathname
    for (const m of MODULES) if (p.includes(`/${m.key}`)) return m.key
    return 'knowledge-graph'
  }

  const isAiTutor = location.pathname === '/ai-tutor'
  const activeModule = getActiveModule()

  if (loading) {
    return (
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: '100vh', background: '#f8faff' }}>
        <Spin size="large" />
      </div>
    )
  }

  return (
    <div style={{ display: 'flex', minHeight: '100vh', background: '#f8faff' }}>

      {/* ── Claude 风格侧边栏 ── */}
      <div style={{
        width: collapsed ? 64 : 288,
        transition: 'width 0.2s ease-out',
        flexShrink: 0,
        position: 'fixed',
        top: 0, left: 0, bottom: 0,
        zIndex: 100,
        background: '#ffffff',
        borderRight: '1px solid #e5e7eb',
        display: 'flex', flexDirection: 'column',
        overflow: 'hidden',
      }}>

        {/* Logo 区域 */}
        <div style={{ padding: collapsed ? '16px 0' : '16px 16px', display: 'flex', alignItems: 'center', gap: 12, borderBottom: '1px solid #f3f4f6', flexShrink: 0, justifyContent: collapsed ? 'center' : 'flex-start' }}>
          {collapsed ? (
            <button onClick={handleToggleCollapsed}
              style={{ width: 32, height: 32, borderRadius: 8, border: 'none', background: 'linear-gradient(145deg, #0ea5e9, #6366f1, #8b5cf6)', cursor: 'pointer', display: 'flex', alignItems: 'center', justifyContent: 'center', boxShadow: '0 4px 12px rgba(99,102,241,0.4)', transition: 'all 0.15s' }}
              onMouseEnter={e => { e.currentTarget.style.transform = 'scale(1.05)' }}
              onMouseLeave={e => { e.currentTarget.style.transform = 'scale(1)' }}
            >
              <MenuUnfoldOutlined style={{ fontSize: 14, color: '#fff' }} />
            </button>
          ) : (
            <>
              <div style={{
                width: 32, height: 32, borderRadius: 8,
                background: 'linear-gradient(145deg, #0ea5e9, #6366f1, #8b5cf6)',
                display: 'flex', alignItems: 'center', justifyContent: 'center',
                flexShrink: 0,
                boxShadow: '0 4px 12px rgba(99,102,241,0.4), inset 0 1px 0 rgba(255,255,255,0.2)',
                border: '1px solid rgba(255,255,255,0.15)',
                cursor: 'pointer',
              }}>
                <span style={{
                  fontSize: 18,
                  fontWeight: 800,
                  color: '#fff',
                  textShadow: '0 2px 4px rgba(0,0,0,0.15)',
                }}>T</span>
              </div>
              <span style={{ fontSize: 15, fontWeight: 600, color: '#111827', letterSpacing: '-0.3px', flex: 1 }}>
                AI Tutor
              </span>
              <button onClick={handleToggleCollapsed}
                style={{ width: 28, height: 28, borderRadius: 6, border: 'none', background: 'transparent', cursor: 'pointer', display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#9ca3af', transition: 'all 0.15s', flexShrink: 0 }}
                onMouseEnter={e => { e.currentTarget.style.background = 'rgba(99,102,241,0.08)'; e.currentTarget.style.color = '#6366f1' }}
                onMouseLeave={e => { e.currentTarget.style.background = 'transparent'; e.currentTarget.style.color = '#9ca3af' }}
              >
                <MenuFoldOutlined style={{ fontSize: 13 }} />
              </button>
            </>
          )}
        </div>

        {/* 导航内容 */}
        <div style={{ flex: 1, overflowY: 'auto', overflowX: 'hidden', padding: collapsed ? '12px 8px' : '12px 12px' }}>

          {/* New Chat 按钮 */}
          <motion.div
            onClick={() => navigate('/ai-tutor')}
            whileHover={{ backgroundColor: 'rgba(99,102,241,0.06)' }}
            whileTap={{ scale: 0.98 }}
            onContextMenu={handleAiTutorContextMenu}
            style={{
              display: 'flex', alignItems: 'center', gap: 12,
              padding: collapsed ? '10px 0' : '10px 12px',
              borderRadius: 8, marginBottom: 4, cursor: 'pointer',
              justifyContent: collapsed ? 'center' : 'flex-start',
              background: isAiTutor ? 'rgba(99,102,241,0.08)' : 'transparent',
              transition: 'background 0.15s ease',
            }}
          >
            <div style={{
              width: 28, height: 28, borderRadius: 6,
              background: isAiTutor ? 'linear-gradient(145deg, #0ea5e9, #6366f1, #8b5cf6)' : 'rgba(99,102,241,0.1)',
              display: 'flex', alignItems: 'center', justifyContent: 'center',
              flexShrink: 0,
              boxShadow: isAiTutor ? '0 3px 8px rgba(99,102,241,0.35), inset 0 1px 0 rgba(255,255,255,0.2)' : 'none',
              border: isAiTutor ? '1px solid rgba(255,255,255,0.15)' : 'none',
            }}>
              <span style={{
                fontSize: 14,
                fontWeight: 700,
                color: isAiTutor ? '#fff' : undefined,
                textShadow: isAiTutor ? '0 1px 2px rgba(0,0,0,0.15)' : undefined,
              }}>T</span>
            </div>
            {!collapsed && (
              <span style={{ fontSize: 14, fontWeight: 500, color: '#374151' }}>
                {aiTutorName}
              </span>
            )}
          </motion.div>

          {/* Divider */}
          {!collapsed && (
            <div style={{ padding: '8px 12px 4px', display: 'flex', alignItems: 'center', gap: 8 }}>
              <div style={{ height: 1, flex: 1, background: '#f3f4f6' }} />
              <span style={{ fontSize: 11, fontWeight: 600, color: '#9ca3af', letterSpacing: 0.5, textTransform: 'uppercase' }}>学习目标</span>
              <div style={{ height: 1, flex: 1, background: '#f3f4f6' }} />
            </div>
          )}

          {/* 新建学习目标按钮 */}
          <motion.div
            onClick={() => setShowGoalForm(true)}
            whileHover={{ backgroundColor: 'rgba(99,102,241,0.06)' }}
            whileTap={{ scale: 0.98 }}
            style={{
              display: 'flex', alignItems: 'center', gap: 12,
              padding: collapsed ? '10px 0' : '10px 12px',
              borderRadius: 8, marginBottom: 4, cursor: 'pointer',
              justifyContent: collapsed ? 'center' : 'flex-start',
              background: 'transparent',
              transition: 'background 0.15s ease',
            }}
          >
            <div style={{
              width: 28, height: 28, borderRadius: 6,
              background: 'rgba(99,102,241,0.1)',
              display: 'flex', alignItems: 'center', justifyContent: 'center',
              flexShrink: 0,
            }}>
              <PlusOutlined style={{ color: '#6366f1', fontSize: 14 }} />
            </div>
            {!collapsed && (
              <span style={{ fontSize: 14, fontWeight: 500, color: '#6366f1' }}>
                新建学习目标
              </span>
            )}
          </motion.div>

          {/* Goals list */}
          {goals.length === 0 && !collapsed ? (
            <motion.div
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              style={{
                padding: '16px 12px',
                textAlign: 'center',
                borderRadius: 8,
                margin: '8px 0',
              }}
            >
              <div style={{ fontSize: 13, color: '#9ca3af', lineHeight: 1.5 }}>
                暂无学习目标
              </div>
            </motion.div>
          ) : (
            goals.map((goal, idx) => {
              const isActive = String(goalId) === String(goal.id)
              const isExpanded = expandedGoals.includes(String(goal.id))
              const grad = GOAL_GRADIENTS[idx % GOAL_GRADIENTS.length]

              return (
                <div key={goal.id} style={{ marginBottom: 2 }}>
                  {/* Goal header */}
                  <motion.div
                    whileHover={{ backgroundColor: isActive ? 'rgba(99,102,241,0.08)' : 'rgba(0,0,0,0.03)' }}
                    whileTap={{ scale: 0.99 }}
                    onContextMenu={(e) => handleGoalContextMenu(e, goal)}
                    style={{
                      display: 'flex', alignItems: 'center', gap: 12,
                      padding: collapsed ? '8px 0' : '8px 12px',
                      borderRadius: 8, cursor: 'pointer',
                      justifyContent: collapsed ? 'center' : 'flex-start',
                      background: isActive ? 'rgba(99,102,241,0.08)' : 'transparent',
                      transition: 'background 0.15s ease',
                    }}>
                    <div style={{
                      width: 28, height: 28, borderRadius: 6,
                      background: grad,
                      display: 'flex', alignItems: 'center', justifyContent: 'center',
                      flexShrink: 0,
                    }}
                      onClick={() => navigate(`/goals/${goal.id}/knowledge-graph`)}>
                      <BookOutlined style={{ color: '#fff', fontSize: 13 }} />
                    </div>
                    {!collapsed && (
                      <>
                        <span onClick={() => navigate(`/goals/${goal.id}/knowledge-graph`)}
                          style={{ flex: 1, fontSize: 13, fontWeight: isActive ? 600 : 500, color: isActive ? '#6366f1' : '#374151', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                          {goal.title}
                        </span>
                        <span onClick={(e) => toggleExpand(String(goal.id), e)}
                          style={{ flexShrink: 0, color: '#9ca3af', fontSize: 10, transition: 'transform 0.2s', transform: isExpanded ? 'rotate(90deg)' : 'rotate(0deg)', display: 'flex', cursor: 'pointer' }}>
                          <RightOutlined style={{ fontSize: 10 }} />
                        </span>
                      </>
                    )}
                  </motion.div>

                  {/* Sub-modules */}
                  <AnimatePresence>
                    {isExpanded && !collapsed && (
                      <motion.div initial={{ height: 0, opacity: 0 }} animate={{ height: 'auto', opacity: 1 }} exit={{ height: 0, opacity: 0 }} transition={{ duration: 0.2 }}
                        style={{ overflow: 'hidden', paddingLeft: 8 }}>
                        {MODULES.map(mod => {
                          const isModActive = isActive && activeModule === mod.key
                          return (
                            <div key={mod.key}
                              onClick={() => navigate(`/goals/${goal.id}/${mod.key}`)}
                              style={{
                                display: 'flex', alignItems: 'center', gap: 10,
                                padding: '6px 12px', borderRadius: 6, cursor: 'pointer',
                                margin: '1px 0',
                                background: isModActive ? `rgba(99,102,241,0.08)` : 'transparent',
                                transition: 'background 0.15s ease',
                              }}
                              onMouseEnter={e => { if (!isModActive) e.currentTarget.style.background = 'rgba(0,0,0,0.03)' }}
                              onMouseLeave={e => { if (!isModActive) e.currentTarget.style.background = 'transparent' }}
                            >
                              <span style={{ color: isModActive ? mod.color : '#9ca3af', fontSize: 13 }}>{mod.icon}</span>
                              <span style={{ fontSize: 13, fontWeight: isModActive ? 600 : 400, color: isModActive ? mod.color : '#6b7280' }}>
                                {mod.label}
                              </span>
                            </div>
                          )
                        })}
                      </motion.div>
                    )}
                  </AnimatePresence>
                </div>
              )
            })
          )}
        </div>

        {/* User Profile */}
        <div
          style={{
            padding: collapsed ? '12px 8px' : '12px 12px',
            borderTop: '1px solid #f3f4f6',
            flexShrink: 0,
            position: 'relative',
          }}
          onMouseEnter={() => setProfileMenuVisible(true)}
          onMouseLeave={() => setProfileMenuVisible(false)}
        >
          <motion.div
            whileHover={{ backgroundColor: 'rgba(99,102,241,0.06)' }}
            whileTap={{ scale: 0.98 }}
            style={{
              display: 'flex', alignItems: 'center', gap: 12,
              padding: collapsed ? '8px 0' : '8px 12px',
              borderRadius: 8, cursor: 'pointer',
              justifyContent: collapsed ? 'center' : 'flex-start',
              transition: 'background 0.15s ease',
            }}
          >
            <div style={{
              width: 32, height: 32, borderRadius: 8,
              background: 'linear-gradient(135deg, #1a1a2e 0%, #16213e 100%)',
              display: 'flex', alignItems: 'center', justifyContent: 'center',
              flexShrink: 0,
            }}>
              <span style={{
                fontSize: 14,
                fontWeight: 700,
                background: 'linear-gradient(135deg, #fff 0%, #a5b4fc 100%)',
                backgroundClip: 'text',
                WebkitBackgroundClip: 'text',
                WebkitTextFillColor: 'transparent',
              }}>{getUserInfo().username.charAt(0).toUpperCase()}</span>
            </div>
            {!collapsed && (
              <div style={{ flex: 1, overflow: 'hidden' }}>
                <div style={{ fontSize: 13, fontWeight: 600, color: '#111827', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                  {getUserInfo().username}
                </div>
                <div style={{ fontSize: 11, color: '#9ca3af', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                  点击管理账号
                </div>
              </div>
            )}
          </motion.div>

          {/* Profile Menu */}
          <AnimatePresence>
            {profileMenuVisible && !collapsed && (
              <motion.div
                initial={{ opacity: 0, y: 8, scale: 0.95 }}
                animate={{ opacity: 1, y: 0, scale: 1 }}
                exit={{ opacity: 0, y: 8, scale: 0.95 }}
                transition={{ duration: 0.15 }}
                style={{
                  position: 'absolute',
                  bottom: 'calc(100% + 8px)',
                  left: 12,
                  right: 12,
                  background: '#fff',
                  borderRadius: 8,
                  boxShadow: '0 4px 20px rgba(0,0,0,0.1)',
                  border: '1px solid #e5e7eb',
                  padding: 4,
                  zIndex: 1000,
                }}
              >
                <motion.button
                  whileHover={{ backgroundColor: 'rgba(99,102,241,0.06)' }}
                  style={{
                    width: '100%',
                    display: 'flex',
                    alignItems: 'center',
                    gap: 10,
                    padding: '8px 12px',
                    border: 'none',
                    background: 'transparent',
                    borderRadius: 6,
                    cursor: 'pointer',
                    textAlign: 'left',
                  }}
                  onClick={() => {
                    navigate('/settings')
                    setProfileMenuVisible(false)
                  }}
                >
                  <SettingOutlined style={{ color: '#6366f1', fontSize: 14 }} />
                  <span style={{ fontSize: 13, color: '#111827', fontWeight: 500 }}>设置</span>
                </motion.button>

                <motion.button
                  whileHover={{ backgroundColor: 'rgba(245,158,11,0.08)' }}
                  style={{
                    width: '100%',
                    display: 'flex',
                    alignItems: 'center',
                    gap: 10,
                    padding: '8px 12px',
                    border: 'none',
                    background: 'transparent',
                    borderRadius: 6,
                    cursor: 'pointer',
                    textAlign: 'left',
                  }}
                  onClick={() => {
                    navigate('/skills')
                    setProfileMenuVisible(false)
                  }}
                >
                  <AppstoreOutlined style={{ color: '#f59e0b', fontSize: 14 }} />
                  <span style={{ fontSize: 13, color: '#111827', fontWeight: 500 }}>Skill 管理</span>
                </motion.button>

                <motion.button
                  whileHover={{ backgroundColor: 'rgba(244,114,182,0.08)' }}
                  style={{
                    width: '100%',
                    display: 'flex',
                    alignItems: 'center',
                    gap: 10,
                    padding: '8px 12px',
                    border: 'none',
                    background: 'transparent',
                    borderRadius: 6,
                    cursor: 'pointer',
                    textAlign: 'left',
                  }}
                  onClick={() => {
                    setLearningStyleVisible(true)
                    setProfileMenuVisible(false)
                  }}
                >
                  <HeartOutlined style={{ color: '#f472b6', fontSize: 14 }} />
                  <span style={{ fontSize: 13, color: '#111827', fontWeight: 500 }}>学习风格</span>
                </motion.button>

                <motion.button
                  whileHover={{ backgroundColor: 'rgba(244,63,94,0.06)' }}
                  style={{
                    width: '100%',
                    display: 'flex',
                    alignItems: 'center',
                    gap: 10,
                    padding: '8px 12px',
                    border: 'none',
                    background: 'transparent',
                    borderRadius: 6,
                    cursor: 'pointer',
                    textAlign: 'left',
                  }}
                  onClick={handleLogout}
                >
                  <LogoutOutlined style={{ color: '#f43f5e', fontSize: 14 }} />
                  <span style={{ fontSize: 13, color: '#f43f5e', fontWeight: 500 }}>退出登录</span>
                </motion.button>
              </motion.div>
            )}
          </AnimatePresence>
        </div>
      </div>

      {/* 右键菜单 */}
      <AnimatePresence>
        {contextMenu.visible && (
          <motion.div
            initial={{ opacity: 0, scale: 0.95 }}
            animate={{ opacity: 1, scale: 1 }}
            exit={{ opacity: 0, scale: 0.95 }}
            transition={{ duration: 0.1 }}
            style={{
              position: 'fixed',
              left: contextMenu.x,
              top: contextMenu.y,
              zIndex: 9999,
              background: '#fff',
              borderRadius: 8,
              boxShadow: '0 4px 20px rgba(0,0,0,0.15)',
              border: '1px solid rgba(0,0,0,0.08)',
              padding: 4,
              minWidth: 140,
            }}
            onClick={(e) => e.stopPropagation()}
          >
            {contextMenu.type === 'aiTutor' && (
              <div
                onClick={handleRenameAiTutor}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: 8,
                  padding: '8px 12px',
                  borderRadius: 6,
                  cursor: 'pointer',
                  transition: 'background 0.15s',
                }}
                onMouseEnter={(e) => e.currentTarget.style.background = 'rgba(99,102,241,0.06)'}
                onMouseLeave={(e) => e.currentTarget.style.background = 'transparent'}
              >
                <EditOutlined style={{ color: '#6366f1', fontSize: 14 }} />
                <span style={{ fontSize: 13, color: '#111827', fontWeight: 500 }}>重命名</span>
              </div>
            )}
            {contextMenu.type === 'aiTutor' && (
              <div
                onClick={handleClearChat}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: 8,
                  padding: '8px 12px',
                  borderRadius: 6,
                  cursor: 'pointer',
                  transition: 'background 0.15s',
                }}
                onMouseEnter={(e) => e.currentTarget.style.background = 'rgba(239,68,68,0.08)'}
                onMouseLeave={(e) => e.currentTarget.style.background = 'transparent'}
              >
                <DeleteOutlined style={{ color: '#ef4444', fontSize: 14 }} />
                <span style={{ fontSize: 13, color: '#ef4444', fontWeight: 500 }}>清空聊天</span>
              </div>
            )}
            {contextMenu.type === 'goal' && (
              <div
                onClick={handleDeleteGoal}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: 8,
                  padding: '8px 12px',
                  borderRadius: 6,
                  cursor: 'pointer',
                  transition: 'background 0.15s',
                }}
                onMouseEnter={(e) => e.currentTarget.style.background = '#fee2e2'}
                onMouseLeave={(e) => e.currentTarget.style.background = 'transparent'}
              >
                <DeleteOutlined style={{ color: '#ef4444', fontSize: 14 }} />
                <span style={{ fontSize: 13, color: '#ef4444', fontWeight: 500 }}>删除目标</span>
              </div>
            )}
          </motion.div>
        )}
      </AnimatePresence>

      {/* AI Tutor 重命名弹窗 */}
      <Modal
        title="重命名"
        open={aiTutorRenameVisible}
        onOk={handleSaveAiTutorName}
        onCancel={() => setAiTutorRenameVisible(false)}
        okText="保存"
        cancelText="取消"
        width={360}
        centered
      >
        <Input
          value={renameInput}
          onChange={(e) => setRenameInput(e.target.value)}
          onPressEnter={handleSaveAiTutorName}
          placeholder="输入名称"
          autoFocus
          style={{ borderRadius: 6 }}
        />
      </Modal>

      {/* ── Main Content ── */}
      <div style={{ marginLeft: collapsed ? 64 : 288, transition: 'margin-left 0.2s ease-out', flex: 1, minHeight: '100vh', background: '#ffffff' }}>
        <div style={{ padding: 24, minHeight: '100vh' }}>
          <Outlet />
        </div>
      </div>

      {/* 学习风格抽屉 */}
      <Drawer
        title={
          <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            <HeartOutlined style={{ color: '#f472b6' }} />
            <span>学习风格与综合分析</span>
          </div>
        }
        placement="right"
        onClose={() => setLearningStyleVisible(false)}
        open={learningStyleVisible}
        width={580}
        styles={{ 
          body: { padding: 0, background: '#fafbfc' },
          header: { borderBottom: '1px solid #f0f0f0' }
        }}
      >
        <LearningStyle />
      </Drawer>

      {/* 学习目标创建表单弹窗 */}
      <Modal
        title={
          <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
            <div style={{
              width: 32,
              height: 32,
              borderRadius: 8,
              background: 'linear-gradient(135deg, #6366f1, #8b5cf6)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
            }}>
              <AimOutlined style={{ color: '#fff', fontSize: 16 }} />
            </div>
            <span style={{ fontWeight: 600, fontSize: 16 }}>创建学习目标</span>
          </div>
        }
        open={showGoalForm}
        onCancel={handleGoalFormClose}
        footer={null}
        width={560}
        centered
      >
        <div style={{ marginTop: 16 }}>
          <div style={{
            background: 'linear-gradient(135deg, rgba(99,102,241,0.06) 0%, rgba(139,92,246,0.03) 100%)',
            borderRadius: 10,
            padding: '12px 16px',
            marginBottom: 20,
            border: '1px solid rgba(99,102,241,0.1)',
          }}>
            <div style={{ fontSize: 13, color: '#475569', lineHeight: 1.6 }}>
              请填写学习目标的基本信息。创建完成后，你可以在目标详情页上传学习资料、生成知识图谱和学习计划。
            </div>
          </div>
          
          <Form
            form={form}
            name="studyGoalForm"
            layout="vertical"
            onFinish={handleGoalFormSubmit}
            initialValues={{
              targetHoursPerWeek: 5,
              studyDepth: 'intermediate',
            }}
          >
            <Form.Item
              name="title"
              label={<span style={{ fontWeight: 500, color: '#374151' }}>学习目标</span>}
              rules={[{ required: true, message: '请输入学习目标' }]}
            >
              <Input 
                placeholder="例如：掌握 Python 编程基础" 
                size="large"
                style={{ borderRadius: 8 }}
              />
            </Form.Item>
            
            <Form.Item
              name="subject"
              label={<span style={{ fontWeight: 500, color: '#374151' }}>学科领域</span>}
            >
              <Select 
                placeholder="请选择学科领域" 
                allowClear
                size="large"
                style={{ borderRadius: 8 }}
              >
                <Option value="计算机">计算机 / 编程</Option>
                <Option value="数学">数学</Option>
                <Option value="物理">物理</Option>
                <Option value="化学">化学</Option>
                <Option value="生物">生物</Option>
                <Option value="英语">英语 / 语言</Option>
                <Option value="经济学">经济学 / 商科</Option>
                <Option value="心理学">心理学</Option>
                <Option value="历史">历史 / 人文</Option>
                <Option value="其他">其他</Option>
              </Select>
            </Form.Item>
            
            <Form.Item
              name="description"
              label={<span style={{ fontWeight: 500, color: '#374151' }}>详细描述</span>}
            >
              <Input.TextArea 
                placeholder="描述一下你的学习目标，例如：希望能够使用 Python 进行数据分析，掌握基本语法和常用库" 
                rows={3}
                style={{ borderRadius: 8 }}
              />
            </Form.Item>
            
            <Form.Item
              name="targetHoursPerWeek"
              label={<span style={{ fontWeight: 500, color: '#374151' }}>每周学习时长</span>}
            >
              <div style={{ padding: '0 8px' }}>
                <Slider
                  min={1}
                  max={20}
                  marks={{
                    2: '2h',
                    5: '5h',
                    10: '10h',
                    15: '15h',
                    20: '20h'
                  }}
                  tooltip={{ formatter: (value) => `${value} 小时/周` }}
                />
              </div>
            </Form.Item>
            
            <Form.Item
              name="studyDepth"
              label={<span style={{ fontWeight: 500, color: '#374151' }}>学习深度</span>}
            >
              <Radio.Group buttonStyle="solid" style={{ width: '100%' }}>
                <Radio.Button value="basic" style={{ width: '33.33%', textAlign: 'center' }}>
                  <div>
                    <div style={{ fontWeight: 500 }}>了解</div>
                    <div style={{ fontSize: 11, color: '#999', marginTop: 2 }}>每类约5个知识点</div>
                  </div>
                </Radio.Button>
                <Radio.Button value="intermediate" style={{ width: '33.33%', textAlign: 'center' }}>
                  <div>
                    <div style={{ fontWeight: 500 }}>熟悉</div>
                    <div style={{ fontSize: 11, color: '#999', marginTop: 2 }}>每类约10个知识点</div>
                  </div>
                </Radio.Button>
                <Radio.Button value="advanced" style={{ width: '33.33%', textAlign: 'center' }}>
                  <div>
                    <div style={{ fontWeight: 500 }}>深入</div>
                    <div style={{ fontSize: 11, color: '#999', marginTop: 2 }}>每类15个以上</div>
                  </div>
                </Radio.Button>
              </Radio.Group>
            </Form.Item>
            
            <Form.Item
              name="targetCompletionDate"
              label={<span style={{ fontWeight: 500, color: '#374151' }}>目标完成日期</span>}
            >
              <DatePicker 
                style={{ width: '100%', borderRadius: 8 }} 
                placeholder="选择预计完成日期"
                format="YYYY-MM-DD"
                disabledDate={(current) => current && current < dayjs().endOf('day')}
              />
            </Form.Item>

            <div style={{ display: 'flex', gap: 12, marginTop: 24 }}>
              <Button 
                size="large"
                onClick={handleGoalFormClose}
                style={{ flex: 1, borderRadius: 8 }}
              >
                取消
              </Button>
              <Button 
                type="primary"
                size="large"
                htmlType="submit"
                loading={goalFormLoading}
                style={{ 
                  flex: 2, 
                  borderRadius: 8,
                  background: 'linear-gradient(135deg, #6366f1, #8b5cf6)',
                  border: 'none',
                  fontWeight: 600,
                }}
              >
                创建学习目标
              </Button>
            </div>
          </Form>
        </div>
      </Modal>
    </div>
  )
}

export default MainLayout
