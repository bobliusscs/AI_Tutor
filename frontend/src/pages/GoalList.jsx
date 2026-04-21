import { useState, useEffect } from 'react'
import { Card, Empty, Spin, message, Typography } from 'antd'
import { BookOutlined, RightOutlined } from '@ant-design/icons'
import { useNavigate } from 'react-router-dom'
import { studyGoalAPI } from '../utils/api'
import LearningStyle from '../components/LearningStyle'

const { Title, Text } = Typography

function GoalList() {
  const navigate = useNavigate()
  const [goals, setGoals] = useState([])
  const [loading, setLoading] = useState(true)

  // 获取学习目标列表
  const fetchGoals = async () => {
    try {
      const studentId = localStorage.getItem('student_id') || '1'
      const result = await studyGoalAPI.list(parseInt(studentId))
      if (result.data?.success) {
        setGoals(result.data.data || [])
      }
    } catch (error) {
      message.error('获取学习目标失败')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchGoals()
  }, [])

  // 创建学习目标
  const handleCreateGoal = async (values) => {
    setCreating(true)
    try {
      const result = await studyGoalAPI.create({
        title: values.title,
        description: values.description,
        subject: values.subject,
        target_hours_per_week: values.target_hours_per_week || 5,
        target_completion_date: values.target_completion_date?.toISOString(),
        student_background: {
          level: values.level || 'beginner'
        }
      })

      if (result.data?.success) {
        message.success('学习目标创建成功！')
        setIsModalOpen(false)
        form.resetFields()
        fetchGoals()
        // 跳转到新创建的学习目标
        navigate(`/goals/${result.data.data.goal_id}/knowledge-graph`)
      }
    } catch (error) {
      message.error('创建失败：' + error.message)
    } finally {
      setCreating(false)
    }
  }

  // 渲染空状态 - 引导使用 AI Tutor
  const renderEmptyState = () => (
    <Empty
      image={Empty.PRESENTED_IMAGE_SIMPLE}
      description={
        <div style={{ textAlign: 'center' }}>
          <Title level={4}>还没有学习目标</Title>
          <Text type="secondary" style={{ display: 'block', marginBottom: 16 }}>
            与 AI Tutor 交流，让 AI 帮你制定个性化的学习计划！
          </Text>
          <div style={{ 
            background: '#f6ffed', 
            border: '1px solid #b7eb8f', 
            borderRadius: 8, 
            padding: 16, 
            maxWidth: 500,
            textAlign: 'left'
          }}>
            <Text strong style={{ color: '#52c41a', display: 'block', marginBottom: 8 }}>
              🤖 AI 家教可以帮你：
            </Text>
            <ul style={{ margin: 0, paddingLeft: 20, color: '#595959' }}>
              <li>了解你的学习需求和目标</li>
              <li>根据你的情况生成知识图谱</li>
              <li>制定个性化的学习计划</li>
              <li>推荐适合的学习资料和习题</li>
              <li>跟踪学习进度并给出建议</li>
            </ul>
          </div>
        </div>
      }
    />
  )

  // 渲染学习目标卡片
  const renderGoalCard = (goal) => {
    const progress = goal.progress || {}
    const masteryPercentage = progress.total > 0 
      ? Math.round((progress.mastered / progress.total) * 100) 
      : 0

    return (
      <Card
        key={goal.id}
        hoverable
        style={{ marginBottom: 16, cursor: 'pointer' }}
        onClick={() => navigate(`/goals/${goal.id}/knowledge-graph`)}
      >
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
          <div style={{ flex: 1 }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 8 }}>
              <BookOutlined style={{ fontSize: 20, color: '#1890ff' }} />
              <Title level={5} style={{ margin: 0 }}>{goal.title}</Title>
              {goal.subject && (
                <span style={{ 
                  background: '#e6f7ff', 
                  color: '#1890ff', 
                  padding: '2px 8px', 
                  borderRadius: 4,
                  fontSize: 12 
                }}>
                  {goal.subject}
                </span>
              )}
            </div>
            {goal.description && (
              <Text type="secondary" style={{ display: 'block', marginBottom: 12 }}>
                {goal.description}
              </Text>
            )}
            <div style={{ display: 'flex', gap: 24, fontSize: 14 }}>
              <span>
                <Text type="secondary">知识点掌握：</Text>
                <Text strong>{progress.mastered || 0}/{progress.total || 0}</Text>
                <Text type="secondary"> ({masteryPercentage}%)</Text>
              </span>
              <span>
                <Text type="secondary">已完成课时：</Text>
                <Text strong>{progress.completed_lessons || 0}</Text>
              </span>
              <span>
                <Text type="secondary">每周投入：</Text>
                <Text strong>{goal.target_hours_per_week}小时</Text>
              </span>
            </div>
          </div>
          <RightOutlined style={{ color: '#bfbfbf', fontSize: 20 }} />
        </div>
        {/* 进度条 */}
        <div style={{ marginTop: 12 }}>
          <div style={{ 
            height: 6, 
            background: '#f0f0f0', 
            borderRadius: 3,
            overflow: 'hidden'
          }}>
            <div style={{ 
              width: `${masteryPercentage}%`, 
              height: '100%', 
              background: '#52c41a',
              borderRadius: 3,
              transition: 'width 0.3s'
            }} />
          </div>
        </div>
      </Card>
    )
  }

  if (loading) {
    return (
      <div style={{ textAlign: 'center', padding: 100 }}>
        <Spin size="large" tip="加载中..." />
      </div>
    )
  }

  return (
    <div style={{ maxWidth: 900, margin: '0 auto', padding: 24 }}>
      <Title level={3} style={{ marginBottom: 24 }}>我的学习目标</Title>
      
      {/* 学习风格分析组件 */}
      <LearningStyle />
  
      {goals.length === 0 ? renderEmptyState() : (
        <div>
          {goals.map(renderGoalCard)}
        </div>
      )}
    </div>
  )
}

export default GoalList
