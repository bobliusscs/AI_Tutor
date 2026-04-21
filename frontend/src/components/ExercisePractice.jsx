import React, { useState, useEffect } from 'react'
import { Spin, Button, Radio, Progress, Modal, App } from 'antd'
import { CheckCircleOutlined, CloseCircleOutlined, RightOutlined, LeftOutlined, ReloadOutlined, StopOutlined, TrophyOutlined } from '@ant-design/icons'
import { motion } from 'framer-motion'
import { practiceAPI } from '../utils/api'

// 难度标签配置
const DIFFICULTY_CONFIG = {
  basic: { label: '基础题', color: '#52c41a', bg: '#f6ffed', border: '#b7eb8f' },
  comprehensive: { label: '综合题', color: '#faad14', bg: '#fffbe6', border: '#ffe58f' },
  challenge: { label: '挑战题', color: '#ff4d4f', bg: '#fff2f0', border: '#ffccc7' }
}

// 单选题组件
function SingleChoiceQuestion({ question, index, selectedAnswer, onAnswerChange, showResult }) {
  const difficulty = DIFFICULTY_CONFIG[question.difficulty] || DIFFICULTY_CONFIG.basic
  
  // ========== 统一字段适配 ==========
  // 题目内容: stem, question, question_text
  const questionText = question.question_text || question.stem || question.question || question.knowledge_point_name || '请完成本题'
  
  // 选项处理：统一转换为带序号的字符串数组
  const rawOptions = question.options || []
  const processedOptions = rawOptions.map((opt, idx) => {
    if (typeof opt === 'string') {
      // 字符串格式: "武陵山" 或 "A. 武陵山"
      const cleanText = opt.replace(/^[A-D]\.\s*/, '')
      return { label: String.fromCharCode(65 + idx), text: cleanText }
    } else if (typeof opt === 'object' && opt !== null) {
      // 对象格式: {key: "A", text: "武陵山"} 或 {text: "武陵山"}
      return { 
        label: opt.key || String.fromCharCode(65 + idx), 
        text: opt.text || opt.label || String(opt) 
      }
    }
    return { label: String.fromCharCode(65 + idx), text: String(opt) }
  })
  
  // 正确答案处理：统一转换为选项索引 (0-based)
  let correctIndex = -1
  // 支持的字段: correct_answer, correct_option, correct_index, correct
  const answerValue = question.correct_answer || question.correct_option || question.correct_index || question.correct
  
  if (answerValue !== undefined && answerValue !== null) {
    if (typeof answerValue === 'string') {
      // "A", "B", "C", "D" 或 "C" 格式
      const answer = answerValue.toUpperCase()
      if (answer.length === 1 && answer >= 'A' && answer <= 'D') {
        correctIndex = answer.charCodeAt(0) - 65
      }
    } else {
      // 数字格式: 0, 1, 2, 3
      correctIndex = Number(answerValue)
    }
  }
  
  // 正确选项的标签 (A, B, C, D)
  const correctLabel = correctIndex >= 0 ? String.fromCharCode(65 + correctIndex) : ''
  const correctOptionText = correctIndex >= 0 && correctIndex < processedOptions.length 
    ? processedOptions[correctIndex].text 
    : ''
  
  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3, delay: index * 0.1 }}
      style={{
        background: '#fff',
        borderRadius: 12,
        padding: 16,
        marginBottom: 14,
        border: '1px solid rgba(226,232,240,0.8)',
        boxShadow: '0 2px 12px rgba(99,102,241,0.04)'
      }}
    >
      {/* 题目头部 */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 6 }}>
        <div style={{ flex: 1 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            <span style={{
              display: 'inline-block',
              padding: '2px 10px',
              borderRadius: 6,
              background: difficulty.bg,
              border: `1px solid ${difficulty.border}`,
              color: difficulty.color,
              fontSize: 12,
              fontWeight: 600
            }}>
              {difficulty.label}
            </span>
            {question.knowledge_point_name && (
              <span style={{
                fontSize: 12,
                color: '#94a3b8',
                background: '#f1f5f9',
                padding: '2px 8px',
                borderRadius: 4
              }}>
                {question.knowledge_point_name}
              </span>
            )}
          </div>
          {/* 题目内容 */}
          <div style={{ fontSize: 14, fontWeight: 600, color: '#1e293b', lineHeight: 1.5 }}>
            <span style={{ color: '#6366f1', marginRight: 8 }}>Q{index + 1}.</span>
            {questionText}
          </div>
        </div>
      </div>

      {/* 选项列表 */}
      <Radio.Group
        value={selectedAnswer}
        onChange={(e) => onAnswerChange(e.target.value)}
        style={{ width: '100%' }}
      >
        <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
          {processedOptions.map((opt, optIdx) => {
            const isSelected = selectedAnswer === opt.label
            const isCorrect = showResult && opt.label === correctLabel
            const isWrong = showResult && isSelected && opt.label !== correctLabel
            
            let style = {
              display: 'flex',
              alignItems: 'flex-start',
              padding: '8px 12px',
              borderRadius: 10,
              border: '1px solid #e5e7eb',
              cursor: showResult ? 'default' : 'pointer',
              transition: 'all 0.2s ease',
              background: '#fff'
            }
            
            if (isCorrect) {
              style = { ...style, borderColor: '#52c41a', background: '#f6ffed' }
            } else if (isWrong) {
              style = { ...style, borderColor: '#ff4d4f', background: '#fff2f0' }
            } else if (isSelected) {
              style = { ...style, borderColor: '#6366f1', background: '#f0f5ff' }
            }
            
            return (
              <Radio
                key={optIdx}
                value={opt.label}
                disabled={showResult}
                style={{ margin: 0, width: '100%' }}
              >
                <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                  <span style={{
                    width: 22,
                    height: 22,
                    borderRadius: '50%',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    background: isCorrect ? '#52c41a' : isWrong ? '#ff4d4f' : isSelected ? '#6366f1' : '#f1f5f9',
                    color: isCorrect || isWrong || isSelected ? '#fff' : '#64748b',
                    fontWeight: 600,
                    fontSize: 12
                  }}>
                    {opt.label}
                  </span>
                  <span style={{ color: '#374151', fontSize: 13, lineHeight: 1.4 }}>
                    {opt.text}
                  </span>
                  {isCorrect && <CheckCircleOutlined style={{ color: '#52c41a', marginLeft: 'auto' }} />}
                  {isWrong && <CloseCircleOutlined style={{ color: '#ff4d4f', marginLeft: 'auto' }} />}
                </div>
              </Radio>
            )
          })}
        </div>
      </Radio.Group>
      
      {/* 正确答案提示（答错时显示） */}
      {showResult && correctLabel && selectedAnswer?.toUpperCase() !== correctLabel && (
        <div style={{
          marginTop: 10,
          padding: '8px 12px',
          background: '#f0f5ff',
          borderRadius: 8,
          border: '1px solid #d9d9d9',
          fontSize: 12,
          color: '#666'
        }}>
          <strong>正确答案：</strong>{correctLabel}. {correctOptionText}
          {question.explanation && (
            <div style={{ marginTop: 4, color: '#888' }}>
              <small>{question.explanation}</small>
            </div>
          )}
        </div>
      )}
    </motion.div>
  )
}

// 诊断分析结果组件
function DiagnosisResult({ result, onNextAction, lessonId, onMarkComplete }) {
  const { message } = App.useApp()
  const [confirmLoading, setConfirmLoading] = useState(false)
  const accuracy = result.accuracy || 0
  const masteryChanges = result.diagnosis?.mastery_changes || []
  const suggestions = result.diagnosis?.suggestions || []
  
  const [confirmModalVisible, setConfirmModalVisible] = useState(false)
  
  const getAccuracyColor = (acc) => {
    if (acc >= 80) return '#52c41a'
    if (acc >= 60) return '#faad14'
    return '#ff4d4f'
  }
  
  const getAccuracyText = (acc) => {
    if (acc >= 80) return '优秀'
    if (acc >= 60) return '良好'
    return '需加强'
  }
  
  // 处理标记完成学习
  const handleMarkComplete = async () => {
    // lessonId 验证增强：检查是否为有效的正整数
    if (lessonId === null || lessonId === undefined || !Number.isInteger(lessonId) || lessonId <= 0) {
      message.error('课时信息缺失，请重新获取练习题')
      return
    }

    setConfirmLoading(true)
    try {
      const res = await practiceAPI.markLessonComplete(lessonId)
      if (res.data?.success) {
        // 检查是否整个小节已全部学习完成
        if (res.data.data?.all_completed) {
          message.success('恭喜！本小节已全部学习完成')
        } else {
          message.success('已标记本节学习完成！')
        }
        setConfirmModalVisible(false)
        // 刷新学情分析
        window.dispatchEvent(new CustomEvent('refresh-analysis', { detail: { goalId: null } }))
        // 继续下一步操作
        onNextAction('next')
      } else {
        // API 返回 success: false，解析 message 给出友好提示
        const errorMsg = res.data?.message || '标记失败，请稍后重试'
        message.error(errorMsg)
        // 错误时不关闭确认弹窗，让用户可以重试
      }
    } catch (err) {
      console.error('标记课时完成失败:', err)
      // 处理 HTTP 404 错误
      if (err.response?.status === 404) {
        message.error('该课时不存在，可能数据已更新，请刷新页面')
      } else {
        // 其他网络错误
        message.error('网络异常，请重试')
      }
      // 错误时不关闭确认弹窗，让用户可以重试
    } finally {
      setConfirmLoading(false)
    }
  }
  
  return (
    <motion.div
      initial={{ opacity: 0, scale: 0.95 }}
      animate={{ opacity: 1, scale: 1 }}
      transition={{ duration: 0.4 }}
      style={{
        background: '#fff',
        borderRadius: 16,
        padding: 20,
        border: '1px solid rgba(226,232,240,0.8)',
        boxShadow: '0 4px 20px rgba(99,102,241,0.06)'
      }}
    >
      {/* 标题 */}
      <div style={{ textAlign: 'center', marginBottom: 16 }}>
        <h3 style={{ fontSize: 17, fontWeight: 700, color: '#1e293b', marginBottom: 12 }}>
          练习完成
        </h3>
        
        {/* 正确率大卡片 */}
        <div style={{
          width: 100,
          height: 100,
          borderRadius: '50%',
          margin: '0 auto 14px',
          background: `linear-gradient(135deg, ${getAccuracyColor(accuracy)}20, ${getAccuracyColor(accuracy)}40)`,
          border: `3px solid ${getAccuracyColor(accuracy)}`,
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          justifyContent: 'center',
          boxShadow: `0 4px 16px ${getAccuracyColor(accuracy)}30`
        }}>
          <span style={{ fontSize: 28, fontWeight: 800, color: getAccuracyColor(accuracy) }}>
            {accuracy}%
          </span>
          <span style={{ fontSize: 12, color: '#64748b', fontWeight: 500 }}>
            {getAccuracyText(accuracy)}
          </span>
        </div>
        
        {/* 统计信息 */}
        <div style={{ display: 'flex', justifyContent: 'center', gap: 24, marginBottom: 14 }}>
          <div style={{ textAlign: 'center' }}>
            <div style={{ fontSize: 20, fontWeight: 700, color: '#6366f1' }}>
              {result.correct_count}
            </div>
            <div style={{ fontSize: 11, color: '#94a3b8' }}>答对</div>
          </div>
          <div style={{ textAlign: 'center' }}>
            <div style={{ fontSize: 20, fontWeight: 700, color: '#94a3b8' }}>
              {result.total_questions - result.correct_count}
            </div>
            <div style={{ fontSize: 11, color: '#94a3b8' }}>答错</div>
          </div>
          <div style={{ textAlign: 'center' }}>
            <div style={{ fontSize: 20, fontWeight: 700, color: '#10b981' }}>
              {result.overall_mastery || 0}%
            </div>
            <div style={{ fontSize: 11, color: '#94a3b8' }}>整体掌握</div>
          </div>
        </div>
      </div>
      
      {/* 建议 */}
      {suggestions.length > 0 && (
        <div style={{
          background: '#f8fafc',
          borderRadius: 10,
          padding: 12,
          marginBottom: 16
        }}>
          <h4 style={{ fontSize: 13, fontWeight: 600, color: '#374151', marginBottom: 8 }}>
            诊断分析
          </h4>
          <ul style={{ margin: 0, paddingLeft: 18, color: '#64748b', fontSize: 13, lineHeight: 1.7 }}>
            {suggestions.map((s, i) => (
              <li key={i} style={{ marginBottom: 4 }}>{s}</li>
            ))}
          </ul>
        </div>
      )}
      
      {/* 知识点掌握变化 */}
      {masteryChanges.length > 0 && (
        <div style={{ marginBottom: 16 }}>
          <h4 style={{ fontSize: 13, fontWeight: 600, color: '#374151', marginBottom: 8 }}>
            知识点掌握度变化
          </h4>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
            {masteryChanges.map((m, i) => (
              <div key={i} style={{
                display: 'flex',
                alignItems: 'center',
                gap: 10,
                padding: '8px 12px',
                background: m.is_correct ? '#f6ffed' : '#fff2f0',
                borderRadius: 8,
                border: `1px solid ${m.is_correct ? '#b7eb8f' : '#ffccc7'}`
              }}>
                <span style={{ 
                  fontSize: 16,
                  color: m.is_correct ? '#52c41a' : '#ff4d4f'
                }}>
                  {m.is_correct ? <CheckCircleOutlined /> : <CloseCircleOutlined />}
                </span>
                <span style={{ flex: 1, fontSize: 13, color: '#374151' }}>
                  {m.node_id}
                </span>
                <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                  <span style={{ fontSize: 12, color: '#94a3b8' }}>
                    {m.old_mastery}%
                  </span>
                  <span style={{ color: '#94a3b8' }}>→</span>
                  <span style={{ 
                    fontSize: 14, 
                    fontWeight: 600,
                    color: m.new_mastery > m.old_mastery ? '#52c41a' : m.new_mastery < m.old_mastery ? '#ff4d4f' : '#64748b'
                  }}>
                    {m.new_mastery}%
                  </span>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
      
      {/* 后续操作按钮 */}
      <div style={{
        display: 'flex',
        flexDirection: 'column',
        gap: 8,
        marginTop: 16
      }}>
        <Button
          type="primary"
          icon={<TrophyOutlined />}
          size="middle"
          block
          onClick={() => setConfirmModalVisible(true)}
          style={{ borderRadius: 8, height: 40, fontWeight: 500, background: 'linear-gradient(135deg, #52c41a, #73d13d)' }}
        >
          标记完成学习
        </Button>
        <div style={{ display: 'flex', gap: 8 }}>
          <Button
            icon={<ReloadOutlined />}
            size="middle"
            block
            onClick={() => onNextAction('retry')}
            style={{ borderRadius: 8, height: 40, fontWeight: 500 }}
          >
            继续练习
          </Button>
          <Button
            icon={<StopOutlined />}
            size="middle"
            block
            onClick={() => onNextAction('finish')}
            style={{ borderRadius: 8, height: 40, fontWeight: 500 }}
          >
            结束学习
          </Button>
        </div>
      </div>
      
      {/* 确认对话框 */}
      <Modal
        title={
          <span style={{ fontSize: 18, fontWeight: 600 }}>
            <TrophyOutlined style={{ color: '#52c41a', marginRight: 8 }} />
            确认完成本节学习？
          </span>
        }
        open={confirmModalVisible}
        onOk={handleMarkComplete}
        confirmLoading={confirmLoading}
        onCancel={() => setConfirmModalVisible(false)}
        okText="确认完成"
        cancelText="取消"
        okButtonProps={{ 
          style: { 
            background: 'linear-gradient(135deg, #52c41a, #73d13d)',
            border: 'none'
          }
        }}
      >
        <div style={{ padding: '12px 0' }}>
          <p style={{ fontSize: 15, color: '#374151', marginBottom: 12 }}>
            确认你已经完成了本节内容的学习？完成后：
          </p>
          <ul style={{ fontSize: 14, color: '#64748b', paddingLeft: 20, lineHeight: 1.8 }}>
            <li>本节将标记为已完成</li>
            <li>你可以继续学习下一节内容</li>
            <li>系统将更新你的学习进度</li>
          </ul>
          {result && (
            <div style={{
              marginTop: 16,
              padding: 12,
              background: '#f6ffed',
              borderRadius: 8,
              border: '1px solid #b7eb8f'
            }}>
              <div style={{ fontSize: 13, color: '#52c41a', fontWeight: 500 }}>
                本节练习成绩：{result.accuracy || 0}% 正确率
              </div>
            </div>
          )}
        </div>
      </Modal>
    </motion.div>
  )
}

// 主组件：练习巩固
function ExercisePractice({ goalId, sectionId, sectionTitle, lessonId: propLessonId, exerciseData, onComplete, onNextSection, onFinish }) {
  const { message } = App.useApp()
  const [loading, setLoading] = useState(true)
  const [submitting, setSubmitting] = useState(false)
  const [exercises, setExercises] = useState([])
  const [answers, setAnswers] = useState({})
  const [showResult, setShowResult] = useState(false)
  const [submitResult, setSubmitResult] = useState(null)
  const [exerciseId, setExerciseId] = useState(null)
  const [currentIndex, setCurrentIndex] = useState(0) // 当前题目索引
  const [currentLessonId, setCurrentLessonId] = useState(propLessonId || null) // 当前课时ID
  
  // 加载练习题
  useEffect(() => {
    if (exerciseData && exerciseData.exercises && exerciseData.exercises.length > 0) {
      // 从 prop 直接使用习题数据（Agent 工具返回）
      setExercises(exerciseData.exercises)
      setExerciseId(exerciseData.exercise_id || null)
      setCurrentIndex(0)
      if (exerciseData.lesson_id) {
        setCurrentLessonId(exerciseData.lesson_id)
      }
      const initialAnswers = {}
      exerciseData.exercises.forEach(q => {
        initialAnswers[q.id] = null
      })
      setAnswers(initialAnswers)
      setLoading(false)
    } else if (goalId && sectionId) {
      fetchExercises()
    }
  }, [exerciseData, goalId, sectionId])
  
  const fetchExercises = async () => {
    setLoading(true)
    setCurrentIndex(0) // 重置当前题目索引
    try {
      const res = await practiceAPI.getSectionExercises(goalId, sectionId)
      if (res.data?.success) {
        setExercises(res.data.data?.exercises || [])
        setExerciseId(res.data.data?.exercise_id)
        setCurrentIndex(0) // 确保索引从0开始
        // 如果 API 返回了 lesson_id，保存下来
        if (res.data.data?.lesson_id) {
          setCurrentLessonId(res.data.data.lesson_id)
        }
        // 初始化答案状态
        const initialAnswers = {}
        res.data.data?.exercises?.forEach(q => {
          initialAnswers[q.id] = null
        })
        setAnswers(initialAnswers)
      } else {
        message.error(res.data?.message || '加载练习题失败')
      }
    } catch (err) {
      console.error('获取练习题失败:', err)
      message.error('加载练习题失败')
    } finally {
      setLoading(false)
    }
  }
  
  const handleAnswerChange = (questionId, answer) => {
    setAnswers(prev => ({
      ...prev,
      [questionId]: answer
    }))
  }
  
  // 检查是否所有题目都已作答
  const allAnswered = exercises.length > 0 && exercises.every(q => answers[q.id] !== null)
  
  // 提交答案
  const handleSubmit = async () => {
    if (!allAnswered) {
      message.warning('请完成所有题目后再提交')
      return
    }
    
    setSubmitting(true)
    try {
      // 构建答题结果
      const answerList = exercises.map(q => ({
        question_id: q.id,
        user_answer: answers[q.id],
        is_correct: answers[q.id] === q.correct_answer
      }))
      
      const res = await practiceAPI.submitResults(goalId, {
        exercise_id: exerciseId,
        answers: answerList
      })
      
      if (res.data?.success) {
        setSubmitResult(res.data.data)
        setShowResult(true)
        // 提交成功后立即触发学情分析刷新
        window.dispatchEvent(new CustomEvent('refresh-analysis', { detail: { goalId } }))
      } else {
        message.error(res.data?.message || '提交失败')
      }
    } catch (err) {
      console.error('提交答案失败:', err)
      message.error('提交答案失败')
    } finally {
      setSubmitting(false)
    }
  }
  
  // 处理后续操作
  const handleNextAction = (action) => {
    // 触发学情分析刷新事件
    window.dispatchEvent(new CustomEvent('refresh-analysis', { detail: { goalId } }))

    switch (action) {
      case 'next':
        onNextSection?.()
        break
      case 'retry':
        // 重新开始练习
        setShowResult(false)
        setSubmitResult(null)
        setAnswers({})
        setCurrentIndex(0)
        fetchExercises()
        break
      case 'finish':
        onFinish?.()
        break
    }
  }
  
  if (loading) {
    return (
      <div style={{
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        padding: 60
      }}>
        <Spin size="large" />
        <div style={{ marginTop: 16, color: '#64748b' }}>正在加载练习题...</div>
      </div>
    )
  }
  
  if (exercises.length === 0) {
    return (
      <div style={{
        textAlign: 'center',
        padding: 40,
        background: '#fff',
        borderRadius: 16,
        border: '1px solid rgba(226,232,240,0.8)'
      }}>
        <div style={{ fontSize: 48, marginBottom: 16 }}>📚</div>
        <h3 style={{ color: '#374151', marginBottom: 8 }}>暂无练习题</h3>
        <p style={{ color: '#94a3b8' }}>
          该小节暂无可练习的知识点，请学习其他内容或联系管理员添加习题。
        </p>
        <Button type="primary" onClick={onComplete} style={{ marginTop: 16 }}>
          返回继续学习
        </Button>
      </div>
    )
  }
  
  // 显示诊断结果
  if (showResult && submitResult) {
    return (
      <DiagnosisResult 
        result={submitResult} 
        onNextAction={handleNextAction}
        lessonId={currentLessonId}
      />
    )
  }
  
  return (
    <div style={{
      width: '100%'
    }}>
      {/* 练习头部 */}
      <div style={{
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
        marginBottom: 12,
        padding: '12px 16px',
        background: 'linear-gradient(135deg, #6366f1, #8b5cf6)',
        borderRadius: 10,
        color: '#fff'
      }}>
        <div>
          <div style={{ fontSize: 11, opacity: 0.8 }}>练习巩固</div>
          <div style={{ fontSize: 14, fontWeight: 600 }}>{sectionTitle}</div>
        </div>
        <div style={{ textAlign: 'right' }}>
          <div style={{ fontSize: 11, opacity: 0.8 }}>进度</div>
          <div style={{ fontSize: 16, fontWeight: 700 }}>
            {Object.values(answers).filter(a => a !== null).length}/{exercises.length}
          </div>
        </div>
      </div>
      
      {/* 进度条 */}
      <Progress 
        percent={Math.round((Object.values(answers).filter(a => a !== null).length / exercises.length) * 100)}
        showInfo={false}
        strokeColor="#6366f1"
        trailColor="#f1f5f9"
        style={{ marginBottom: 14 }}
      />
      
      {/* 答题窗口 */}
      <div style={{
        background: '#fff',
        borderRadius: 12,
        padding: 14,
        border: '1px solid rgba(226,232,240,0.8)',
        boxShadow: '0 2px 12px rgba(99,102,241,0.06)',
        minHeight: 240,
        display: 'flex',
        flexDirection: 'column'
      }}>
        {/* 题目内容 */}
        {exercises[currentIndex] && (
          <SingleChoiceQuestion
            question={exercises[currentIndex]}
            index={currentIndex}
            selectedAnswer={answers[exercises[currentIndex].id]}
            onAnswerChange={(ans) => handleAnswerChange(exercises[currentIndex].id, ans)}
            showResult={showResult}
          />
        )}
        
        {/* 左右切换按钮 */}
        <div style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          marginTop: 14,
          paddingTop: 14,
          borderTop: '1px solid #f1f5f9'
        }}>
          <Button
            icon={<LeftOutlined />}
            onClick={() => setCurrentIndex(prev => Math.max(0, prev - 1))}
            disabled={currentIndex === 0}
            style={{ borderRadius: 8 }}
          >
            上一题
          </Button>
          
          {/* 题目指示器 */}
          <div style={{
            display: 'flex',
            gap: 6,
            alignItems: 'center'
          }}>
            {exercises.map((_, idx) => (
              <div
                key={idx}
                onClick={() => setCurrentIndex(idx)}
                style={{
                  width: answers[exercises[idx].id] !== null ? 10 : 8,
                  height: answers[exercises[idx].id] !== null ? 10 : 8,
                  borderRadius: '50%',
                  background: idx === currentIndex 
                    ? '#6366f1' 
                    : answers[exercises[idx].id] !== null 
                      ? '#52c41a' 
                      : '#e5e7eb',
                  cursor: 'pointer',
                  transition: 'all 0.2s',
                  transform: idx === currentIndex ? 'scale(1.2)' : 'scale(1)'
                }}
              />
            ))}
          </div>
          
          {currentIndex < exercises.length - 1 ? (
            <Button
              type="primary"
              onClick={() => setCurrentIndex(prev => prev + 1)}
              disabled={answers[exercises[currentIndex]?.id] === null}
              style={{ borderRadius: 8 }}
            >
              下一题
              <RightOutlined />
            </Button>
          ) : (
            <Button
              type="primary"
              onClick={handleSubmit}
              loading={submitting}
              disabled={!allAnswered}
              style={{ borderRadius: 8 }}
            >
              提交答案
            </Button>
          )}
        </div>
      </div>
      
      {/* 底部提示 */}
      <div style={{
        textAlign: 'center',
        marginTop: 10,
        fontSize: 11,
        color: '#94a3b8'
      }}>
        {answers[exercises[currentIndex]?.id] === null 
          ? '请选择答案后继续' 
          : currentIndex < exercises.length - 1 
            ? '点击"下一题"继续答题' 
            : '点击"提交答案"完成练习'}
      </div>
    </div>
  )
}

export default ExercisePractice

// ── 内联习题卡片：嵌入聊天消息中的紧凑版本 ──────────────────────────────────
export function InlineExerciseCard({ exerciseData, onComplete, onNextSection, onFinish }) {
  if (!exerciseData || !exerciseData.success) return null

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      style={{
        marginTop: 8,
        borderRadius: 10,
        border: '1px solid rgba(99,102,241,0.2)',
        overflow: 'hidden',
        boxShadow: '0 2px 8px rgba(99,102,241,0.06)'
      }}
    >
      <ExercisePractice
        goalId={exerciseData.goal_id}
        sectionId={exerciseData.section_id}
        sectionTitle={exerciseData.section_title}
        lessonId={exerciseData.lesson_id}
        exerciseData={exerciseData}
        onComplete={onComplete}
        onNextSection={onNextSection}
        onFinish={onFinish}
      />
    </motion.div>
  )
}
