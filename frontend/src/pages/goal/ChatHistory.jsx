import { useState, useEffect } from 'react'
import { message, Empty, Spin, Modal } from 'antd'
import {
  MessageOutlined,
  UserOutlined,
  RobotOutlined,
  RightOutlined,
  ClockCircleOutlined,
  CommentOutlined,
  PlusOutlined,
  BookOutlined,
  ScheduleOutlined,
  DeleteOutlined,
} from '@ant-design/icons'
import { useParams, useNavigate } from 'react-router-dom'
import { motion } from 'framer-motion'
import { studyGoalAPI } from '../../utils/api'

function ChatHistory() {
  const { goalId } = useParams()
  const navigate   = useNavigate()
  const [records, setRecords]   = useState([])  // 学习记录列表
  const [loading, setLoading] = useState(true)

  useEffect(() => { fetchChatHistory() }, [goalId])

  const fetchChatHistory = async () => {
    if (!goalId) {
      setLoading(false)
      return
    }
    
    setLoading(true)
    try {
      const res = await studyGoalAPI.getRecords(goalId)
      if (res.data?.success && res.data.data?.records) {
        setRecords(res.data.data.records)
      } else {
        setRecords([])
      }
    } catch (err) {
      console.error('获取学习记录失败:', err)
      message.error('获取学习记录失败')
      setRecords([])
    } finally {
      setLoading(false)
    }
  }

  const handleContinueChat = (sessionId) => navigate(`/ai-tutor?goalId=${goalId}&sessionId=${sessionId}`)
  const handleNewChat = () => navigate(`/ai-tutor?goalId=${goalId}`)

  const formatTime = (timeStr) => {
    if (!timeStr) return '未知时间'
    const date = new Date(timeStr)
    const diff = Date.now() - date.getTime()
    if (diff < 24 * 3600 * 1000) {
      const h = Math.floor(diff / 3600000)
      if (h < 1) { const m = Math.floor(diff / 60000); return m < 1 ? '刚刚' : `${m}分钟前` }
      return `${h}小时前`
    }
    return date.toLocaleDateString('zh-CN', { month: 'short', day: 'numeric' })
  }

  const formatDate = (dateStr) => {
    if (!dateStr) return ''
    const date = new Date(dateStr)
    return date.toLocaleDateString('zh-CN', { month: 'long', day: 'numeric', weekday: 'long' })
  }

  // 将所有会话扁平化为列表
  const allSessions = []
  records.forEach(record => {
    if (record.sessions && record.sessions.length > 0) {
      record.sessions.forEach(session => {
        allSessions.push({
          ...session,
          recordId: record.id,  // 添加 record_id 用于删除
          recordDate: record.record_date,
          studyDuration: record.study_duration_minutes,
          lessonsCompleted: record.lessons_completed,
        })
      })
    }
  })

  // 删除学习记录
  const handleDeleteRecord = (recordId, sessionId, e) => {
    e?.stopPropagation()  // 阻止冒泡到继续学习
    
    Modal.confirm({
      title: '确认删除',
      content: '确定要删除这条学习记录吗？删除后将无法恢复。',
      okText: '删除',
      okType: 'danger',
      cancelText: '取消',
      onOk: async () => {
        try {
          await studyGoalAPI.deleteRecord(goalId, recordId)
          message.success('删除成功')
          // 重新加载记录列表
          fetchChatHistory()
        } catch (err) {
          console.error('删除学习记录失败:', err)
          message.error('删除失败')
        }
      }
    })
  }

  // 按时间降序排序
  allSessions.sort((a, b) => new Date(b.created_at) - new Date(a.created_at))

  if (loading) {
    return (
      <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', minHeight: 300 }}>
        <Spin tip="加载学习记录..." />
      </div>
    )
  }

  return (
    <motion.div initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.4 }}>
      {/* Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 20 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
          <div style={{ width: 40, height: 40, borderRadius: 10, background: 'linear-gradient(135deg,#8b5cf6,#6366f1)', display: 'flex', alignItems: 'center', justifyContent: 'center', boxShadow: '0 4px 12px rgba(139,92,246,0.35)' }}>
            <MessageOutlined style={{ color: '#fff', fontSize: 18 }} />
          </div>
          <div>
            <h2 style={{ margin: 0, fontSize: 20, fontWeight: 800, color: '#0f172a' }}>学习记录</h2>
            {records.length > 0 && (
              <div style={{ fontSize: 12, color: '#94a3b8', marginTop: 2 }}>
                共 {records.length} 天学习，{allSessions.length} 次会话
              </div>
            )}
          </div>
        </div>
        <button onClick={handleNewChat}
          style={{ display: 'flex', alignItems: 'center', gap: 7, padding: '10px 20px', borderRadius: 10, border: 'none', background: 'linear-gradient(135deg,#6366f1,#8b5cf6)', color: '#fff', fontSize: 13.5, fontWeight: 700, cursor: 'pointer', boxShadow: '0 4px 14px rgba(99,102,241,0.38)' }}>
          <PlusOutlined /> 新对话
        </button>
      </div>

      {/* Session list */}
      {allSessions.length === 0 ? (
        <div style={{ borderRadius: 20, padding: 48, background: '#fff', border: '1px solid rgba(226,232,240,0.8)', textAlign: 'center' }}>
          <Empty description="暂无学习记录">
            <button onClick={handleNewChat} style={{ padding: '10px 24px', borderRadius: 10, border: 'none', background: 'linear-gradient(135deg,#6366f1,#8b5cf6)', color: '#fff', fontSize: 14, fontWeight: 700, cursor: 'pointer' }}>
              开始新对话
            </button>
          </Empty>
        </div>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
          {allSessions.map((session, idx) => (
            <motion.div key={session.session_id} initial={{ opacity: 0, y: 14 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.4, delay: idx * 0.08 }}
              onClick={() => handleContinueChat(session.session_id)}
              whileHover={{ y: -3, boxShadow: '0 12px 40px rgba(99,102,241,0.12)' }}
              style={{ borderRadius: 18, padding: '22px 24px', background: '#fff', border: '1px solid rgba(226,232,240,0.8)', boxShadow: '0 4px 20px rgba(99,102,241,0.06)', cursor: 'pointer', transition: 'all 0.25s', position: 'relative', overflow: 'hidden' }}>
              {/* Left accent */}
              <div style={{ position: 'absolute', left: 0, top: 0, bottom: 0, width: 4, background: 'linear-gradient(180deg,#6366f1,#8b5cf6)', borderRadius: '18px 0 0 18px' }} />

              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', paddingLeft: 8 }}>
                <div style={{ flex: 1, minWidth: 0 }}>
                  {/* Title row */}
                  <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 14 }}>
                    <div style={{ width: 38, height: 38, borderRadius: 10, background: 'linear-gradient(135deg,#6366f1,#8b5cf6)', display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0 }}>
                      <RobotOutlined style={{ color: '#fff', fontSize: 16 }} />
                    </div>
                    <div style={{ flex: 1, minWidth: 0 }}>
                      <div style={{ fontWeight: 700, fontSize: 15, color: '#0f172a', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                        {session.recordDate ? formatDate(session.recordDate) : '学习会话'}
                      </div>
                      <div style={{ display: 'flex', gap: 12, marginTop: 3, flexWrap: 'wrap' }}>
                        <span style={{ fontSize: 12, color: '#94a3b8', display: 'flex', alignItems: 'center', gap: 4 }}>
                          <ClockCircleOutlined style={{ fontSize: 10 }} /> {formatTime(session.created_at)}
                        </span>
                        {session.message_count && (
                          <span style={{ fontSize: 12, color: '#94a3b8', display: 'flex', alignItems: 'center', gap: 4 }}>
                            <CommentOutlined style={{ fontSize: 10 }} /> {session.message_count} 条消息
                          </span>
                        )}
                        {session.studyDuration > 0 && (
                          <span style={{ fontSize: 12, color: '#94a3b8', display: 'flex', alignItems: 'center', gap: 4 }}>
                            <ScheduleOutlined style={{ fontSize: 10 }} /> {session.studyDuration} 分钟
                          </span>
                        )}
                      </div>
                    </div>
                  </div>

                  {/* Summary preview */}
                  {session.summary && (
                    <div style={{ background: 'rgba(99,102,241,0.04)', borderRadius: 12, padding: '12px 14px', border: '1px solid rgba(99,102,241,0.1)', marginBottom: 10 }}>
                      <div style={{ fontSize: 13, color: '#374151', lineHeight: 1.6, whiteSpace: 'pre-wrap' }}>
                        {session.summary.length > 200 ? session.summary.slice(0, 200) + '...' : session.summary}
                      </div>
                    </div>
                  )}

                  <div style={{ fontSize: 12, color: '#94a3b8', paddingLeft: 2 }}>
                    点击继续本次学习对话
                  </div>
                </div>

                {/* Arrow and delete button */}
                <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginLeft: 16, flexShrink: 0 }}>
                  {/* Delete button */}
                  <div
                    onClick={(e) => handleDeleteRecord(session.recordId, session.session_id, e)}
                    style={{ width: 32, height: 32, borderRadius: 9, background: 'rgba(239,68,68,0.08)', display: 'flex', alignItems: 'center', justifyContent: 'center', cursor: 'pointer', transition: 'all 0.2s' }}
                    onMouseEnter={(e) => {
                      e.currentTarget.style.background = 'rgba(239,68,68,0.15)'
                      e.currentTarget.style.transform = 'scale(1.05)'
                    }}
                    onMouseLeave={(e) => {
                      e.currentTarget.style.background = 'rgba(239,68,68,0.08)'
                      e.currentTarget.style.transform = 'scale(1)'
                    }}
                  >
                    <DeleteOutlined style={{ color: '#ef4444', fontSize: 14 }} />
                  </div>
                  {/* Arrow */}
                  <div style={{ width: 32, height: 32, borderRadius: 9, background: 'rgba(99,102,241,0.08)', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                    <RightOutlined style={{ color: '#6366f1', fontSize: 12 }} />
                  </div>
                </div>
              </div>
            </motion.div>
          ))}
        </div>
      )}

      {/* Tips card */}
      <div style={{ marginTop: 20, borderRadius: 16, padding: '20px 24px', background: 'linear-gradient(135deg,rgba(99,102,241,0.06),rgba(139,92,246,0.04))', border: '1px solid rgba(99,102,241,0.15)' }}>
        <div style={{ display: 'flex', gap: 16, alignItems: 'flex-start' }}>
          <div style={{ width: 44, height: 44, borderRadius: 12, background: 'linear-gradient(135deg,#6366f1,#8b5cf6)', display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0 }}>
            <RobotOutlined style={{ color: '#fff', fontSize: 20 }} />
          </div>
          <div>
            <div style={{ fontWeight: 700, fontSize: 15, color: '#0f172a', marginBottom: 6 }}>AI 家教随时为你解答</div>
            <div style={{ fontSize: 13.5, color: '#64748b', lineHeight: 1.6, marginBottom: 12 }}>
              在学习过程中遇到任何问题，都可以随时向 AI 家教提问。所有学习记录都会保存，方便随时回顾。
            </div>
            <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
              {['知识点答疑', '题目讲解', '学习计划', '方法建议'].map(tag => (
                <span key={tag} style={{ padding: '3px 12px', borderRadius: 99, background: 'rgba(99,102,241,0.1)', color: '#6366f1', fontSize: 12, fontWeight: 600 }}>{tag}</span>
              ))}
            </div>
          </div>
        </div>
      </div>
    </motion.div>
  )
}

export default ChatHistory
