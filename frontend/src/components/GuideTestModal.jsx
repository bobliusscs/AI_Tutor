import { useState } from 'react'
import { Modal, Button, Radio, Card, Tag, Progress, Space, Typography, Divider, List, Avatar } from 'antd'
import { CheckCircleOutlined, CloseCircleOutlined, TrophyOutlined, BookOutlined, StarOutlined } from '@ant-design/icons'

const { Title, Text, Paragraph } = Typography

/**
 * 学习测试弹窗组件
 * 用于展示测试题目、收集答案、显示结果
 */
function GuideTestModal({
  visible,
  questions,
  onClose,
  onSubmit,
  encouragement,
  achievements = [],
  goalId = null
}) {
  const [currentIndex, setCurrentIndex] = useState(0)
  const [answers, setAnswers] = useState({})
  const [showResult, setShowResult] = useState(false)
  const [submitted, setSubmitted] = useState(false)

  // 如果没有题目，不显示
  if (!questions || questions.length === 0) return null

  const currentQuestion = questions[currentIndex]
  const totalQuestions = questions.length
  const answeredCount = Object.keys(answers).length
  const progressPercent = Math.round((answeredCount / totalQuestions) * 100)

  // 处理选择答案
  const handleSelectAnswer = (value) => {
    setAnswers(prev => ({
      ...prev,
      [currentQuestion.question]: value
    }))
  }

  // 计算得分
  const calculateScore = () => {
    let correct = 0
    questions.forEach(q => {
      if (answers[q.question] === q.answer) {
        correct++
      }
    })
    return {
      correct,
      total: totalQuestions,
      percentage: Math.round((correct / totalQuestions) * 100)
    }
  }

  // 提交答案
  const handleSubmit = () => {
    setSubmitted(true)
    setShowResult(true)
    const score = calculateScore()
    if (onSubmit) {
      onSubmit({ answers, score, questions })
    }
  }

  // 关闭弹窗并重置状态
  const handleClose = () => {
    setCurrentIndex(0)
    setAnswers({})
    setShowResult(false)
    setSubmitted(false)
    onClose()
  }

  // 获取难度标签
  const getDifficultyTag = (difficulty) => {
    const config = {
      easy: { color: 'success', text: '简单' },
      medium: { color: 'warning', text: '中等' },
      hard: { color: 'error', text: '困难' }
    }
    const { color, text } = config[difficulty] || config.medium
    return <Tag color={color}>{text}</Tag>
  }

  // 获取成就图标
  const getAchievementIcon = (icon) => {
    const icons = {
      trophy: <TrophyOutlined />,
      star: <StarOutlined />,
      rocket: <span>🚀</span>,
      medal: <span>🏅</span>,
      crown: <span>👑</span>,
      gem: <span>💎</span>,
      compass: <span>🧭</span>,
      fire: <span>🔥</span>
    }
    return icons[icon] || <StarOutlined />
  }

  // 渲染成就列表
  const renderAchievements = () => {
    if (!achievements || achievements.length === 0) return null

    return (
      <div style={{ marginBottom: 24 }}>
        <Title level={5} style={{ textAlign: 'center', marginBottom: 16 }}>
          <TrophyOutlined style={{ color: '#faad14', marginRight: 8 }} />
          新成就解锁！
        </Title>
        <List
          itemLayout="horizontal"
          dataSource={achievements}
          renderItem={(item) => (
            <List.Item>
              <List.Item.Meta
                avatar={
                  <Avatar
                    size="large"
                    style={{ backgroundColor: '#faad14', fontSize: 24 }}
                  >
                    {getAchievementIcon(item.icon)}
                  </Avatar>
                }
                title={item.title}
                description={item.description}
              />
            </List.Item>
          )}
        />
      </div>
    )
  }

  // 渲染结果页面
  const renderResult = () => {
    const score = calculateScore()
    return (
      <div style={{ textAlign: 'center', padding: '20px 0' }}>
        <TrophyOutlined style={{ fontSize: 64, color: '#faad14', marginBottom: 16 }} />
        <Title level={3}>测试完成！</Title>

        {/* 鼓励语 */}
        {encouragement && (
          <Paragraph
            style={{
              fontSize: 20,
              fontWeight: 600,
              color: score.percentage >= 60 ? '#52c41a' : '#1890ff',
              marginBottom: 16
            }}
          >
            {encouragement}
          </Paragraph>
        )}

        <Paragraph style={{ fontSize: 18, marginBottom: 24 }}>
          你答对了 <Text strong style={{ fontSize: 24, color: '#52c41a' }}>{score.correct}</Text> / {score.total} 道题
        </Paragraph>
        <Progress
          percent={score.percentage}
          status={score.percentage >= 60 ? 'success' : 'exception'}
          strokeWidth={20}
          style={{ marginBottom: 32, maxWidth: 400, margin: '0 auto 32px' }}
        />

        {/* 成就列表 */}
        {renderAchievements()}

        <Divider />

        <div style={{ textAlign: 'left', maxHeight: 300, overflowY: 'auto' }}>
          {questions.map((q, idx) => {
            const userAnswer = answers[q.question]
            const isCorrect = userAnswer === q.answer
            return (
              <Card
                key={idx}
                size="small"
                style={{
                  marginBottom: 12,
                  borderLeft: `4px solid ${isCorrect ? '#52c41a' : '#ff4d4f'}`
                }}
              >
                <Space direction="vertical" style={{ width: '100%' }}>
                  <Text strong>第 {idx + 1} 题 {isCorrect ?
                    <CheckCircleOutlined style={{ color: '#52c41a' }} /> :
                    <CloseCircleOutlined style={{ color: '#ff4d4f' }} />
                  }</Text>
                  <Text>{q.question}</Text>
                  <Space>
                    <Text type="secondary">你的答案: {userAnswer || '未作答'}</Text>
                    {!isCorrect && <Text type="success">正确答案: {q.answer}</Text>}
                  </Space>
                </Space>
              </Card>
            )
          })}
        </div>
      </div>
    )
  }

  // 渲染题目页面
  const renderQuestion = () => {
    return (
      <div>
        {/* 进度条 */}
        <div style={{ marginBottom: 24 }}>
          <Space style={{ marginBottom: 8, display: 'flex', justifyContent: 'space-between' }}>
            <Text type="secondary">
              <BookOutlined /> 第 {currentIndex + 1} / {totalQuestions} 题
            </Text>
            {getDifficultyTag(currentQuestion.difficulty)}
          </Space>
          <Progress percent={progressPercent} size="small" showInfo={false} />
        </div>

        {/* 题目内容 */}
        <Card style={{ marginBottom: 24 }}>
          <Paragraph style={{ fontSize: 16, fontWeight: 500, marginBottom: 20 }}>
            {currentQuestion.question}
          </Paragraph>
          
          <Radio.Group
            onChange={(e) => handleSelectAnswer(e.target.value)}
            value={answers[currentQuestion.question]}
            style={{ width: '100%' }}
          >
            <Space direction="vertical" style={{ width: '100%' }} size="middle">
              {currentQuestion.options.map((option) => (
                <Radio
                  key={option.key}
                  value={option.key}
                  style={{
                    display: 'flex',
                    alignItems: 'flex-start',
                    padding: '12px 16px',
                    borderRadius: 8,
                    border: '1px solid #d9d9d9',
                    width: '100%',
                    margin: 0,
                    backgroundColor: answers[currentQuestion.question] === option.key ? '#e6f7ff' : 'transparent',
                    borderColor: answers[currentQuestion.question] === option.key ? '#1890ff' : '#d9d9d9'
                  }}
                >
                  <span style={{ fontWeight: 500, marginRight: 8 }}>{option.key}.</span>
                  <span>{option.text}</span>
                </Radio>
              ))}
            </Space>
          </Radio.Group>
        </Card>

        {/* 导航按钮 */}
        <div style={{ display: 'flex', justifyContent: 'space-between' }}>
          <Button
            disabled={currentIndex === 0}
            onClick={() => setCurrentIndex(prev => prev - 1)}
          >
            上一题
          </Button>
          
          {currentIndex < totalQuestions - 1 ? (
            <Button
              type="primary"
              onClick={() => setCurrentIndex(prev => prev + 1)}
            >
              下一题
            </Button>
          ) : (
            <Button
              type="primary"
              onClick={handleSubmit}
              disabled={answeredCount < totalQuestions}
            >
              提交答案 ({answeredCount}/{totalQuestions})
            </Button>
          )}
        </div>
      </div>
    )
  }

  return (
    <Modal
      title={showResult ? '测试结果' : '学习测试'}
      open={visible}
      onCancel={handleClose}
      width={700}
      footer={showResult ? [
        <Button key="close" type="primary" onClick={handleClose}>
          关闭
        </Button>
      ] : null}
      maskClosable={false}
      destroyOnHidden
    >
      {showResult ? renderResult() : renderQuestion()}
    </Modal>
  )
}

export default GuideTestModal
