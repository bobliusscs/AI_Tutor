import { useState, useEffect, useRef } from 'react'
import { Button, Tag, Space, Radio, Modal, Empty, Typography, Select, Popconfirm, Checkbox, Row, Col, Dropdown, Upload, Form, Input, Divider, Steps, Card, Alert, App } from 'antd'
import {
  CheckCircleOutlined,
  CloseCircleOutlined,
  PlayCircleOutlined,
  PlusOutlined,
  BookOutlined,
  FireOutlined,
  QuestionCircleOutlined,
  DeleteOutlined,
  NodeIndexOutlined,
  DownloadOutlined,
  FilterOutlined,
  RobotOutlined,
  UserOutlined,
  FileExcelOutlined,
  FileWordOutlined,
  FileTextOutlined,
  UploadOutlined,
  EditOutlined,
  FileSearchOutlined,
  SaveOutlined,
  LeftOutlined,
  RightOutlined,
  CheckOutlined,
  ThunderboltOutlined,
} from '@ant-design/icons'
import { useParams } from 'react-router-dom'
import { motion, AnimatePresence } from 'framer-motion'
import { questionAPI } from '../../utils/api'

const { Title, Text } = Typography
const { Option } = Select
const { TextArea } = Input
const { Step } = Steps

// 新难度配置：基础题/综合题/挑战题
const DIFFICULTY_CONFIG = {
  basic:        { label: '基础题', bg: 'rgba(16,185,129,0.1)',  color: '#10b981', border: 'rgba(16,185,129,0.3)', desc: '考察基本概念' },
  comprehensive: { label: '综合题', bg: 'rgba(245,158,11,0.1)',  color: '#f59e0b', border: 'rgba(245,158,11,0.3)', desc: '考察理解应用' },
  challenge:    { label: '挑战题', bg: 'rgba(244,63,94,0.1)',   color: '#f43f5e', border: 'rgba(244,63,94,0.3)', desc: '考察综合分析' },
  // 兼容旧数据
  easy:         { label: '基础题', bg: 'rgba(16,185,129,0.1)',  color: '#10b981', border: 'rgba(16,185,129,0.3)', desc: '考察基本概念' },
  medium:       { label: '综合题', bg: 'rgba(245,158,11,0.1)',  color: '#f59e0b', border: 'rgba(245,158,11,0.3)', desc: '考察理解应用' },
  hard:         { label: '挑战题', bg: 'rgba(244,63,94,0.1)',   color: '#f43f5e', border: 'rgba(244,63,94,0.3)', desc: '考察综合分析' },
}

const TYPE_CONFIG = {
  choice:       { label: '选择题', bg: 'rgba(99,102,241,0.1)',  color: '#6366f1' },
  fill_blank:   { label: '填空题', bg: 'rgba(139,92,246,0.1)',  color: '#8b5cf6' },
  short_answer: { label: '简答题', bg: 'rgba(245,158,11,0.1)',  color: '#f59e0b' },
}

// 题目来源配置
const SOURCE_CONFIG = {
  ai: { label: 'AI生成', icon: <RobotOutlined />, color: '#6366f1' },
  user: { label: '用户上传', icon: <UserOutlined />, color: '#8b5cf6' },
}

function Questions() {
  const { goalId } = useParams()
  const { message: messageApi } = App.useApp()
  const [questions, setQuestions] = useState([])
  const [loading, setLoading] = useState(true)
  const [isPracticeMode, setIsPracticeMode] = useState(false)
  const [currentIndex, setCurrentIndex] = useState(0)
  const [selectedAnswer, setSelectedAnswer] = useState(null)
  const [practiceResults, setPracticeResults] = useState([])
  const [showResult, setShowResult] = useState(false)
  const [submittedAnswer, setSubmittedAnswer] = useState(null)  // 当前题目提交后的信息

  // 个性化练习相关状态
  const [personalizedModalVisible, setPersonalizedModalVisible] = useState(false)
  const [personalizedCount, setPersonalizedCount] = useState(10)
  const [personalizedLoading, setPersonalizedLoading] = useState(false)
  const [personalizedExercises, setPersonalizedExercises] = useState(null)
  const [personalizedMode, setPersonalizedMode] = useState(false)  // 是否处于个性化练习模式
  const [personalizedExerciseId, setPersonalizedExerciseId] = useState(null)
  const [personalizedResults, setPersonalizedResults] = useState([])
  const [showPersonalizedResult, setShowPersonalizedResult] = useState(false)

  // 生成配置
  const [isGenerating, setIsGenerating] = useState(false)
  const [generateDifficulty, setGenerateDifficulty] = useState('basic')
  const [selectedNodeIds, setSelectedNodeIds] = useState([])  // 多选知识点
  const [generateCount, setGenerateCount] = useState(3)  // 每个知识点生成数量
  const [isBatchMode, setIsBatchMode] = useState(false)  // 批量模式
  
  // 进度弹窗相关状态
  const [showProgress, setShowProgress] = useState(false)
  const [progressInfo, setProgressInfo] = useState({
    status: '',        // starting | preparing | generating | completed | error | cancelled
    progress: 0,
    message: '',
    currentNode: '',
    currentIndex: 0,
    total: 0
  })
  const [elapsedTime, setElapsedTime] = useState(0)
  const timerRef = useRef(null)
  const abortControllerRef = useRef(null)
  
  // 筛选配置
  const [filterDifficulty, setFilterDifficulty] = useState(null)
  const [filterKnowledgePoints, setFilterKnowledgePoints] = useState([])
  const [filterSource, setFilterSource] = useState(null)  // null/all/ai/user
  const [showFilterPanel, setShowFilterPanel] = useState(false)
  
  const [knowledgePoints, setKnowledgePoints] = useState([])
  const [viewModalVisible, setViewModalVisible] = useState(false)
  const [viewingQuestion, setViewingQuestion] = useState(null)
  const [totalCount, setTotalCount] = useState(0)

  // ============ 习题上传相关状态 ============
  const [uploadModalVisible, setUploadModalVisible] = useState(false)
  const [uploadMode, setUploadMode] = useState('structured') // 'structured' | 'parse'
  const [structuredStep, setStructuredStep] = useState(0) // 0: 选择方式, 1: 填写题目, 2: 确认
  const [parseStep, setParseStep] = useState(0) // 0: 上传文件, 1: 预览解析结果, 2: 确认保存
  const [parsingFile, setParsingFile] = useState(false)
  const [parsedQuestions, setParsedQuestions] = useState([])
  const [currentQuestionIndex, setCurrentQuestionIndex] = useState(0)
  const [batchQuestions, setBatchQuestions] = useState([]) // 批量结构化上传的题目列表
  const [isUploading, setIsUploading] = useState(false)
  
  // 单题表单
  const [singleQuestionForm, setSingleQuestionForm] = useState({
    question_text: '',
    question_type: 'choice',
    difficulty: 'basic',
    knowledge_point_id: undefined,
    options: [
      { key: 'A', text: '' },
      { key: 'B', text: '' },
      { key: 'C', text: '' },
      { key: 'D', text: '' }
    ],
    correct_answer: 'A',
    explanation: ''
  })

  useEffect(() => { 
    fetchQuestions() 
    fetchKnowledgePoints()
  }, [goalId, filterDifficulty, filterKnowledgePoints, filterSource])
  
  // 计时器逻辑
  useEffect(() => {
    if (showProgress && progressInfo.status !== 'completed' && progressInfo.status !== 'error' && progressInfo.status !== 'cancelled') {
      timerRef.current = setInterval(() => {
        setElapsedTime(prev => prev + 1)
      }, 1000)
    } else {
      if (timerRef.current) {
        clearInterval(timerRef.current)
        timerRef.current = null
      }
    }
    return () => {
      if (timerRef.current) {
        clearInterval(timerRef.current)
        timerRef.current = null
      }
    }
  }, [showProgress, progressInfo.status])
  
  // 重置计时器
  useEffect(() => {
    if (showProgress && progressInfo.status === 'starting') {
      setElapsedTime(0)
    }
  }, [showProgress, progressInfo.status])

  const fetchQuestions = async () => {
    setLoading(true)
    try {
      const params = {
        limit: 100,
      }
      if (filterDifficulty) params.difficulty = filterDifficulty
      if (filterKnowledgePoints.length > 0) params.knowledge_point_ids = filterKnowledgePoints.join(',')
      if (filterSource !== null) params.is_ai_generated = filterSource === 'ai'
      
      const result = await questionAPI.list(goalId, params)
      if (result.data?.success) {
        setQuestions(result.data.data?.questions || [])
        setTotalCount(result.data.data?.total || 0)
      }
    } catch { 
      messageApi.error('获取习题失败') 
    }
    finally { setLoading(false) }
  }

  const fetchKnowledgePoints = async () => {
    try {
      const result = await questionAPI.getKnowledgePoints(goalId)
      if (result.data?.success) {
        setKnowledgePoints(result.data.data?.knowledge_points || [])
      }
    } catch (e) {
      console.log('获取知识点列表失败', e)
    }
  }

  const handleDeleteQuestion = async (questionId) => {
    try {
      const result = await questionAPI.delete(goalId, questionId)
      if (result.data?.success) {
        messageApi.success('题目删除成功')
        fetchQuestions()
      }
    } catch {
      messageApi.error('删除题目失败')
    }
  }

  const handleViewQuestion = (question) => {
    setViewingQuestion(question)
    setViewModalVisible(true)
  }

  // 格式化时间
  const formatTime = (seconds) => {
    const mins = Math.floor(seconds / 60)
    const secs = seconds % 60
    return `${mins}:${secs.toString().padStart(2, '0')}`
  }

  // 关闭进度弹窗
  const handleCloseProgress = () => {
    if (progressInfo.status === 'completed' || progressInfo.status === 'error' || progressInfo.status === 'cancelled') {
      setShowProgress(false)
      setElapsedTime(0)
      setIsGenerating(false)
    }
  }

  // 取消生成 - 立即更新状态，不等待后端响应
  const handleCancelGeneration = async () => {
    // 立即更新UI状态为已取消
    setProgressInfo({
      status: 'cancelled',
      progress: 0,
      message: '用户取消了生成',
      currentNode: '',
      currentIndex: 0,
      total: 0
    })
    setIsGenerating(false)

    // 通知后端停止生成（不等待响应）
    if (abortControllerRef.current) {
      abortControllerRef.current.abort()
    }
    try {
      await questionAPI.cancelGeneration()
    } catch (e) {
      // 忽略取消请求的错误，用户已经看到取消状态
    }
  }

  // 进度弹窗头部图标
  const renderProgressHeaderIcon = () => {
    const status = progressInfo.status
    if (status === 'completed') {
      return (
        <div style={{
          width: 80, height: 80, borderRadius: '50%', background: 'linear-gradient(135deg,#10b981,#06b6d4)',
          display: 'flex', alignItems: 'center', justifyContent: 'center', margin: '0 auto 24px',
          boxShadow: '0 8px 32px rgba(16,185,129,0.35)'
        }}>
          <CheckCircleOutlined style={{ fontSize: 40, color: '#fff' }} />
        </div>
      )
    }
    if (status === 'error') {
      return (
        <div style={{
          width: 80, height: 80, borderRadius: '50%', background: 'linear-gradient(135deg,#f43f5e,#ec4899)',
          display: 'flex', alignItems: 'center', justifyContent: 'center', margin: '0 auto 24px',
          boxShadow: '0 8px 32px rgba(244,63,94,0.35)'
        }}>
          <CloseCircleOutlined style={{ fontSize: 40, color: '#fff' }} />
        </div>
      )
    }
    if (status === 'cancelled') {
      return (
        <div style={{
          width: 80, height: 80, borderRadius: '50%', background: 'linear-gradient(135deg,#f59e0b,#fb923c)',
          display: 'flex', alignItems: 'center', justifyContent: 'center', margin: '0 auto 24px',
          boxShadow: '0 8px 32px rgba(245,158,11,0.35)'
        }}>
          <CloseCircleOutlined style={{ fontSize: 40, color: '#fff' }} />
        </div>
      )
    }
    return (
      <div style={{
        width: 80, height: 80, borderRadius: '50%', background: 'linear-gradient(135deg,#6366f1,#8b5cf6)',
        display: 'flex', alignItems: 'center', justifyContent: 'center', margin: '0 auto 24px',
        boxShadow: '0 8px 32px rgba(99,102,241,0.35)',
        animation: 'pulse 2s ease-in-out infinite'
      }}>
        <RobotOutlined style={{ fontSize: 36, color: '#fff' }} />
      </div>
    )
  }

  const handleGenerateQuestions = async () => {
    setIsGenerating(true)
    setShowProgress(true)
    setProgressInfo({
      status: 'starting',
      progress: 0,
      message: '正在准备生成任务...',
      currentNode: '',
      currentIndex: 0,
      total: 0
    })
    
    try {
      const params = { 
        count: generateCount, 
        difficulty: generateDifficulty,
        batch_mode: isBatchMode
      }
      
      if (selectedNodeIds.length > 0) {
        params.node_ids = selectedNodeIds
      }
      
      // 使用 SSE 流式接口
      const token = localStorage.getItem('token')
      const response = await fetch(`/api/questions/${goalId}/generate/stream`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': token ? `Bearer ${token}` : ''
        },
        body: JSON.stringify(params)
      })
      
      if (!response.ok) {
        throw new Error('Network response was not ok')
      }
      
      const reader = response.body.getReader()
      const decoder = new TextDecoder()
      
      while (true) {
        const { done, value } = await reader.read()
        if (done) break
        
        const chunk = decoder.decode(value, { stream: true })
        for (const line of chunk.split('\n')) {
          if (line.startsWith('data: ')) {
            try {
              const data = JSON.parse(line.slice(6))
              
              if (data.type === 'status' || data.type === 'progress') {
                setProgressInfo({
                  status: data.status,
                  progress: data.progress || 0,
                  message: data.message || '',
                  currentNode: data.current_node || '',
                  currentIndex: data.current_index || 0,
                  total: data.total || 0
                })
              } else if (data.type === 'question_complete') {
                // 单题生成完成，更新进度
                setProgressInfo({
                  status: 'generating',
                  progress: data.progress || 0,
                  message: `已生成 ${data.generated_count}/${data.total} 道题目`,
                  currentNode: data.question?.knowledge_point_name || '',
                  currentIndex: data.generated_count || 0,
                  total: data.total || 0
                })
              } else if (data.type === 'complete') {
                setProgressInfo({
                  status: 'completed',
                  progress: 100,
                  message: data.message,
                  currentNode: '',
                  currentIndex: data.generated_count || 0,
                  total: data.total || 0
                })
                setTimeout(() => {
                  messageApi.success(data.message)
                  fetchQuestions()
                }, 1500)
              } else if (data.type === 'error') {
                setProgressInfo({
                  status: 'error',
                  progress: 0,
                  message: data.message,
                  currentNode: '',
                  currentIndex: 0,
                  total: 0
                })
                messageApi.error(data.message)
              } else if (data.type === 'cancelled') {
                setProgressInfo({
                  status: 'cancelled',
                  progress: data.progress || 0,
                  message: data.message || '用户取消了生成',
                  currentNode: '',
                  currentIndex: 0,
                  total: 0
                })
              }
            } catch (e) {
              console.log('解析SSE数据失败:', e)
            }
          }
        }
      }
      
    } catch (err) {
      console.error('生成题目失败:', err)
      setProgressInfo({
        status: 'error',
        progress: 0,
        message: err.message || '生成失败，请稍后重试',
        currentNode: '',
        currentIndex: 0,
        total: 0
      })
      messageApi.error(err.message || '生成题目失败，请稍后重试')
    } finally {
      if (progressInfo.status !== 'completed' && progressInfo.status !== 'error' && progressInfo.status !== 'cancelled') {
        setIsGenerating(false)
      }
    }
  }

  const handleExport = async (format) => {
    try {
      const params = { format }
      if (filterDifficulty) params.difficulty = filterDifficulty
      if (filterKnowledgePoints.length > 0) params.knowledge_point_ids = filterKnowledgePoints.join(',')
      if (filterSource !== null) params.is_ai_generated = filterSource === 'ai'
      
      const result = await questionAPI.export(goalId, params)
      if (result.data?.success) {
        const data = result.data.data
        
        if (format === 'json') {
          // 下载JSON文件
          const blob = new Blob([JSON.stringify(data.questions, null, 2)], { type: 'application/json' })
          const url = URL.createObjectURL(blob)
          const a = document.createElement('a')
          a.href = url
          a.download = `习题库_${new Date().toISOString().split('T')[0]}.json`
          a.click()
          URL.revokeObjectURL(url)
        } else if (format === 'csv') {
          // 下载CSV文件
          const blob = new Blob(['\ufeff' + data.content], { type: 'text/csv;charset=utf-8;' })
          const url = URL.createObjectURL(blob)
          const a = document.createElement('a')
          a.href = url
          a.download = `习题库_${new Date().toISOString().split('T')[0]}.csv`
          a.click()
          URL.revokeObjectURL(url)
        } else if (format === 'word') {
          messageApi.info('Word格式导出功能开发中，请先使用JSON或CSV格式')
        }
        
        messageApi.success(`成功导出 ${data.count} 道题目`)
      }
    } catch (err) {
      messageApi.error(err.response?.data?.detail || '导出失败')
    }
  }

  const handleStartPractice = () => {
    if (questions.length === 0) { messageApi.info('暂无习题，请先生成题目'); return }
    setIsPracticeMode(true); setCurrentIndex(0); setPracticeResults([]); setShowResult(false); setSelectedAnswer(null); setSubmittedAnswer(null)
  }

  const handleSubmitAnswer = async () => {
    if (!selectedAnswer) { messageApi.warning('请选择答案'); return }
    const q = questions[currentIndex]
    try {
      const result = await questionAPI.submit(goalId, q.id, selectedAnswer)
      const answerData = result.data?.data  // 获取嵌套的 data 字段
      const isCorrect = answerData?.is_correct
      const newResults = [...practiceResults, { question: q, userAnswer: selectedAnswer, isCorrect, correctAnswer: answerData?.correct_answer }]
      setPracticeResults(newResults)
      // 设置提交后的答案信息（显示在题目下方）
      const explanation = answerData?.explanation
      setSubmittedAnswer({
        isCorrect,
        correctAnswer: answerData?.correct_answer,
        explanation: explanation && explanation.trim() ? explanation : '暂无解析',
        userAnswer: selectedAnswer
      })
    } catch { messageApi.error('提交答案失败') }
  }

  // 下一题
  const handleNextQuestion = () => {
    if (currentIndex < questions.length - 1) {
      setCurrentIndex(currentIndex + 1)
      setSelectedAnswer(null)
      setSubmittedAnswer(null)
    } else {
      setShowResult(true)
      setIsPracticeMode(false)
    }
  }

  // 返回（退出练习）
  const handleExitPractice = () => {
    setIsPracticeMode(false)
    setShowResult(false)
    setSubmittedAnswer(null)
    fetchQuestions()
  }

  // ============ 个性化练习相关函数 ============

  // 开始个性化练习
  const handleStartPersonalizedPractice = async () => {
    setPersonalizedLoading(true)
    try {
      const res = await questionAPI.getPersonalizedPractice(goalId, personalizedCount)
      if (res.data?.success && res.data.data?.exercises?.length > 0) {
        setPersonalizedExercises(res.data.data.exercises)
        setPersonalizedExerciseId(res.data.data.exercise_id)
        setPersonalizedMode(true)
        setPersonalizedModalVisible(false)
        setCurrentIndex(0)
        setSelectedAnswer(null)
        setSubmittedAnswer(null)
        setPersonalizedResults([])
        setShowPersonalizedResult(false)
        messageApi.success(`已为您推荐 ${res.data.data.exercises.length} 道个性化练习题`)
      } else {
        messageApi.warning('暂无可推荐的练习题，请先生成或上传习题')
      }
    } catch (err) {
      messageApi.error('获取推荐练习失败')
    } finally {
      setPersonalizedLoading(false)
    }
  }

  // 提交个性化练习答案
  const handleSubmitPersonalizedAnswer = async () => {
    if (!selectedAnswer) { messageApi.warning('请选择答案'); return }
    const q = personalizedExercises[currentIndex]
    try {
      const result = await questionAPI.submit(goalId, q.id, selectedAnswer)
      const answerData = result.data?.data
      const isCorrect = answerData?.is_correct
      const newResults = [...personalizedResults, { question: q, userAnswer: selectedAnswer, isCorrect, correctAnswer: answerData?.correct_answer }]
      setPersonalizedResults(newResults)
      const explanation = answerData?.explanation
      setSubmittedAnswer({
        isCorrect,
        correctAnswer: answerData?.correct_answer,
        explanation: explanation && explanation.trim() ? explanation : '暂无解析',
        userAnswer: selectedAnswer
      })
    } catch { messageApi.error('提交答案失败') }
  }

  // 个性化练习下一题
  const handleNextPersonalizedQuestion = () => {
    if (currentIndex < personalizedExercises.length - 1) {
      setCurrentIndex(currentIndex + 1)
      setSelectedAnswer(null)
      setSubmittedAnswer(null)
    } else {
      setShowPersonalizedResult(true)
      setPersonalizedMode(false)
    }
  }

  // 退出个性化练习
  const handleExitPersonalizedPractice = () => {
    setPersonalizedMode(false)
    setShowPersonalizedResult(false)
    setSubmittedAnswer(null)
    setPersonalizedExercises(null)
    setPersonalizedExerciseId(null)
    setPersonalizedResults([])
  }

  const clearFilters = () => {
    setFilterDifficulty(null)
    setFilterKnowledgePoints([])
    setFilterSource(null)
  }

  // ============ 习题上传相关函数 ============
  
  // 打开上传弹窗
  const handleOpenUpload = () => {
    setUploadModalVisible(true)
    setUploadMode('structured')
    setStructuredStep(0)
    setParseStep(0)
    setBatchQuestions([])
    setParsedQuestions([])
    resetSingleQuestionForm()
  }
  
  // 重置单题表单
  const resetSingleQuestionForm = () => {
    setSingleQuestionForm({
      question_text: '',
      question_type: 'choice',
      difficulty: 'basic',
      knowledge_point_id: undefined,
      options: [
        { key: 'A', text: '' },
        { key: 'B', text: '' },
        { key: 'C', text: '' },
        { key: 'D', text: '' }
      ],
      correct_answer: 'A',
      explanation: ''
    })
  }
  
  // 更新选项内容
  const handleOptionChange = (index, value) => {
    const newOptions = [...singleQuestionForm.options]
    newOptions[index].text = value
    setSingleQuestionForm({ ...singleQuestionForm, options: newOptions })
  }
  
  // 添加当前题目到批量列表
  const handleAddToBatch = () => {
    // 验证必填字段
    if (!singleQuestionForm.question_text.trim()) {
      messageApi.warning('请填写题干内容')
      return
    }
    if (singleQuestionForm.options.some(opt => !opt.text.trim())) {
      messageApi.warning('请填写所有选项内容')
      return
    }
    
    setBatchQuestions([...batchQuestions, { ...singleQuestionForm }])
    resetSingleQuestionForm()
    messageApi.success('题目已添加到批量列表')
  }
  
  // 从批量列表移除题目
  const handleRemoveFromBatch = (index) => {
    const newBatch = batchQuestions.filter((_, i) => i !== index)
    setBatchQuestions(newBatch)
  }
  
  // 提交批量上传
  const handleBatchUpload = async () => {
    if (batchQuestions.length === 0) {
      messageApi.warning('请先添加题目')
      return
    }
    
    setIsUploading(true)
    try {
      const data = {
        questions: batchQuestions.map(q => ({
          question_text: q.question_text,
          question_type: q.question_type,
          difficulty: q.difficulty,
          knowledge_point_id: q.knowledge_point_id,
          options: q.options,
          correct_answer: q.correct_answer,
          explanation: q.explanation
        }))
      }
      
      const result = await questionAPI.batchUpload(goalId, data)
      if (result.data?.success) {
        messageApi.success(`成功上传 ${result.data.data?.created_count || 0} 道题目`)
        setUploadModalVisible(false)
        setBatchQuestions([])
        fetchQuestions()
      } else {
        messageApi.error(result.data?.message || '上传失败')
      }
    } catch (err) {
      messageApi.error(err.response?.data?.detail || '上传失败')
    } finally {
      setIsUploading(false)
    }
  }
  
  // 提交单题上传
  const handleSingleUpload = async () => {
    // 验证必填字段
    if (!singleQuestionForm.question_text.trim()) {
      messageApi.warning('请填写题干内容')
      return
    }
    if (singleQuestionForm.options.some(opt => !opt.text.trim())) {
      messageApi.warning('请填写所有选项内容')
      return
    }
    
    setIsUploading(true)
    try {
      const data = {
        question_text: singleQuestionForm.question_text,
        question_type: singleQuestionForm.question_type,
        difficulty: singleQuestionForm.difficulty,
        knowledge_point_id: singleQuestionForm.knowledge_point_id,
        options: singleQuestionForm.options,
        correct_answer: singleQuestionForm.correct_answer,
        explanation: singleQuestionForm.explanation
      }
      
      const result = await questionAPI.upload(goalId, data)
      if (result.data?.success) {
        messageApi.success('题目上传成功')
        setUploadModalVisible(false)
        resetSingleQuestionForm()
        fetchQuestions()
      } else {
        messageApi.error(result.data?.message || '上传失败')
      }
    } catch (err) {
      messageApi.error(err.response?.data?.detail || '上传失败')
    } finally {
      setIsUploading(false)
    }
  }
  
  // 处理文件上传并解析
  const handleFileUpload = async (file) => {
    const allowedTypes = ['.txt', '.doc', '.docx', '.pdf']
    const fileExt = file.name.slice(file.name.lastIndexOf('.')).toLowerCase()
    
    if (!allowedTypes.includes(fileExt)) {
      messageApi.error(`不支持的文件类型：${fileExt}，仅支持 ${allowedTypes.join(', ')}`)
      return false
    }
    
    setParsingFile(true)
    try {
      const formData = new FormData()
      formData.append('file', file)
      
      const result = await questionAPI.parseFromFile(goalId, formData)
      if (result.data?.success) {
        const data = result.data.data
        setParsedQuestions(data.questions || [])
        setParseStep(1)
        messageApi.success(`成功解析 ${data.total_count} 道题目`)
      } else {
        messageApi.error(result.data?.message || '解析失败')
      }
    } catch (err) {
      messageApi.error(err.response?.data?.detail || '文件解析失败')
    } finally {
      setParsingFile(false)
    }
    return false // 阻止自动上传
  }
  
  // 确认保存解析的题目
  const handleConfirmParsed = async () => {
    if (parsedQuestions.length === 0) {
      messageApi.warning('没有可保存的题目')
      return
    }
    
    setIsUploading(true)
    try {
      const data = {
        questions: parsedQuestions,
        total_count: parsedQuestions.length,
        parsing_status: 'success'
      }
      
      const result = await questionAPI.confirmParsed(goalId, data)
      if (result.data?.success) {
        messageApi.success(`成功保存 ${result.data.data?.created_count || 0} 道题目`)
        setUploadModalVisible(false)
        setParsedQuestions([])
        setParseStep(0)
        fetchQuestions()
      } else {
        messageApi.error(result.data?.message || '保存失败')
      }
    } catch (err) {
      messageApi.error(err.response?.data?.detail || '保存失败')
    } finally {
      setIsUploading(false)
    }
  }
  
  // 更新解析后的题目
  const handleUpdateParsedQuestion = (index, field, value) => {
    const newQuestions = [...parsedQuestions]
    newQuestions[index] = { ...newQuestions[index], [field]: value }
    setParsedQuestions(newQuestions)
  }
  
  // 更新解析题目的选项
  const handleUpdateParsedOption = (qIndex, optIndex, value) => {
    const newQuestions = [...parsedQuestions]
    const options = [...newQuestions[qIndex].options]
    options[optIndex] = { ...options[optIndex], text: value }
    newQuestions[qIndex].options = options
    setParsedQuestions(newQuestions)
  }
  
  // 删除解析的题目
  const handleRemoveParsedQuestion = (index) => {
    const newQuestions = parsedQuestions.filter((_, i) => i !== index)
    setParsedQuestions(newQuestions)
    if (currentQuestionIndex >= newQuestions.length) {
      setCurrentQuestionIndex(Math.max(0, newQuestions.length - 1))
    }
  }

  // ── Personalized Practice Result screen ──
  if (showPersonalizedResult) {
    const correctCount = personalizedResults.filter(r => r.isCorrect).length
    const accuracy = Math.round((correctCount / personalizedResults.length) * 100)
    const grad = accuracy >= 80 ? 'linear-gradient(135deg,#10b981,#06b6d4)' : accuracy >= 60 ? 'linear-gradient(135deg,#f59e0b,#fb923c)' : 'linear-gradient(135deg,#f43f5e,#ec4899)'

    // 统计薄弱知识点
    const weakPoints = personalizedResults
      .filter(r => !r.isCorrect && r.question?.mastery_info)
      .map(r => r.question.mastery_info.node_name)
      .filter((name, idx, arr) => arr.indexOf(name) === idx)

    return (
      <motion.div initial={{ opacity: 0, scale: 0.97 }} animate={{ opacity: 1, scale: 1 }} style={{ maxWidth: 640, margin: '0 auto' }}>
        <div style={{ borderRadius: 24, padding: '40px', background: grad, textAlign: 'center', marginBottom: 24, boxShadow: '0 16px 48px rgba(139,92,246,0.25)', position: 'relative', overflow: 'hidden' }}>
          <div style={{ position: 'absolute', top: -40, right: -40, width: 180, height: 180, background: 'rgba(255,255,255,0.08)', borderRadius: '50%' }} />
          <div style={{ fontSize: 20, color: 'rgba(255,255,255,0.9)', marginBottom: 12, fontWeight: 600 }}>
            <ThunderboltOutlined style={{ marginRight: 8 }} />个性化练习完成
          </div>
          <div style={{ fontSize: 64, fontWeight: 900, color: '#fff', lineHeight: 1 }}>{accuracy}%</div>
          <div style={{ color: 'rgba(255,255,255,0.85)', fontSize: 18, marginTop: 8, fontWeight: 600 }}>
            {accuracy >= 80 ? '太棒了！' : accuracy >= 60 ? '继续加油！' : '还需努力！'}
          </div>
          <div style={{ color: 'rgba(255,255,255,0.7)', fontSize: 14, marginTop: 8 }}>
            {correctCount} 题正确 · {personalizedResults.length - correctCount} 题错误
          </div>
        </div>

        {weakPoints.length > 0 && (
          <div style={{ borderRadius: 20, padding: 24, background: '#fff', border: '1px solid rgba(226,232,240,0.8)', marginBottom: 20 }}>
            <h3 style={{ margin: '0 0 16px', fontSize: 16, fontWeight: 700, color: '#0f172a' }}>
              <ThunderboltOutlined style={{ color: '#8b5cf6', marginRight: 8 }} />需要加强的知识点
            </h3>
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8 }}>
              {weakPoints.map((name, i) => (
                <span key={i} style={{ padding: '6px 12px', borderRadius: 99, background: 'rgba(139,92,246,0.1)', color: '#8b5cf6', fontSize: 13, fontWeight: 600 }}>
                  {name}
                </span>
              ))}
            </div>
          </div>
        )}

        {personalizedResults.filter(r => !r.isCorrect).length > 0 && (
          <div style={{ borderRadius: 20, padding: 24, background: '#fff', border: '1px solid rgba(226,232,240,0.8)', marginBottom: 20 }}>
            <h3 style={{ margin: '0 0 16px', fontSize: 16, fontWeight: 700, color: '#0f172a' }}>错题回顾</h3>
            {personalizedResults.filter(r => !r.isCorrect).map((r, i) => (
              <div key={i} style={{ padding: '14px', borderRadius: 10, background: 'rgba(244,63,94,0.04)', border: '1px solid rgba(244,63,94,0.15)', marginBottom: 10 }}>
                <div style={{ fontWeight: 600, color: '#0f172a', marginBottom: 8 }}>{r.question.question_text}</div>
                <div style={{ fontSize: 13, color: '#f43f5e' }}>你的答案: {r.userAnswer}</div>
                <div style={{ fontSize: 13, color: '#10b981' }}>正确答案: {r.correctAnswer}</div>
              </div>
            ))}
          </div>
        )}
        <button onClick={handleExitPersonalizedPractice}
          style={{ width: '100%', padding: '14px', borderRadius: 12, border: 'none', background: grad, color: '#fff', fontSize: 15, fontWeight: 700, cursor: 'pointer', boxShadow: '0 6px 20px rgba(139,92,246,0.35)' }}>
          返回习题库
        </button>
      </motion.div>
    )
  }

  // ── Result screen ──
  if (showResult) {
    const correctCount = practiceResults.filter(r => r.isCorrect).length
    const accuracy = Math.round((correctCount / practiceResults.length) * 100)
    const grad = accuracy >= 80 ? 'linear-gradient(135deg,#10b981,#06b6d4)' : accuracy >= 60 ? 'linear-gradient(135deg,#f59e0b,#fb923c)' : 'linear-gradient(135deg,#f43f5e,#ec4899)'
    return (
      <motion.div initial={{ opacity: 0, scale: 0.97 }} animate={{ opacity: 1, scale: 1 }} style={{ maxWidth: 640, margin: '0 auto' }}>
        <div style={{ borderRadius: 24, padding: '40px', background: grad, textAlign: 'center', marginBottom: 24, boxShadow: '0 16px 48px rgba(99,102,241,0.25)', position: 'relative', overflow: 'hidden' }}>
          <div style={{ position: 'absolute', top: -40, right: -40, width: 180, height: 180, background: 'rgba(255,255,255,0.08)', borderRadius: '50%' }} />
          <div style={{ fontSize: 64, fontWeight: 900, color: '#fff', lineHeight: 1 }}>{accuracy}%</div>
          <div style={{ color: 'rgba(255,255,255,0.85)', fontSize: 18, marginTop: 8, fontWeight: 600 }}>
            {accuracy >= 80 ? '太棒了！' : accuracy >= 60 ? '继续加油！' : '还需努力！'}
          </div>
          <div style={{ color: 'rgba(255,255,255,0.7)', fontSize: 14, marginTop: 8 }}>
            {correctCount} 题正确 · {practiceResults.length - correctCount} 题错误
          </div>
        </div>
        {practiceResults.filter(r => !r.isCorrect).length > 0 && (
          <div style={{ borderRadius: 20, padding: 24, background: '#fff', border: '1px solid rgba(226,232,240,0.8)', marginBottom: 20 }}>
            <h3 style={{ margin: '0 0 16px', fontSize: 16, fontWeight: 700, color: '#0f172a' }}>错题回顾</h3>
            {practiceResults.filter(r => !r.isCorrect).map((r, i) => (
              <div key={i} style={{ padding: '14px', borderRadius: 10, background: 'rgba(244,63,94,0.04)', border: '1px solid rgba(244,63,94,0.15)', marginBottom: 10 }}>
                <div style={{ fontWeight: 600, color: '#0f172a', marginBottom: 8 }}>{r.question.question_text}</div>
                <div style={{ fontSize: 13, color: '#f43f5e' }}>你的答案: {r.userAnswer}</div>
                <div style={{ fontSize: 13, color: '#10b981' }}>正确答案: {r.correctAnswer}</div>
              </div>
            ))}
          </div>
        )}
        <button onClick={() => setShowResult(false)}
          style={{ width: '100%', padding: '14px', borderRadius: 12, border: 'none', background: grad, color: '#fff', fontSize: 15, fontWeight: 700, cursor: 'pointer', boxShadow: '0 6px 20px rgba(99,102,241,0.35)' }}>
          返回习题库
        </button>
      </motion.div>
    )
  }

  // ── Personalized Practice mode ──
  if (personalizedMode) {
    const currentQuestion = personalizedExercises[currentIndex]
    const progress = ((currentIndex + 1) / personalizedExercises.length) * 100
    const dc = DIFFICULTY_CONFIG[currentQuestion?.difficulty] || DIFFICULTY_CONFIG.basic
    const tc = TYPE_CONFIG[currentQuestion?.question_type] || TYPE_CONFIG.choice

    // 获取掌握信息
    const masteryInfo = currentQuestion?.mastery_info

    return (
      <motion.div initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }} style={{ maxWidth: 640, margin: '0 auto' }}>
        {/* 返回按钮 */}
        <button onClick={handleExitPersonalizedPractice}
          style={{ marginBottom: 16, padding: '8px 16px', borderRadius: 8, border: '1px solid #e2e8f0', background: '#fff', color: '#64748b', fontSize: 13, cursor: 'pointer', display: 'flex', alignItems: 'center', gap: 6 }}>
          ← 返回习题列表
        </button>

        <div style={{ marginBottom: 24 }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 8 }}>
            <span style={{ fontSize: 13, color: '#94a3b8' }}>个性化练习进度</span>
            <span style={{ fontSize: 13, fontWeight: 700, color: '#8b5cf6' }}>{currentIndex + 1} / {personalizedExercises.length}</span>
          </div>
          <div style={{ height: 6, background: '#f1f5f9', borderRadius: 3, overflow: 'hidden' }}>
            <div style={{ width: `${progress}%`, height: '100%', background: 'linear-gradient(90deg,#8b5cf6,#6366f1)', borderRadius: 3, transition: 'width 0.4s ease' }} />
          </div>
        </div>

        {/* 掌握信息卡片 */}
        {masteryInfo && (
          <div style={{
            marginBottom: 16,
            padding: '12px 16px',
            borderRadius: 12,
            background: 'linear-gradient(135deg, rgba(139,92,246,0.08), rgba(99,102,241,0.08))',
            border: '1px solid rgba(139,92,246,0.2)',
            display: 'flex',
            alignItems: 'center',
            gap: 12
          }}>
            <ThunderboltOutlined style={{ fontSize: 18, color: '#8b5cf6' }} />
            <div style={{ flex: 1 }}>
              <div style={{ fontSize: 13, fontWeight: 600, color: '#0f172a' }}>
                {masteryInfo.node_name}
              </div>
              <div style={{ fontSize: 12, color: '#64748b', marginTop: 2 }}>
                掌握度: {masteryInfo.mastery_level?.toFixed(1) || 0}% · 正确率: {masteryInfo.correct_rate?.toFixed(1) || 0}%
              </div>
            </div>
            <div style={{
              padding: '4px 10px',
              borderRadius: 99,
              background: masteryInfo.mastery_level < 60 ? 'rgba(244,63,94,0.1)' : masteryInfo.mastery_level < 80 ? 'rgba(245,158,11,0.1)' : 'rgba(16,185,129,0.1)',
              color: masteryInfo.mastery_level < 60 ? '#f43f5e' : masteryInfo.mastery_level < 80 ? '#f59e0b' : '#10b981',
              fontSize: 12,
              fontWeight: 600
            }}>
              {masteryInfo.mastery_level < 60 ? '薄弱' : masteryInfo.mastery_level < 80 ? '一般' : '良好'}
            </div>
          </div>
        )}

        <div style={{ borderRadius: 20, padding: 32, background: '#fff', border: '1px solid rgba(226,232,240,0.8)', boxShadow: '0 8px 32px rgba(139,92,246,0.08)' }}>
          <div style={{ display: 'flex', gap: 8, marginBottom: 20 }}>
            <span style={{ padding: '3px 12px', borderRadius: 99, background: dc.bg, color: dc.color, fontSize: 12, fontWeight: 700 }}>{dc.label}</span>
            <span style={{ padding: '3px 12px', borderRadius: 99, background: tc.bg, color: tc.color, fontSize: 12, fontWeight: 700 }}>{tc.label}</span>
          </div>
          <h3 style={{ fontSize: 17, fontWeight: 700, color: '#0f172a', marginBottom: 28, lineHeight: 1.5 }}>{currentQuestion?.question_text}</h3>
          {currentQuestion?.options && (
            <Radio.Group value={selectedAnswer} onChange={e => setSelectedAnswer(e.target.value)} style={{ width: '100%' }} disabled={!!submittedAnswer}>
              <Space direction="vertical" style={{ width: '100%', gap: 10 }}>
                {currentQuestion.options.map((opt, i) => {
                  const letter = String.fromCharCode(65 + i)
                  const isThisCorrect = letter === submittedAnswer?.correctAnswer
                  const isThisSelected = letter === selectedAnswer
                  let bgColor = 'rgba(99,102,241,0.03)'
                  let borderColor = 'rgba(99,102,241,0.15)'

                  if (submittedAnswer) {
                    if (isThisCorrect) {
                      bgColor = 'rgba(16,185,129,0.1)'
                      borderColor = '#10b981'
                    } else if (isThisSelected && !isThisCorrect) {
                      bgColor = 'rgba(244,63,94,0.1)'
                      borderColor = '#f43f5e'
                    }
                  }

                  return (
                    <Radio.Button key={i} value={letter}
                      style={{ width: '100%', height: 'auto', padding: '12px 16px', textAlign: 'left', lineHeight: 1.5, borderRadius: 10, transition: 'all 0.2s', background: bgColor, borderColor: borderColor }}>
                      <span style={{ fontWeight: 600, marginRight: 8, color: submittedAnswer ? (isThisCorrect ? '#10b981' : '#64748b') : '#6366f1' }}>{letter}.</span>{opt}
                    </Radio.Button>
                  )
                })}
              </Space>
            </Radio.Group>
          )}

          {/* 答案和解析显示区域 */}
          {submittedAnswer && (
            <div style={{ marginTop: 24, padding: 20, borderRadius: 12, background: submittedAnswer.isCorrect ? 'rgba(16,185,129,0.08)' : 'rgba(244,63,94,0.08)', border: `1px solid ${submittedAnswer.isCorrect ? 'rgba(16,185,129,0.2)' : 'rgba(244,63,94,0.2)'}` }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 12 }}>
                {submittedAnswer.isCorrect ? (
                  <span style={{ fontSize: 18 }}>✅</span>
                ) : (
                  <span style={{ fontSize: 18 }}>❌</span>
                )}
                <span style={{ fontSize: 16, fontWeight: 700, color: submittedAnswer.isCorrect ? '#10b981' : '#f43f5e' }}>
                  {submittedAnswer.isCorrect ? '回答正确！' : '回答错误'}
                </span>
              </div>
              {!submittedAnswer.isCorrect && (
                <div style={{ fontSize: 14, color: '#64748b', marginBottom: 12 }}>
                  <strong>你的答案：</strong>{submittedAnswer.userAnswer} &nbsp;&nbsp;
                  <strong>正确答案：</strong><span style={{ color: '#10b981', fontWeight: 600 }}>{submittedAnswer.correctAnswer}</span>
                </div>
              )}
              <div style={{ fontSize: 14, color: '#475569', lineHeight: 1.6 }}>
                <strong>解析：</strong>{submittedAnswer.explanation}
              </div>
            </div>
          )}

          {/* 按钮区域 */}
          <div style={{ marginTop: 28, display: 'flex', gap: 12 }}>
            {!submittedAnswer ? (
              <button onClick={handleSubmitPersonalizedAnswer} disabled={!selectedAnswer}
                style={{ flex: 1, padding: '14px', borderRadius: 12, border: 'none', background: selectedAnswer ? 'linear-gradient(135deg,#8b5cf6,#6366f1)' : '#e2e8f0', color: '#fff', fontSize: 15, fontWeight: 700, cursor: selectedAnswer ? 'pointer' : 'not-allowed', boxShadow: selectedAnswer ? '0 6px 20px rgba(139,92,246,0.38)' : 'none', transition: 'all 0.2s' }}>
                提交答案
              </button>
            ) : (
              <button onClick={handleNextPersonalizedQuestion}
                style={{ flex: 1, padding: '14px', borderRadius: 12, border: 'none', background: 'linear-gradient(135deg,#8b5cf6,#6366f1)', color: '#fff', fontSize: 15, fontWeight: 700, cursor: 'pointer', boxShadow: '0 6px 20px rgba(139,92,246,0.38)', transition: 'all 0.2s' }}>
                {currentIndex < personalizedExercises.length - 1 ? '下一题 →' : '查看结果'}
              </button>
            )}
          </div>
        </div>
      </motion.div>
    )
  }

  // ── Practice mode ──
  if (isPracticeMode) {
    const currentQuestion = questions[currentIndex]
    const progress = ((currentIndex + 1) / questions.length) * 100
    const dc = DIFFICULTY_CONFIG[currentQuestion?.difficulty] || DIFFICULTY_CONFIG.basic
    const tc = TYPE_CONFIG[currentQuestion?.question_type] || TYPE_CONFIG.choice
    return (
      <motion.div initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }} style={{ maxWidth: 640, margin: '0 auto' }}>
        {/* 返回按钮 */}
        <button onClick={handleExitPractice}
          style={{ marginBottom: 16, padding: '8px 16px', borderRadius: 8, border: '1px solid #e2e8f0', background: '#fff', color: '#64748b', fontSize: 13, cursor: 'pointer', display: 'flex', alignItems: 'center', gap: 6 }}>
          ← 返回习题列表
        </button>

        <div style={{ marginBottom: 24 }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 8 }}>
            <span style={{ fontSize: 13, color: '#94a3b8' }}>练习进度</span>
            <span style={{ fontSize: 13, fontWeight: 700, color: '#6366f1' }}>{currentIndex + 1} / {questions.length}</span>
          </div>
          <div style={{ height: 6, background: '#f1f5f9', borderRadius: 3, overflow: 'hidden' }}>
            <div style={{ width: `${progress}%`, height: '100%', background: 'linear-gradient(90deg,#6366f1,#8b5cf6)', borderRadius: 3, transition: 'width 0.4s ease' }} />
          </div>
        </div>
        <div style={{ borderRadius: 20, padding: 32, background: '#fff', border: '1px solid rgba(226,232,240,0.8)', boxShadow: '0 8px 32px rgba(99,102,241,0.08)' }}>
          <div style={{ display: 'flex', gap: 8, marginBottom: 20 }}>
            <span style={{ padding: '3px 12px', borderRadius: 99, background: dc.bg, color: dc.color, fontSize: 12, fontWeight: 700 }}>{dc.label}</span>
            <span style={{ padding: '3px 12px', borderRadius: 99, background: tc.bg, color: tc.color, fontSize: 12, fontWeight: 700 }}>{tc.label}</span>
          </div>
          <h3 style={{ fontSize: 17, fontWeight: 700, color: '#0f172a', marginBottom: 28, lineHeight: 1.5 }}>{currentQuestion?.question_text}</h3>
          {currentQuestion?.options && (
            <Radio.Group value={selectedAnswer} onChange={e => setSelectedAnswer(e.target.value)} style={{ width: '100%' }} disabled={!!submittedAnswer}>
              <Space direction="vertical" style={{ width: '100%', gap: 10 }}>
                {currentQuestion.options.map((opt, i) => {
                  const letter = String.fromCharCode(65 + i)
                  const isThisCorrect = letter === submittedAnswer?.correctAnswer
                  const isThisSelected = letter === selectedAnswer
                  let bgColor = 'rgba(99,102,241,0.03)'
                  let borderColor = 'rgba(99,102,241,0.15)'

                  if (submittedAnswer) {
                    if (isThisCorrect) {
                      bgColor = 'rgba(16,185,129,0.1)'
                      borderColor = '#10b981'
                    } else if (isThisSelected && !isThisCorrect) {
                      bgColor = 'rgba(244,63,94,0.1)'
                      borderColor = '#f43f5e'
                    }
                  }

                  return (
                    <Radio.Button key={i} value={letter}
                      style={{ width: '100%', height: 'auto', padding: '12px 16px', textAlign: 'left', lineHeight: 1.5, borderRadius: 10, transition: 'all 0.2s', background: bgColor, borderColor: borderColor }}>
                      <span style={{ fontWeight: 600, marginRight: 8, color: submittedAnswer ? (isThisCorrect ? '#10b981' : '#64748b') : '#6366f1' }}>{letter}.</span>{opt}
                    </Radio.Button>
                  )
                })}
              </Space>
            </Radio.Group>
          )}

          {/* 答案和解析显示区域 */}
          {submittedAnswer && (
            <div style={{ marginTop: 24, padding: 20, borderRadius: 12, background: submittedAnswer.isCorrect ? 'rgba(16,185,129,0.08)' : 'rgba(244,63,94,0.08)', border: `1px solid ${submittedAnswer.isCorrect ? 'rgba(16,185,129,0.2)' : 'rgba(244,63,94,0.2)'}` }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 12 }}>
                {submittedAnswer.isCorrect ? (
                  <span style={{ fontSize: 18 }}>✅</span>
                ) : (
                  <span style={{ fontSize: 18 }}>❌</span>
                )}
                <span style={{ fontSize: 16, fontWeight: 700, color: submittedAnswer.isCorrect ? '#10b981' : '#f43f5e' }}>
                  {submittedAnswer.isCorrect ? '回答正确！' : '回答错误'}
                </span>
              </div>
              {!submittedAnswer.isCorrect && (
                <div style={{ fontSize: 14, color: '#64748b', marginBottom: 12 }}>
                  <strong>你的答案：</strong>{submittedAnswer.userAnswer} &nbsp;&nbsp;
                  <strong>正确答案：</strong><span style={{ color: '#10b981', fontWeight: 600 }}>{submittedAnswer.correctAnswer}</span>
                </div>
              )}
              <div style={{ fontSize: 14, color: '#475569', lineHeight: 1.6 }}>
                <strong>解析：</strong>{submittedAnswer.explanation}
              </div>
            </div>
          )}

          {/* 按钮区域 */}
          <div style={{ marginTop: 28, display: 'flex', gap: 12 }}>
            {!submittedAnswer ? (
              <button onClick={handleSubmitAnswer} disabled={!selectedAnswer}
                style={{ flex: 1, padding: '14px', borderRadius: 12, border: 'none', background: selectedAnswer ? 'linear-gradient(135deg,#6366f1,#8b5cf6)' : '#e2e8f0', color: '#fff', fontSize: 15, fontWeight: 700, cursor: selectedAnswer ? 'pointer' : 'not-allowed', boxShadow: selectedAnswer ? '0 6px 20px rgba(99,102,241,0.38)' : 'none', transition: 'all 0.2s' }}>
                提交答案
              </button>
            ) : (
              <button onClick={handleNextQuestion}
                style={{ flex: 1, padding: '14px', borderRadius: 12, border: 'none', background: 'linear-gradient(135deg,#6366f1,#8b5cf6)', color: '#fff', fontSize: 15, fontWeight: 700, cursor: 'pointer', boxShadow: '0 6px 20px rgba(99,102,241,0.38)', transition: 'all 0.2s' }}>
                {currentIndex < questions.length - 1 ? '下一题 →' : '查看结果'}
              </button>
            )}
          </div>
        </div>
      </motion.div>
    )
  }

  // ── Question list ──
  return (
    <App>
      <motion.div initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.4 }}>
        {/* 头部区域 */}
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 20 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
            <div style={{ width: 40, height: 40, borderRadius: 10, background: 'linear-gradient(135deg,#ec4899,#6366f1)', display: 'flex', alignItems: 'center', justifyContent: 'center', boxShadow: '0 4px 12px rgba(236,72,153,0.35)' }}>
              <QuestionCircleOutlined style={{ color: '#fff', fontSize: 18 }} />
            </div>
            <div>
              <h2 style={{ margin: 0, fontSize: 20, fontWeight: 800, color: '#0f172a' }}>习题库</h2>
              <div style={{ fontSize: 13, color: '#94a3b8' }}>{totalCount} 道题目</div>
            </div>
          </div>
          <div style={{ display: 'flex', gap: 10 }}>
          <button onClick={() => setShowFilterPanel(!showFilterPanel)}
            style={{ display: 'flex', alignItems: 'center', gap: 7, padding: '9px 18px', borderRadius: 9, border: '1.5px solid rgba(99,102,241,0.3)', background: showFilterPanel ? 'rgba(99,102,241,0.1)' : '#fff', color: '#6366f1', fontSize: 13.5, fontWeight: 600, cursor: 'pointer' }}>
            <FilterOutlined /> 筛选
          </button>
          <button onClick={handleOpenUpload}
            style={{ display: 'flex', alignItems: 'center', gap: 7, padding: '9px 18px', borderRadius: 9, border: '1.5px solid rgba(139,92,246,0.3)', background: '#fff', color: '#8b5cf6', fontSize: 13.5, fontWeight: 600, cursor: 'pointer' }}>
            <UploadOutlined /> 上传习题
          </button>
          <Dropdown menu={{
            items: [
              { key: 'json', icon: <FileTextOutlined />, label: '导出 JSON', onClick: () => handleExport('json') },
              { key: 'csv', icon: <FileExcelOutlined />, label: '导出 CSV', onClick: () => handleExport('csv') },
              { key: 'word', icon: <FileWordOutlined />, label: '导出 Word', onClick: () => handleExport('word') },
            ]
          }}>
            <button style={{ display: 'flex', alignItems: 'center', gap: 7, padding: '9px 18px', borderRadius: 9, border: '1.5px solid rgba(16,185,129,0.3)', background: '#fff', color: '#10b981', fontSize: 13.5, fontWeight: 600, cursor: 'pointer' }}>
              <DownloadOutlined /> 导出
            </button>
          </Dropdown>
          <button onClick={() => setPersonalizedModalVisible(true)}
            style={{ display: 'flex', alignItems: 'center', gap: 7, padding: '9px 18px', borderRadius: 9, border: 'none', background: 'linear-gradient(135deg,#8b5cf6,#6366f1)', color: '#fff', fontSize: 13.5, fontWeight: 700, cursor: 'pointer', boxShadow: '0 4px 14px rgba(139,92,246,0.38)' }}>
            <ThunderboltOutlined /> 个性化练习
          </button>
          <button onClick={handleStartPractice} disabled={questions.length === 0}
            style={{ display: 'flex', alignItems: 'center', gap: 7, padding: '9px 18px', borderRadius: 9, border: 'none', background: questions.length > 0 ? 'linear-gradient(135deg,#6366f1,#8b5cf6)' : '#f1f5f9', color: questions.length > 0 ? '#fff' : '#94a3b8', fontSize: 13.5, fontWeight: 700, cursor: questions.length > 0 ? 'pointer' : 'not-allowed', boxShadow: questions.length > 0 ? '0 4px 14px rgba(99,102,241,0.38)' : 'none' }}>
            <PlayCircleOutlined /> 开始练习
          </button>
        </div>
      </div>

      {/* 筛选面板 */}
      {showFilterPanel && (
        <div style={{ 
          marginBottom: 20, 
          padding: '16px 20px', 
          background: '#fff', 
          borderRadius: 12, 
          border: '1px solid rgba(226,232,240,0.8)',
          boxShadow: '0 2px 8px rgba(99,102,241,0.04)'
        }}>
          <div style={{ display: 'flex', gap: 16, flexWrap: 'wrap', alignItems: 'center' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
              <span style={{ fontSize: 13, color: '#64748b', fontWeight: 500 }}>难度:</span>
              <Select 
                value={filterDifficulty} 
                onChange={setFilterDifficulty}
                style={{ width: 120 }}
                size="small"
                allowClear
                placeholder="全部难度"
              >
                <Option value="basic"><span style={{ color: '#10b981', fontWeight: 600 }}>基础题</span></Option>
                <Option value="comprehensive"><span style={{ color: '#f59e0b', fontWeight: 600 }}>综合题</span></Option>
                <Option value="challenge"><span style={{ color: '#f43f5e', fontWeight: 600 }}>挑战题</span></Option>
              </Select>
            </div>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
              <span style={{ fontSize: 13, color: '#64748b', fontWeight: 500 }}>知识点:</span>
              <Select 
                mode="multiple"
                value={filterKnowledgePoints} 
                onChange={setFilterKnowledgePoints}
                style={{ width: 240 }}
                size="small"
                placeholder="选择知识点"
                maxTagCount={2}
              >
                {knowledgePoints.map(kp => (
                  <Option key={kp.id} value={kp.id}>{kp.name}</Option>
                ))}
              </Select>
            </div>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
              <span style={{ fontSize: 13, color: '#64748b', fontWeight: 500 }}>来源:</span>
              <Select 
                value={filterSource} 
                onChange={setFilterSource}
                style={{ width: 120 }}
                size="small"
                allowClear
                placeholder="全部来源"
              >
                <Option value="ai"><RobotOutlined style={{ color: '#6366f1' }} /> AI生成</Option>
                <Option value="user"><UserOutlined style={{ color: '#8b5cf6' }} /> 用户上传</Option>
              </Select>
            </div>
            <button onClick={clearFilters}
              style={{ padding: '6px 14px', borderRadius: 6, border: '1px solid #e2e8f0', background: '#f8fafc', color: '#64748b', fontSize: 12.5, fontWeight: 500, cursor: 'pointer' }}>
              清除筛选
            </button>
          </div>
        </div>
      )}

      {/* 生成配置区域 */}
      <div style={{ 
        marginBottom: 20, 
        padding: '16px 20px', 
        background: 'linear-gradient(135deg, rgba(99,102,241,0.05), rgba(139,92,246,0.05))', 
        borderRadius: 12, 
        border: '1px solid rgba(99,102,241,0.15)',
      }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 }}>
          <span style={{ fontSize: 14, fontWeight: 700, color: '#0f172a' }}>AI生成习题</span>
          <Checkbox checked={isBatchMode} onChange={e => setIsBatchMode(e.target.checked)}>
            <span style={{ fontSize: 12, color: '#64748b' }}>批量模式（为每个知识点生成{generateCount}道题）</span>
          </Checkbox>
        </div>
        <div style={{ display: 'flex', gap: 16, flexWrap: 'wrap', alignItems: 'center' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            <span style={{ fontSize: 13, color: '#64748b', fontWeight: 500 }}>难度:</span>
            <Select 
              value={generateDifficulty} 
              onChange={setGenerateDifficulty}
              style={{ width: 120 }}
              size="small"
            >
              <Option value="basic">
                <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                  <span style={{ width: 8, height: 8, borderRadius: '50%', background: '#10b981' }}></span>
                  <span style={{ color: '#10b981', fontWeight: 600 }}>基础题</span>
                </div>
              </Option>
              <Option value="comprehensive">
                <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                  <span style={{ width: 8, height: 8, borderRadius: '50%', background: '#f59e0b' }}></span>
                  <span style={{ color: '#f59e0b', fontWeight: 600 }}>综合题</span>
                </div>
              </Option>
              <Option value="challenge">
                <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                  <span style={{ width: 8, height: 8, borderRadius: '50%', background: '#f43f5e' }}></span>
                  <span style={{ color: '#f43f5e', fontWeight: 600 }}>挑战题</span>
                </div>
              </Option>
            </Select>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8, flex: 1 }}>
            <span style={{ fontSize: 13, color: '#64748b', fontWeight: 500 }}>知识点:</span>
            <Select 
              mode="multiple"
              value={selectedNodeIds} 
              onChange={setSelectedNodeIds}
              style={{ width: 280 }}
              size="small"
              placeholder="选择知识点（可多选，不选则随机）"
              maxTagCount={2}
            >
              {knowledgePoints.map(kp => (
                <Option key={kp.id} value={kp.id}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                    <NodeIndexOutlined style={{ fontSize: 12, color: '#6366f1' }} />
                    <span>{kp.name}</span>
                  </div>
                </Option>
              ))}
            </Select>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            <span style={{ fontSize: 13, color: '#64748b', fontWeight: 500 }}>每知识点:</span>
            <Select 
              value={generateCount} 
              onChange={setGenerateCount}
              style={{ width: 70 }}
              size="small"
            >
              <Option value={1}>1道</Option>
              <Option value={2}>2道</Option>
              <Option value={3}>3道</Option>
              <Option value={5}>5道</Option>
            </Select>
          </div>
          <button onClick={handleGenerateQuestions} disabled={isGenerating}
            style={{ display: 'flex', alignItems: 'center', gap: 7, padding: '8px 16px', borderRadius: 8, border: 'none', background: isGenerating ? '#e2e8f0' : 'linear-gradient(135deg,#6366f1,#8b5cf6)', color: isGenerating ? '#94a3b8' : '#fff', fontSize: 13, fontWeight: 700, cursor: isGenerating ? 'not-allowed' : 'pointer', opacity: isGenerating ? 0.7 : 1 }}>
            <PlusOutlined /> {isGenerating ? '生成中...' : '生成习题'}
          </button>
        </div>
      </div>

      {/* 题目列表 */}
      <div style={{ borderRadius: 20, background: '#fff', border: '1px solid rgba(226,232,240,0.8)', boxShadow: '0 4px 20px rgba(99,102,241,0.06)', overflow: 'hidden' }}>
        {questions.length === 0 ? (
          <div style={{ padding: 48 }}>
            <Empty description="暂无习题，请使用上方配置生成">
              <div style={{ fontSize: 13, color: '#94a3b8', marginTop: 8 }}>
                可选择知识点和难度后点击"生成习题"
              </div>
            </Empty>
          </div>
        ) : (
          <div style={{ padding: '8px 0' }}>
            {questions.map((item, idx) => {
              const dc = DIFFICULTY_CONFIG[item.difficulty] || DIFFICULTY_CONFIG.basic
              const tc = TYPE_CONFIG[item.question_type] || TYPE_CONFIG.choice
              const source = item.is_ai_generated !== false ? SOURCE_CONFIG.ai : SOURCE_CONFIG.user
              return (
                <motion.div key={item.id} initial={{ opacity: 0, x: -12 }} animate={{ opacity: 1, x: 0 }} transition={{ delay: idx * 0.04 }}
                  style={{ padding: '16px 24px', borderBottom: idx < questions.length - 1 ? '1px solid rgba(226,232,240,0.5)' : 'none', display: 'flex', justifyContent: 'space-between', alignItems: 'center', transition: 'background 0.15s' }}
                  onMouseEnter={e => { e.currentTarget.style.background = 'rgba(99,102,241,0.025)' }}
                  onMouseLeave={e => { e.currentTarget.style.background = 'transparent' }}
                >
                  <div style={{ flex: 1, minWidth: 0 }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 6 }}>
                      {item.question_number && (
                        <span style={{ fontSize: 11, color: '#94a3b8', fontFamily: 'monospace' }}>{item.question_number}</span>
                      )}
                    </div>
                    <div style={{ fontSize: 14.5, fontWeight: 600, color: '#0f172a', marginBottom: 8, lineHeight: 1.5, overflow: 'hidden', textOverflow: 'ellipsis', display: '-webkit-box', WebkitLineClamp: 2, WebkitBoxOrient: 'vertical' }}>
                      {item.question_text}
                    </div>
                    <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', alignItems: 'center' }}>
                      <span style={{ padding: '2px 10px', borderRadius: 99, background: dc.bg, color: dc.color, fontSize: 11.5, fontWeight: 700 }}>{dc.label}</span>
                      <span style={{ padding: '2px 10px', borderRadius: 99, background: tc.bg, color: tc.color, fontSize: 11.5, fontWeight: 700 }}>{tc.label}</span>
                      <span style={{ 
                        padding: '2px 10px', 
                        borderRadius: 99, 
                        background: 'rgba(99,102,241,0.08)', 
                        color: '#6366f1', 
                        fontSize: 11.5, 
                        display: 'flex', 
                        alignItems: 'center', 
                        gap: 4,
                        border: '1px solid rgba(99,102,241,0.15)'
                      }}>
                        <NodeIndexOutlined style={{ fontSize: 10 }} /> 
                        {item.knowledge_point_name || '未知知识点'}
                      </span>
                      <span style={{ padding: '2px 10px', borderRadius: 99, background: source.color + '15', color: source.color, fontSize: 11.5, display: 'flex', alignItems: 'center', gap: 4 }}>
                        {source.icon}
                        {source.label}
                      </span>
                    </div>
                  </div>
                  <div style={{ display: 'flex', gap: 8, marginLeft: 16 }}>
                    <button 
                      onClick={() => handleViewQuestion(item)}
                      style={{ flexShrink: 0, padding: '6px 14px', borderRadius: 8, border: '1px solid rgba(99,102,241,0.25)', background: 'rgba(99,102,241,0.05)', color: '#6366f1', fontSize: 12.5, fontWeight: 600, cursor: 'pointer', transition: 'all 0.15s' }}
                    >
                      查看
                    </button>
                    <Popconfirm
                      title="确认删除"
                      description="确定要删除这道题目吗？此操作不可恢复。"
                      onConfirm={() => handleDeleteQuestion(item.id)}
                      okText="删除"
                      cancelText="取消"
                      okButtonProps={{ danger: true }}
                    >
                      <button style={{ 
                        flexShrink: 0, 
                        padding: '6px 12px', 
                        borderRadius: 8, 
                        border: '1px solid rgba(244,63,94,0.25)', 
                        background: 'rgba(244,63,94,0.05)', 
                        color: '#f43f5e', 
                        fontSize: 12.5, 
                        fontWeight: 600, 
                        cursor: 'pointer', 
                        transition: 'all 0.15s',
                        display: 'flex',
                        alignItems: 'center',
                        gap: 4
                      }}>
                        <DeleteOutlined style={{ fontSize: 12 }} />
                      </button>
                    </Popconfirm>
                  </div>
                </motion.div>
              )
            })}
          </div>
        )}
      </div>

      {/* 习题上传弹窗 */}
      <Modal
        title={
          <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
            <UploadOutlined style={{ color: '#8b5cf6' }} />
            <span>上传习题</span>
          </div>
        }
        open={uploadModalVisible}
        onCancel={() => {
          setUploadModalVisible(false)
          setBatchQuestions([])
          setParsedQuestions([])
          setStructuredStep(0)
          setParseStep(0)
        }}
        footer={null}
        width={800}
        destroyOnHidden
      >
        <div style={{ padding: '8px 0' }}>
          {/* 上传方式选择 */}
          {structuredStep === 0 && parseStep === 0 && (
            <div>
              <div style={{ marginBottom: 24, textAlign: 'center' }}>
                <h3 style={{ margin: '0 0 8px', fontSize: 18, fontWeight: 700, color: '#0f172a' }}>选择上传方式</h3>
                <p style={{ margin: 0, fontSize: 14, color: '#64748b' }}>支持结构化手动录入或文件自动解析</p>
              </div>
              
              <Row gutter={16}>
                <Col span={12}>
                  <Card
                    hoverable
                    onClick={() => {
                      setUploadMode('structured')
                      setStructuredStep(1)
                    }}
                    style={{ 
                      textAlign: 'center', 
                      border: uploadMode === 'structured' ? '2px solid #8b5cf6' : '1px solid #e2e8f0',
                      borderRadius: 12,
                      cursor: 'pointer'
                    }}
                  >
                    <div style={{ 
                      width: 64, 
                      height: 64, 
                      borderRadius: '50%', 
                      background: 'linear-gradient(135deg, #8b5cf6, #6366f1)',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      margin: '0 auto 16px'
                    }}>
                      <EditOutlined style={{ fontSize: 28, color: '#fff' }} />
                    </div>
                    <h4 style={{ margin: '0 0 8px', fontSize: 16, fontWeight: 700, color: '#0f172a' }}>结构化上传</h4>
                    <p style={{ margin: 0, fontSize: 13, color: '#64748b', lineHeight: 1.6 }}>
                      手动逐题录入<br />
                      适合题目数量较少时使用
                    </p>
                  </Card>
                </Col>
                <Col span={12}>
                  <Card
                    hoverable
                    onClick={() => {
                      setUploadMode('parse')
                      setParseStep(0)
                    }}
                    style={{ 
                      textAlign: 'center', 
                      border: uploadMode === 'parse' ? '2px solid #10b981' : '1px solid #e2e8f0',
                      borderRadius: 12,
                      cursor: 'pointer'
                    }}
                  >
                    <div style={{ 
                      width: 64, 
                      height: 64, 
                      borderRadius: '50%', 
                      background: 'linear-gradient(135deg, #10b981, #06b6d4)',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      margin: '0 auto 16px'
                    }}>
                      <FileSearchOutlined style={{ fontSize: 28, color: '#fff' }} />
                    </div>
                    <h4 style={{ margin: '0 0 8px', fontSize: 16, fontWeight: 700, color: '#0f172a' }}>自动解析上传</h4>
                    <p style={{ margin: 0, fontSize: 13, color: '#64748b', lineHeight: 1.6 }}>
                      上传文件自动解析<br />
                      支持 TXT/DOC/DOCX/PDF
                    </p>
                  </Card>
                </Col>
              </Row>
            </div>
          )}

          {/* 结构化上传 - 填写题目 */}
          {uploadMode === 'structured' && structuredStep === 1 && (
            <div>
              <Steps current={0} size="small" style={{ marginBottom: 24 }}>
                <Step title="选择方式" />
                <Step title="填写题目" />
                <Step title="确认上传" />
              </Steps>
              
              <div style={{ 
                background: '#f8fafc', 
                padding: '16px 20px', 
                borderRadius: 12,
                marginBottom: 16
              }}>
                <div style={{ marginBottom: 16 }}>
                  <label style={{ display: 'block', fontSize: 13, fontWeight: 600, color: '#374151', marginBottom: 8 }}>
                    题干内容 <span style={{ color: '#ef4444' }}>*</span>
                  </label>
                  <TextArea
                    value={singleQuestionForm.question_text}
                    onChange={(e) => setSingleQuestionForm({ ...singleQuestionForm, question_text: e.target.value })}
                    placeholder="请输入题目内容..."
                    rows={3}
                    style={{ borderRadius: 8 }}
                  />
                </div>
                
                <Row gutter={16} style={{ marginBottom: 16 }}>
                  <Col span={8}>
                    <label style={{ display: 'block', fontSize: 13, fontWeight: 600, color: '#374151', marginBottom: 8 }}>
                      难度
                    </label>
                    <Select
                      value={singleQuestionForm.difficulty}
                      onChange={(value) => setSingleQuestionForm({ ...singleQuestionForm, difficulty: value })}
                      style={{ width: '100%' }}
                    >
                      <Option value="basic">
                        <span style={{ color: '#10b981', fontWeight: 600 }}>基础题</span>
                      </Option>
                      <Option value="comprehensive">
                        <span style={{ color: '#f59e0b', fontWeight: 600 }}>综合题</span>
                      </Option>
                      <Option value="challenge">
                        <span style={{ color: '#f43f5e', fontWeight: 600 }}>挑战题</span>
                      </Option>
                    </Select>
                  </Col>
                  <Col span={16}>
                    <label style={{ display: 'block', fontSize: 13, fontWeight: 600, color: '#374151', marginBottom: 8 }}>
                      关联知识点
                    </label>
                    <Select
                      value={singleQuestionForm.knowledge_point_id}
                      onChange={(value) => setSingleQuestionForm({ ...singleQuestionForm, knowledge_point_id: value })}
                      style={{ width: '100%' }}
                      placeholder="选择知识点（可选）"
                      allowClear
                    >
                      {knowledgePoints.map(kp => (
                        <Option key={kp.id} value={kp.id}>{kp.name}</Option>
                      ))}
                    </Select>
                  </Col>
                </Row>
                
                <div style={{ marginBottom: 16 }}>
                  <label style={{ display: 'block', fontSize: 13, fontWeight: 600, color: '#374151', marginBottom: 8 }}>
                    选项 <span style={{ color: '#ef4444' }}>*</span>
                  </label>
                  <Space direction="vertical" style={{ width: '100%' }}>
                    {singleQuestionForm.options.map((opt, index) => (
                      <div key={opt.key} style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
                        <Radio
                          checked={singleQuestionForm.correct_answer === opt.key}
                          onChange={() => setSingleQuestionForm({ ...singleQuestionForm, correct_answer: opt.key })}
                        >
                          <span style={{ 
                            width: 24, 
                            height: 24, 
                            borderRadius: '50%', 
                            background: singleQuestionForm.correct_answer === opt.key ? '#10b981' : '#e2e8f0',
                            color: singleQuestionForm.correct_answer === opt.key ? '#fff' : '#64748b',
                            display: 'inline-flex',
                            alignItems: 'center',
                            justifyContent: 'center',
                            fontSize: 12,
                            fontWeight: 700
                          }}>
                            {opt.key}
                          </span>
                        </Radio>
                        <Input
                          value={opt.text}
                          onChange={(e) => handleOptionChange(index, e.target.value)}
                          placeholder={`选项 ${opt.key}`}
                          style={{ flex: 1 }}
                        />
                      </div>
                    ))}
                  </Space>
                  <div style={{ marginTop: 8, fontSize: 12, color: '#64748b' }}>
                    <CheckOutlined style={{ color: '#10b981', marginRight: 4 }} />
                    点击选项前的圆圈标记为正确答案
                  </div>
                </div>
                
                <div>
                  <label style={{ display: 'block', fontSize: 13, fontWeight: 600, color: '#374151', marginBottom: 8 }}>
                    答案解析
                  </label>
                  <TextArea
                    value={singleQuestionForm.explanation}
                    onChange={(e) => setSingleQuestionForm({ ...singleQuestionForm, explanation: e.target.value })}
                    placeholder="请输入答案解析（可选）..."
                    rows={2}
                    style={{ borderRadius: 8 }}
                  />
                </div>
              </div>
              
              {/* 批量列表 */}
              {batchQuestions.length > 0 && (
                <div style={{ marginBottom: 16 }}>
                  <div style={{ fontSize: 13, fontWeight: 600, color: '#374151', marginBottom: 8 }}>
                    已添加题目 ({batchQuestions.length}道)
                  </div>
                  <div style={{ maxHeight: 150, overflow: 'auto' }}>
                    {batchQuestions.map((q, idx) => (
                      <div 
                        key={idx} 
                        style={{ 
                          padding: '8px 12px', 
                          background: '#f1f5f9', 
                          borderRadius: 8, 
                          marginBottom: 8,
                          display: 'flex',
                          justifyContent: 'space-between',
                          alignItems: 'center'
                        }}
                      >
                        <span style={{ fontSize: 13, color: '#0f172a' }}>
                          {idx + 1}. {q.question_text.slice(0, 30)}...
                        </span>
                        <Button 
                          type="text" 
                          danger 
                          size="small"
                          onClick={() => handleRemoveFromBatch(idx)}
                        >
                          删除
                        </Button>
                      </div>
                    ))}
                  </div>
                </div>
              )}
              
              <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                <Button onClick={() => setStructuredStep(0)}>
                  <LeftOutlined /> 返回
                </Button>
                <Space>
                  <Button onClick={handleAddToBatch}>
                    <PlusOutlined /> 添加到批量列表
                  </Button>
                  {batchQuestions.length > 0 ? (
                    <Button 
                      type="primary" 
                      onClick={handleBatchUpload}
                      loading={isUploading}
                      style={{ background: 'linear-gradient(135deg,#8b5cf6,#6366f1)' }}
                    >
                      <SaveOutlined /> 批量上传 ({batchQuestions.length}道)
                    </Button>
                  ) : (
                    <Button 
                      type="primary" 
                      onClick={handleSingleUpload}
                      loading={isUploading}
                      style={{ background: 'linear-gradient(135deg,#8b5cf6,#6366f1)' }}
                    >
                      <SaveOutlined /> 直接上传
                    </Button>
                  )}
                </Space>
              </div>
            </div>
          )}

          {/* 自动解析上传 - 上传文件 */}
          {uploadMode === 'parse' && parseStep === 0 && (
            <div>
              <Steps current={0} size="small" style={{ marginBottom: 24 }}>
                <Step title="上传文件" />
                <Step title="预览结果" />
                <Step title="确认保存" />
              </Steps>
              
              <div style={{ textAlign: 'center', padding: '40px 20px' }}>
                <Upload.Dragger
                  beforeUpload={handleFileUpload}
                  showUploadList={false}
                  accept=".txt,.doc,.docx,.pdf"
                  disabled={parsingFile}
                >
                  <div style={{ padding: '20px 0' }}>
                    <p style={{ fontSize: 48, marginBottom: 16 }}>
                      {parsingFile ? <RobotOutlined spin style={{ color: '#6366f1' }} /> : <UploadOutlined style={{ color: '#8b5cf6' }} />}
                    </p>
                    <p style={{ fontSize: 16, fontWeight: 600, color: '#0f172a', marginBottom: 8 }}>
                      {parsingFile ? 'AI正在解析文件...' : '点击或拖拽文件到此处上传'}
                    </p>
                    <p style={{ fontSize: 13, color: '#64748b' }}>
                      支持格式：TXT、DOC、DOCX、PDF
                    </p>
                  </div>
                </Upload.Dragger>
                
                <Alert
                  message="自动解析与改编说明"
                  description="上传文件后，AI将自动识别文档中的各类习题（填空、简答、判断、计算等），并将其统一改编为单项选择题格式。系统会为每道题生成4个选项（A/B/C/D），包含正确答案和合理的干扰项。"
                  type="info"
                  showIcon
                  style={{ marginTop: 20, textAlign: 'left' }}
                />
              </div>
              
              <div style={{ display: 'flex', justifyContent: 'flex-start' }}>
                <Button onClick={() => setParseStep(-1) || setStructuredStep(0)}>
                  <LeftOutlined /> 返回
                </Button>
              </div>
            </div>
          )}

          {/* 自动解析上传 - 预览结果 */}
          {uploadMode === 'parse' && parseStep === 1 && (
            <div>
              <Steps current={1} size="small" style={{ marginBottom: 24 }}>
                <Step title="上传文件" />
                <Step title="预览结果" />
                <Step title="确认保存" />
              </Steps>
              
              {parsedQuestions.length === 0 ? (
                <div style={{ textAlign: 'center', padding: 40 }}>
                  <Empty description="未解析到任何题目" />
                  <Button onClick={() => setParseStep(0)} style={{ marginTop: 16 }}>
                    重新上传
                  </Button>
                </div>
              ) : (
                <div>
                  <div style={{ marginBottom: 16, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <span style={{ fontSize: 14, fontWeight: 600, color: '#0f172a' }}>
                      共解析到 {parsedQuestions.length} 道题目
                    </span>
                    <Space>
                      <Button 
                        size="small"
                        disabled={currentQuestionIndex === 0}
                        onClick={() => setCurrentQuestionIndex(currentQuestionIndex - 1)}
                      >
                        <LeftOutlined /> 上一题
                      </Button>
                      <span style={{ fontSize: 13, color: '#64748b' }}>
                        {currentQuestionIndex + 1} / {parsedQuestions.length}
                      </span>
                      <Button 
                        size="small"
                        disabled={currentQuestionIndex === parsedQuestions.length - 1}
                        onClick={() => setCurrentQuestionIndex(currentQuestionIndex + 1)}
                      >
                        下一题 <RightOutlined />
                      </Button>
                    </Space>
                  </div>
                  
                  {parsedQuestions[currentQuestionIndex] && (
                    <div style={{ 
                      background: '#f8fafc', 
                      padding: '20px', 
                      borderRadius: 12,
                      marginBottom: 16
                    }}>
                      <Alert
                        message="AI自动改编为选择题"
                        description="系统已将文档中的各类题型（填空、简答、判断等）自动改编为单项选择题，您可以直接编辑调整。"
                        type="info"
                        showIcon
                        style={{ marginBottom: 16 }}
                      />
                      
                      <div style={{ marginBottom: 16 }}>
                        <label style={{ display: 'block', fontSize: 12, color: '#64748b', marginBottom: 4 }}>
                          题干
                        </label>
                        <TextArea
                          value={parsedQuestions[currentQuestionIndex].question_text}
                          onChange={(e) => handleUpdateParsedQuestion(currentQuestionIndex, 'question_text', e.target.value)}
                          rows={2}
                          style={{ borderRadius: 8 }}
                        />
                      </div>
                      
                      <Row gutter={16} style={{ marginBottom: 16 }}>
                        <Col span={12}>
                          <label style={{ display: 'block', fontSize: 12, color: '#64748b', marginBottom: 4 }}>
                            难度
                          </label>
                          <Select
                            value={parsedQuestions[currentQuestionIndex].difficulty || 'basic'}
                            onChange={(value) => handleUpdateParsedQuestion(currentQuestionIndex, 'difficulty', value)}
                            style={{ width: '100%' }}
                          >
                            <Option value="basic">基础题</Option>
                            <Option value="comprehensive">综合题</Option>
                            <Option value="challenge">挑战题</Option>
                          </Select>
                        </Col>
                        <Col span={12}>
                          <label style={{ display: 'block', fontSize: 12, color: '#64748b', marginBottom: 4 }}>
                            关联知识点
                          </label>
                          <Select
                            value={parsedQuestions[currentQuestionIndex].knowledge_point_id}
                            onChange={(value) => handleUpdateParsedQuestion(currentQuestionIndex, 'knowledge_point_id', value)}
                            style={{ width: '100%' }}
                            placeholder="选择知识点"
                            allowClear
                          >
                            {knowledgePoints.map(kp => (
                              <Option key={kp.id} value={kp.id}>{kp.name}</Option>
                            ))}
                          </Select>
                        </Col>
                      </Row>
                      
                      <div style={{ marginBottom: 16 }}>
                        <label style={{ display: 'block', fontSize: 12, color: '#64748b', marginBottom: 4 }}>
                          选项
                        </label>
                        <Space direction="vertical" style={{ width: '100%' }}>
                          {parsedQuestions[currentQuestionIndex].options?.map((opt, idx) => (
                            <div key={idx} style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                              <Radio
                                checked={parsedQuestions[currentQuestionIndex].correct_answer === opt.key}
                                onChange={() => handleUpdateParsedQuestion(currentQuestionIndex, 'correct_answer', opt.key)}
                              />
                              <span style={{ 
                                width: 24, 
                                height: 24, 
                                borderRadius: '50%', 
                                background: parsedQuestions[currentQuestionIndex].correct_answer === opt.key ? '#10b981' : '#e2e8f0',
                                color: parsedQuestions[currentQuestionIndex].correct_answer === opt.key ? '#fff' : '#64748b',
                                display: 'inline-flex',
                                alignItems: 'center',
                                justifyContent: 'center',
                                fontSize: 12,
                                fontWeight: 700
                              }}>
                                {opt.key}
                              </span>
                              <Input
                                value={opt.text}
                                onChange={(e) => handleUpdateParsedOption(currentQuestionIndex, idx, e.target.value)}
                                style={{ flex: 1 }}
                              />
                            </div>
                          ))}
                        </Space>
                      </div>
                      
                      <div>
                        <label style={{ display: 'block', fontSize: 12, color: '#64748b', marginBottom: 4 }}>
                          答案解析
                        </label>
                        <TextArea
                          value={parsedQuestions[currentQuestionIndex].explanation || ''}
                          onChange={(e) => handleUpdateParsedQuestion(currentQuestionIndex, 'explanation', e.target.value)}
                          rows={2}
                          style={{ borderRadius: 8 }}
                        />
                      </div>
                      
                      <div style={{ marginTop: 16, textAlign: 'right' }}>
                        <Button 
                          danger 
                          size="small"
                          onClick={() => handleRemoveParsedQuestion(currentQuestionIndex)}
                        >
                          <DeleteOutlined /> 删除此题
                        </Button>
                      </div>
                    </div>
                  )}
                </div>
              )}
              
              <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                <Button onClick={() => setParseStep(0)}>
                  <LeftOutlined /> 返回
                </Button>
                <Button 
                  type="primary" 
                  onClick={handleConfirmParsed}
                  loading={isUploading}
                  disabled={parsedQuestions.length === 0}
                  style={{ background: 'linear-gradient(135deg,#10b981,#06b6d4)' }}
                >
                  <SaveOutlined /> 确认保存 ({parsedQuestions.length}道)
                </Button>
              </div>
            </div>
          )}
        </div>
      </Modal>

      {/* 查看题目详情弹窗 */}
      <Modal
        title="题目详情"
        open={viewModalVisible}
        onCancel={() => setViewModalVisible(false)}
        footer={[
          <Button key="close" onClick={() => setViewModalVisible(false)}>
            关闭
          </Button>
        ]}
        width={640}
      >
        {viewingQuestion && (
          <div style={{ padding: '8px 0' }}>
            <div style={{ display: 'flex', gap: 8, marginBottom: 16, flexWrap: 'wrap' }}>
              <Tag color={DIFFICULTY_CONFIG[viewingQuestion.difficulty]?.color || '#6366f1'}>
                {DIFFICULTY_CONFIG[viewingQuestion.difficulty]?.label || '基础题'}
              </Tag>
              <Tag color={TYPE_CONFIG[viewingQuestion.question_type]?.color || '#6366f1'}>
                {TYPE_CONFIG[viewingQuestion.question_type]?.label || '选择题'}
              </Tag>
              {viewingQuestion.knowledge_point_name && (
                <Tag icon={<NodeIndexOutlined />} color="purple">
                  {viewingQuestion.knowledge_point_name}
                </Tag>
              )}
              <Tag icon={viewingQuestion.is_ai_generated !== false ? <RobotOutlined /> : <UserOutlined />} color={viewingQuestion.is_ai_generated !== false ? 'blue' : 'cyan'}>
                {viewingQuestion.is_ai_generated !== false ? 'AI生成' : '用户上传'}
              </Tag>
            </div>

            <div style={{ marginBottom: 20 }}>
              <Text strong style={{ fontSize: 15, color: '#0f172a', lineHeight: 1.6 }}>
                {viewingQuestion.question_text}
              </Text>
            </div>

            {viewingQuestion.options && viewingQuestion.options.length > 0 && (
              <div style={{ marginBottom: 20 }}>
                <div style={{ fontSize: 13, color: '#64748b', marginBottom: 12, fontWeight: 600 }}>选项</div>
                <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
                  {viewingQuestion.options.map((opt, idx) => {
                    const letter = String.fromCharCode(65 + idx)
                    const isCorrect = letter === viewingQuestion.correct_answer
                    const optText = opt.replace(/^[A-D][\.、\s]+/, '').trim()
                    return (
                      <div 
                        key={idx}
                        style={{ 
                          padding: '12px 16px', 
                          borderRadius: 8, 
                          background: isCorrect ? 'rgba(16,185,129,0.08)' : '#f8fafc',
                          border: isCorrect ? '1px solid rgba(16,185,129,0.3)' : '1px solid #e2e8f0',
                          display: 'flex',
                          alignItems: 'center',
                          gap: 10
                        }}
                      >
                        <span style={{ 
                          width: 24, 
                          height: 24, 
                          borderRadius: '50%', 
                          background: isCorrect ? '#10b981' : '#e2e8f0',
                          color: isCorrect ? '#fff' : '#64748b',
                          display: 'flex',
                          alignItems: 'center',
                          justifyContent: 'center',
                          fontSize: 12,
                          fontWeight: 700
                        }}>
                          {letter}
                        </span>
                        <span style={{ flex: 1, color: '#0f172a', fontSize: 14 }}>{optText}</span>
                        {isCorrect && (
                          <CheckCircleOutlined style={{ color: '#10b981', fontSize: 16 }} />
                        )}
                      </div>
                    )
                  })}
                </div>
              </div>
            )}

            <div style={{ 
              padding: '12px 16px', 
              borderRadius: 8, 
              background: 'rgba(16,185,129,0.08)', 
              border: '1px solid rgba(16,185,129,0.2)',
              marginBottom: 16
            }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                <CheckCircleOutlined style={{ color: '#10b981' }} />
                <span style={{ fontWeight: 600, color: '#10b981' }}>
                  正确答案：{viewingQuestion.correct_answer}
                </span>
              </div>
            </div>

            {viewingQuestion.explanation && (
              <div style={{ 
                padding: '16px', 
                borderRadius: 8, 
                background: '#f8fafc', 
                border: '1px solid #e2e8f0'
              }}>
                <div style={{ fontSize: 13, color: '#64748b', marginBottom: 8, fontWeight: 600 }}>解析</div>
                <div style={{ color: '#334155', fontSize: 14, lineHeight: 1.7 }}>
                  {viewingQuestion.explanation}
                </div>
              </div>
            )}
          </div>
        )}
      </Modal>

      {/* 习题生成进度弹窗 */}
      <Modal
        title={null}
        open={showProgress}
        closable={progressInfo.status === 'completed' || progressInfo.status === 'error' || progressInfo.status === 'cancelled'}
        onCancel={handleCloseProgress}
        footer={
          progressInfo.status === 'completed' ? [
            <Button key="close" type="primary" onClick={handleCloseProgress}
              style={{ 
                borderRadius: 10,
                height: 44,
                paddingLeft: 32,
                paddingRight: 32,
                background: 'linear-gradient(135deg,#6366f1,#8b5cf6)',
                border: 'none',
                fontWeight: 600,
                fontSize: 15
              }}
            >
              完成
            </Button>
          ] : progressInfo.status === 'error' ? [
            <Button key="close" onClick={handleCloseProgress} style={{ borderRadius: 10, height: 40 }}>
              关闭
            </Button>,
            <Button key="retry" type="primary" onClick={handleGenerateQuestions}
              style={{ 
                borderRadius: 10,
                height: 40,
                paddingLeft: 24,
                paddingRight: 24,
                background: 'linear-gradient(135deg,#6366f1,#8b5cf6)',
                border: 'none',
                fontWeight: 600
              }}
            >
              重试
            </Button>
          ] : progressInfo.status === 'cancelled' ? [
            <Button key="close" type="primary" onClick={handleCloseProgress}
              style={{ 
                borderRadius: 10,
                height: 40,
                paddingLeft: 24,
                paddingRight: 24,
                background: 'linear-gradient(135deg,#6366f1,#8b5cf6)',
                border: 'none',
                fontWeight: 600
              }}
            >
              确定
            </Button>
          ] : [
            <Button key="cancel" onClick={handleCancelGeneration}
              style={{ 
                borderRadius: 10,
                height: 40,
                borderColor: '#ff4d4f',
                color: '#ff4d4f'
              }}
            >
              停止生成
            </Button>
          ]
        }
        maskClosable={false}
        width={560}
        styles={{ body: { padding: '32px' } }}
      >
        <style>{`
          @keyframes spin {
            from { transform: rotate(0deg); }
            to { transform: rotate(360deg); }
          }
          @keyframes pulse {
            0% { transform: scale(0.8); opacity: 0; }
            50% { transform: scale(1.05); }
            100% { transform: scale(1); opacity: 1; }
          }
        `}</style>
        
        {/* 顶部图标区域 */}
        <div style={{ textAlign: 'center', marginBottom: 24 }}>
          {renderProgressHeaderIcon()}
          <div style={{ fontSize: 18, fontWeight: 700, color: '#0f172a', marginBottom: 8 }}>
            {progressInfo.status === 'completed' ? '生成完成' : 
             progressInfo.status === 'error' ? '生成失败' :
             progressInfo.status === 'cancelled' ? '已取消' : '正在生成习题'}
          </div>
          <div style={{ fontSize: 14, color: '#64748b' }}>
            {progressInfo.message}
          </div>
        </div>
        
        {/* 进度条 */}
        {progressInfo.status !== 'completed' && progressInfo.status !== 'error' && progressInfo.status !== 'cancelled' && (
          <div style={{ marginBottom: 24 }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 8 }}>
              <span style={{ fontSize: 13, color: '#64748b' }}>
                {progressInfo.currentIndex > 0 ? `第 ${progressInfo.currentIndex}/${progressInfo.total} 道` : '准备中...'}
              </span>
              <span style={{ fontSize: 13, fontWeight: 600, color: '#6366f1' }}>
                {progressInfo.progress}%
              </span>
            </div>
            <div style={{ height: 8, background: '#f1f5f9', borderRadius: 4, overflow: 'hidden' }}>
              <div style={{ 
                width: `${progressInfo.progress}%`, 
                height: '100%', 
                background: 'linear-gradient(90deg,#6366f1,#8b5cf6)', 
                borderRadius: 4,
                transition: 'width 0.3s ease'
              }} />
            </div>
            {progressInfo.currentNode && (
              <div style={{ marginTop: 12, padding: '12px 16px', background: '#f8fafc', borderRadius: 8, textAlign: 'center' }}>
                <div style={{ fontSize: 12, color: '#94a3b8', marginBottom: 4 }}>当前知识点</div>
                <div style={{ fontSize: 14, fontWeight: 600, color: '#0f172a' }}>{progressInfo.currentNode}</div>
              </div>
            )}
          </div>
        )}
        
        {/* 耗时显示 */}
        <div style={{ textAlign: 'center', fontSize: 13, color: '#94a3b8' }}>
          已用时: {formatTime(elapsedTime)}
        </div>
      </Modal>

      {/* 个性化练习数量选择弹窗 */}
      <Modal
        title={null}
        open={personalizedModalVisible}
        onCancel={() => setPersonalizedModalVisible(false)}
        footer={[
          <Button key="cancel" onClick={() => setPersonalizedModalVisible(false)}
            style={{ borderRadius: 10, height: 40 }}>
            取消
          </Button>,
          <Button key="start" type="primary" loading={personalizedLoading} onClick={handleStartPersonalizedPractice}
            style={{
              borderRadius: 10,
              height: 40,
              paddingLeft: 24,
              paddingRight: 24,
              background: 'linear-gradient(135deg,#8b5cf6,#6366f1)',
              border: 'none',
              fontWeight: 600
            }}>
            开始练习
          </Button>
        ]}
        width={480}
        styles={{ body: { padding: '32px' } }}
      >
        <div style={{ textAlign: 'center', marginBottom: 24 }}>
          <div style={{
            width: 64,
            height: 64,
            borderRadius: '50%',
            background: 'linear-gradient(135deg,#8b5cf6,#6366f1)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            margin: '0 auto 16px',
            boxShadow: '0 8px 24px rgba(139,92,246,0.35)'
          }}>
            <ThunderboltOutlined style={{ fontSize: 28, color: '#fff' }} />
          </div>
          <div style={{ fontSize: 18, fontWeight: 700, color: '#0f172a', marginBottom: 8 }}>
            个性化练习
          </div>
          <div style={{ fontSize: 14, color: '#64748b' }}>
            根据您的知识掌握情况，智能推荐最适合的练习题目
          </div>
        </div>

        <div style={{ marginBottom: 8 }}>
          <div style={{ fontSize: 13, color: '#64748b', marginBottom: 12, fontWeight: 500 }}>
            选择题目数量
          </div>
          <Radio.Group
            value={personalizedCount}
            onChange={(e) => setPersonalizedCount(e.target.value)}
            style={{ width: '100%' }}
          >
            <div style={{ display: 'flex', gap: 12 }}>
              <Radio.Button
                value={5}
                style={{
                  flex: 1,
                  height: 48,
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  borderRadius: 10,
                  fontSize: 15,
                  fontWeight: 600
                }}
              >
                5 题
              </Radio.Button>
              <Radio.Button
                value={10}
                style={{
                  flex: 1,
                  height: 48,
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  borderRadius: 10,
                  fontSize: 15,
                  fontWeight: 600
                }}
              >
                10 题
              </Radio.Button>
            </div>
          </Radio.Group>
        </div>
      </Modal>
    </motion.div>
    </App>
  )
}

export default Questions
