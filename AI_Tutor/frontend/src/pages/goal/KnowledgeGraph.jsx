import { useState, useEffect, useCallback, useRef } from 'react'
import { Button, Spin, message, Modal, Typography, Radio, Space, Tag, Drawer, Progress, Tooltip, Empty, Steps } from 'antd'
import { ReloadOutlined, PlayCircleOutlined, InfoCircleOutlined, BookOutlined, ApartmentOutlined, RocketOutlined, BulbOutlined, ExperimentOutlined, FireOutlined, CrownOutlined, FileTextOutlined, LoadingOutlined, CheckCircleOutlined, CloseCircleOutlined, BlockOutlined, ClockCircleOutlined, NodeIndexOutlined, BranchesOutlined, MergeCellsOutlined } from '@ant-design/icons'
import ReactECharts from 'echarts-for-react'
import { useParams } from 'react-router-dom'
import { motion } from 'framer-motion'
import { knowledgeGraphAPI } from '../../utils/api'

const { Title, Text, Paragraph } = Typography

// 5级掌握度配置
const MASTERY_LEVELS = [
  { 
    key: 'sprouting', 
    label: '萌芽', 
    icon: <BulbOutlined />,
    color: '#d9d9d9', 
    borderColor: '#bfbfbf',
    gradient: 'linear-gradient(135deg,#d9d9d9,#f0f0f0)',
    range: '0%',
    description: '尚未开始学习'
  },
  { 
    key: 'learning', 
    label: '入门', 
    icon: <RocketOutlined />,
    color: '#1890ff', 
    borderColor: '#40a9ff',
    gradient: 'linear-gradient(135deg,#1890ff,#40a9ff)',
    range: '1-20%',
    description: '刚刚接触，需要从基础开始'
  },
  { 
    key: 'developing', 
    label: '发展', 
    icon: <ExperimentOutlined />,
    color: '#40a9ff', 
    borderColor: '#69c0ff',
    gradient: 'linear-gradient(135deg,#1890ff,#69c0ff)',
    range: '21-40%',
    description: '初步了解，需要深入学习'
  },
  { 
    key: 'understanding', 
    label: '理解', 
    icon: <BulbOutlined />,
    color: '#fadb14', 
    borderColor: '#ffe58f',
    gradient: 'linear-gradient(135deg,#faad14,#fadb14)',
    range: '41-60%',
    description: '基本理解，需要巩固练习'
  },
  { 
    key: 'proficient', 
    label: '熟练', 
    icon: <FireOutlined />,
    color: '#fa8c16', 
    borderColor: '#ffc53d',
    gradient: 'linear-gradient(135deg,#fa8c16,#ffc53d)',
    range: '61-80%',
    description: '较好掌握，能够独立完成'
  },
  { 
    key: 'mastered', 
    label: '精通', 
    icon: <CrownOutlined />,
    color: '#52c41a', 
    borderColor: '#73d13d',
    gradient: 'linear-gradient(135deg,#52c41a,#73d13d)',
    range: '81-100%',
    description: '完全掌握，可以灵活应用'
  }
]

function StatCard({ label, value, gradient, icon, color }) {
  return (
    <motion.div whileHover={{ y: -3 }}
      style={{
        flex: 1, borderRadius: 16, padding: '20px 24px',
        background: '#fff', border: '1px solid rgba(226,232,240,0.8)',
        boxShadow: '0 4px 20px rgba(99,102,241,0.07)',
        position: 'relative', overflow: 'hidden',
      }}>
      <div style={{ position: 'absolute', bottom: 0, left: 0, right: 0, height: 3, background: gradient }} />
      <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 8 }}>
        <div style={{ 
          width: 28, height: 28, borderRadius: 8, 
          background: gradient, display: 'flex', alignItems: 'center', justifyContent: 'center',
          color: '#fff', fontSize: 14
        }}>
          {icon}
        </div>
        <div style={{ fontSize: 11, fontWeight: 700, letterSpacing: 1, textTransform: 'uppercase', color: '#94a3b8' }}>{label}</div>
      </div>
      <div style={{ fontSize: 36, fontWeight: 800, background: gradient, WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent', lineHeight: 1 }}>{value}</div>
    </motion.div>
  )
}

function getMasteryConfig(mastery) {
  if (mastery >= 81) return MASTERY_LEVELS[5]
  if (mastery >= 61) return MASTERY_LEVELS[4]
  if (mastery >= 41) return MASTERY_LEVELS[3]
  if (mastery >= 21) return MASTERY_LEVELS[2]
  if (mastery >= 1) return MASTERY_LEVELS[1]
  return MASTERY_LEVELS[0]
}

function KnowledgeGraph() {
  const { goalId } = useParams()
  const [loading, setLoading]           = useState(true)
  const [generating, setGenerating] = useState(false)
  const [graphData, setGraphData]       = useState(null)
  const [hasGraph, setHasGraph] = useState(false)
  const [showAssessment, setShowAssessment] = useState(false)
  const [assessmentStep, setAssessmentStep] = useState(0)
  const [assessmentResults, setAssessmentResults] = useState([])
  const [selectedAnswer, setSelectedAnswer] = useState(null)
  const [selectedNode, setSelectedNode] = useState(null)
  const [drawerVisible, setDrawerVisible] = useState(false)
  const [isCancelled, setIsCancelled] = useState(false)
  
  // 关系类型配置
  const RELATION_TYPES = {
    '前置依赖': { color: '#1890ff', bgColor: '#e6f7ff', borderColor: '#91d5ff', label: '前置' },
    '组成关系': { color: '#722ed1', bgColor: '#f9f0ff', borderColor: '#d3adf7', label: '组成' },
    '进阶关系': { color: '#52c41a', bgColor: '#f6ffed', borderColor: '#b7eb8f', label: '进阶' },
    '对立关系': { color: '#ff4d4f', bgColor: '#fff1f0', borderColor: '#ffa39e', label: '对立' },
    '对比关系': { color: '#fa8c16', bgColor: '#fff7e6', borderColor: '#ffd591', label: '对比' },
    '应用关系': { color: '#13c2c2', bgColor: '#e6fffb', borderColor: '#87e8de', label: '应用' },
    '等价关系': { color: '#faad14', bgColor: '#fffbe6', borderColor: '#ffe58f', label: '等价' },
    '关联关系': { color: '#8c8c8c', bgColor: '#f5f5f5', borderColor: '#d9d9d9', label: '关联' },
  }
  
  // 生成进度相关状态
  const [showProgress, setShowProgress] = useState(false)
  const [progressInfo, setProgressInfo] = useState({
    status: '',        // loading_documents | processing_documents | generating_graph | completed | error | cancelled
    progress: 0,
    message: '',
    total: 0,
    current: 0,
    totalChunks: 0,
    chunk: 0,
    totalNodes: 0,
    totalEdges: 0
  })
  const [generationError, setGenerationError] = useState(null)
  
  // 计时器状态
  const [elapsedTime, setElapsedTime] = useState(0)
  const timerRef = useRef(null)
  
  // 计时器逻辑
  useEffect(() => {
    if (showProgress && progressInfo.status !== 'completed' && progressInfo.status !== 'error') {
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
      }
    }
  }, [showProgress, progressInfo.status])
  
  // 重置计时器
  useEffect(() => {
    if (showProgress && progressInfo.status === 'starting') {
      setElapsedTime(0)
    }
  }, [showProgress, progressInfo.status])

  const fetchGraphData = useCallback(async () => {
    setLoading(true)
    try {
      const result = await knowledgeGraphAPI.visualizeByGoal(goalId)
      if (result.data.success) {
        setGraphData(result.data.data)
        setHasGraph(true)
        const stats = result.data.data.mastery_stats || {}
        // 如果所有节点都是萌芽状态，显示测评
        if (stats.sprouting === result.data.data.total_nodes) {
          setShowAssessment(true)
        }
      } else {
        setHasGraph(false)
      }
    } catch { 
      setHasGraph(false)
    }
    finally { setLoading(false) }
  }, [goalId])

  useEffect(() => { fetchGraphData() }, [fetchGraphData])

  // 生成知识图谱（SSE流式版本 - 基于主题的分层生成）
  const handleGenerateGraph = async () => {
    setGenerating(true)
    setShowProgress(true)
    setGenerationError(null)
    setIsCancelled(false)
    setProgressInfo({
      status: 'starting',
      progress: 0,
      message: '正在准备生成知识图谱...',
      total: 0,
      current: 0,
      totalChunks: 0,
      chunk: 0
    })
    
    try {
      // 使用基于主题的分层生成流式接口
      const response = await knowledgeGraphAPI.generateFromGoalStream(goalId)
      
      if (!response.ok) {
        throw new Error('生成请求失败')
      }
      
      const reader = response.body.getReader()
      const decoder = new TextDecoder()
      
      let buffer = ''
      
      while (true) {
        const { done, value } = await reader.read()
        
        if (done) break
        
        buffer += decoder.decode(value, { stream: true })
        
        // 处理SSE数据
        const lines = buffer.split('\n')
        buffer = lines.pop() // 保留未完成的行
        
        for (const line of lines) {
          if (line.startsWith('data: ')) {
            try {
              const data = JSON.parse(line.substring(6))
              
              if (data.error) {
                setGenerationError(data.error)
                setProgressInfo(prev => ({ ...prev, status: 'error', message: data.error }))
              } else if (data.status === 'fallback') {
                // 回退到普通模式
                message.info('未找到学习资料，使用普通模式生成')
                setShowProgress(false)
                const result = await knowledgeGraphAPI.generateFromGoal(goalId)
                if (result.data.success) {
                  message.success('知识图谱生成成功！')
                  fetchGraphData()
                } else {
                  message.error(result.data.message || '生成失败')
                }
                return
              } else if (data.status === 'cancelled') {
                // 生成被取消
                setIsCancelled(true)
                setProgressInfo(prev => ({ ...prev, status: 'cancelled', message: '已取消生成' }))
                message.info('已取消生成')
              } else {
                // 更新进度
                setProgressInfo(prev => ({
                  ...prev,
                  status: data.status,
                  progress: data.progress || prev.progress,
                  message: data.message || prev.message,
                  total: data.total || prev.total,
                  current: data.current || prev.current,
                  totalChunks: data.total_chunks || prev.totalChunks,
                  chunk: data.chunk || prev.chunk,
                  totalNodes: data.result?.total_nodes || data.total_nodes || prev.totalNodes,
                  totalEdges: data.result?.total_edges || data.total_edges || prev.totalEdges
                }))
                
                // 检查是否完成
                if (data.status === 'completed' && data.result) {
                  // 成功完成
                  setTimeout(() => {
                    setShowProgress(false)
                    message.success('知识图谱生成成功！')
                    fetchGraphData()
                  }, 1000)
                }
                
                if (data.status === 'error') {
                  setGenerationError(data.error || '生成过程中出错')
                }
              }
            } catch (e) {
              console.error('解析SSE数据失败:', e)
            }
          }
        }
      }
    } catch (error) {
      console.error('生成知识图谱失败:', error)
      setGenerationError(error.message || '生成知识图谱失败')
      message.error('生成知识图谱失败')
    } finally {
      setGenerating(false)
    }
  }
  
  // 取消生成
  const handleCancelGeneration = async () => {
    try {
      await knowledgeGraphAPI.cancelGeneration()
      setIsCancelled(true)
      message.info('正在停止生成...')
    } catch (error) {
      console.error('取消生成失败:', error)
      message.error('取消失败')
    }
  }
  
  // 关闭进度弹窗
  const handleCloseProgress = () => {
    if (progressInfo.status === 'completed') {
      setShowProgress(false)
      setElapsedTime(0)
    } else if (progressInfo.status === 'error' || !generating || progressInfo.status === 'cancelled') {
      setShowProgress(false)
      setElapsedTime(0)
      setIsCancelled(false)
    }
  }

  const generateAssessmentQuestions = () => {
    if (!graphData?.nodes) return []
    const shuffled = [...graphData.nodes].sort(() => 0.5 - Math.random())
    return shuffled.slice(0, Math.min(5, shuffled.length)).map((node, i) => ({
      id: i, 
      node_id: node.id, 
      node_name: node.name,
      question: `关于"${node.name}"，你现在的掌握程度如何？`,
      options: [
        { value: 90, label: '完全掌握，能够灵活应用', score: 90 },
        { value: 70, label: '基本理解，可以独立完成', score: 70 },
        { value: 50, label: '有些了解，需要更多练习', score: 50 },
        { value: 20, label: '刚刚接触，需要从基础开始', score: 20 },
        { value: 0, label: '完全不了解', score: 0 },
      ],
    }))
  }

  const [localQuestions] = useState(() => generateAssessmentQuestions())

  const handleAnswer = async () => {
    if (!selectedAnswer) { message.warning('请选择一个答案'); return }
    const question = localQuestions[assessmentStep]
    const results = [...assessmentResults, { node_id: question.node_id, node_name: question.node_name, score: selectedAnswer }]
    setAssessmentResults(results)
    if (assessmentStep < localQuestions.length - 1) {
      setAssessmentStep(assessmentStep + 1)
      setSelectedAnswer(null)
    } else {
      try {
        const result = await knowledgeGraphAPI.submitAssessment(goalId, results)
        if (result.data.success) { 
          message.success('测评完成！知识图谱已更新'); 
          setShowAssessment(false); 
          fetchGraphData() 
        }
      } catch { message.error('提交测评失败') }
    }
  }

  const handleNodeClick = (params) => {
    if (params.dataType === 'node') {
      const node = graphData.nodes.find(n => n.id === params.data.id)
      if (node) { setSelectedNode(node); setDrawerVisible(true) }
    }
  }

  const getChartOption = () => {
    if (!graphData) return {}
    
    // 根据关系类型设置边的样式
    const getEdgeStyle = (relation) => {
      const config = RELATION_TYPES[relation] || RELATION_TYPES['关联关系']
      return {
        color: config.color,
        width: 1.5,
        opacity: 0.6,
        curveness: 0.2
      }
    }
    
    // 处理边数据，添加样式
    const processedEdges = (graphData.edges || []).map(edge => ({
      ...edge,
      lineStyle: getEdgeStyle(edge.relation)
    }))
    
    return {
      backgroundColor: 'transparent',
      tooltip: {
        trigger: 'item',
        backgroundColor: 'rgba(15,23,42,0.95)',
        borderColor: 'rgba(99,102,241,0.3)',
        borderWidth: 1,
        borderRadius: 12,
        padding: [12, 16],
        textStyle: { color: '#fff', fontSize: 13 },
        formatter: (params) => {
          if (params.dataType === 'node') {
            const m = params.data.mastery || 0
            const config = getMasteryConfig(m)
            return `
              <div style="font-size:14px;font-weight:600;margin-bottom:6px">${params.data.name}</div>
              <div style="color:#94a3b8;font-size:12px;margin-bottom:4px">${params.data.description || ''}</div>
              <div style="margin-top:8px;padding:6px 10px;background:rgba(255,255,255,0.1);border-radius:6px">
                <span style="color:${config.color}">●</span> ${config.label} ${m.toFixed(0)}%
              </div>
              <div style="color:#64748b;font-size:11px;margin-top:6px">${config.description}</div>
            `
          } else if (params.dataType === 'edge') {
            const relation = params.data.relation || '关联关系'
            const relConfig = RELATION_TYPES[relation] || RELATION_TYPES['关联关系']
            return `
              <div style="display:flex;align-items:center;gap:8px">
                <span style="color:${relConfig.color};font-weight:600">${relation}</span>
              </div>
            `
          }
          return params.name
        },
      },
      legend: {
        show: false,
      },
      series: [{
        type: 'graph',
        layout: 'force',
        data: graphData.nodes || [], 
        links: processedEdges,
        roam: true, 
        draggable: true,
        label: { 
          show: true, 
          position: 'bottom', 
          formatter: '{b}', 
          fontSize: 11, 
          color: '#374151',
          overflow: 'truncate',
          width: 80
        },
        force: { repulsion: 500, edgeLength: 180, gravity: 0.1, layoutAnimation: true },
        lineStyle: { color: 'source', curveness: 0.2, width: 1.5, opacity: 0.5 },
        itemStyle: { borderWidth: 2, borderColor: '#fff' },
        emphasis: { 
          focus: 'adjacency', 
          lineStyle: { width: 3, opacity: 0.8 },
          itemStyle: { shadowBlur: 10, shadowColor: 'rgba(99,102,241,0.3)' }
        },
        categories: graphData.categories?.map(cat => ({ name: cat })) || [],
      }],
    }
  }

  // 节点详情抽屉
  const renderNodeDrawer = () => {
    if (!selectedNode) return null
    const mastery = selectedNode.mastery || 0
    const config = getMasteryConfig(mastery)
    
    return (
      <Drawer 
        title={
          <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
            <div style={{ 
              width: 36, height: 36, borderRadius: 10, 
              background: config.gradient,
              display: 'flex', alignItems: 'center', justifyContent: 'center',
              color: '#fff', fontSize: 16
            }}>
              {config.icon}
            </div>
            <div>
              <div style={{ fontWeight: 700, fontSize: 16 }}>{selectedNode.name}</div>
              <div style={{ fontSize: 11, color: '#64748b' }}>{selectedNode.category}</div>
            </div>
          </div>
        }
        placement="right" 
        onClose={() => setDrawerVisible(false)} 
        open={drawerVisible} 
        width={400}
        styles={{ body: { padding: 20 } }}
      >
        <motion.div initial={{ opacity: 0, x: 20 }} animate={{ opacity: 1, x: 0 }} transition={{ duration: 0.35 }}>
          {/* 掌握度进度 */}
          <div style={{ 
            marginBottom: 24, 
            padding: 20, 
            background: '#f8fafc', 
            borderRadius: 16,
            border: `1px solid ${config.borderColor}30`
          }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                <span style={{ 
                  padding: '4px 12px', 
                  borderRadius: 99, 
                  background: config.gradient, 
                  color: '#fff', 
                  fontSize: 13, 
                  fontWeight: 600
                }}>
                  {config.icon} {config.label}
                </span>
              </div>
              <div style={{ fontSize: 28, fontWeight: 800, color: config.color }}>{Math.round(mastery)}%</div>
            </div>
            <div style={{ height: 8, background: '#e8ecf0', borderRadius: 4, overflow: 'hidden' }}>
              <div style={{ 
                width: `${mastery}%`, 
                height: '100%', 
                background: config.gradient, 
                borderRadius: 4, 
                transition: 'width 0.6s ease' 
              }} />
            </div>
            <div style={{ fontSize: 11, color: '#94a3b8', marginTop: 8 }}>{config.description}</div>
          </div>

          {/* 详细信息 */}
          {selectedNode.description && (
            <div style={{ marginBottom: 20 }}>
              <div style={{ 
                fontSize: 11, fontWeight: 700, color: '#94a3b8', 
                textTransform: 'uppercase', letterSpacing: 1, marginBottom: 10
              }}>知识点描述</div>
              <div style={{ 
                padding: 14, background: '#f8fafc', borderRadius: 10, 
                border: '1px solid rgba(226,232,240,0.8)', 
                fontSize: 14, color: '#374151', lineHeight: 1.6
              }}>{selectedNode.description}</div>
            </div>
          )}

          {/* 知识点属性 */}
          <div style={{ 
            display: 'grid', 
            gridTemplateColumns: '1fr 1fr', 
            gap: 12, 
            marginBottom: 20 
          }}>
            <div style={{ 
              padding: 14, background: '#f8fafc', borderRadius: 10,
              border: '1px solid rgba(226,232,240,0.8)'
            }}>
              <div style={{ fontSize: 10, color: '#94a3b8', marginBottom: 4 }}>难度等级</div>
              <div style={{ fontWeight: 600, color: '#374151', textTransform: 'capitalize' }}>
                {selectedNode.difficulty || 'intermediate'}
              </div>
            </div>
            <div style={{ 
              padding: 14, background: '#f8fafc', borderRadius: 10,
              border: '1px solid rgba(226,232,240,0.8)'
            }}>
              <div style={{ fontSize: 10, color: '#94a3b8', marginBottom: 4 }}>前置依赖</div>
              <div style={{ fontWeight: 600, color: '#374151' }}>
                {(graphData.edges.filter(e => e.target === selectedNode.id).length) || 0} 个
              </div>
            </div>
          </div>

          {/* 相关知识点（按关系类型分组） */}
          {(() => {
            // 收集所有关联的边
            const allEdges = graphData.edges.filter(
              e => e.source === selectedNode.id || e.target === selectedNode.id
            )
            
            // 按关系类型分组
            const grouped = {}
            
            allEdges.forEach(edge => {
              const rel = edge.relation || '关联关系'
              if (!grouped[rel]) grouped[rel] = []
              
              // 获取关联的节点（排除当前节点）
              const relatedNodeId = edge.source === selectedNode.id ? edge.target : edge.source
              const node = graphData.nodes.find(n => n.id === relatedNodeId)
              if (node) grouped[rel].push(node)
            })
            
            const hasRelations = Object.keys(grouped).length > 0
            
            return (
              <div>
                <div style={{ 
                  fontSize: 11, fontWeight: 700, color: '#94a3b8', 
                  textTransform: 'uppercase', letterSpacing: 1, marginBottom: 10
                }}>相关知识点</div>
                {!hasRelations ? (
                  <span style={{ color: '#94a3b8', fontSize: 13 }}>无关联知识点</span>
                ) : (
                  <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
                    {Object.entries(grouped).map(([rel, nodes]) => {
                      const relConfig = RELATION_TYPES[rel] || RELATION_TYPES['关联关系']
                      return (
                        <div key={rel}>
                          <div style={{ 
                            fontSize: 10, color: relConfig.color, fontWeight: 600, 
                            marginBottom: 8, display: 'flex', alignItems: 'center', gap: 4
                          }}>
                            <span style={{ 
                              width: 6, height: 6, borderRadius: '50%', 
                              background: relConfig.color, display: 'inline-block'
                            }} />
                            {rel}
                          </div>
                          <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8 }}>
                            {nodes.map(node => (
                              <Tag 
                                key={node.id}
                                style={{ 
                                  borderRadius: 8, 
                                  padding: '4px 12px',
                                  background: relConfig.bgColor,
                                  border: `1px solid ${relConfig.borderColor}`,
                                  color: relConfig.color,
                                  cursor: 'pointer'
                                }}
                                onClick={() => setSelectedNode(node)}
                              >
                                {node.name}
                              </Tag>
                            ))}
                          </div>
                        </div>
                      )
                    })}
                  </div>
                )}
              </div>
            )
          })()}
        </motion.div>
      </Drawer>
    )
  }

  // 测评弹窗
  const renderAssessmentModal = () => {
    if (localQuestions.length === 0) return null
    const question = localQuestions[assessmentStep]
    const progress = ((assessmentStep + 1) / localQuestions.length) * 100
    return (
      <Modal 
        title={
          <div style={{ fontWeight: 700, fontSize: 17 }}>
            <RocketOutlined style={{ color: '#6366f1', marginRight: 8 }} />
            学习水平测评
          </div>
        }
        open={showAssessment} 
        onCancel={() => setShowAssessment(false)} 
        width={580}
        footer={[
          <Button key="skip" onClick={() => setShowAssessment(false)} style={{ borderRadius: 8 }}>
            稍后测评
          </Button>,
          <Button 
            key="next" 
            type="primary" 
            onClick={handleAnswer} 
            style={{ 
              borderRadius: 8, 
              background: 'linear-gradient(135deg,#6366f1,#8b5cf6)', 
              border: 'none' 
            }}
          >
            {assessmentStep < localQuestions.length - 1 ? '下一题' : '完成测评'}
          </Button>,
        ]}
        closable={false} 
        maskClosable={false}
      >
        <div style={{ marginBottom: 20 }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 8, fontSize: 13, color: '#64748b' }}>
            <span>测评进度</span>
            <span style={{ fontWeight: 600, color: '#6366f1' }}>{assessmentStep + 1} / {localQuestions.length}</span>
          </div>
          <div style={{ height: 5, background: '#f1f5f9', borderRadius: 3, overflow: 'hidden' }}>
            <div style={{ 
              width: `${progress}%`, 
              height: '100%', 
              background: 'linear-gradient(90deg,#6366f1,#8b5cf6)', 
              borderRadius: 3, 
              transition: 'width 0.4s ease' 
            }} />
          </div>
        </div>
        <div style={{ marginBottom: 16 }}>
          <span style={{ 
            padding: '4px 12px', 
            borderRadius: 99, 
            background: 'rgba(99,102,241,0.1)', 
            color: '#6366f1', 
            fontSize: 12, 
            fontWeight: 600
          }}>
            知识点: {question.node_name}
          </span>
        </div>
        <Paragraph style={{ fontSize: 16, fontWeight: 600, color: '#0f172a', marginBottom: 20 }}>
          {question.question}
        </Paragraph>
        <Radio.Group 
          value={selectedAnswer} 
          onChange={e => setSelectedAnswer(e.target.value)} 
          style={{ width: '100%' }}
        >
          <Space direction="vertical" style={{ width: '100%', gap: 10 }}>
            {question.options.map(opt => (
              <Radio.Button 
                key={opt.value} 
                value={opt.value} 
                style={{ 
                  width: '100%', 
                  height: 'auto', 
                  padding: '14px 16px', 
                  textAlign: 'left', 
                  lineHeight: 1.5, 
                  borderRadius: 10,
                  fontSize: 14
                }}
              >
                {opt.label}
              </Radio.Button>
            ))}
          </Space>
        </Radio.Group>
      </Modal>
    )
  }

  // 无图谱时的空状态
  const renderEmptyState = () => (
    <div style={{ 
      display: 'flex', 
      flexDirection: 'column', 
      alignItems: 'center', 
      justifyContent: 'center',
      padding: '60px 20px',
      background: '#fff',
      borderRadius: 20,
      border: '2px dashed #e8ecf0'
    }}>
      <div style={{ 
        width: 80, height: 80, borderRadius: 20, 
        background: 'linear-gradient(135deg,#6366f1,#8b5cf6)',
        display: 'flex', alignItems: 'center', justifyContent: 'center',
        marginBottom: 24, boxShadow: '0 8px 24px rgba(99,102,241,0.3)'
      }}>
        <ApartmentOutlined style={{ fontSize: 36, color: '#fff' }} />
      </div>
      <Title level={4} style={{ margin: '0 0 8px 0', color: '#1e293b' }}>
        尚未生成知识图谱
      </Title>
      <Paragraph style={{ color: '#64748b', marginBottom: 24, textAlign: 'center', maxWidth: 400 }}>
        根据您的学习目标，智能构建知识图谱，清晰呈现知识点之间的逻辑关系和学习路径
      </Paragraph>
      <Button
        type="primary"
        size="large"
        icon={<RocketOutlined />}
        loading={generating}
        onClick={handleGenerateGraph}
        style={{ 
          borderRadius: 12, 
          height: 48,
          paddingLeft: 24,
          paddingRight: 24,
          background: 'linear-gradient(135deg,#6366f1,#8b5cf6)',
          border: 'none',
          fontWeight: 600,
          fontSize: 15
        }}
      >
        {generating ? '正在生成...' : '立即生成知识图谱'}
      </Button>
    </div>
  )
  
  // 格式化时间 mm:ss
  const formatTime = (seconds) => {
    const mins = Math.floor(seconds / 60).toString().padStart(2, '0')
    const secs = (seconds % 60).toString().padStart(2, '0')
    return `${mins}:${secs}`
  }

  // 生成进度弹窗
  const renderProgressModal = () => {
    // 计算当前步骤
    const getCurrentStep = () => {
      const status = progressInfo.status
      // 分层生成流程
      if (status === 'decomposing_categories') return 0  // 分析知识结构
      if (status === 'generating_sub_graphs') return 1  // 生成子图谱
      if (status === 'integrating_graph') return 2      // 整合图谱
      if (status === 'saving_graph') return 3           // 保存图谱
      // 基于文档生成流程（兼容）
      if (status === 'loading_documents') return 0
      if (status === 'processing_documents') return 1
      if (status === 'generating_graph') return 2
      if (status === 'merging_graph') return 3
      if (status === 'completed') return 4
      if (status === 'error') return -1
      return 0
    }
    
    const currentStep = getCurrentStep()
    const isCompleted = progressInfo.status === 'completed'
    const isError = progressInfo.status === 'error'
    const isCancelled = progressInfo.status === 'cancelled'
    const isProcessing = ['decomposing_categories', 'generating_sub_graphs', 'integrating_graph', 'saving_graph', 'loading_documents', 'processing_documents', 'generating_graph', 'merging_graph'].includes(progressInfo.status)
    
    const steps = [
      {
        title: '分析结构',
        description: '拆分知识领域',
        icon: <FileTextOutlined />
      },
      {
        title: '生成子图谱',
        description: '构建各类知识点',
        icon: <BlockOutlined />
      },
      {
        title: '整合图谱',
        description: 'AI融合优化',
        icon: <ApartmentOutlined />
      },
      {
        title: '保存图谱',
        description: '完成知识网络',
        icon: <MergeCellsOutlined />
      }
    ]
    
    // 顶部大图标动画区域
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
        open={showProgress}
        closable={isCompleted || isError || isCancelled}
        onCancel={handleCloseProgress}
        footer={
          isCompleted ? [
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
              查看知识图谱
            </Button>
          ] : isError ? [
            <Button key="close" onClick={handleCloseProgress} style={{ borderRadius: 10, height: 40 }}>
              关闭
            </Button>,
            <Button key="retry" type="primary" onClick={handleGenerateGraph}
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
          ] : isCancelled ? [
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
          @keyframes dots {
            0%, 20% { content: '.'; }
            40% { content: '..'; }
            60%, 100% { content: '...'; }
          }
          @keyframes pulse-dot {
            0%, 100% { opacity: 0.4; transform: scale(0.8); }
            50% { opacity: 1; transform: scale(1); }
          }
        `}</style>
        
        {/* 顶部大图标区域 */}
        {renderHeaderIcon()}
        
        {/* 标题区域 */}
        <div style={{ textAlign: 'center', marginBottom: 28 }}>
          <div style={{ fontSize: 22, fontWeight: 700, color: '#1e293b', marginBottom: 6 }}>
            {isCompleted ? '生成完成！' : isError ? '生成失败' : isCancelled ? '已取消' : '正在生成知识图谱'}
          </div>
          <div style={{ fontSize: 14, color: '#64748b' }}>
            {isCompleted ? '您的知识图谱已准备就绪' : isError ? '请检查网络或稍后重试' : isCancelled ? '生成已停止，不会保存任何数据' : '基于您的学习资料智能构建中'}
          </div>
        </div>
        
        {/* 进度条区域 */}
        <div style={{ 
          marginBottom: 28,
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
            }}>{progressInfo.progress}%</span>
          </div>
          <Progress 
            percent={progressInfo.progress} 
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
        
        {/* 处理详情卡片区域 */}
        {isProcessing && (
          <div style={{ 
            display: 'flex', 
            gap: 16, 
            marginBottom: 28 
          }}>
            {/* 资料数卡片 */}
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
                <FileTextOutlined style={{ fontSize: 20, color: '#fff' }} />
              </div>
              <div style={{ fontSize: 20, fontWeight: 700, color: '#1e293b', marginBottom: 4 }}>
                {progressInfo.current > 0 ? `${progressInfo.current} / ${progressInfo.total || '?'}` : '-'}
              </div>
              <div style={{ fontSize: 12, color: '#94a3b8', fontWeight: 500 }}>已加载资料</div>
            </div>
            
            {/* 分块数卡片 */}
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
                {progressInfo.totalChunks > 0 ? `${progressInfo.chunk} / ${progressInfo.totalChunks}` : (progressInfo.status === 'generating_graph' ? '准备中...' : '-')}
              </div>
              <div style={{ fontSize: 12, color: '#94a3b8', fontWeight: 500 }}>已处理分块</div>
            </div>
            
            {/* 计时器卡片 */}
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
                background: 'linear-gradient(135deg, #f59e0b, #fbbf24)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                margin: '0 auto 12px'
              }}>
                <ClockCircleOutlined style={{ fontSize: 20, color: '#fff' }} />
              </div>
              <div style={{ fontSize: 20, fontWeight: 700, color: '#1e293b', marginBottom: 4, fontFamily: 'monospace' }}>
                {formatTime(elapsedTime)}
              </div>
              <div style={{ fontSize: 12, color: '#94a3b8', fontWeight: 500 }}>已用时间</div>
            </div>
          </div>
        )}
        
        {/* 步骤条 - 水平方向 */}
        <div style={{ 
          marginBottom: 24,
          padding: '20px 24px',
          background: '#fff',
          borderRadius: 14,
          border: '1px solid rgba(226,232,240,0.8)'
        }}>
          <Steps
            current={isError ? -1 : currentStep}
            direction="horizontal"
            size="small"
            items={steps.map((step, index) => ({
              title: <span style={{ fontSize: 13, fontWeight: 600, color: index <= currentStep ? '#6366f1' : '#94a3b8' }}>{step.title}</span>,
              description: <span style={{ fontSize: 11, color: '#94a3b8' }}>{step.description}</span>,
              icon: index < currentStep ? <CheckCircleOutlined style={{ color: '#52c41a' }} /> :
                     index === currentStep && isProcessing ? 
                     <LoadingOutlined style={{ color: '#6366f1' }} spin /> :
                     step.icon
            }))}
          />
        </div>
        
        {/* 当前状态消息区域 */}
        <div style={{ 
          padding: '18px 22px',
          background: isError ? '#fff2f0' : '#f8f9ff',
          borderRadius: 12,
          border: `1px solid ${isError ? '#ffccc7' : 'rgba(99,102,241,0.15)'}`,
          borderLeft: `4px solid ${isError ? '#ff4d4f' : '#6366f1'}`,
          display: 'flex',
          alignItems: 'center',
          gap: 12
        }}>
          {isProcessing && (
            <div style={{
              width: 8,
              height: 8,
              borderRadius: '50%',
              background: '#6366f1',
              animation: 'pulse-dot 1.5s ease-in-out infinite'
            }} />
          )}
          <div style={{ 
            fontSize: 14, 
            color: isError ? '#ff4d4f' : '#374151',
            fontWeight: 500,
            flex: 1
          }}>
            {progressInfo.message || '正在处理...'}
            {isProcessing && (
              <span style={{ 
                display: 'inline-block',
                marginLeft: 4,
                animation: 'dots 1.5s steps(3, end) infinite'
              }}>...</span>
            )}
          </div>
        </div>
        
        {/* 错误信息 */}
        {generationError && (
          <div style={{ 
            marginTop: 16,
            padding: '14px 18px',
            background: '#fff2f0',
            borderRadius: 10,
            border: '1px solid #ffccc7'
          }}>
            <div style={{ fontSize: 13, color: '#ff4d4f', fontWeight: 500 }}>
              <CloseCircleOutlined style={{ marginRight: 8 }} />
              错误: {generationError}
            </div>
          </div>
        )}
        
        {/* 完成时的结果摘要卡片 */}
        {isCompleted && (
          <div style={{ marginTop: 24 }}>
            <div style={{ 
              fontSize: 14, 
              fontWeight: 600, 
              color: '#374151', 
              marginBottom: 16,
              display: 'flex',
              alignItems: 'center',
              gap: 8
            }}>
              <NodeIndexOutlined style={{ color: '#6366f1' }} />
              生成结果摘要
            </div>
            <div style={{ display: 'flex', gap: 16 }}>
              {/* 知识点数量 */}
              <div style={{
                flex: 1,
                padding: '24px 20px',
                background: 'linear-gradient(135deg, rgba(99,102,241,0.08), rgba(139,92,246,0.08))',
                borderRadius: 16,
                border: '1px solid rgba(99,102,241,0.2)',
                textAlign: 'center'
              }}>
                <div style={{
                  width: 48,
                  height: 48,
                  borderRadius: 14,
                  background: 'linear-gradient(135deg, #6366f1, #8b5cf6)',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  margin: '0 auto 14px',
                  boxShadow: '0 4px 16px rgba(99,102,241,0.3)'
                }}>
                  <NodeIndexOutlined style={{ fontSize: 24, color: '#fff' }} />
                </div>
                <div style={{ 
                  fontSize: 36, 
                  fontWeight: 800, 
                  background: 'linear-gradient(135deg, #6366f1, #8b5cf6)',
                  WebkitBackgroundClip: 'text',
                  WebkitTextFillColor: 'transparent',
                  lineHeight: 1,
                  marginBottom: 6
                }}>
                  {progressInfo.totalNodes || 0}
                </div>
                <div style={{ fontSize: 13, color: '#64748b', fontWeight: 500 }}>知识点</div>
              </div>
              
              {/* 关联关系数量 */}
              <div style={{
                flex: 1,
                padding: '24px 20px',
                background: 'linear-gradient(135deg, rgba(139,92,246,0.08), rgba(167,139,250,0.08))',
                borderRadius: 16,
                border: '1px solid rgba(139,92,246,0.2)',
                textAlign: 'center'
              }}>
                <div style={{
                  width: 48,
                  height: 48,
                  borderRadius: 14,
                  background: 'linear-gradient(135deg, #8b5cf6, #a78bfa)',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  margin: '0 auto 14px',
                  boxShadow: '0 4px 16px rgba(139,92,246,0.3)'
                }}>
                  <BranchesOutlined style={{ fontSize: 24, color: '#fff' }} />
                </div>
                <div style={{ 
                  fontSize: 36, 
                  fontWeight: 800, 
                  background: 'linear-gradient(135deg, #8b5cf6, #a78bfa)',
                  WebkitBackgroundClip: 'text',
                  WebkitTextFillColor: 'transparent',
                  lineHeight: 1,
                  marginBottom: 6
                }}>
                  {progressInfo.totalEdges || 0}
                </div>
                <div style={{ fontSize: 13, color: '#64748b', fontWeight: 500 }}>关联关系</div>
              </div>
              
              {/* 使用资料数量 */}
              <div style={{
                flex: 1,
                padding: '24px 20px',
                background: 'linear-gradient(135deg, rgba(245,158,11,0.08), rgba(251,191,36,0.08))',
                borderRadius: 16,
                border: '1px solid rgba(245,158,11,0.2)',
                textAlign: 'center'
              }}>
                <div style={{
                  width: 48,
                  height: 48,
                  borderRadius: 14,
                  background: 'linear-gradient(135deg, #f59e0b, #fbbf24)',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  margin: '0 auto 14px',
                  boxShadow: '0 4px 16px rgba(245,158,11,0.3)'
                }}>
                  <FileTextOutlined style={{ fontSize: 24, color: '#fff' }} />
                </div>
                <div style={{ 
                  fontSize: 36, 
                  fontWeight: 800, 
                  background: 'linear-gradient(135deg, #f59e0b, #fbbf24)',
                  WebkitBackgroundClip: 'text',
                  WebkitTextFillColor: 'transparent',
                  lineHeight: 1,
                  marginBottom: 6
                }}>
                  {progressInfo.total || 0}
                </div>
                <div style={{ fontSize: 13, color: '#64748b', fontWeight: 500 }}>使用资料</div>
              </div>
            </div>
          </div>
        )}
      </Modal>
    )
  }

  if (loading) {
    return (
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: '60vh', flexDirection: 'column', gap: 16 }}>
        <Spin size="large" />
        <span style={{ color: '#94a3b8', fontSize: 14 }}>正在加载知识图谱...</span>
      </div>
    )
  }

  return (
    <motion.div initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.4 }}>
      {/* Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 20 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
          <div style={{ 
            width: 44, height: 44, borderRadius: 12, 
            background: 'linear-gradient(135deg,#6366f1,#8b5cf6)', 
            display: 'flex', alignItems: 'center', justifyContent: 'center', 
            boxShadow: '0 4px 12px rgba(99,102,241,0.35)'
          }}>
            <ApartmentOutlined style={{ color: '#fff', fontSize: 20 }} />
          </div>
          <div>
            <h2 style={{ margin: 0, fontSize: 20, fontWeight: 800, color: '#0f172a' }}>知识图谱</h2>
            {graphData && <div style={{ fontSize: 13, color: '#94a3b8' }}>共 {graphData.total_nodes} 个知识点</div>}
          </div>
        </div>
        <div style={{ display: 'flex', gap: 10 }}>
          <Button icon={<ReloadOutlined />} onClick={fetchGraphData} style={{ borderRadius: 8 }}>
            刷新
          </Button>
          {hasGraph && (
            <Button 
              type="primary" 
              icon={<PlayCircleOutlined />} 
              onClick={() => setShowAssessment(true)} 
              style={{ 
                borderRadius: 8,
                background: 'linear-gradient(135deg,#6366f1,#8b5cf6)',
                border: 'none'
              }}
            >
              重新测评
            </Button>
          )}
        </div>
      </div>

      {/* 空状态 */}
      {!hasGraph && renderEmptyState()}

      {/* 有图谱时显示内容 */}
      {hasGraph && graphData && (
        <>
          {/* 掌握度等级图例 */}
          <div style={{ 
            display: 'flex', 
            gap: 12, 
            marginBottom: 20, 
            flexWrap: 'wrap',
            padding: '16px 20px',
            background: '#fff',
            borderRadius: 16,
            border: '1px solid rgba(226,232,240,0.8)'
          }}>
            {MASTERY_LEVELS.map(cfg => (
              <Tooltip key={cfg.key} title={cfg.description} placement="bottom">
                <div style={{ 
                  display: 'flex', alignItems: 'center', gap: 8, 
                  padding: '8px 14px', 
                  borderRadius: 99, 
                  background: '#f8fafc',
                  border: `1px solid ${cfg.borderColor}30`,
                  cursor: 'pointer',
                  transition: 'all 0.2s ease'
                }}>
                  <div style={{ 
                    width: 12, height: 12, borderRadius: '50%', 
                    background: cfg.gradient,
                    boxShadow: `0 0 8px ${cfg.color}50`
                  }} />
                  <span style={{ fontSize: 12.5, fontWeight: 600, color: '#374151' }}>{cfg.label}</span>
                  <span style={{ fontSize: 11, color: '#94a3b8' }}>{cfg.range}</span>
                </div>
              </Tooltip>
            ))}
          </div>

          {/* 统计卡片 */}
          {graphData.mastery_stats && (
            <div style={{ display: 'flex', gap: 16, marginBottom: 20 }}>
              <StatCard 
                label="精通" 
                value={graphData.mastery_stats.mastered || 0} 
                gradient="linear-gradient(135deg,#52c41a,#73d13d)"
                icon={<CrownOutlined />}
                color="#52c41a"
              />
              <StatCard 
                label="熟练" 
                value={graphData.mastery_stats.proficient || 0} 
                gradient="linear-gradient(135deg,#fa8c16,#ffc53d)"
                icon={<FireOutlined />}
                color="#fa8c16"
              />
              <StatCard 
                label="理解" 
                value={graphData.mastery_stats.understanding || 0} 
                gradient="linear-gradient(135deg,#fadb14,#ffe58f)"
                icon={<BulbOutlined />}
                color="#fadb14"
              />
              <StatCard 
                label="发展中" 
                value={(graphData.mastery_stats.developing || 0) + (graphData.mastery_stats.learning || 0) + (graphData.mastery_stats.sprouting || 0)} 
                gradient="linear-gradient(135deg,#1890ff,#69c0ff)"
                icon={<RocketOutlined />}
                color="#1890ff"
              />
            </div>
          )}

          {/* 图表 */}
          <div style={{ 
            borderRadius: 20, 
            overflow: 'hidden', 
            background: '#fff', 
            border: '1px solid rgba(226,232,240,0.8)', 
            boxShadow: '0 4px 24px rgba(99,102,241,0.07)', 
            padding: '12px' 
          }}>
            <ReactECharts 
              option={getChartOption()} 
              style={{ height: 580 }} 
              opts={{ renderer: 'canvas' }} 
              onEvents={{ click: handleNodeClick }} 
            />
          </div>

          <div style={{ marginTop: 14, textAlign: 'center' }}>
            <span style={{ fontSize: 12, color: '#94a3b8' }}>
              <InfoCircleOutlined style={{ marginRight: 6 }} />
              点击节点查看详情，滚轮缩放，拖拽调整布局
            </span>
          </div>
        </>
      )}

      {renderAssessmentModal()}
      {renderNodeDrawer()}
      {renderProgressModal()}
    </motion.div>
  )
}

export default KnowledgeGraph
