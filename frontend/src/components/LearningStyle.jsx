import { useState, useEffect } from 'react'
import { Card, Progress, Tag, Button, Slider, Select, message, Spin, Row, Col, Divider, List, Badge } from 'antd'
import { 
  EyeOutlined, 
  SoundOutlined, 
  ReadOutlined, 
  FieldBinaryOutlined,
  ClockCircleOutlined,
  FireOutlined,
  TrophyOutlined,
  BookOutlined,
  EditOutlined,
  CheckCircleOutlined,
  StarOutlined,
  CalendarOutlined,
  ThunderboltOutlined,
  AimOutlined,
  ExperimentOutlined,
  BulbOutlined,
  AlertOutlined,
  LineChartOutlined,
  RobotOutlined,
  FundProjectionScreenOutlined,
  DashboardOutlined,
  SolutionOutlined,
  RiseOutlined,
  CustomerServiceOutlined
} from '@ant-design/icons'
import { memoryAPI, studyGoalAPI } from '../utils/api'

// 学习风格类型配置
const STYLE_CONFIG = {
  visual: {
    label: '视觉型',
    icon: <EyeOutlined />,
    color: '#6B5CE7',
    description: '偏好图表、颜色、空间信息',
    tip: '适合使用思维导图、流程图等可视化工具'
  },
  auditory: {
    label: '听觉型',
    icon: <SoundOutlined />,
    color: '#00BCD4',
    description: '偏好听讲、讨论、音频',
    tip: '适合听课、讨论和录音学习'
  },
  reading: {
    label: '阅读型',
    icon: <ReadOutlined />,
    color: '#FF9800',
    description: '偏好文字材料、笔记',
    tip: '适合阅读教材、做笔记和书面练习'
  },
  kinesthetic: {
    label: '动觉型',
    icon: <FieldBinaryOutlined />,
    color: '#4CAF50',
    description: '偏好动手实践、案例演练',
    tip: '适合做实验、案例分析和动手练习'
  }
}

const TIME_OPTIONS = [
  { value: 'morning', label: '上午', icon: '🌅' },
  { value: 'afternoon', label: '下午', icon: '☀️' },
  { value: 'evening', label: '晚上', icon: '🌙' }
]

const LEARNING_PATTERNS = {
  '学霸模式': { color: '#f73f01', icon: '🏆', desc: '高效且持续学习' },
  '高效学习者': { color: '#52c41a', icon: '⚡', desc: '学习效率出众' },
  '稳步提升': { color: '#1890ff', icon: '📈', desc: '稳扎稳打进步中' },
  '入门新手': { color: '#faad14', icon: '🌱', desc: '刚刚开始学习之旅' },
  '均衡发展': { color: '#722ed1', icon: '⚖️', desc: '各维度平衡发展' }
}

function LearningStyle() {
  const [loading, setLoading] = useState(true)
  const [editing, setEditing] = useState(false)
  const [learningStyle, setLearningStyle] = useState(null)
  const [summary, setSummary] = useState(null)
  const [goals, setGoals] = useState([])
  
  const [editData, setEditData] = useState({
    primary_style: 'visual',
    style_scores: { visual: 60, auditory: 60, reading: 60, kinesthetic: 60 },
    preferred_time: 'morning',
    study_duration: 45
  })

  const fetchData = async () => {
    setLoading(true)
    try {
      const [styleRes, summaryRes, goalsRes] = await Promise.all([
        memoryAPI.getLearningStyle(),
        memoryAPI.getLearningSummary(),
        studyGoalAPI.list().catch(() => ({ data: { success: true, data: [] } }))
      ])
      
      if (styleRes.data?.success) {
        setLearningStyle(styleRes.data.data)
        setEditData({
          primary_style: styleRes.data.data.primary_style || 'visual',
          style_scores: styleRes.data.data.style_scores || { visual: 60, auditory: 60, reading: 60, kinesthetic: 60 },
          preferred_time: styleRes.data.data.preferred_time || 'morning',
          study_duration: styleRes.data.data.study_duration || 45
        })
      }
      
      if (summaryRes.data?.success) {
        setSummary(summaryRes.data.data)
      }
      
      if (goalsRes.data?.success) {
        setGoals(goalsRes.data.data || [])
      }
    } catch (error) {
      console.error('获取学习风格失败:', error)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchData()
  }, [])

  const handleUpdate = async () => {
    try {
      const result = await memoryAPI.updateLearningStyle(editData)
      if (result.data?.success) {
        message.success('学习风格已更新')
        setLearningStyle(result.data.data)
        setEditing(false)
      }
    } catch (error) {
      message.error('更新失败')
    }
  }

  const handleCancel = () => {
    if (learningStyle) {
      setEditData({
        primary_style: learningStyle.primary_style,
        style_scores: learningStyle.style_scores,
        preferred_time: learningStyle.preferred_time,
        study_duration: learningStyle.study_duration
      })
    }
    setEditing(false)
  }

  if (loading) {
    return (
      <div style={{ padding: 24 }}>
        <Spin tip="加载学习分析数据..." />
      </div>
    )
  }

  const primaryStyleConfig = STYLE_CONFIG[learningStyle?.primary_style] || STYLE_CONFIG.reading
  const primaryTime = TIME_OPTIONS.find(t => t.value === learningStyle?.preferred_time)
  const patternInfo = LEARNING_PATTERNS[summary?.learning_pattern] || LEARNING_PATTERNS['均衡发展']

  return (
    <div style={{ padding: 20, background: '#f8fafc', minHeight: '100%' }}>
      {/* 学习风格分析卡片 */}
      <Card 
        size="small"
        title={
          <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            <SolutionOutlined style={{ color: primaryStyleConfig.color }} />
            <span>学习风格分析</span>
            <Tag color={primaryStyleConfig.color}>{primaryStyleConfig.label}</Tag>
          </div>
        }
        extra={
          !editing && (
            <Button type="text" icon={<EditOutlined />} onClick={() => setEditing(true)} size="small">
              调整偏好
            </Button>
          )
        }
        style={{ marginBottom: 16, borderRadius: 12 }}
      >
        <Row gutter={[12, 12]} style={{ marginBottom: 16 }}>
          {Object.entries(STYLE_CONFIG).map(([key, config]) => {
            const score = editing ? editData.style_scores[key] : learningStyle?.style_scores?.[key] || 0
            const isPrimary = learningStyle?.primary_style === key
            
            return (
              <Col span={12} key={key}>
                <div 
                  style={{
                    padding: 14,
                    borderRadius: 10,
                    background: isPrimary ? `${config.color}10` : '#f5f5f5',
                    border: isPrimary ? `2px solid ${config.color}` : '1px solid #e8e8e8',
                    transition: 'all 0.2s'
                  }}
                >
                  <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 10 }}>
                    <span style={{ fontSize: 20, color: config.color }}>{config.icon}</span>
                    <span style={{ fontWeight: 600, fontSize: 14 }}>{config.label}</span>
                    {isPrimary && <Tag color={config.color} style={{ marginLeft: 'auto', fontSize: 10 }}>主要</Tag>}
                  </div>
                  {editing ? (
                    <Slider 
                      value={editData.style_scores[key]} 
                      onChange={(v) => setEditData({
                        ...editData,
                        style_scores: { ...editData.style_scores, [key]: v }
                      })}
                      min={0} max={100}
                      trackStyle={{ background: config.color }}
                      handleStyle={{ borderColor: config.color }}
                    />
                  ) : (
                    <Progress 
                      percent={score} 
                      size="small"
                      strokeColor={config.color}
                      format={(p) => `${p}%`}
                      showInfo={false}
                    />
                  )}
                  <div style={{ fontSize: 11, color: '#888', marginTop: 6 }}>{config.description}</div>
                </div>
              </Col>
            )
          })}
        </Row>

        {!editing && (
          <div 
            style={{
              padding: '14px 16px',
              background: `linear-gradient(135deg, ${primaryStyleConfig.color}15 0%, ${primaryStyleConfig.color}08 100%)`,
              borderRadius: 10,
              borderLeft: `4px solid ${primaryStyleConfig.color}`
            }}
          >
            <div style={{ fontWeight: 600, marginBottom: 6, display: 'flex', alignItems: 'center', gap: 6 }}>
              <BulbOutlined style={{ color: primaryStyleConfig.color }} />
              {primaryStyleConfig.label}学习建议
            </div>
            <div style={{ color: '#555', fontSize: 13, lineHeight: 1.7 }}>
              {primaryStyleConfig.tip}
            </div>
          </div>
        )}

        <Divider style={{ margin: '16px 0' }}>学习参数</Divider>
        
        <Row gutter={16}>
          <Col span={12}>
            <div style={{ marginBottom: 8 }}>
              <div style={{ color: '#888', fontSize: 12, marginBottom: 6, display: 'flex', alignItems: 'center', gap: 4 }}>
                <CalendarOutlined /> 最佳学习时段
              </div>
              {editing ? (
                <Select
                  value={editData.preferred_time}
                  onChange={(v) => setEditData({ ...editData, preferred_time: v })}
                  options={TIME_OPTIONS.map(t => ({ value: t.value, label: `${t.icon} ${t.label}` }))}
                  style={{ width: '100%' }}
                />
              ) : (
                <div style={{ fontWeight: 500, fontSize: 15 }}>
                  {primaryTime?.icon} {primaryTime?.label}
                </div>
              )}
            </div>
          </Col>
          <Col span={12}>
            <div style={{ marginBottom: 8 }}>
              <div style={{ color: '#888', fontSize: 12, marginBottom: 6, display: 'flex', alignItems: 'center', gap: 4 }}>
                <ClockCircleOutlined /> 推荐学习时长
              </div>
              {editing ? (
                <Slider
                  value={editData.study_duration}
                  onChange={(v) => setEditData({ ...editData, study_duration: v })}
                  min={15} max={120}
                  marks={{ 15: '15分', 60: '60分', 120: '120分' }}
                />
              ) : (
                <div style={{ fontWeight: 500, fontSize: 15 }}>{learningStyle?.study_duration || 45} 分钟</div>
              )}
            </div>
          </Col>
        </Row>

        {editing && (
          <div style={{ display: 'flex', gap: 8, justifyContent: 'flex-end', marginTop: 16 }}>
            <Button onClick={handleCancel}>取消</Button>
            <Button type="primary" onClick={handleUpdate}>保存设置</Button>
          </div>
        )}
      </Card>

      {/* 学习模式与效率分析 */}
      <Card 
        size="small"
        title={
          <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            <LineChartOutlined style={{ color: patternInfo.color }} />
            <span>学习模式与效率</span>
          </div>
        }
        style={{ marginBottom: 16, borderRadius: 12 }}
      >
        <Row gutter={16}>
          <Col span={8}>
            <div style={{ textAlign: 'center', padding: '12px 8px', background: `${patternInfo.color}10`, borderRadius: 10 }}>
              <div style={{ fontSize: 24, marginBottom: 4 }}>{patternInfo.icon}</div>
              <div style={{ fontWeight: 600, color: patternInfo.color, marginBottom: 4 }}>{summary?.learning_pattern || '均衡发展'}</div>
              <div style={{ fontSize: 11, color: '#888' }}>{patternInfo.desc}</div>
            </div>
          </Col>
          <Col span={8}>
            <div style={{ textAlign: 'center', padding: '12px 8px', background: '#f5f5f5', borderRadius: 10 }}>
              <div style={{ fontSize: 24, marginBottom: 4, color: '#1890ff' }}>
                <RiseOutlined />
              </div>
              <div style={{ fontWeight: 600, color: '#1890ff', fontSize: 18 }}>{summary?.study_efficiency || 0}</div>
              <div style={{ fontSize: 11, color: '#888' }}>学习效率指数</div>
            </div>
          </Col>
          <Col span={8}>
            <div style={{ textAlign: 'center', padding: '12px 8px', background: '#f5f5f5', borderRadius: 10 }}>
              <div style={{ fontSize: 24, marginBottom: 4, color: '#722ed1' }}>
                <RobotOutlined />
              </div>
              <div style={{ fontWeight: 600, color: '#722ed1', fontSize: 18 }}>{summary?.session_count || 0}</div>
              <div style={{ fontSize: 11, color: '#888' }}>AI对话次数</div>
            </div>
          </Col>
        </Row>

        <Divider style={{ margin: '16px 0' }} />

        <Row gutter={16}>
          <Col span={12}>
            <div style={{ fontSize: 12, color: '#888', marginBottom: 6 }}>活跃度（近7天）</div>
            <Progress 
              percent={Math.round((summary?.active_days || 0) / 7 * 100)} 
              strokeColor="#52c41a"
              format={(p) => `${summary?.active_days || 0}/7天`}
            />
          </Col>
          <Col span={12}>
            <div style={{ fontSize: 12, color: '#888', marginBottom: 6 }}>平均记忆强度</div>
            <Progress 
              percent={summary?.memory_strength_avg || 0} 
              strokeColor={summary?.memory_strength_avg >= 70 ? '#52c41a' : summary?.memory_strength_avg >= 40 ? '#faad14' : '#ff4d4f'}
              format={(p) => `${p}%`}
            />
          </Col>
        </Row>
      </Card>

      {/* 学习进度总览 */}
      <Card 
        size="small"
        title={
          <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            <AimOutlined style={{ color: '#6366f1' }} />
            <span>学习进度总览</span>
          </div>
        }
        style={{ marginBottom: 16, borderRadius: 12 }}
      >
        <Row gutter={[16, 16]}>
          <Col span={6}>
            <div style={{ textAlign: 'center' }}>
              <div style={{ fontSize: 22, fontWeight: 700, color: '#6366f1' }}>
                {summary?.active_goals || 0}<span style={{ fontSize: 14, color: '#999', fontWeight: 400 }}>/{summary?.total_goals || 0}</span>
              </div>
              <div style={{ fontSize: 11, color: '#888' }}>进行中目标</div>
            </div>
          </Col>
          <Col span={6}>
            <div style={{ textAlign: 'center' }}>
              <div style={{ fontSize: 22, fontWeight: 700, color: '#52c41a' }}>
                {summary?.mastered_points || 0}
              </div>
              <div style={{ fontSize: 11, color: '#888' }}>已掌握</div>
            </div>
          </Col>
          <Col span={6}>
            <div style={{ textAlign: 'center' }}>
              <div style={{ fontSize: 22, fontWeight: 700, color: '#faad14' }}>
                {summary?.overall_mastery || 0}%
              </div>
              <div style={{ fontSize: 11, color: '#888' }}>整体掌握度</div>
            </div>
          </Col>
          <Col span={6}>
            <div style={{ textAlign: 'center' }}>
              <div style={{ fontSize: 22, fontWeight: 700, color: '#ff6b6b' }}>
                {summary?.study_streak || 0}
              </div>
              <div style={{ fontSize: 11, color: '#888' }}>连续天数</div>
            </div>
          </Col>
        </Row>

        <Divider style={{ margin: '16px 0' }} />

        <Row gutter={16}>
          <Col span={12}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8, padding: '10px 12px', background: summary?.urgent_reviews > 0 ? '#fff2f0' : '#f6ffed', borderRadius: 8, border: `1px solid ${summary?.urgent_reviews > 0 ? '#ffccc7' : '#b7eb8f'}` }}>
              <AlertOutlined style={{ color: summary?.urgent_reviews > 0 ? '#ff4d4f' : '#52c41a', fontSize: 18 }} />
              <div>
                <div style={{ fontWeight: 600, color: summary?.urgent_reviews > 0 ? '#ff4d4f' : '#52c41a' }}>
                  {summary?.urgent_reviews || 0} 个待复习
                </div>
                {summary?.upcoming_reviews > 0 && (
                  <div style={{ fontSize: 11, color: '#faad14' }}>+ {summary?.upcoming_reviews} 个即将到期</div>
                )}
              </div>
            </div>
          </Col>
          <Col span={12}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8, padding: '10px 12px', background: '#f5f5f5', borderRadius: 8 }}>
              <ExperimentOutlined style={{ color: '#1890ff', fontSize: 18 }} />
              <div>
                <div style={{ fontWeight: 600, color: '#1890ff' }}>
                  还需约 {summary?.estimated_hours_needed || 0} 小时
                </div>
                <div style={{ fontSize: 11, color: '#888' }}>完成剩余 {summary?.remaining_points || 0} 个知识点</div>
              </div>
            </div>
          </Col>
        </Row>
      </Card>

      {/* 各学习目标详情 */}
      {goals.length > 0 && (
        <Card 
          size="small"
          title={
            <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
              <ThunderboltOutlined style={{ color: '#f59e0b' }} />
              <span>学习目标详情</span>
              <Badge count={goals.length} style={{ marginLeft: 4 }} />
            </div>
          }
          style={{ borderRadius: 12 }}
        >
          <List
            size="small"
            dataSource={goals}
            renderItem={(goal) => {
              const progress = goal.progress || {}
              const mastery = progress.total > 0 ? Math.round((progress.mastered / progress.total) * 100) : 0
              const statusColor = goal.status === 'completed' ? '#52c41a' : mastery >= 80 ? '#52c41a' : mastery >= 50 ? '#faad14' : '#1890ff'
              
              return (
                <List.Item style={{ padding: '12px 0' }}>
                  <div style={{ width: '100%' }}>
                    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 8 }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                        <span style={{ fontWeight: 600 }}>{goal.title}</span>
                        {goal.subject && <Tag color="blue" style={{ fontSize: 10 }}>{goal.subject}</Tag>}
                      </div>
                      <Tag color={goal.status === 'completed' ? 'success' : 'processing'}>
                        {goal.status === 'completed' ? '已完成' : '进行中'}
                      </Tag>
                    </div>
                    <div style={{ display: 'flex', gap: 12, fontSize: 12, color: '#666', marginBottom: 6 }}>
                      <span><BookOutlined /> {progress.mastered || 0}/{progress.total || 0} 掌握</span>
                      <span><CalendarOutlined /> {progress.completed_lessons || 0} 课时</span>
                      <span><ClockCircleOutlined /> {goal.target_hours_per_week || 0}h/周</span>
                    </div>
                    <Progress 
                      percent={mastery} 
                      size="small"
                      strokeColor={statusColor}
                      format={(p) => `${p}%`}
                    />
                  </div>
                </List.Item>
              )
            }}
          />
        </Card>
      )}

      {/* 学习历史 */}
      {summary?.last_study_date && (
        <Card size="small" style={{ marginTop: 16, borderRadius: 12 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8, color: '#666', fontSize: 12 }}>
            <ClockCircleOutlined />
            <span>最近学习：{new Date(summary.last_study_date).toLocaleDateString('zh-CN', { 
              year: 'numeric', month: 'long', day: 'numeric', hour: '2-digit', minute: '2-digit' 
            })}</span>
          </div>
        </Card>
      )}
    </div>
  )
}

export default LearningStyle
