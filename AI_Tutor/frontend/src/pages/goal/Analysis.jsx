import { useState, useEffect } from 'react'
import { Spin, message, Empty } from 'antd'
import {
  CheckCircleOutlined,
  RiseOutlined,
  WarningOutlined,
  TrophyOutlined,
  FireOutlined,
} from '@ant-design/icons'
import ReactECharts from 'echarts-for-react'
import { useParams } from 'react-router-dom'
import { motion } from 'framer-motion'
import { analysisAPI } from '../../utils/api'

// 掌握度标签映射
const MASTERY_LABELS = { excellent: '优秀', good: '良好', average: '一般', poor: '较差', weak: '薄弱' }

// 掌握度标签颜色映射
const MASTERY_COLORS = {
  excellent: { bg: 'rgba(16,185,129,0.1)', text: '#10b981' },
  good: { bg: 'rgba(6,182,212,0.1)', text: '#06b6d4' },
  average: { bg: 'rgba(245,158,11,0.1)', text: '#f59e0b' },
  poor: { bg: 'rgba(251,146,60,0.1)', text: '#fb923c' },
  weak: { bg: 'rgba(244,63,94,0.1)', text: '#f43f5e' },
}

// 根据掌握度获取标签
const getMasteryLabel = (level) => {
  if (level >= 80) return 'excellent'
  if (level >= 60) return 'good'
  if (level >= 40) return 'average'
  if (level >= 20) return 'poor'
  return 'weak'
}

function StatCard({ icon, title, value, suffix, gradient, delay = 0, subText }) {
  return (
    <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.45, delay }}
      whileHover={{ y: -3 }}
      style={{ borderRadius: 18, padding: '24px', background: '#fff', border: '1px solid rgba(226,232,240,0.8)', boxShadow: '0 4px 20px rgba(99,102,241,0.07)', position: 'relative', overflow: 'hidden' }}>
      <div style={{ position: 'absolute', bottom: 0, left: 0, right: 0, height: 3, background: gradient }} />
      <div style={{ width: 42, height: 42, borderRadius: 11, background: gradient, display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 18, color: '#fff', marginBottom: 16, boxShadow: '0 4px 12px rgba(99,102,241,0.28)' }}>
        {icon}
      </div>
      <div style={{ fontSize: 12, color: '#94a3b8', fontWeight: 600, letterSpacing: 0.5, marginBottom: 4 }}>{title}</div>
      <div style={{ display: 'flex', alignItems: 'baseline', gap: 4 }}>
        <span style={{ fontSize: 32, fontWeight: 800, background: gradient, WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent', lineHeight: 1 }}>{value}</span>
        {suffix && <span style={{ fontSize: 16, fontWeight: 700, color: '#94a3b8' }}>{suffix}</span>}
      </div>
      {subText && <div style={{ marginTop: 6, fontSize: 11, color: '#94a3b8' }}>{subText}</div>}
    </motion.div>
  )
}

function Analysis() {
  const { goalId } = useParams()
  const [loading, setLoading]       = useState(true)
  const [overview, setOverview]     = useState(null)
  const [trends, setTrends]         = useState([])
  const [weakPoints, setWeakPoints] = useState([])

  useEffect(() => { fetchAnalysisData() }, [goalId])

  // 监听答题完成后的学情刷新事件
  useEffect(() => {
    const handleRefresh = (e) => {
      // 如果刷新事件的 goalId 与当前页面一致，刷新数据
      if (!e.detail?.goalId || e.detail.goalId === parseInt(goalId)) {
        fetchAnalysisData()
      }
    }
    window.addEventListener('refresh-analysis', handleRefresh)
    return () => window.removeEventListener('refresh-analysis', handleRefresh)
  }, [goalId])

  const fetchAnalysisData = async () => {
    setLoading(true)
    try {
      const [ovRes, trRes, wpRes] = await Promise.all([
        analysisAPI.getOverview(goalId),
        analysisAPI.getTrends(goalId, 30),
        analysisAPI.getWeakPoints(goalId, 10),
      ])
      // axios 返回的是完整 response 对象，后端数据在 response.data 中
      // 业务数据在 response.data.data 中
      if (ovRes.data?.success) setOverview(ovRes.data.data)
      if (trRes.data?.success) setTrends(trRes.data.data?.trends || [])
      if (wpRes.data?.success) setWeakPoints(wpRes.data.data?.weak_points || [])
    } catch { message.error('获取学情分析失败') }
    finally { setLoading(false) }
  }

  const getTrendOption = () => ({
    backgroundColor: 'transparent',
    tooltip: { trigger: 'axis', backgroundColor: 'rgba(15,23,42,0.9)', borderColor: 'rgba(99,102,241,0.3)', borderRadius: 10, textStyle: { color: '#fff', fontSize: 13 } },
    xAxis: { type: 'category', data: trends.map(t => t.date), axisLabel: { rotate: 40, fontSize: 11, color: '#94a3b8' }, axisLine: { lineStyle: { color: '#e2e8f0' } } },
    yAxis: { type: 'value', name: '掌握度(%)', max: 100, nameTextStyle: { color: '#94a3b8', fontSize: 12 }, axisLabel: { color: '#94a3b8', fontSize: 11 }, splitLine: { lineStyle: { color: '#f1f5f9' } } },
    series: [{
      data: trends.map(t => t.mastery || 0),
      type: 'line', smooth: true,
      lineStyle: { color: '#6366f1', width: 3 },
      itemStyle: { color: '#6366f1', borderWidth: 2 },
      areaStyle: { color: { type: 'linear', x: 0, y: 0, x2: 0, y2: 1, colorStops: [{ offset: 0, color: 'rgba(99,102,241,0.25)' }, { offset: 1, color: 'rgba(99,102,241,0.02)' }] } },
      symbol: 'circle', symbolSize: 7,
    }],
    grid: { left: '4%', right: '4%', bottom: '18%', containLabel: true },
  })

  if (loading) {
    return (
      <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '50vh', gap: 16 }}>
        <Spin size="large" />
        <span style={{ color: '#94a3b8' }}>加载学情分析...</span>
      </div>
    )
  }

  return (
    <motion.div initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.4 }}>
      {/* Page header */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 24 }}>
        <div style={{ width: 40, height: 40, borderRadius: 10, background: 'linear-gradient(135deg,#6366f1,#8b5cf6)', display: 'flex', alignItems: 'center', justifyContent: 'center', boxShadow: '0 4px 12px rgba(99,102,241,0.35)' }}>
          <RiseOutlined style={{ color: '#fff', fontSize: 18 }} />
        </div>
        <h2 style={{ margin: 0, fontSize: 20, fontWeight: 800, color: '#0f172a' }}>学情分析</h2>
      </div>

      {/* Stats row - 4 cards */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4,1fr)', gap: 16, marginBottom: 24 }}>
        <StatCard 
          icon={<TrophyOutlined />}       
          title="总体掌握度"   
          value={overview?.overall_mastery || 0}                                             
          suffix="%" 
          gradient="linear-gradient(135deg,#6366f1,#8b5cf6)" 
          delay={0} 
          subText="所有知识点平均掌握水平"
        />
        <StatCard 
          icon={<CheckCircleOutlined />}  
          title="已掌握知识点" 
          value={`${overview?.mastered_knowledge_points?.mastered || 0}/${overview?.mastered_knowledge_points?.total || 0}`} 
          gradient="linear-gradient(135deg,#06b6d4,#10b981)" 
          delay={0.08} 
        />
        <StatCard 
          icon={<RiseOutlined />}         
          title="学习进度"     
          value={overview?.learning_progress?.description || '未开始'}                                         
          gradient="linear-gradient(135deg,#8b5cf6,#ec4899)" 
          delay={0.16} 
        />
        <StatCard 
          icon={<FireOutlined />}         
          title="练习正确率"   
          value={overview?.practice_accuracy?.rate || 0}                    
          suffix="%" 
          gradient="linear-gradient(135deg,#f59e0b,#fb923c)" 
          delay={0.24} 
        />
      </div>

      {/* Charts row - 学习趋势 */}
      <div style={{ marginBottom: 24 }}>
        <div style={{ borderRadius: 20, padding: '20px 16px', background: '#fff', border: '1px solid rgba(226,232,240,0.8)', boxShadow: '0 4px 20px rgba(99,102,241,0.06)' }}>
          <h3 style={{ margin: '0 0 16px 8px', fontSize: 15, fontWeight: 700, color: '#0f172a' }}>学习趋势（30天）</h3>
          <ReactECharts option={getTrendOption()} style={{ height: 300 }} />
        </div>
      </div>

      {/* Bottom row - 薄弱知识点 */}
      <div style={{ borderRadius: 20, padding: 24, background: '#fff', border: '1px solid rgba(226,232,240,0.8)', boxShadow: '0 4px 20px rgba(99,102,241,0.06)' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 20 }}>
          <WarningOutlined style={{ color: '#f43f5e', fontSize: 16 }} />
          <h3 style={{ margin: 0, fontSize: 15, fontWeight: 700, color: '#0f172a' }}>薄弱知识点</h3>
        </div>
        {weakPoints.length === 0 ? (
          <Empty description="暂无薄弱知识点，继续保持！" />
        ) : (
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(300px, 1fr))', gap: 16 }}>
            {weakPoints.map((item, i) => {
              // 使用后端返回的 mastery_label 或根据 mastery_level 计算
              const labelKey = item.mastery_label === '薄弱' ? 'weak' : 
                               item.mastery_label === '较差' ? 'poor' : 
                               item.mastery_label === '一般' ? 'average' :
                               getMasteryLabel(item.mastery_level)
              const colors = MASTERY_COLORS[labelKey] || MASTERY_COLORS.weak
              
              return (
                <div key={i} style={{ 
                  padding: 16, 
                  borderRadius: 12, 
                  background: '#f8fafc', 
                  border: '1px solid #e2e8f0' 
                }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 10 }}>
                    <span style={{ fontSize: 14, fontWeight: 600, color: '#374151' }}>{item.node_name}</span>
                    <span style={{ 
                      padding: '3px 10px', 
                      borderRadius: 99, 
                      background: colors.bg, 
                      color: colors.text, 
                      fontSize: 12, 
                      fontWeight: 700 
                    }}>
                      {item.mastery_label || MASTERY_LABELS[labelKey]}
                    </span>
                  </div>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 6 }}>
                    <span style={{ fontSize: 12, color: '#94a3b8' }}>掌握度</span>
                    <span style={{ fontSize: 14, fontWeight: 700, color: colors.text }}>{item.mastery_level}%</span>
                  </div>
                  <div style={{ height: 6, background: '#e2e8f0', borderRadius: 3, overflow: 'hidden' }}>
                    <div style={{ 
                      width: `${item.mastery_level}%`, 
                      height: '100%', 
                      background: colors.text, 
                      borderRadius: 3 
                    }} />
                  </div>
                  <div style={{ marginTop: 8, fontSize: 11, color: '#94a3b8' }}>
                    答题 {item.total_attempts} 次，正确 {item.correct_attempts} 次
                  </div>
                </div>
              )
            })}
          </div>
        )}
      </div>
    </motion.div>
  )
}

export default Analysis
