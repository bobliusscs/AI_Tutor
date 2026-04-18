import { useState, useEffect } from 'react'
import { Button, Tag, Typography, message, Empty, Collapse, Spin, Modal, Space, Progress } from 'antd'
import {
  PlayCircleOutlined,
  CheckCircleOutlined,
  ClockCircleOutlined,
  BookOutlined,
  CalendarOutlined,
  LockOutlined,
  FilePptOutlined,
  CaretRightOutlined,
  LoadingOutlined,
  RocketOutlined,
  CloseCircleOutlined,
  ApartmentOutlined,
  BlockOutlined,
  MergeCellsOutlined,
  SolutionOutlined,
  UnorderedListOutlined,
} from '@ant-design/icons'
import { useParams, useNavigate } from 'react-router-dom'
import { motion } from 'framer-motion'
import { learningPlanAPI, studyGoalAPI } from '../../utils/api'

const { Text } = Typography
const { Panel } = Collapse

function LearningPlan() {
  const { goalId } = useParams()
  const navigate   = useNavigate()
  const [plan, setPlan]           = useState(null)
  const [lessons, setLessons]     = useState([])
  const [loading, setLoading]      = useState(true)
  const [goal, setGoal]           = useState(null)
  const [chapters, setChapters]   = useState([])     // 章节结构数据
  const [planStructure, setPlanStructure] = useState(null)  // 完整的计划结构
  const [useChapterView, setUseChapterView] = useState(false) // 是否使用章节视图
  const [expandedChapters, setExpandedChapters] = useState([]) // 展开的章节
  const [generatingPPT, setGeneratingPPT] = useState({}) // 记录正在生成PPT的章节/节
  const [pptModal, setPptModal] = useState({ visible: false, slides: [], title: '' })
  const [generatingPlan, setGeneratingPlan] = useState(false) // 是否正在生成学习计划
  const [generatingProgress, setGeneratingProgress] = useState(0) // 生成进度百分比
  const [generatingMessage, setGeneratingMessage] = useState('') // 生成进度消息
  const [showPlanTypeModal, setShowPlanTypeModal] = useState(false) // 显示生成方式选择弹窗
  const [showProgressModal, setShowProgressModal] = useState(false) // 显示生成进度弹窗
  const [progressInfo, setProgressInfo] = useState({
    status: 'preparing', // preparing | analyzing_graph | generating_structure | creating_plan | saving | completed | error
    progress: 0,
    message: '',
    chaptersCount: 0,
    sectionsCount: 0,
    lessonsCount: 0
  })
  // PPT生成进度状态
  const [showPPTTProgress, setShowPPTTProgress] = useState(false) // 显示PPT生成进度弹窗
  const [pptProgressInfo, setPptProgressInfo] = useState({
    sectionId: null,
    sectionTitle: '',
    status: 'preparing', // preparing | generating | completed | error | cancelled
    progress: 0,
    message: ''
  })
  // 批量PPT生成进度状态
  const [showBatchPPTProgress, setShowBatchPPTProgress] = useState(false) // 显示批量PPT生成进度弹窗
  const [batchPptProgressInfo, setBatchPptProgressInfo] = useState({
    chapterId: null,
    chapterTitle: '',
    totalSections: 0,
    currentSection: 0,
    currentSectionTitle: '',
    status: 'preparing', // preparing | generating | completed | error | cancelled
    progress: 0,
    message: '',
    results: [] // 记录每个小节的生成结果
  })
  const [showResetModal, setShowResetModal] = useState(false) // 重置进度确认弹窗

  useEffect(() => { fetchData() }, [goalId])

  const fetchData = async () => {
    setLoading(true)
    try {
      const goalResult = await studyGoalAPI.get(goalId)
      const goalData = goalResult.data
      if (goalData.success) setGoal(goalData.data)
      
      // 如果有 plan_id，从后端获取真实的学习计划数据
      if (goalData.data?.plan_id) {
        try {
          const planResult = await learningPlanAPI.get(goalData.data.plan_id)
          const planData = planResult.data
          if (planData.success) {
            setPlan({
              id: planData.data.id,
              title: planData.data.title || `${goalData.data?.title || '学习目标'} — 学习计划`,
              total_lessons: planData.data.total_lessons || 0,
              completed_lessons: planData.data.completed_lessons || 0,
              weekly_hours: goalData.data?.target_hours_per_week || 5,
            })
          }
        } catch (planError) {
          console.error('获取学习计划详情失败:', planError)
          // 使用目标数据初始化 plan
          setPlan({
            id: goalData.data.plan_id,
            title: `${goalData.data?.title || '学习目标'} — 学习计划`,
            total_lessons: goalData.data?.progress?.total_knowledge_points || 0,
            completed_lessons: goalData.data?.progress?.completed_lessons || 0,
            weekly_hours: goalData.data?.target_hours_per_week || 5,
          })
        }
        
        // 获取课时列表
        try {
          const lessonsResult = await learningPlanAPI.getLessons(goalData.data.plan_id)
          const lessonsData = lessonsResult.data
          if (lessonsData.success) {
            setLessons(lessonsData.data.map(l => ({
              id: l.id,
              lesson_number: l.lesson_number,
              title: l.title,
              estimated_minutes: l.estimated_minutes || 30,
              is_completed: l.is_completed || false,
              knowledge_points: [],
              is_next: false,
            })))
          }
        } catch (lessonsError) {
          console.error('获取课时列表失败:', lessonsError)
          setLessons([])
        }

        // 尝试获取章节结构
        try {
          const structureResult = await learningPlanAPI.getPlanStructure(goalData.data.plan_id)
          if (structureResult.data?.success && structureResult.data.data?.chapters?.length > 0) {
            setPlanStructure(structureResult.data.data)
            setChapters(structureResult.data.data.chapters || [])
            setUseChapterView(true)
            // 默认展开第一个章节
            if (structureResult.data.data.chapters?.length > 0) {
              setExpandedChapters([structureResult.data.data.chapters[0].id])
            }
          }
        } catch (structError) {
          console.log('章节结构不存在，使用传统视图')
        }
      } else {
        // 没有 plan_id，使用目标数据初始化
        setPlan({
          id: 1,
          title: `${goalData.data?.title || '学习目标'} — 学习计划`,
          total_lessons: goalData.data?.progress?.total_knowledge_points || 0,
          completed_lessons: goalData.data?.progress?.completed_lessons || 0,
          weekly_hours: goalData.data?.target_hours_per_week || 5,
        })
        setLessons([])
      }
    } catch { 
      message.error('获取学习计划失败') 
      // 设置默认 plan，避免显示 undefined
      setPlan({
        id: null,
        title: '学习计划',
        total_lessons: 0,
        completed_lessons: 0,
        weekly_hours: 5,
      })
      setLessons([])
    }
    finally { setLoading(false) }
  }

  // 开始学习指定课时 - 跳转到聊天页面并自动加载课件
  const handleStartLesson = (lessonId) => {
    navigate(`/ai-tutor?goalId=${goalId}&autoLesson=true`, {
      state: { goalTitle: goal?.title || '' }
    })
  }

  // 继续学习 - 跳转到聊天页面，复用首页"继续学习"按钮的逻辑
  const handleContinueLearning = () => {
    navigate(`/ai-tutor?goalId=${goalId}`, {
      state: { 
        goalTitle: goal?.title || '',
        autoContinue: true  // 标记为继续学习，自动发送消息
      }
    })
  }

  // 重置学习进度
  const handleResetProgress = async () => {
    if (!goal?.plan_id) return
    
    try {
      const result = await learningPlanAPI.resetProgress(goal.plan_id)
      if (result.data?.success) {
        message.success('学习进度已重置')
        setShowResetModal(false)
        // 刷新页面数据
        fetchData()
      } else {
        message.error(result.data?.message || '重置失败')
      }
    } catch (error) {
      console.error('重置学习进度失败:', error)
      message.error('重置学习进度失败')
    }
  }

  // 生成学习计划（使用SSE流式进度）
  const handleGeneratePlan = async (useChaptered = true) => {
    setShowPlanTypeModal(false)
    setGeneratingPlan(true)
    setGeneratingProgress(0)
    setGeneratingMessage('正在准备...')
    
    // 打开进度弹窗
    setProgressInfo({
      status: 'preparing',
      progress: 0,
      message: '正在准备生成学习计划...',
      chaptersCount: 0,
      sectionsCount: 0,
      lessonsCount: 0
    })
    setShowProgressModal(true)
    
    try {
      // 获取学习目标的graph_id
      const goalResult = await studyGoalAPI.get(goalId)
      if (!goalResult.data?.success) {
        message.error('获取学习目标失败')
        setProgressInfo(prev => ({ ...prev, status: 'error', message: '获取学习目标失败' }))
        setTimeout(() => setShowProgressModal(false), 2000)
        return
      }
      const goalData = goalResult.data.data
      const graphId = goalData?.graph_id || goalData?.knowledge_graph_id
      
      if (!graphId) {
        message.error('请先生成知识图谱')
        setProgressInfo(prev => ({ ...prev, status: 'error', message: '请先生成知识图谱' }))
        setTimeout(() => setShowProgressModal(false), 2000)
        setGeneratingPlan(false)
        return
      }

      // 确保graph_id是整数
      const graphIdInt = parseInt(graphId, 10)
      if (isNaN(graphIdInt)) {
        message.error('知识图谱ID无效')
        setProgressInfo(prev => ({ ...prev, status: 'error', message: '知识图谱ID无效' }))
        setTimeout(() => setShowProgressModal(false), 2000)
        setGeneratingPlan(false)
        return
      }

      const weeklyHours = parseFloat(goalData?.target_hours_per_week) || 5
      
      // 使用 SSE 流式版本
      if (useChaptered) {
        // 生成章节式学习计划（带进度）
        learningPlanAPI.generateChapteredStream(
          {
            graph_id: graphIdInt,
            study_goal_id: goalId,
            weekly_hours: weeklyHours,
            max_chapters: 12,
            max_sections_per_chapter: 6,
            title: goalData.title ? `${goalData.title} - 学习计划` : '学习计划'
          },
          // 进度回调
          (progress, msg) => {
            setGeneratingProgress(progress)
            setGeneratingMessage(msg)
            
            // 根据消息内容更新进度状态
            let newStatus = progressInfo.status
            if (msg.includes('准备') || msg.includes('初始化')) {
              newStatus = 'preparing'
            } else if (msg.includes('分析') || msg.includes('知识图谱')) {
              newStatus = 'analyzing_graph'
            } else if (msg.includes('【生成章】')) {
              newStatus = 'generating_chapters'
            } else if (msg.includes('【生成节】')) {
              newStatus = 'generating_sections'
            } else if (msg.includes('章节') && !msg.includes('完成')) {
              newStatus = 'generating_chapters'
            } else if (msg.includes('创建') || msg.includes('计划') || msg.includes('保存')) {
              newStatus = 'creating_plan'
            } else if (msg.includes('完成') || msg.includes('成功')) {
              newStatus = 'completed'
            }
            
            setProgressInfo(prev => ({
              ...prev,
              status: newStatus,
              progress: progress,
              message: msg
            }))
          },
          // 完成回调
          (data) => {
            setProgressInfo(prev => ({
              ...prev,
              status: 'completed',
              progress: 100,
              message: '学习计划生成成功！',
              chaptersCount: data?.chapter_count || 0,
              sectionsCount: data?.chapters?.reduce((acc, ch) => acc + (ch.sections?.length || 0), 0) || 0,
              lessonsCount: data?.total_lessons || 0
            }))
            setGeneratingPlan(false)
            setGeneratingProgress(100)
            setGeneratingMessage('完成')
            message.success('学习计划生成成功！')
            setTimeout(() => {
              setShowProgressModal(false)
              fetchData()
              setUseChapterView(true)
            }, 2000)
          },
          // 错误回调
          (errorMsg) => {
            message.error(`生成失败: ${errorMsg}`)
            setProgressInfo(prev => ({
              ...prev,
              status: 'error',
              message: errorMsg || '生成失败'
            }))
            setGeneratingPlan(false)
            setGeneratingMessage('')
            setTimeout(() => setShowProgressModal(false), 3000)
          },
          // 取消回调
          (cancelMsg) => {
            console.log('学习计划生成被取消:', cancelMsg)
            setProgressInfo(prev => ({
              ...prev,
              status: 'cancelled',
              message: cancelMsg || '用户取消了生成'
            }))
            setGeneratingPlan(false)
            setGeneratingMessage('')
            message.info('已取消学习计划生成')
          }
        )
      } else {
        // 普通学习计划（保持原逻辑）
        setProgressInfo(prev => ({ ...prev, status: 'creating_plan', message: '正在创建学习计划...' }))
        let result
        result = await learningPlanAPI.generate({
          graph_id: graphIdInt,
          study_goal_id: goalId,
          weekly_hours: weeklyHours,
          title: goalData.title ? `${goalData.title} - 学习计划` : '学习计划'
        })
        
        if (result.data?.success) {
          setProgressInfo(prev => ({ ...prev, status: 'completed', progress: 100, message: '学习计划生成成功！' }))
          message.success('学习计划生成成功！')
          setTimeout(() => {
            setShowProgressModal(false)
            fetchData()
          }, 1500)
        } else {
          const errorMsg = result.data?.message || result.data?.detail || '生成失败'
          setProgressInfo(prev => ({ ...prev, status: 'error', message: errorMsg }))
          message.error(`生成失败: ${errorMsg}`)
          setTimeout(() => setShowProgressModal(false), 3000)
        }
        setGeneratingPlan(false)
      }
    } catch (error) {
      console.error('生成学习计划失败:', error)
      const errorMsg = error.response?.data?.detail || error.message || '网络错误'
      message.error(`生成学习计划失败: ${errorMsg}`)
      setProgressInfo(prev => ({
        ...prev,
        status: 'error',
        message: errorMsg
      }))
      setGeneratingPlan(false)
      setGeneratingMessage('')
      setTimeout(() => setShowProgressModal(false), 3000)
    }
  }

  // 取消学习计划生成
  const handleCancelGeneration = async () => {
    try {
      await learningPlanAPI.cancelGeneration()
      message.info('正在停止生成...')
    } catch (error) {
      console.error('取消生成失败:', error)
      message.error('取消失败')
    }
  }

  // 关闭进度弹窗
  const handleCloseProgressModal = () => {
    if (progressInfo.status === 'completed' || progressInfo.status === 'error' || progressInfo.status === 'cancelled') {
      setShowProgressModal(false)
    }
  }

  // 打开生成方式选择弹窗
  const handleOpenGenerateModal = () => {
    setShowPlanTypeModal(true)
  }

  // 批量为章节下所有小节生成PPT（串行执行+进度弹窗）
  const handleGenerateAllSectionsPPT = async (chapterId, chapterTitle, sections) => {
    if (!sections?.length) {
      message.warning('该章节下没有小节')
      return
    }
    
    setGeneratingPPT(prev => ({ ...prev, [chapterId]: 'chapter' }))
    
    // 初始化批量进度弹窗
    setBatchPptProgressInfo({
      chapterId,
      chapterTitle,
      totalSections: sections.length,
      currentSection: 0,
      currentSectionTitle: '',
      status: 'preparing',
      progress: 0,
      message: '正在准备生成PPT...',
      results: []
    })
    setShowBatchPPTProgress(true)
    
    const results = []
    let firstSuccessSectionId = null
    let firstSuccessSectionTitle = null
    let lastSuccessResult = null  // 记录最后一个成功的PPT用于预览
    
    console.log(`开始为${chapterTitle}生成PPT，小节数量：${sections.length}`)
    console.log('小节列表：', sections.map(s => ({ id: s.id, title: s.title })))
    
    try {
      // 串行为所有小节生成PPT，确保稳定性
      // 添加请求间隔（3秒）减轻服务器压力
      const REQUEST_INTERVAL = 3000
      
      // 更新状态为生成中
      setBatchPptProgressInfo(prev => ({
        ...prev,
        status: 'generating',
        message: '开始生成PPT...'
      }))
      
      for (let i = 0; i < sections.length; i++) {
        const section = sections[i]
        const sectionNum = i + 1
        
        // 更新当前小节进度
        const sectionProgress = Math.round(((sectionNum - 1) / sections.length) * 100)
        setBatchPptProgressInfo(prev => ({
          ...prev,
          currentSection: sectionNum,
          currentSectionTitle: section.title,
          progress: sectionProgress,
          message: `正在生成第${sectionNum}/${sections.length}个小节：${section.title}`
        }))
        
        console.log(`[${sectionNum}/${sections.length}] 正在生成小节 ${section.id} (${section.title}) 的PPT...`)
        
        try {
          // 更新按钮文字显示进度
          setGeneratingPPT(prev => ({ ...prev, [chapterId]: `chapter-${sectionNum}` }))
          
          let result
          try {
            result = await learningPlanAPI.generateSectionPPT(section.id)
          } catch (apiError) {
            // API调用本身失败（如网络错误、超时等）
            console.error(`[${sectionNum}/${sections.length}] API调用失败：`, apiError)
            results.push({ 
              sectionId: section.id, 
              sectionTitle: section.title, 
              success: false, 
              error: apiError?.message || apiError?.response?.data?.detail || '网络错误' 
            })
            setBatchPptProgressInfo(prev => ({
              ...prev,
              results: [...prev.results, { sectionId: section.id, sectionTitle: section.title, success: false, error: apiError?.message || '网络错误' }]
            }))
            // 继续处理下一个
            if (i < sections.length - 1) {
              await new Promise(resolve => setTimeout(resolve, REQUEST_INTERVAL))
            }
            continue
          }
          
          console.log(`[${sectionNum}/${sections.length}] 小节${section.id}生成结果：`, result)
          
          // 检查API响应是否有效
          if (!result || !result.data) {
            console.error(`[${sectionNum}/${sections.length}] API响应无效：`, result)
            results.push({ 
              sectionId: section.id, 
              sectionTitle: section.title, 
              success: false,
              error: 'API响应无效'
            })
            setBatchPptProgressInfo(prev => ({
              ...prev,
              results: [...prev.results, { sectionId: section.id, sectionTitle: section.title, success: false, error: 'API响应无效' }]
            }))
            if (i < sections.length - 1) {
              await new Promise(resolve => setTimeout(resolve, REQUEST_INTERVAL))
            }
            continue
          }
          
          // 检查HTTP状态和业务状态
          if (result.status === 200 && result.data?.success) {
            const slidesCount = result.data?.data?.slide_count || 0
            results.push({ 
              sectionId: section.id, 
              sectionTitle: section.title, 
              success: true,
              slidesCount
            })
            
            // 更新结果列表
            setBatchPptProgressInfo(prev => ({
              ...prev,
              progress: Math.round((sectionNum / sections.length) * 100),
              message: `已完成第${sectionNum}/${sections.length}个：${section.title}`,
              results: [...prev.results, { sectionId: section.id, sectionTitle: section.title, success: true }]
            }))
            
            // 记录第一个成功的小节用于预览
            if (!firstSuccessSectionId) {
              firstSuccessSectionId = section.id
              firstSuccessSectionTitle = section.title
            }
            
            // 总是记录最后一个成功的结果用于预览
            lastSuccessResult = {
              sectionId: section.id,
              sectionTitle: section.title,
              slides: result?.data?.data?.slides || []
            }
          } else {
            // API返回了错误（HTTP 200但业务失败，或HTTP 4xx/5xx）
            const errorMsg = result.data?.detail || result.data?.message || result.data?.error || '生成失败'
            console.error(`[${sectionNum}/${sections.length}] 业务错误：`, errorMsg)
            results.push({ 
              sectionId: section.id, 
              sectionTitle: section.title, 
              success: false,
              error: errorMsg
            })
            // 更新结果列表（包含失败）
            setBatchPptProgressInfo(prev => ({
              ...prev,
              results: [...prev.results, { sectionId: section.id, sectionTitle: section.title, success: false, error: errorMsg }]
            }))
          }
        } catch (error) {
          console.error(`[${sectionNum}/${sections.length}] 小节${section.id}生成出错：`, error)
          results.push({ 
            sectionId: section.id, 
            sectionTitle: section.title, 
            success: false, 
            error: error?.message || '网络错误'
          })
          // 更新结果列表（包含错误）
          setBatchPptProgressInfo(prev => ({
            ...prev,
            results: [...prev.results, { sectionId: section.id, sectionTitle: section.title, success: false, error: error?.message }]
          }))
        }
        
        // 在请求之间添加间隔（除了最后一个）
        if (i < sections.length - 1) {
          await new Promise(resolve => setTimeout(resolve, REQUEST_INTERVAL))
        }
      }
      
      console.log('所有小节PPT生成结果：', results)
      
      const successCount = results.filter(r => r.success).length
      const totalCount = results.length
      
      // 更新最终状态
      setBatchPptProgressInfo(prev => ({
        ...prev,
        status: 'completed',
        progress: 100,
        message: successCount > 0 ? `${successCount}/${totalCount} 个小节PPT生成成功` : '所有小节PPT生成失败'
      }))
      
      if (successCount > 0) {
        message.success(`${chapterTitle}：${successCount}/${totalCount} 个小节PPT生成成功`)
      } else {
        message.error(`${chapterTitle}：所有小节PPT生成失败`)
      }
      
      // 刷新数据
      await fetchData()
      
      // 显示最后一个成功的小节PPT预览（确保用户看到最新的内容）
      let previewData = null
      if (lastSuccessResult) {
        previewData = {
          visible: true,
          slides: lastSuccessResult.slides,
          title: lastSuccessResult.sectionTitle
        }
      } else if (firstSuccessSectionId) {
        // 如果没有最后一个成功的结果但有第一个成功的，获取并显示
        const result = await learningPlanAPI.getSectionPPT(firstSuccessSectionId)
        if (result?.data?.success && result?.data?.data?.slides?.length > 0) {
          previewData = {
            visible: true,
            slides: result.data.data.slides,
            title: firstSuccessSectionTitle
          }
        }
      }
      
      // 延迟关闭弹窗，让用户看到最终结果
      setTimeout(() => {
        setShowBatchPPTProgress(false)
        if (previewData) {
          setPptModal(previewData)
        }
      }, 1500)
      
    } catch (error) {
      console.error('批量生成PPT失败：', error)
      setBatchPptProgressInfo(prev => ({
        ...prev,
        status: 'error',
        message: error?.message || '批量生成PPT失败'
      }))
      message.error('批量生成PPT失败')
    } finally {
      setGeneratingPPT(prev => {
        const newState = { ...prev }
        delete newState[chapterId]
        return newState
      })
    }
  }

  // 查看节PPT
  const handleViewSectionPPT = async (sectionId, sectionTitle) => {
    setGeneratingPPT(prev => ({ ...prev, [sectionId]: 'viewing' }))
    try {
      const result = await learningPlanAPI.getSectionPPT(sectionId)
      if (result.data?.success && result.data.data?.slides?.length > 0) {
        setPptModal({
          visible: true,
          slides: result.data.data.slides,
          title: sectionTitle
        })
      } else {
        message.warning('暂无可查看的PPT内容')
      }
    } catch (error) {
      message.error('获取节PPT时出错')
    } finally {
      setGeneratingPPT(prev => {
        const newState = { ...prev }
        delete newState[sectionId]
        return newState
      })
    }
  }

  // 生成节PPT
  // 生成节PPT（带流式进度）
  const handleGenerateSectionPPT = (sectionId, sectionTitle) => {
    setGeneratingPPT(prev => ({ ...prev, [sectionId]: 'section' }))
    
    // 打开PPT生成进度弹窗
    setPptProgressInfo({
      sectionId,
      sectionTitle,
      status: 'preparing',
      progress: 0,
      message: '正在准备生成PPT...'
    })
    setShowPPTTProgress(true)
    
    learningPlanAPI.generateSectionPPTStream(
      sectionId,
      // 进度回调
      (progress, msg) => {
        setPptProgressInfo(prev => ({
          ...prev,
          status: 'generating',
          progress,
          message: msg
        }))
      },
      // 完成回调
      (data) => {
        setPptProgressInfo(prev => ({
          ...prev,
          status: 'completed',
          progress: 100,
          message: 'PPT生成成功！'
        }))
        
        setGeneratingPPT(prev => {
          const newState = { ...prev }
          delete newState[sectionId]
          return newState
        })
        
        message.success(`${sectionTitle} PPT生成成功`)
        
        // 刷新数据
        fetchData()
        
        // 关闭进度弹窗并显示PPT预览
        setTimeout(() => {
          setShowPPTTProgress(false)
          if (data?.slides?.length > 0) {
            setPptModal({
              visible: true,
              slides: data.slides,
              title: sectionTitle
            })
          }
        }, 1500)
      },
      // 错误回调
      (errorMsg) => {
        setPptProgressInfo(prev => ({
          ...prev,
          status: 'error',
          message: errorMsg || '生成失败'
        }))
        
        setGeneratingPPT(prev => {
          const newState = { ...prev }
          delete newState[sectionId]
          return newState
        })
        
        message.error(`PPT生成失败: ${errorMsg}`)
        setTimeout(() => setShowPPTTProgress(false), 3000)
      },
      // 取消回调
      (cancelMsg) => {
        console.log('PPT生成被取消:', cancelMsg)
        setPptProgressInfo(prev => ({
          ...prev,
          status: 'cancelled',
          message: cancelMsg || '用户取消了生成'
        }))
        
        setGeneratingPPT(prev => {
          const newState = { ...prev }
          delete newState[sectionId]
          return newState
        })
        
        message.info('已取消PPT生成')
        setTimeout(() => setShowPPTTProgress(false), 2000)
      }
    )
  }
  
  // 取消PPT生成
  const handleCancelPPTGeneration = async () => {
    try {
      await learningPlanAPI.cancelGeneration()
      message.info('正在停止生成...')
    } catch (error) {
      console.error('取消PPT生成失败:', error)
      message.error('取消失败')
    }
  }

  if (loading) {
    return (
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: '50vh', gap: 16 }}>
        <div style={{ width: 24, height: 24, border: '2.5px solid rgba(99,102,241,0.3)', borderTopColor: '#6366f1', borderRadius: '50%', animation: 'spin 0.8s linear infinite' }} />
        <span style={{ color: '#94a3b8' }}>加载中...</span>
        <style>{`@keyframes spin { from{transform:rotate(0)} to{transform:rotate(360deg)} }`}</style>
      </div>
    )
  }

  const progressPct = plan?.total_lessons > 0 ? Math.round((plan.completed_lessons / plan.total_lessons) * 100) : 0

  // 渲染章节视图
  const renderChapterView = () => (
    <div>
      {chapters.map((chapter, chapterIdx) => {
        const isChapterGenerating = generatingPPT[chapter.id] === 'chapter'
        const completedLessonsInChapter = chapter.sections?.reduce((acc, section) => {
          return acc + (section.lessons?.filter(l => l.is_completed).length || 0)
        }, 0) || 0
        const totalLessonsInChapter = chapter.sections?.reduce((acc, section) => {
          return acc + (section.lessons?.length || 0)
        }, 0) || 0

        return (
          <motion.div 
            key={chapter.id}
            initial={{ opacity: 0, y: 16 }} 
            animate={{ opacity: 1, y: 0 }} 
            transition={{ duration: 0.4, delay: chapterIdx * 0.1 }}
            style={{ marginBottom: 16 }}
          >
            <div style={{ 
              borderRadius: 16, 
              background: '#fff', 
              border: '1px solid rgba(226,232,240,0.8)', 
              boxShadow: '0 4px 24px rgba(99,102,241,0.07)',
              overflow: 'hidden'
            }}>
              {/* 章节头部 */}
              <div style={{ 
                padding: '16px 20px', 
                background: 'linear-gradient(135deg,rgba(99,102,241,0.08),rgba(139,92,246,0.04))',
                borderBottom: '1px solid rgba(226,232,240,0.5)'
              }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: 12 }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
                    <div style={{ 
                      width: 40, height: 40, borderRadius: 10, 
                      background: 'linear-gradient(135deg,#6366f1,#8b5cf6)',
                      display: 'flex', alignItems: 'center', justifyContent: 'center',
                      color: '#fff', fontWeight: 700, fontSize: 16
                    }}>
                      {chapter.chapter_number}
                    </div>
                    <div>
                      <h4 style={{ margin: 0, fontSize: 16, fontWeight: 700, color: '#0f172a' }}>
                        {chapter.title}
                      </h4>
                      <div style={{ fontSize: 12, color: '#64748b', marginTop: 2 }}>
                        {chapter.description}
                      </div>
                    </div>
                  </div>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
                    <Tag color="blue" style={{ margin: 0 }}>
                      <ClockCircleOutlined /> {chapter.estimated_minutes || 0} 分钟
                    </Tag>
                    <Button 
                      size="small" 
                      icon={isChapterGenerating ? <LoadingOutlined /> : <FilePptOutlined />}
                      onClick={() => handleGenerateAllSectionsPPT(chapter.id, chapter.title, chapter.sections)}
                      disabled={isChapterGenerating || !chapter.sections?.length}
                      style={{ borderRadius: 8 }}
                    >
                      {isChapterGenerating ? '生成中...' : `为${chapter.sections?.length || 0}个小节生成PPT`}
                    </Button>
                  </div>
                </div>
                {/* 学习目标 */}
                {chapter.learning_objectives?.length > 0 && (
                  <div style={{ marginTop: 10, display: 'flex', flexWrap: 'wrap', gap: 6 }}>
                    {chapter.learning_objectives.slice(0, 3).map((obj, idx) => (
                      <span key={idx} style={{ 
                        padding: '2px 8px', borderRadius: 4, 
                        background: 'rgba(99,102,241,0.1)', 
                        color: '#6366f1', fontSize: 11
                      }}>
                        {obj}
                      </span>
                    ))}
                  </div>
                )}
              </div>

              {/* 节列表 */}
              <Collapse 
                bordered={false} 
                defaultActiveKey={expandedChapters.includes(chapter.id) ? [chapter.id] : []}
                expandIcon={({ isActive }) => <CaretRightOutlined rotate={isActive ? 90 : 0} />}
                style={{ background: '#fff' }}
                onChange={(keys) => {
                  if (keys.includes(chapter.id)) {
                    setExpandedChapters(prev => [...prev, chapter.id])
                  } else {
                    setExpandedChapters(prev => prev.filter(id => id !== chapter.id))
                  }
                }}
              >
                <Panel 
                  header={<span style={{ color: '#64748b', fontSize: 13 }}>查看 {chapter.sections?.length || 0} 个小节</span>}
                  key={chapter.id}
                  style={{ padding: 0 }}
                >
                  {chapter.sections?.map((section, sectionIdx) => {
                    const isSectionGenerating = generatingPPT[section.id] === 'section'
                    return (
                      <div key={section.id} style={{ 
                        padding: '12px 16px 12px 32px', 
                        borderBottom: sectionIdx < chapter.sections.length - 1 ? '1px solid #f1f5f9' : 'none'
                      }}>
                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                          <div style={{ flex: 1 }}>
                            <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 4 }}>
                              <span style={{ 
                                width: 20, height: 20, borderRadius: 4, 
                                background: '#f1f5f9', color: '#64748b',
                                display: 'flex', alignItems: 'center', justifyContent: 'center',
                                fontSize: 11, fontWeight: 600
                              }}>
                                {section.section_number}
                              </span>
                              <span style={{ fontSize: 14, fontWeight: 600, color: '#334155' }}>
                                {section.title}
                              </span>
                            </div>
                            <div style={{ fontSize: 12, color: '#94a3b8', marginLeft: 28 }}>
                              {section.description}
                            </div>
                            {/* 课时列表 */}
                            <div style={{ marginTop: 8, marginLeft: 28, display: 'flex', flexWrap: 'wrap', gap: 8 }}>
                              {section.lessons?.map(lesson => (
                                <Tag 
                                  key={lesson.id}
                                  color={lesson.is_completed ? 'green' : 'default'}
                                  style={{ borderRadius: 4, margin: 0 }}
                                >
                                  {lesson.is_completed && <CheckCircleOutlined style={{ fontSize: 10 }} />}{' '}
                                  {lesson.title} ({lesson.estimated_minutes}分钟)
                                </Tag>
                              ))}
                            </div>
                          </div>
                          {section.ppt_generated && (
                            <Button
                              size="small"
                              icon={<FilePptOutlined />}
                              onClick={() => handleViewSectionPPT(section.id, section.title)}
                              style={{ marginLeft: 8, borderRadius: 6 }}
                            >
                              查看PPT
                            </Button>
                          )}
                          <Button 
                            size="small"
                            icon={isSectionGenerating ? <LoadingOutlined /> : <FilePptOutlined />}
                            onClick={() => handleGenerateSectionPPT(section.id, section.title)}
                            disabled={isSectionGenerating}
                            style={{ marginLeft: 12, borderRadius: 6 }}
                          >
                            {section.ppt_generated ? '重新生成' : '生成PPT'}
                          </Button>
                        </div>
                      </div>
                    )
                  })}
                </Panel>
              </Collapse>
            </div>
          </motion.div>
        )
      })}
    </div>
  )

  // 学习计划生成进度弹窗
  const renderPlanProgressModal = () => {
    const { status, progress, message, chaptersCount, sectionsCount, lessonsCount } = progressInfo
    const isCompleted = status === 'completed'
    const isError = status === 'error'
    const isCancelled = status === 'cancelled'
    const isProcessing = ['preparing', 'analyzing_graph', 'generating_chapters', 'generating_sections', 'creating_plan'].includes(status)
    
    // 计算当前步骤（根据消息内容判断）
    const getCurrentStep = () => {
      if (status === 'preparing') return 0
      if (status === 'analyzing_graph') return 1
      if (status === 'generating_chapters') return 2
      if (status === 'generating_sections') return 3
      if (status === 'creating_plan') return 4
      if (status === 'completed') return 5
      if (status === 'error' || status === 'cancelled') return -1
      return 0
    }
    
    const currentStep = getCurrentStep()
    
    const steps = [
      {
        title: '准备阶段',
        description: '初始化生成环境',
        icon: <RocketOutlined />
      },
      {
        title: '分析图谱',
        description: '解析知识图谱结构',
        icon: <ApartmentOutlined />
      },
      {
        title: '生成章',
        description: 'AI编排章结构',
        icon: <BlockOutlined />
      },
      {
        title: '生成节',
        description: 'AI编排节结构',
        icon: <UnorderedListOutlined />
      },
      {
        title: '创建课时',
        description: '生成学习计划内容',
        icon: <SolutionOutlined />
      }
    ]
    
    // 顶部大图标
    const renderHeaderIcon = () => {
      if (isCompleted) {
        return (
          <div style={{
            width: 100,
            height: 100,
            borderRadius: '50%',
            background: 'linear-gradient(135deg, #52c41a, #73d13d)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            margin: '0 auto 24px',
            boxShadow: '0 8px 32px rgba(82, 196, 26, 0.4)',
            animation: 'pulse 0.6s ease-out'
          }}>
            <CheckCircleOutlined style={{ fontSize: 48, color: '#fff' }} />
          </div>
        )
      }
      if (isError) {
        return (
          <div style={{
            width: 100,
            height: 100,
            borderRadius: '50%',
            background: 'linear-gradient(135deg, #ff4d4f, #ff7875)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            margin: '0 auto 24px',
            boxShadow: '0 8px 32px rgba(255, 77, 79, 0.4)'
          }}>
            <CloseCircleOutlined style={{ fontSize: 48, color: '#fff' }} />
          </div>
        )
      }
      return (
        <div style={{
          width: 100,
          height: 100,
          borderRadius: '50%',
          background: 'linear-gradient(135deg, #6366f1, #8b5cf6)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          margin: '0 auto 24px',
          boxShadow: '0 8px 32px rgba(99, 102, 241, 0.4)',
          animation: 'spin 2s linear infinite'
        }}>
          <LoadingOutlined style={{ fontSize: 48, color: '#fff' }} />
        </div>
      )
    }
    
    return (
      <Modal
        title={null}
        open={showProgressModal}
        closable={isCompleted || isError}
        onCancel={() => isCompleted || isError ? setShowProgressModal(false) : null}
        footer={
          isCompleted ? [
            <Button key="close" type="primary" onClick={() => setShowProgressModal(false)}
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
              查看学习计划
            </Button>
          ] : isError || status === 'cancelled' ? [
            <Button key="close" type="primary" onClick={() => setShowProgressModal(false)} style={{ borderRadius: 10, height: 40 }}>
              关闭
            </Button>
          ] : isProcessing ? [
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
          ] : null
        }
        maskClosable={false}
        width={680}
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
        
        {/* 顶部大图标区域 */}
        {renderHeaderIcon()}
        
        {/* 标题区域 */}
        <div style={{ textAlign: 'center', marginBottom: 28 }}>
          <div style={{ fontSize: 22, fontWeight: 700, color: '#1e293b', marginBottom: 6 }}>
            {isCompleted ? '生成完成！' : status === 'cancelled' ? '已取消' : isError ? '生成失败' : '正在生成学习计划'}
          </div>
          <div style={{ fontSize: 14, color: '#64748b' }}>
            {isCompleted ? '您的学习计划已准备就绪' : status === 'cancelled' ? '生成已停止，不会保存任何数据' : isError ? '请检查网络或稍后重试' : message || '基于知识图谱智能编排中'}
          </div>
        </div>
        
        {/* 进度条区域 */}
        <div style={{ 
          marginBottom: 24,
          padding: '24px 28px',
          background: 'linear-gradient(135deg, rgba(99,102,241,0.03), rgba(139,92,246,0.03))',
          borderRadius: 16,
          border: '1px solid rgba(99,102,241,0.1)'
        }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 12, alignItems: 'center' }}>
            <span style={{ fontSize: 14, fontWeight: 600, color: '#374151' }}>总体进度</span>
            <span style={{ 
              fontSize: 18, 
              fontWeight: 700,
              background: 'linear-gradient(135deg, #6366f1, #8b5cf6)',
              WebkitBackgroundClip: 'text',
              WebkitTextFillColor: 'transparent'
            }}>{progress}%</span>
          </div>
          <Progress 
            percent={progress} 
            status={isCompleted ? 'success' : isError ? 'exception' : 'active'}
            strokeColor={{
              '0%': '#6366f1',
              '100%': '#8b5cf6',
            }}
            trailColor="#e8ecf0"
            showInfo={false}
            strokeWidth={12}
            style={{ marginBottom: 0 }}
          />
        </div>
        
        {/* 步骤指示器 */}
        {isProcessing && (
          <div style={{ 
            display: 'flex',
            gap: 8,
            marginBottom: 24
          }}>
            {steps.map((step, index) => {
              const isActive = index === currentStep
              const isPast = index < currentStep
              const isFuture = index > currentStep
              
              return (
                <div key={index} style={{ flex: 1, textAlign: 'center' }}>
                  <div style={{
                    width: 40,
                    height: 40,
                    borderRadius: '50%',
                    background: isPast ? 'linear-gradient(135deg, #52c41a, #73d13d)' : 
                               isActive ? 'linear-gradient(135deg, #6366f1, #8b5cf6)' : 
                               '#f1f5f9',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    margin: '0 auto 8px',
                    boxShadow: isActive ? '0 4px 16px rgba(99, 102, 241, 0.4)' : 
                              isPast ? '0 4px 12px rgba(82, 196, 26, 0.3)' : 'none',
                    transition: 'all 0.3s'
                  }}>
                    {isPast ? (
                      <CheckCircleOutlined style={{ fontSize: 20, color: '#fff' }} />
                    ) : (
                      <span style={{ 
                        color: isActive ? '#fff' : '#94a3b8', 
                        fontSize: 14,
                        fontWeight: 600
                      }}>
                        {index + 1}
                      </span>
                    )}
                  </div>
                  <div style={{ 
                    fontSize: 11, 
                    fontWeight: isActive ? 600 : 500,
                    color: isPast ? '#52c41a' : isActive ? '#6366f1' : '#94a3b8'
                  }}>
                    {step.title}
                  </div>
                </div>
              )
            })}
          </div>
        )}
        
        {/* 完成后的统计信息 */}
        {isCompleted && (
          <div style={{ 
            display: 'flex', 
            gap: 16, 
            marginBottom: 16 
          }}>
            <div style={{
              flex: 1,
              padding: '18px 16px',
              background: '#fff',
              borderRadius: 14,
              border: '1px solid rgba(226,232,240,0.8)',
              boxShadow: '0 4px 16px rgba(99,102,241,0.06)',
              textAlign: 'center'
            }}>
              <div style={{
                width: 40,
                height: 40,
                borderRadius: 12,
                background: 'linear-gradient(135deg, #6366f1, #8b5cf6)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                margin: '0 auto 12px'
              }}>
                <BookOutlined style={{ fontSize: 20, color: '#fff' }} />
              </div>
              <div style={{ fontSize: 20, fontWeight: 700, color: '#1e293b', marginBottom: 4 }}>
                {chaptersCount}
              </div>
              <div style={{ fontSize: 12, color: '#94a3b8', fontWeight: 500 }}>章节数</div>
            </div>
            
            <div style={{
              flex: 1,
              padding: '18px 16px',
              background: '#fff',
              borderRadius: 14,
              border: '1px solid rgba(226,232,240,0.8)',
              boxShadow: '0 4px 16px rgba(99,102,241,0.06)',
              textAlign: 'center'
            }}>
              <div style={{
                width: 40,
                height: 40,
                borderRadius: 12,
                background: 'linear-gradient(135deg, #8b5cf6, #a78bfa)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                margin: '0 auto 12px'
              }}>
                <BlockOutlined style={{ fontSize: 20, color: '#fff' }} />
              </div>
              <div style={{ fontSize: 20, fontWeight: 700, color: '#1e293b', marginBottom: 4 }}>
                {sectionsCount}
              </div>
              <div style={{ fontSize: 12, color: '#94a3b8', fontWeight: 500 }}>小节数</div>
            </div>
            
            <div style={{
              flex: 1,
              padding: '18px 16px',
              background: '#fff',
              borderRadius: 14,
              border: '1px solid rgba(226,232,240,0.8)',
              boxShadow: '0 4px 16px rgba(99,102,241,0.06)',
              textAlign: 'center'
            }}>
              <div style={{
                width: 40,
                height: 40,
                borderRadius: 12,
                background: 'linear-gradient(135deg, #10b981, #06b6d4)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                margin: '0 auto 12px'
              }}>
                <SolutionOutlined style={{ fontSize: 20, color: '#fff' }} />
              </div>
              <div style={{ fontSize: 20, fontWeight: 700, color: '#1e293b', marginBottom: 4 }}>
                {lessonsCount}
              </div>
              <div style={{ fontSize: 12, color: '#94a3b8', fontWeight: 500 }}>课时数</div>
            </div>
          </div>
        )}
        
        {/* 当前步骤详情 */}
        {isProcessing && message && (
          <div style={{
            padding: '14px 16px',
            background: 'rgba(99,102,241,0.05)',
            borderRadius: 10,
            border: '1px solid rgba(99,102,241,0.1)',
            textAlign: 'center'
          }}>
            <div style={{ fontSize: 13, color: '#6366f1', fontWeight: 500 }}>
              {message}
            </div>
          </div>
        )}
      </Modal>
    )
  }

  // PPT生成进度弹窗
  const renderPPTProgressModal = () => {
    const { sectionTitle, status, progress, message } = pptProgressInfo
    const isCompleted = status === 'completed'
    const isError = status === 'error'
    const isCancelled = status === 'cancelled'
    const isGenerating = status === 'generating' || status === 'preparing'
    
    const isSuccess = status === 'completed'
    
    return (
      <Modal
        title={null}
        open={showPPTTProgress}
        closable={isCompleted || isError || isCancelled}
        onCancel={() => (isCompleted || isError || isCancelled) ? setShowPPTTProgress(false) : null}
        footer={
          isCompleted ? [
            <Button key="close" type="primary" onClick={() => setShowPPTTProgress(false)}
              style={{ 
                borderRadius: 10,
                height: 44,
                paddingLeft: 32,
                paddingRight: 32,
                background: 'linear-gradient(135deg,#10b981,#06b6d4)',
                border: 'none',
                fontWeight: 600,
                fontSize: 15
              }}
            >
              查看PPT
            </Button>
          ] : isError || isCancelled ? [
            <Button key="close" type="primary" onClick={() => setShowPPTTProgress(false)} style={{ borderRadius: 10, height: 40 }}>
              关闭
            </Button>
          ] : isGenerating ? [
            <Button key="cancel" onClick={handleCancelPPTGeneration}
              style={{ 
                borderRadius: 10,
                height: 40,
                borderColor: '#ff4d4f',
                color: '#ff4d4f'
              }}
            >
              停止生成
            </Button>
          ] : null
        }
        maskClosable={false}
        width={500}
        styles={{ body: { padding: '28px' } }}
      >
        {/* 顶部图标 */}
        <div style={{ textAlign: 'center', marginBottom: 20 }}>
          {isCompleted ? (
            <div style={{
              width: 72,
              height: 72,
              borderRadius: '50%',
              background: 'linear-gradient(135deg, #10b981, #06b6d4)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              margin: '0 auto 16px',
              boxShadow: '0 6px 24px rgba(16, 185, 129, 0.4)',
              animation: 'pulse 0.5s ease-out'
            }}>
              <CheckCircleOutlined style={{ fontSize: 36, color: '#fff' }} />
            </div>
          ) : isError || isCancelled ? (
            <div style={{
              width: 72,
              height: 72,
              borderRadius: '50%',
              background: 'linear-gradient(135deg, #ff4d4f, #ff7875)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              margin: '0 auto 16px',
              boxShadow: '0 6px 24px rgba(255, 77, 79, 0.4)'
            }}>
              <CloseCircleOutlined style={{ fontSize: 36, color: '#fff' }} />
            </div>
          ) : (
            <div style={{
              width: 72,
              height: 72,
              borderRadius: '50%',
              background: 'linear-gradient(135deg, #10b981, #06b6d4)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              margin: '0 auto 16px',
              boxShadow: '0 6px 24px rgba(16, 185, 129, 0.3)',
              animation: 'spin 2s linear infinite'
            }}>
              <LoadingOutlined style={{ fontSize: 36, color: '#fff' }} />
            </div>
          )}
        </div>
        
        {/* 标题 */}
        <div style={{ textAlign: 'center', marginBottom: 16 }}>
          <div style={{ fontSize: 18, fontWeight: 700, color: '#1e293b', marginBottom: 4 }}>
            {isCompleted ? 'PPT生成完成！' : isCancelled ? '已取消' : isError ? '生成失败' : `正在生成"${sectionTitle}"PPT`}
          </div>
          <div style={{ fontSize: 13, color: '#64748b' }}>
            {isCompleted ? 'PPT已准备就绪' : isCancelled ? '生成已停止' : isError ? '请检查网络或稍后重试' : message || 'AI正在生成教学内容...'}
          </div>
        </div>
        
        {/* 进度条 */}
        {isGenerating && (
          <div style={{ marginBottom: 0 }}>
            <Progress 
              percent={progress} 
              status="active"
              strokeColor={{
                '0%': '#10b981',
                '100%': '#06b6d4',
              }}
              trailColor="#e8ecf0"
              showInfo={true}
              format={(percent) => `${percent}%`}
              strokeWidth={8}
            />
          </div>
        )}
        
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
      </Modal>
    )
  }

  // 批量PPT生成进度弹窗
  const renderBatchPPTProgressModal = () => {
    const { chapterTitle, totalSections, currentSection, currentSectionTitle, status, progress, message, results } = batchPptProgressInfo
    const isCompleted = status === 'completed'
    const isError = status === 'error'
    const isCancelled = status === 'cancelled'
    const isGenerating = status === 'generating' || status === 'preparing'
    
    return (
      <Modal
        title={null}
        open={showBatchPPTProgress}
        closable={isCompleted || isError || isCancelled}
        onCancel={() => (isCompleted || isError || isCancelled) ? setShowBatchPPTProgress(false) : null}
        footer={
          isCompleted ? [
            <Button key="close" type="primary" onClick={() => setShowBatchPPTProgress(false)}
              style={{ 
                borderRadius: 10,
                height: 44,
                paddingLeft: 32,
                paddingRight: 32,
                background: 'linear-gradient(135deg,#10b981,#06b6d4)',
                border: 'none',
                fontWeight: 600,
                fontSize: 15
              }}
            >
              完成
            </Button>
          ] : isError || isCancelled ? [
            <Button key="close" type="primary" onClick={() => setShowBatchPPTProgress(false)} style={{ borderRadius: 10, height: 40 }}>
              关闭
            </Button>
          ] : isGenerating ? [
            <Button key="cancel" onClick={() => {
              setBatchPptProgressInfo(prev => ({ ...prev, status: 'cancelled', message: '用户取消了生成' }))
              message.info('已取消批量生成')
            }}
              style={{ 
                borderRadius: 10,
                height: 40,
                borderColor: '#ff4d4f',
                color: '#ff4d4f'
              }}
            >
              停止生成
            </Button>
          ] : null
        }
        maskClosable={false}
        width={520}
        styles={{ body: { padding: '28px' } }}
      >
        {/* 顶部图标 */}
        <div style={{ textAlign: 'center', marginBottom: 20 }}>
          {isCompleted ? (
            <div style={{
              width: 72,
              height: 72,
              borderRadius: '50%',
              background: 'linear-gradient(135deg, #10b981, #06b6d4)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              margin: '0 auto 16px',
              boxShadow: '0 6px 24px rgba(16, 185, 129, 0.4)',
              animation: 'pulse 0.5s ease-out'
            }}>
              <CheckCircleOutlined style={{ fontSize: 36, color: '#fff' }} />
            </div>
          ) : isError || isCancelled ? (
            <div style={{
              width: 72,
              height: 72,
              borderRadius: '50%',
              background: 'linear-gradient(135deg, #ff4d4f, #ff7875)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              margin: '0 auto 16px',
              boxShadow: '0 6px 24px rgba(255, 77, 79, 0.4)'
            }}>
              <CloseCircleOutlined style={{ fontSize: 36, color: '#fff' }} />
            </div>
          ) : (
            <div style={{
              width: 72,
              height: 72,
              borderRadius: '50%',
              background: 'linear-gradient(135deg, #10b981, #06b6d4)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              margin: '0 auto 16px',
              boxShadow: '0 6px 24px rgba(16, 185, 129, 0.3)',
              animation: 'spin 2s linear infinite'
            }}>
              <LoadingOutlined style={{ fontSize: 36, color: '#fff' }} />
            </div>
          )}
        </div>
        
        {/* 标题 */}
        <div style={{ textAlign: 'center', marginBottom: 16 }}>
          <div style={{ fontSize: 18, fontWeight: 700, color: '#1e293b', marginBottom: 4 }}>
            {isCompleted ? '全部PPT生成完成！' : isCancelled ? '已取消' : isError ? '生成失败' : `正在生成"${chapterTitle}"章节PPT`}
          </div>
          <div style={{ fontSize: 13, color: '#64748b' }}>
            {isCompleted ? message : isCancelled ? '生成已停止' : isError ? '请检查网络或稍后重试' : message || '正在批量生成小节PPT...'}
          </div>
        </div>
        
        {/* 进度条 */}
        {isGenerating && (
          <div style={{ marginBottom: 16 }}>
            <Progress 
              percent={progress} 
              status="active"
              strokeColor={{
                '0%': '#10b981',
                '100%': '#06b6d4',
              }}
              trailColor="#e8ecf0"
              showInfo={true}
              format={(percent) => `${percent}%`}
              strokeWidth={8}
            />
          </div>
        )}
        
        {/* 小节进度列表 */}
        <div style={{ maxHeight: 200, overflowY: 'auto', marginTop: 12 }}>
          {batchPptProgressInfo.results.length > 0 ? (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
              {batchPptProgressInfo.results.map((result, idx) => (
                <div key={idx} style={{ 
                  display: 'flex', 
                  alignItems: 'center', 
                  gap: 8,
                  padding: '8px 12px',
                  background: result.success ? 'rgba(16, 185, 129, 0.08)' : 'rgba(255, 77, 79, 0.08)',
                  borderRadius: 8,
                  fontSize: 13
                }}>
                  {result.success ? (
                    <CheckCircleOutlined style={{ color: '#10b981', fontSize: 16 }} />
                  ) : (
                    <CloseCircleOutlined style={{ color: '#ff4d4f', fontSize: 16 }} />
                  )}
                  <span style={{ flex: 1, color: '#374151' }}>{result.sectionTitle}</span>
                  <span style={{ color: result.success ? '#10b981' : '#ff4d4f', fontSize: 12 }}>
                    {result.success ? '成功' : (result.error || '失败')}
                  </span>
                </div>
              ))}
              {/* 显示当前正在处理的小节 */}
              {currentSection > batchPptProgressInfo.results.length && currentSectionTitle && (
                <div style={{ 
                  display: 'flex', 
                  alignItems: 'center', 
                  gap: 8,
                  padding: '8px 12px',
                  background: 'rgba(99, 102, 241, 0.08)',
                  borderRadius: 8,
                  fontSize: 13
                }}>
                  <LoadingOutlined style={{ color: '#6366f1', fontSize: 16 }} />
                  <span style={{ flex: 1, color: '#374151' }}>{currentSectionTitle}</span>
                  <span style={{ color: '#6366f1', fontSize: 12 }}>处理中...</span>
                </div>
              )}
            </div>
          ) : isGenerating ? (
            <div style={{ textAlign: 'center', padding: 20, color: '#64748b' }}>
              准备开始生成 {totalSections} 个小节的PPT...
            </div>
          ) : null}
        </div>
        
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
      </Modal>
    )
  }

  // 渲染传统课时视图
  const renderLessonView = () => (
    <div style={{ position: 'relative' }}>
      {/* Timeline line */}
      <div style={{ position: 'absolute', left: 20, top: 24, bottom: 24, width: 2, background: 'linear-gradient(180deg,#6366f1 0%,#c4b5fd 100%)', borderRadius: 1 }} />

      {lessons.map((lesson, idx) => {
        const isCompleted = lesson.is_completed
        const isNext      = lesson.is_next
        const isLocked    = !isCompleted && !isNext && idx > 0 && !lessons.slice(0, idx).every(l => l.is_completed)

        const circleGrad = isCompleted ? 'linear-gradient(135deg,#10b981,#06b6d4)' : isNext ? 'linear-gradient(135deg,#6366f1,#8b5cf6)' : 'linear-gradient(135deg,#94a3b8,#cbd5e1)'

        return (
          <motion.div key={lesson.id} initial={{ opacity: 0, x: -16 }} animate={{ opacity: 1, x: 0 }} transition={{ duration: 0.4, delay: idx * 0.07 }}
            style={{ display: 'flex', gap: 20, marginBottom: 16, alignItems: 'flex-start' }}>
            {/* Circle */}
            <div style={{ width: 42, height: 42, borderRadius: '50%', background: circleGrad, display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0, boxShadow: isNext ? '0 4px 16px rgba(99,102,241,0.4)' : isCompleted ? '0 4px 12px rgba(16,185,129,0.35)' : '0 2px 8px rgba(148,163,184,0.3)', zIndex: 1 }}>
              {isCompleted
                ? <CheckCircleOutlined style={{ color: '#fff', fontSize: 16 }} />
                : isLocked
                  ? <LockOutlined style={{ color: '#fff', fontSize: 13 }} />
                  : <span style={{ color: '#fff', fontWeight: 800, fontSize: 13 }}>{lesson.lesson_number}</span>}
            </div>

            {/* Card */}
            <div style={{
              flex: 1, padding: '16px 20px', borderRadius: 14,
              background: isNext ? 'linear-gradient(135deg,rgba(99,102,241,0.05),rgba(139,92,246,0.04))' : '#fafbfc',
              border: `1.5px solid ${isNext ? 'rgba(99,102,241,0.25)' : 'rgba(226,232,240,0.8)'}`,
              display: 'flex', justifyContent: 'space-between', alignItems: 'center',
              boxShadow: isNext ? '0 4px 20px rgba(99,102,241,0.08)' : '0 1px 6px rgba(0,0,0,0.03)',
              transition: 'all 0.2s',
            }}>
              <div>
                <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 8 }}>
                  <span style={{ fontSize: 14.5, fontWeight: isNext ? 700 : 600, color: isCompleted ? '#94a3b8' : '#0f172a' }}>{lesson.title}</span>
                  {isNext && <span style={{ padding: '2px 10px', borderRadius: 99, background: 'linear-gradient(135deg,#6366f1,#8b5cf6)', color: '#fff', fontSize: 11, fontWeight: 700 }}>推荐</span>}
                  {isCompleted && <span style={{ padding: '2px 10px', borderRadius: 99, background: 'rgba(16,185,129,0.1)', color: '#10b981', fontSize: 11, fontWeight: 700 }}>已完成</span>}
                </div>
                <div style={{ display: 'flex', gap: 12, flexWrap: 'wrap', alignItems: 'center' }}>
                  <span style={{ fontSize: 12.5, color: '#94a3b8', display: 'flex', alignItems: 'center', gap: 4 }}>
                    <ClockCircleOutlined style={{ fontSize: 11 }} /> {lesson.estimated_minutes} 分钟
                  </span>
                  {lesson.knowledge_points?.map(kp => (
                    <span key={kp} style={{ padding: '2px 8px', borderRadius: 99, background: 'rgba(99,102,241,0.07)', color: '#6366f1', fontSize: 11.5, fontWeight: 500 }}>{kp}</span>
                  ))}
                </div>
              </div>

              {isCompleted ? (
                <div style={{ width: 32, height: 32, borderRadius: 10, background: 'rgba(16,185,129,0.1)', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                  <CheckCircleOutlined style={{ color: '#10b981', fontSize: 16 }} />
                </div>
              ) : isNext ? (
                <button onClick={() => handleStartLesson(lesson.id)} style={{
                  padding: '8px 18px', borderRadius: 10, border: 'none',
                  background: 'linear-gradient(135deg,#6366f1,#8b5cf6)',
                  color: '#fff', fontSize: 13, fontWeight: 700, cursor: 'pointer',
                  boxShadow: '0 4px 12px rgba(99,102,241,0.35)', transition: 'all 0.2s',
                }}>
                  开始学习
                </button>
              ) : (
                <div style={{ width: 32, height: 32, borderRadius: 10, background: 'rgba(148,163,184,0.1)', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                  <LockOutlined style={{ color: '#94a3b8', fontSize: 14 }} />
                </div>
              )}
            </div>
          </motion.div>
        )
      })}
    </div>
  )

  return (
    <motion.div initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.4 }}>

      {/* Header card */}
      <div style={{ borderRadius: 20, padding: 28, marginBottom: 24, background: 'linear-gradient(135deg,#6366f1,#8b5cf6)', position: 'relative', overflow: 'hidden', boxShadow: '0 12px 40px rgba(99,102,241,0.3)' }}>
        <div style={{ position: 'absolute', top: -60, right: -60, width: 240, height: 240, background: 'rgba(255,255,255,0.07)', borderRadius: '50%' }} />
        <div style={{ position: 'absolute', bottom: -40, left: -20, width: 160, height: 160, background: 'rgba(6,182,212,0.15)', borderRadius: '50%' }} />
        <div style={{ position: 'relative', zIndex: 1 }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: 16 }}>
            <div>
              <h2 style={{ margin: '0 0 6px', fontSize: 20, fontWeight: 800, color: '#fff' }}>{plan?.title}</h2>
              <div style={{ display: 'flex', gap: 20, flexWrap: 'wrap', marginTop: 12 }}>
                {[
                  { icon: <ClockCircleOutlined />, text: `每周 ${plan?.weekly_hours} 小时` },
                  { icon: <BookOutlined />,        text: `共 ${plan?.total_lessons} 课时` },
                  { icon: <CheckCircleOutlined />, text: `已完成 ${plan?.completed_lessons} 课时` },
                ].map((item, i) => (
                  <div key={i} style={{ display: 'flex', alignItems: 'center', gap: 6, color: 'rgba(255,255,255,0.85)', fontSize: 13.5 }}>
                    {item.icon} {item.text}
                  </div>
                ))}
              </div>
            </div>
            {/* 根据是否有学习计划显示不同按钮 */}
            {!goal?.plan_id || lessons.length === 0 ? (
              <button onClick={handleOpenGenerateModal}
                style={{
                  display: 'flex', alignItems: 'center', gap: 8,
                  padding: '12px 24px', borderRadius: 12, border: 'none',
                  background: 'rgba(255,255,255,0.25)', backdropFilter: 'blur(10px)',
                  color: '#fff', fontSize: 14, fontWeight: 700, cursor: 'pointer',
                  boxShadow: '0 4px 16px rgba(0,0,0,0.2)', transition: 'all 0.2s',
                }}
                onMouseEnter={e => { e.currentTarget.style.background = 'rgba(255,255,255,0.35)' }}
                onMouseLeave={e => { e.currentTarget.style.background = 'rgba(255,255,255,0.25)' }}
              >
                {generatingPlan ? <LoadingOutlined /> : <RocketOutlined />} {generatingPlan ? '正在生成...' : '生成学习计划'}
              </button>
            ) : (
              <div style={{ display: 'flex', gap: 12 }}>
                <button onClick={handleContinueLearning}
                  style={{
                    display: 'flex', alignItems: 'center', gap: 8,
                    padding: '12px 24px', borderRadius: 12, border: 'none',
                    background: 'rgba(255,255,255,0.2)', backdropFilter: 'blur(10px)',
                    color: '#fff', fontSize: 14, fontWeight: 700, cursor: 'pointer',
                    boxShadow: '0 4px 16px rgba(0,0,0,0.15)', transition: 'all 0.2s',
                  }}
                  onMouseEnter={e => { e.currentTarget.style.background = 'rgba(255,255,255,0.3)' }}
                  onMouseLeave={e => { e.currentTarget.style.background = 'rgba(255,255,255,0.2)' }}
                >
                  <PlayCircleOutlined /> 继续学习
                </button>
                <button onClick={handleOpenGenerateModal}
                  style={{
                    display: 'flex', alignItems: 'center', gap: 8,
                    padding: '12px 24px', borderRadius: 12, border: '2px solid rgba(255,255,255,0.5)',
                    background: 'transparent', backdropFilter: 'blur(10px)',
                    color: '#fff', fontSize: 14, fontWeight: 700, cursor: 'pointer',
                    transition: 'all 0.2s',
                  }}
                  onMouseEnter={e => { e.currentTarget.style.background = 'rgba(255,255,255,0.15)'; e.currentTarget.style.borderColor = 'rgba(255,255,255,0.8)' }}
                  onMouseLeave={e => { e.currentTarget.style.background = 'transparent'; e.currentTarget.style.borderColor = 'rgba(255,255,255,0.5)' }}
                >
                  {generatingPlan ? <LoadingOutlined /> : <RocketOutlined />} {generatingPlan ? '正在生成...' : '重新生成'}
                </button>
              </div>
            )}
          </div>

          {/* Progress bar */}
          <div style={{ marginTop: 20 }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 8 }}>
              <span style={{ color: 'rgba(255,255,255,0.75)', fontSize: 13 }}>总体进度</span>
              <span style={{ color: '#fff', fontWeight: 700, fontSize: 14 }}>{progressPct}%</span>
            </div>
            <div style={{ height: 8, background: 'rgba(255,255,255,0.2)', borderRadius: 4, overflow: 'hidden' }}>
              <div style={{ width: `${progressPct}%`, height: '100%', background: 'rgba(255,255,255,0.9)', borderRadius: 4, transition: 'width 0.6s ease' }} />
            </div>
          </div>
          
          {/* 生成进度条 */}
          {generatingPlan && (
            <div style={{ marginTop: 16 }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 8 }}>
                <span style={{ color: 'rgba(255,255,255,0.75)', fontSize: 13 }}>AI生成中</span>
                <span style={{ color: '#fff', fontWeight: 700, fontSize: 14 }}>{generatingProgress}%</span>
              </div>
              <div style={{ height: 8, background: 'rgba(255,255,255,0.2)', borderRadius: 4, overflow: 'hidden' }}>
                <div style={{ width: `${generatingProgress}%`, height: '100%', background: 'linear-gradient(90deg, #10b981, #06b6d4)', borderRadius: 4, transition: 'width 0.3s ease' }} />
              </div>
              {generatingMessage && (
                <div style={{ marginTop: 8, fontSize: 12, color: 'rgba(255,255,255,0.8)' }}>
                  {generatingMessage}
                </div>
              )}
            </div>
          )}
        </div>
      </div>

      {/* 视图切换 */}
      {chapters.length > 0 && (
        <div style={{ marginBottom: 16, display: 'flex', gap: 8 }}>
          <Button 
            type={useChapterView ? 'primary' : 'default'}
            onClick={() => setUseChapterView(true)}
            style={{ borderRadius: 8 }}
          >
            <BookOutlined /> 章节视图 ({chapters.length}章)
          </Button>
          <Button 
            type={!useChapterView ? 'primary' : 'default'}
            onClick={() => setUseChapterView(false)}
            style={{ borderRadius: 8 }}
          >
            <ClockCircleOutlined /> 课时视图
          </Button>
        </div>
      )}

      {/* Lessons timeline / Chapter structure */}
      <div style={{ borderRadius: 20, padding: '8px 24px 24px', background: '#fff', border: '1px solid rgba(226,232,240,0.8)', boxShadow: '0 4px 24px rgba(99,102,241,0.07)', marginBottom: 24 }}>
        <h3 style={{ margin: '20px 0 24px', fontSize: 16, fontWeight: 700, color: '#0f172a' }}>
          {useChapterView ? '章节结构' : '课时安排'}
        </h3>
        {useChapterView && chapters.length > 0 ? (
          renderChapterView()
        ) : lessons.length === 0 ? (
          <div style={{ textAlign: 'center', padding: '40px 20px' }}>
            <Empty description="暂无课时安排" />
            <Button
              type="primary"
              icon={<RocketOutlined />}
              loading={generatingPlan}
              onClick={handleOpenGenerateModal}
              style={{
                marginTop: 20,
                borderRadius: 10,
                height: 44,
                paddingLeft: 24,
                paddingRight: 24,
                background: 'linear-gradient(135deg,#6366f1,#8b5cf6)',
                border: 'none',
                fontWeight: 600,
                fontSize: 15
              }}
            >
              {generatingPlan ? '正在生成...' : '生成学习计划'}
            </Button>
          </div>
        ) : (
          renderLessonView()
        )}
      </div>

      {/* Study suggestion */}
      {plan && (
        <div style={{ borderRadius: 16, padding: '20px 24px', background: 'linear-gradient(135deg,rgba(6,182,212,0.08),rgba(16,185,129,0.06))', border: '1px solid rgba(6,182,212,0.2)' }}>
          <div style={{ display: 'flex', gap: 12, alignItems: 'flex-start' }}>
            <span style={{ fontSize: 20 }}>💡</span>
            <div>
              <div style={{ fontWeight: 700, color: '#0f172a', fontSize: 14, marginBottom: 4 }}>今日学习建议</div>
              <div style={{ color: '#64748b', fontSize: 13.5, lineHeight: 1.6 }}>
                根据你的学习进度，建议继续完成「{lessons.find(l => l.is_next)?.title || '下一课时'}」。
                保持每天学习 {plan.weekly_hours ? Math.round(plan.weekly_hours / 7 * 60) : 45} 分钟，
                预计 {(plan.total_lessons || 0) - (plan.completed_lessons || 0)} 天后完成本学习计划。
              </div>
            </div>
          </div>
        </div>
      )}

      {/* 重置学习进度 - 放在底部不显眼的位置 */}
      {goal?.plan_id && plan?.completed_lessons > 0 && (
        <div style={{ textAlign: 'center', marginTop: 16, marginBottom: 24 }}>
          <button
            onClick={() => setShowResetModal(true)}
            style={{
              background: 'none',
              border: 'none',
              color: '#94a3b8',
              fontSize: 12,
              cursor: 'pointer',
              padding: '4px 8px',
              borderRadius: 4,
              transition: 'all 0.2s',
            }}
            onMouseEnter={e => { e.currentTarget.style.color = '#64748b' }}
            onMouseLeave={e => { e.currentTarget.style.color = '#94a3b8' }}
          >
            重置学习进度
          </button>
        </div>
      )}

      {/* 重置进度确认弹窗 */}
      <Modal
        title={<div style={{ fontSize: 16, fontWeight: 600 }}>确认重置</div>}
        open={showResetModal}
        onCancel={() => setShowResetModal(false)}
        onOk={handleResetProgress}
        okText="确认重置"
        cancelText="取消"
        okButtonProps={{ danger: true }}
      >
        <div style={{ padding: '8px 0' }}>
          <div style={{ color: '#64748b', fontSize: 14, lineHeight: 1.6 }}>
            确定要重置学习进度吗？此操作将：
          </div>
          <ul style={{ color: '#64748b', fontSize: 14, lineHeight: 1.8, marginTop: 12, paddingLeft: 20 }}>
            <li>将所有已完成的课时标记为未完成</li>
            <li>学习计划结构将保留</li>
            <li>此操作不可撤销</li>
          </ul>
        </div>
      </Modal>

      {/* PPT预览弹窗 */}
      <Modal
        title={pptModal.title}
        open={pptModal.visible}
        onCancel={() => setPptModal({ visible: false, slides: [], title: '' })}
        footer={null}
        width={800}
        style={{ top: 20 }}
      >
        <div style={{ maxHeight: '70vh', overflow: 'auto' }}>
          {pptModal.slides?.map((slide, idx) => {
            // 解析content：兼容字符串和JSON对象格式
            const contentObj = typeof slide.content === 'object' && slide.content !== null ? slide.content : null
            const contentStr = typeof slide.content === 'string' ? slide.content : ''
            
            // 类型标签颜色
            const typeColorMap = { cover: 'purple', intro: 'orange', concept: 'blue', content: 'cyan', example: 'green', comparison: 'geekblue', exercise: 'red', summary: 'green', ending: 'gold', guide: 'purple' }
            const typeLabelMap = { cover: '封面', intro: '导入', concept: '概念', content: '讲解', example: '案例', comparison: '对比', exercise: '练习', summary: '总结', ending: '结束', guide: '导览' }
            const layoutLabel = slide.layout ? ` · ${slide.layout}` : ''

            return (
              <div key={idx} style={{ 
                marginBottom: 16, padding: 16, border: '1px solid #e2e8f0', 
                borderRadius: 8, background: '#f8fafc'
              }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 8 }}>
                  <Tag color={typeColorMap[slide.type] || 'blue'}>
                    {typeLabelMap[slide.type] || slide.type}{layoutLabel}
                  </Tag>
                  <span style={{ fontWeight: 600, color: '#1e293b' }}>{slide.title}</span>
                </div>
                
                {/* 结构化内容渲染 */}
                {contentObj ? (
                  <div style={{ fontSize: 13, color: '#475569' }}>
                    {/* 封面页 */}
                    {contentObj.title && <div style={{ fontWeight: 600, fontSize: 15, marginBottom: 6 }}>{contentObj.title}</div>}
                    {contentObj.subtitle && <div style={{ color: '#64748b', marginBottom: 8 }}>{contentObj.subtitle}</div>}
                    {contentObj.objectives && (
                      <div style={{ marginBottom: 8 }}>
                        <span style={{ fontWeight: 600, color: '#6366f1' }}>学习目标：</span>
                        {contentObj.objectives.join('、')}
                      </div>
                    )}
                    {/* 导入页 */}
                    {contentObj.scene && <div style={{ marginBottom: 6 }}><span style={{ fontWeight: 600 }}>场景：</span>{contentObj.scene}</div>}
                    {contentObj.question && <div style={{ marginBottom: 6, color: '#6366f1' }}><span style={{ fontWeight: 600 }}>思考：</span>{contentObj.question}</div>}
                    {/* 概念页 */}
                    {contentObj.definition && <div style={{ marginBottom: 6 }}><span style={{ fontWeight: 600 }}>定义：</span>{contentObj.definition}</div>}
                    {contentObj.key_attributes && (
                      <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', marginBottom: 6 }}>
                        {contentObj.key_attributes.map((a, i) => (
                          <span key={i} style={{ background: '#EEF2FF', padding: '2px 8px', borderRadius: 4, fontSize: 12 }}>{a.label}: {a.value}</span>
                        ))}
                      </div>
                    )}
                    {/* 内容页 */}
                    {contentObj.main_idea && <div style={{ fontWeight: 600, marginBottom: 6 }}>💡 {contentObj.main_idea}</div>}
                    {contentObj.points && contentObj.points.map((p, i) => (
                      <div key={i} style={{ marginLeft: 12, marginBottom: 4 }}>• <span style={{ fontWeight: 600 }}>{p.title}</span>: {p.detail}</div>
                    ))}
                    {/* 案例页 */}
                    {contentObj.case_title && <div style={{ fontWeight: 600, color: '#059669', marginBottom: 4 }}>📂 {contentObj.case_title}</div>}
                    {contentObj.background && <div style={{ marginBottom: 4, color: '#64748b' }}>{contentObj.background}</div>}
                    {contentObj.steps && contentObj.steps.map((s, i) => (
                      <div key={i} style={{ marginLeft: 12, marginBottom: 4 }}>{i+1}. {s.label}: {s.content}</div>
                    ))}
                    {contentObj.insight && <div style={{ color: '#92400E', marginTop: 4 }}>💡 {contentObj.insight}</div>}
                    {/* 对比页 */}
                    {contentObj.items && contentObj.items.map((item, i) => (
                      <div key={i} style={{ marginLeft: 12, marginBottom: 6 }}>
                        <span style={{ fontWeight: 600, color: i === 0 ? '#6366f1' : '#ef4444' }}>{item.name}</span>
                        {item.features && `：${item.features.join('、')}`}
                      </div>
                    ))}
                    {contentObj.key_difference && <div style={{ color: '#5B21B6', fontWeight: 600 }}>⚡ {contentObj.key_difference}</div>}
                    {/* 总结页 */}
                    {contentObj.key_takeaways && contentObj.key_takeaways.map((t, i) => (
                      <div key={i} style={{ marginLeft: 12, marginBottom: 4 }}>✓ {t.point} {t.keyword && <span style={{ color: '#6366f1', fontSize: 12 }}>[{t.keyword}]</span>}</div>
                    ))}
                    {/* 结束页 */}
                    {contentObj.message && <div style={{ fontWeight: 600 }}>{contentObj.message}</div>}
                    {contentObj.next_topic && <div style={{ color: '#64748b' }}>📖 下节：{contentObj.next_topic}</div>}
                    {contentObj.review_tip && <div style={{ color: '#94a3b8', fontSize: 12 }}>{contentObj.review_tip}</div>}
                    {/* 其他未识别字段回退 */}
                    {!contentObj.title && !contentObj.scene && !contentObj.definition && !contentObj.main_idea && !contentObj.case_title && !contentObj.items && !contentObj.key_takeaways && !contentObj.message && (
                      <pre style={{ fontSize: 12, whiteSpace: 'pre-wrap', color: '#64748b' }}>{JSON.stringify(contentObj, null, 2)}</pre>
                    )}
                  </div>
                ) : (
                  <div style={{ fontSize: 13, color: '#475569', whiteSpace: 'pre-wrap' }}>{contentStr}</div>
                )}
                
                {slide.notes && (
                  <div style={{ marginTop: 8, fontSize: 11, color: '#94a3b8', fontStyle: 'italic' }}>
                    备注: {slide.notes}
                  </div>
                )}
              </div>
            )
          })}
        </div>
      </Modal>

      {/* 学习计划生成进度弹窗 */}
      {renderPlanProgressModal()}

      {/* PPT生成进度弹窗 */}
      {renderPPTProgressModal()}

      {/* 批量PPT生成进度弹窗 */}
      {renderBatchPPTProgressModal()}

      {/* 生成学习计划方式选择弹窗 */}
      <Modal
        title={
          <div style={{ fontWeight: 700, fontSize: 17 }}>
            <RocketOutlined style={{ color: '#6366f1', marginRight: 8 }} />
            选择学习计划生成方式
          </div>
        }
        open={showPlanTypeModal}
        onCancel={() => setShowPlanTypeModal(false)}
        footer={null}
        width={500}
      >
        <div style={{ padding: '16px 0' }}>
          <div style={{ marginBottom: 24, textAlign: 'center' }}>
            <div style={{
              width: 80, height: 80, borderRadius: 20,
              background: 'linear-gradient(135deg,#6366f1,#8b5cf6)',
              display: 'flex', alignItems: 'center', justifyContent: 'center',
              margin: '0 auto 16px', boxShadow: '0 8px 24px rgba(99,102,241,0.3)'
            }}>
              <RocketOutlined style={{ fontSize: 36, color: '#fff' }} />
            </div>
            <p style={{ color: '#64748b', fontSize: 14, margin: 0 }}>
              基于您的知识图谱和学习目标，智能生成个性化学习计划
            </p>
          </div>

          <Space direction="vertical" style={{ width: '100%' }} size={16}>
            <div 
              onClick={() => handleGeneratePlan(true)}
              style={{
                padding: '20px 24px',
                border: '2px solid #e8ecf0',
                borderRadius: 16,
                cursor: 'pointer',
                transition: 'all 0.2s',
                background: '#f8fafc'
              }}
              onMouseEnter={e => {
                e.currentTarget.style.borderColor = '#6366f1'
                e.currentTarget.style.background = 'rgba(99,102,241,0.05)'
              }}
              onMouseLeave={e => {
                e.currentTarget.style.borderColor = '#e8ecf0'
                e.currentTarget.style.background = '#f8fafc'
              }}
            >
              <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 8 }}>
                <div style={{
                  width: 44, height: 44, borderRadius: 12,
                  background: 'linear-gradient(135deg,#6366f1,#8b5cf6)',
                  display: 'flex', alignItems: 'center', justifyContent: 'center'
                }}>
                  <BookOutlined style={{ fontSize: 20, color: '#fff' }} />
                </div>
                <div>
                  <div style={{ fontWeight: 700, fontSize: 15, color: '#1e293b' }}>章节式学习计划（推荐）</div>
                  <div style={{ fontSize: 12, color: '#64748b' }}>AI智能编排章节结构，适合系统性学习</div>
                </div>
              </div>
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8, marginTop: 12 }}>
                <Tag color="purple">AI智能编排</Tag>
                <Tag color="blue">章-节-课时</Tag>
                <Tag color="green">PPT课件</Tag>
              </div>
            </div>

            <div 
              onClick={() => handleGeneratePlan(false)}
              style={{
                padding: '20px 24px',
                border: '2px solid #e8ecf0',
                borderRadius: 16,
                cursor: 'pointer',
                transition: 'all 0.2s',
                background: '#f8fafc'
              }}
              onMouseEnter={e => {
                e.currentTarget.style.borderColor = '#6366f1'
                e.currentTarget.style.background = 'rgba(99,102,241,0.05)'
              }}
              onMouseLeave={e => {
                e.currentTarget.style.borderColor = '#e8ecf0'
                e.currentTarget.style.background = '#f8fafc'
              }}
            >
              <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 8 }}>
                <div style={{
                  width: 44, height: 44, borderRadius: 12,
                  background: 'linear-gradient(135deg,#1890ff,#40a9ff)',
                  display: 'flex', alignItems: 'center', justifyContent: 'center'
                }}>
                  <ClockCircleOutlined style={{ fontSize: 20, color: '#fff' }} />
                </div>
                <div>
                  <div style={{ fontWeight: 700, fontSize: 15, color: '#1e293b' }}>普通学习计划</div>
                  <div style={{ fontSize: 12, color: '#64748b' }}>按知识点顺序生成，简单直接</div>
                </div>
              </div>
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8, marginTop: 12 }}>
                <Tag color="blue">线性排列</Tag>
                <Tag color="default">课时列表</Tag>
              </div>
            </div>
          </Space>
        </div>
      </Modal>
    </motion.div>
  )
}

export default LearningPlan
